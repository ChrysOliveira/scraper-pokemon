
# Para executar o Scrapy, é necessário criar um script com o seguinte texto:
# scrapy runspider pokemon_scraper.py -O pokemons.json:json

import scrapy
from scrapy.http import Request
from scrapy import signals
import pandas as pd
import json
from neo4j_connection import Neo4jConnection, consultar
from neo4j_connection import CriarAmizades

class PokemonScrapper(scrapy.Spider):
    name = 'pokemon_scrapper'
    domain = "https://pokemondb.net"
    start_urls = ["https://pokemondb.net/pokedex/all"]

    def parse(self, response):
        pokemons = response.css('#pokedex > tbody > tr')
        for pokemon in pokemons:
            # pokemon = pokemons[pokemon]
            link = pokemon.css("td.cell-name > a::attr(href)").extract_first()
            yield response.follow(self.domain + link, self.parse_pokemon, dont_filter=True)

    def parse_pokemon(self, response):
        prefix_domain = "https://pokemondb.net"
        atual_pokemon_url = response.css('link[rel="canonical"]::attr(href)').get()

        links_evolucoes = []
        lista_evolucoes = response.css('.infocard-list-evo > div')
        for evolucao in lista_evolucoes:
            links_evolucoes.append(prefix_domain + evolucao.css(".infocard-lg-img > a::attr(href)").get())

        if atual_pokemon_url in links_evolucoes:
            links_evolucoes.remove(atual_pokemon_url)

        table_path = ".sv-tabs-panel.active > div:nth-child(1) > div:nth-child(2) > table > tbody"

        poke_tipos = []
        lista_tipos = response.css(f"{table_path} > tr:nth-child(2) > td > a")
        for tipo in lista_tipos:
            poke_tipos.append(tipo.css('::text').get())

        links_habilidades = []
        lista_habilidades = response.css(f"{table_path} > tr:nth-child(6) > td .text-muted")
        for habilidade in lista_habilidades:
            links_habilidades.append(prefix_domain + habilidade.css("a::attr(href)").get())

        habilidades = Request(links_habilidades[0], callback=self.ability_data, dont_filter=True)
        habilidades.meta['links_habilidades_pendentes'] = links_habilidades[1:]
        habilidades.meta['lista'] = []
        habilidades.meta['links_evolucoes'] = links_evolucoes
        habilidades.meta['dados_principal'] = response
        habilidades.meta['poke_tipos'] = poke_tipos
        habilidades.meta['table_path'] = table_path
        yield habilidades

    def ability_data(self, response):
        links_habilidades_pendentes = response.meta['links_habilidades_pendentes']
        links_evolucoes = response.meta['links_evolucoes']

        ability_info = {
            'ability_name': str(response.css('main > h1::text').get()).strip(),
            'ability_desc': response.css(
                'main > div > div > div > .vitals-table > tbody > tr:nth-Child(1) > td::text').get(),
            'ability_url': response.css('link[rel="canonical"]::attr(href)').get()
        }

        response.meta['lista'].append(ability_info)

        if links_habilidades_pendentes:
            next_request = Request(links_habilidades_pendentes[0], callback=self.ability_data, dont_filter=True)
            next_request.meta['links_habilidades_pendentes'] = links_habilidades_pendentes[1:]
            next_request.meta['lista'] = response.meta['lista']
            next_request.meta['links_evolucoes'] = response.meta['links_evolucoes']
            next_request.meta['dados_principal'] = response.meta['dados_principal']
            next_request.meta['poke_tipos'] = response.meta['poke_tipos']
            next_request.meta['table_path'] = response.meta['table_path']
            yield next_request

        else:
            if links_evolucoes:
                request_evo = Request(links_evolucoes[0], callback=self.evolution_data, dont_filter=True)
                request_evo.meta['pokemon_dados'] = self.getting_data(response.meta['dados_principal'],
                                                                      response.meta['poke_tipos'],
                                                                      response.meta['table_path'],
                                                                      response.meta['lista'])
                request_evo.meta['links_evolucoes_pendentes'] = links_evolucoes[1:]
                yield request_evo
            else:
                yield self.getting_data(response.meta['dados_principal'],
                                        response.meta['poke_tipos'],
                                        response.meta['table_path'],
                                        response.meta['lista'])

    def evolution_data(self, response):
        pokemon_dados = response.meta['pokemon_dados']
        links_evolucoes_pendentes = response.meta['links_evolucoes_pendentes']

        evolution_info = {
            'evo_pokemon_id': response.css('.vitals-table > tbody > tr:nth-child(1) > td > strong::text').get(),
            'evo_pokemon_name': response.css('#main > h1::text').get(),
            'evo_pokemon_url': response.css('link[rel="canonical"]::attr(href)').get()
        }

        if evolution_info['evo_pokemon_id'] > pokemon_dados['pokemon_id']:
            if evolution_info not in pokemon_dados['next_evolutions']:
                pokemon_dados['next_evolutions'].append(evolution_info)

        if links_evolucoes_pendentes:
            next_request = Request(links_evolucoes_pendentes[0], callback=self.evolution_data, dont_filter=True)
            next_request.meta['pokemon_dados'] = pokemon_dados
            next_request.meta['links_evolucoes_pendentes'] = links_evolucoes_pendentes[1:]
            yield next_request
        else:
            yield pokemon_dados

    def getting_data(self, response, poke_tipos, table_path, habilidades):
        return {
            'pokemon_id': response.css(f'{table_path} > tr:nth-child(1) > td > strong::text').get(),
            'pokemon_name': response.css('#main > h1::text').get(),
            'pokemon_types': poke_tipos,
            'pokemon_size': str(round((float(response.css(
                f'{table_path} > tr:nth-child(4) > td::text').get().split(" ", 1)[0]) * 100), 2)) + ' cm',
            'pokemon_weight': response.css(
                f'{table_path} > tr:nth-child(5) > td::text').get().split(" ", 1)[0] + ' kg',
            'pokemon_url': response.css('link[rel="canonical"]::attr(href)').get(),
            'pokemon_abilities': habilidades,
            'next_evolutions': []
        }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(PokemonScrapper, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.feed_exporter_closed, signal=signals.feed_exporter_closed)
        return spider

    def feed_exporter_closed(self):
        file_path = "pokemons.json"

        with open(file_path) as file:
            data = json.load(file)

        df = pd.json_normalize(data, max_level=1)
        df.drop_duplicates(subset=['pokemon_id'], inplace=True)
        df.sort_values(by=['pokemon_id'], inplace=True)
        df.set_index('pokemon_id', inplace=True)
        df.rename(columns={"pokemon_name": "Nome", "pokemon_types": "Tipos",
                           "pokemon_size": "Tamanho", "pokemon_weight": "Peso", "pokemon_url": "URL",
                           "pokemon_abilities": "Habilidades", "next_evolutions": "Evolucoes"}, inplace=True)
        df.rename_axis("ID", inplace=True)
        print(df)
        df.to_json('pokemons_tratados.json')
        df.to_html('pokemons_tratados.html')

        with open('pokemons_tratados.json') as file:
            data_converted = json.load(file)

        data_to_neo4j = ''
        type_set = set()
        ability_set = set()

        conexoes = CriarAmizades()
        conexoes.zera_base()

        for i in data_converted["Nome"]:
            nome = data_converted["Nome"][i]

            if "♀" in nome:
                nome = nome.replace("♀ (female)", "_fem")
            elif "♂" in nome:
                nome = nome.replace("♂ (male)", "_masc")
            elif "'" in nome:
                nome = nome.replace("'", "_")
            elif "." in nome:
                nome = nome.replace(".", "")
            elif "-" in nome:
                nome = nome.replace("-", "_")
            elif "Type: Null" == nome:
                nome = "Tipo_Nulo"

            if " " in nome:
                nome = nome.replace(" ", "_")

            data_to_neo4j = f""" 
            CREATE ({nome}:POKEMON {{id: "{i}", nome: "{data_converted["Nome"][i]}", peso: "{data_converted["Peso"][i]}", 
                    tamanho: "{data_converted["Tamanho"][i]}", url: "{data_converted["URL"][i]}"}})"""

            for tipo in data_converted["Tipos"][i]:
                if tipo in type_set:
                    data_to_neo4j += f"""
                    CREATE ({nome})-[:TEM_TIPO]->({tipo})
                    """
                else:
                    type_set.add(tipo)
                    #criando os nos dos tipos e suas relacoes com os pokemons
                    data_to_neo4j += f"""
                    CREATE ({tipo}:TIPO {{nome: "{tipo}"}})
                    CREATE ({nome})-[:TEM_TIPO]->({tipo})
                    """

            for habilidade in data_converted["Habilidades"][i]:
                ability_name = habilidade["ability_name"]

                if " " in ability_name:
                    ability_name = ability_name.replace(" ", "_")

                if "-" in ability_name:
                    ability_name = ability_name.replace("-", "_")

                if "'" in ability_name:
                    ability_name = ability_name.replace("'", "_")

                if ability_name in ability_set:
                    #criando os nos das habilidades e suas relacoes com os pokemons
                    data_to_neo4j += f""" 
                    CREATE ({nome})-[:TEM_HABILIDADE]->({ability_name})"""
                else:
                    ability_set.add(ability_name)
                    data_to_neo4j += f"""
                    CREATE ({ability_name}:HABILIDADE {{nome: "{habilidade["ability_name"]}",
                    descricao: "{habilidade["ability_desc"]}", url: "{habilidade["ability_url"]}"}}) 
                    CREATE ({nome})-[:TEM_HABILIDADE]->({ability_name})
                    """

            conexoes.carrega_base(query=data_to_neo4j)

        for i in data_converted["Evolucoes"]:
            nome = data_converted["Nome"][i]

            if "♀" in nome:
                nome = nome.replace("♀ (female)", "_fem")
            elif "♂" in nome:
                nome = nome.replace("♂ (male)", "_masc")
            elif "'" in nome:
                nome = nome.replace("'", "_")
            elif "." in nome:
                nome = nome.replace(".", "")
            elif "-" in nome:
                nome = nome.replace("-", "_")
            elif "Type: Null" == nome:
                nome = "Tipo_Nulo"

            if " " in nome:
                nome = nome.replace(" ", "_")

            for evolucao in data_converted["Evolucoes"][i]:
                evo_tratado = evolucao["evo_pokemon_name"]

                if "♀" in evo_tratado:
                    evo_tratado = evo_tratado.replace("♀ (female)", "_fem")
                elif "♂" in evo_tratado:
                    evo_tratado = evo_tratado.replace("♂ (male)", "_masc")
                elif "'" in evo_tratado:
                    evo_tratado = evo_tratado.replace("'", "_")
                elif "." in evo_tratado:
                    evo_tratado = evo_tratado.replace(".", "")
                elif "-" in evo_tratado:
                    evo_tratado = evo_tratado.replace("-", "_")

                if " " in evo_tratado:
                    evo_tratado = evo_tratado.replace(" ", "_")

                data_to_neo4j = f"""
            CREATE ({nome})-[:EVOLUI_PARA]->({evo_tratado})"""

                conexoes.carrega_base(query=data_to_neo4j)

        conexoes.close()
        consulta1 = consultar("""
        MATCH (pokemon:POKEMON)-[:TEM_TIPO]->(tipoPokemon:TIPO)
        WITH pokemon.nome AS nome
        WHERE tipoPokemon = "Ground" AND toFloat(replace(pokemon.peso, ' kg', '')) > 10
        RETURN nome""")
        print(consulta1)
        consulta2 = consultar("""
        MATCH (pokemon:POKEMON)-[:EVOLUI_PARA]-(evolucao:POKEMON)
        WHERE toFloat(replace(evolucao.peso, ' kg', '')) > toFloat(replace(pokemon.peso, ' kg', '')) * 2 
        RETURN count(evolucao) as qtdEvolucoes
        """)
        print(consulta2)

        #print(data_to_neo4j)

