import scrapy


class PokemonScrapper(scrapy.Spider):
    name = 'pokemon_scrapper'
    domain = "https://pokemondb.net"

    start_urls = ["https://pokemondb.net/pokedex/all"]

    def parse(self, response):
        pokemons = response.css('#pokedex > tbody > tr')
        # for pokemon in pokemons:
        pokemon = pokemons[0]
        link = pokemon.css("td.cell-name > a::attr(href)").extract_first()
        yield response.follow(self.domain + link, self.parse_pokemon)

    def parse_pokemon(self, response):
        prefix_domain = "https://pokemondb.net"

        # TODO: remover os links das evoluções que sejam o pokemon atual
        links_evolucoes = []
        lista_evolucoes = response.css('.infocard-list-evo > div')
        for evolucao in lista_evolucoes:
            links_evolucoes.append(prefix_domain + evolucao.css(".infocard-lg-img > a::attr(href)").get())

        links_evolucoes.pop(0)

        yield {
            'pokemon_id': response.css('.vitals-table > tbody > tr:nth-child(1) > td > strong::text').get(),
            'pokemon_url': response.css('link[rel="canonical"]::attr(href)').get(),
            'pokemon_name': response.css('#main > h1::text').get(),
            'next_evolutions': [x for x in self.parse_evolution(links_evolucoes, response)]
            # 'next_evolution': response.css(
            #     '#main > div.infocard-list-evo > div:nth-child(3) > span.infocard-lg-data.text-muted > a::text').get()
        }

    def parse_evolution(self, links_evolucoes, response):
        yield from response.follow_all(links_evolucoes, self.evolution_data)

    def evolution_data(self, response):
        yield {
            'pokemon_id': response.css('.vitals-table > tbody > tr:nth-child(1) > td > strong::text').get(),
            'pokemon_url': response.css('link[rel="canonical"]::attr(href)').get(),
            'pokemon_name': response.css('#main > h1::text').get()
        }
