from neo4j import GraphDatabase

senha = "oRvd7_ix4elyZyZEMzr2Ibx0H0573xpkwz3dg3003zA"
url = "neo4j+s://6347a559.databases.neo4j.io"
usuario = "neo4j"

#conexao com o neo4j
class Neo4jConnection:
    def __init__(self, uri, user, pwd):
        self.__uri = uri
        self.__user = user
        self.__pwd = pwd
        self.__driver = None
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__pwd))
        except Exception as e:
            print("Failed to create the driver:", e)

    def close(self):
        if self.__driver is not None:
            self.__driver.close()

    def query(self, query, parameters=None, db=None):
        assert self.__driver is not None, "Driver not initialized!"
        session = None
        response = None
        try:
            session = self.__driver.session(database=db) if db is not None else self.__driver.session()
            response = list(session.run(query, parameters))
        except Exception as e:
            print("Query failed:", e)
        finally:
            if session is not None:
                session.close()
        return response


#criando relacoes entre os grafos
conn = Neo4jConnection(uri=url,
                       user=usuario,
                       pwd=senha)

def consultar(query):
    return conn.query(query)

class CriarAmizades:
    def __init__(self):
        self.driver = GraphDatabase.driver(url, auth=(usuario, senha))

    def close(self):
        self.driver.close()

    def carrega_base(self, query):
        with self.driver.session() as session:
            session.write_transaction(self._cria_amizade, query)

    def zera_base(self):
        with self.driver.session() as session:
            session.write_transaction(self._zera_base)

    @staticmethod
    def _zera_base(tx):
        tx.run("""
MATCH (n)
DETACH DELETE n
""")

    @staticmethod
    def _cria_amizade(tx, query):
        tx.run(query)