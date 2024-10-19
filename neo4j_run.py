from neo4j_connection import Neo4jConnection, consultar
from neo4j_connection import CriarAmizades
import json


def string_treatment(value):
    if "♀" in value:
        value = value.replace("♀ (female)", "_fem")
    elif "♂" in value:
        value = value.replace("♂ (male)", "_masc")
    elif "'" in value:
        value = value.replace("'", "_")
    elif "." in value:
        value = value.replace(".", "")
    elif "-" in value:
        value = value.replace("-", "_")

    if " " in value:
        value = value.replace(" ", "_")

    return value

def populando_banco():
    connections.zera_base()

    for i in data_converted["Nome"]:
        nome = data_converted["Nome"][i]

        nome = string_treatment(nome)

        print(nome)

        data_to_neo4j = f"""
                CREATE ({nome}:POKEMON {{id: "{i}", nome: "{data_converted["Nome"][i]}", peso: "{data_converted["Peso"][i]}",
                        tamanho: "{data_converted["Tamanho"][i]}", url: "{data_converted["URL"][i]}"}})"""

        print(data_to_neo4j)
        connections.carrega_base(query=data_to_neo4j)

        for tipo in data_converted["Tipos"][i]:
            if tipo in type_set:
                data_to_neo4j = f"""
                        MATCH ({nome}:POKEMON {{nome: "{data_converted["Nome"][i]}"}})
                        OPTIONAL MATCH({tipo}:TIPO {{nome: "{tipo}"}})
                        MERGE ({nome})-[:TEM_TIPO]->({tipo})
                        """
            else:
                type_set.add(tipo)
                # criando os nos dos tipos e suas relacoes com os pokemons
                data_to_neo4j = f"""
                        MERGE ({tipo}:TIPO {{nome: "{tipo}"}})
                        WITH {tipo}
                        MATCH ({nome}:POKEMON {{nome: "{data_converted["Nome"][i]}"}})
                        OPTIONAL MATCH({tipo}:TIPO {{nome: "{tipo}"}})
                        MERGE ({nome})-[:TEM_TIPO]->({tipo})
                        """

            print(data_to_neo4j)
            connections.carrega_base(query=data_to_neo4j)

        for habilidade in data_converted["Habilidades"][i]:
            ability_name = habilidade["ability_name"]

            if " " in ability_name:
                ability_name = ability_name.replace(" ", "_")

            if "-" in ability_name:
                ability_name = ability_name.replace("-", "_")

            if "'" in ability_name:
                ability_name = ability_name.replace("'", "_")

            if ability_name in ability_set:
                # criando os nos das habilidades e suas relacoes com os pokemons
                data_to_neo4j = f"""
                        MATCH ({nome}:POKEMON {{nome: "{data_converted["Nome"][i]}"}})
                        OPTIONAL MATCH ({ability_name}:HABILIDADE {{nome: "{habilidade["ability_name"]}"}})
                        WITH {nome}, {ability_name}
                        MERGE ({nome})-[:TEM_HABILIDADE]->({ability_name})"""
            else:
                ability_set.add(ability_name)
                data_to_neo4j = f"""
                        MERGE ({ability_name}:HABILIDADE {{nome: "{habilidade["ability_name"]}",
                        descricao: "{habilidade["ability_desc"]}", url: "{habilidade["ability_url"]}"}})
                        WITH {ability_name}
                        MATCH ({nome}:POKEMON {{nome: "{data_converted["Nome"][i]}"}})
                        OPTIONAL MATCH ({ability_name}:HABILIDADE {{nome: "{habilidade["ability_name"]}"}})
                        MERGE ({nome})-[:TEM_HABILIDADE]->({ability_name})
                        """

            print(data_to_neo4j)
            connections.carrega_base(query=data_to_neo4j)

    print("\n\n========================EVOLUCAO===================\n\n")
    for i in data_converted["Evolucoes"]:
        nome = data_converted["Nome"][i]

        nome = string_treatment(nome)

        for evolucao in data_converted["Evolucoes"][i]:
            evo_tratado = evolucao["evo_pokemon_name"]

            evo_tratado = string_treatment(evo_tratado)

            data_to_neo4j = f"""
                    MATCH ({nome} {{nome: "{data_converted["Nome"][i]}"}})
                    OPTIONAL MATCH ({evo_tratado} {{nome: "{evolucao["evo_pokemon_name"]}"}})
                    MERGE ({nome})-[:EVOLUI_PARA]->({evo_tratado})"""

            print(f"{nome} -> {evo_tratado}")
            print(data_to_neo4j)
            connections.carrega_base(query=data_to_neo4j)

    connections.close()


if __name__ == '__main__':

    with open('pokemons_tratados.json') as file:
        data_converted = json.load(file)

    print("Hello World")

    data_to_neo4j = ''
    type_set = set()
    ability_set = set()

    connections = CriarAmizades()

    #verifica se o banco esta vazio
    consulta_banco = consultar("""MATCH (n)
RETURN COUNT(n) AS totalNos""")

    if consulta_banco[0]["totalNos"] == 0:
        populando_banco()
    else:
        consulta1 = consultar("""
        MATCH (pokemon:POKEMON)-[:TEM_TIPO]->(tipo:TIPO)
        WHERE tipo.nome = "Ground" AND toFloat(replace(pokemon.peso, ' kg', '')) >= 10
        RETURN pokemon.nome AS nome""")
        print(consulta1)
        consulta2 = consultar("""
        MATCH (pokemon:POKEMON)-[:EVOLUI_PARA]-(evolucao:POKEMON)
        WHERE toFloat(replace(evolucao.peso, ' kg', '')) > toFloat(replace(pokemon.peso, ' kg', '')) * 2
        RETURN count(DISTINCT evolucao.nome) AS qtdEvolucoes
        """)
        print(consulta2)
