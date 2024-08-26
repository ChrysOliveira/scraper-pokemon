import scrapy
from scrapy.http import Request


class PokemonScrapper(scrapy.Spider):
    name = 'pokemon_scrapper'
    domain = "https://pokemondb.net"
    start_urls = ["https://pokemondb.net/pokedex/all"]

    def parse(self, response):
        pokemons = response.css('#pokedex > tbody > tr')
        for pokemon in pokemons:
        # pokemon = pokemons[0]
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

        poke_tipos = []
        lista_tipos = response.css('.vitals-table > tbody > tr:nth-child(2) > td > a')
        for tipo in lista_tipos:
            poke_tipos.append(tipo.css('::text').get())

        # print(f"AAAAAAAAAAAAAAAAAAAAAAAAAA{poke_tipos}")

        if links_evolucoes:
            request = Request(links_evolucoes[0], callback=self.evolution_data, dont_filter=True)
            request.meta['pokemon_dados'] = self.getting_data(response, poke_tipos)
            request.meta['links_evolucoes_pendentes'] = links_evolucoes[1:]
            yield request
        else:
            yield self.getting_data(response, poke_tipos)

    def getting_data(self, response, poke_tipos):
        return {
            'pokemon_id': response.css('.vitals-table > tbody > tr:nth-child(1) > td > strong::text').get(),
            'pokemon_url': response.css('link[rel="canonical"]::attr(href)').get(),
            'pokemon_name': response.css('#main > h1::text').get(),
            'next_evolutions': [],
            'pokemon_size': str((float(response.css('.vitals-table > tbody > tr:nth-child(4) > td::text').get().split(" ", 1)[0]) * 100)) + ' cm',
            'pokemon_weight': response.css('.vitals-table > tbody > tr:nth-child(5) > td::text').get().split(" ", 1)[0] + ' kg',
            'pokemon_types': poke_tipos
        }
    def evolution_data(self, response):
        pokemon_dados = response.meta['pokemon_dados']
        links_evolucoes_pendentes = response.meta['links_evolucoes_pendentes']

        evolution_info = {
            'pokemon_id': response.css('.vitals-table > tbody > tr:nth-child(1) > td > strong::text').get(),
            'pokemon_url': response.css('link[rel="canonical"]::attr(href)').get(),
            'pokemon_name': response.css('#main > h1::text').get()
        }
        pokemon_dados['next_evolutions'].append(evolution_info)

        if links_evolucoes_pendentes:
            next_request = Request(links_evolucoes_pendentes[0], callback=self.evolution_data, dont_filter=True)
            next_request.meta['pokemon_dados'] = pokemon_dados
            next_request.meta['links_evolucoes_pendentes'] = links_evolucoes_pendentes[1:]
            yield next_request
        else:
            yield pokemon_dados