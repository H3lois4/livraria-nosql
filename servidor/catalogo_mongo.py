"""Catálogo de livros no banco NoSQL (Azure Cosmos DB for MongoDB).

Cada livro é um documento. O estoque por loja fica embutido no próprio documento,
um dos pontos fortes do modelo de documentos:

    {
      "_id": "9788535902775",
      "isbn": "9788535902775",
      "titulo": "Dom Casmurro",
      "autor": "Machado de Assis",
      "preco": 29.9,
      "estoque": {"paulista": 3, "pinheiros": 0},
      "busca": "dom casmurro machado de assis"
    }
"""
import os
import re

from .dominio import ItemEstoque, Livro, normalizar

LIVROS_INICIAIS = [
    ("9788535902775", "Dom Casmurro", "Machado de Assis", 29.90, {"paulista": 3, "pinheiros": 0}),
    ("9788571641149", "Memórias Póstumas de Brás Cubas", "Machado de Assis", 34.50, {"paulista": 0}),
    ("9788535914641", "Grande Sertão: Veredas", "João Guimarães Rosa", 89.00, {"pinheiros": 2}),
    ("9788501114775", "A Hora da Estrela", "Clarice Lispector", 39.90, {"paulista": 1, "pinheiros": 5}),
    ("9788501067347", "Vidas Secas", "Graciliano Ramos", 45.00, {"paulista": 4, "pinheiros": 2}),
    ("9788508133877", "O Cortiço", "Aluísio Azevedo", 27.90, {"paulista": 2}),
    ("9788535914061", "Capitães da Areia", "Jorge Amado", 49.90, {"paulista": 0, "pinheiros": 3}),
    ("9788572327251", "Iracema", "José de Alencar", 19.90, {"pinheiros": 6}),
    ("9788520925058", "Macunaíma", "Mário de Andrade", 36.00, {"paulista": 1, "pinheiros": 1}),
    ("9788525406484", "O Alienista", "Machado de Assis", 22.50, {"paulista": 5}),
    ("9788594318602", "Quincas Borba", "Machado de Assis", 32.90, {"paulista": 0, "pinheiros": 0}),
    ("9788508133464", "Memórias de um Sargento de Milícias", "Manuel Antônio de Almeida", 24.90,
     {"pinheiros": 2}),
]


def conectar_colecao():
    """Abre a coleção 'livros' usando a string de conexão da variável MONGODB_URI."""
    uri = os.environ.get("MONGODB_URI")
    nome_banco = os.environ.get("MONGODB_DB", "livraria")
    if uri:
        from pymongo import MongoClient
        cliente = MongoClient(uri, serverSelectionTimeoutMS=10000)
        return cliente[nome_banco]["livros"]
    # Sem banco configurado (ex.: testes ou uso local): banco em memória com a mesma API.
    import mongomock
    return mongomock.MongoClient()[nome_banco]["livros"]


def documento(isbn, titulo, autor, preco, estoque):
    return {"_id": isbn, "isbn": isbn, "titulo": titulo, "autor": autor, "preco": float(preco),
            "estoque": dict(estoque), "busca": normalizar(f"{titulo} {autor}")}


def _livro(doc):
    return Livro(doc["isbn"], doc["titulo"], doc["autor"], float(doc["preco"]))


class CatalogoMongo:
    def __init__(self, colecao, popular=True):
        self._col = colecao
        if popular and self._col.count_documents({}) == 0:
            self._col.insert_many([documento(*l) for l in LIVROS_INICIAIS])

    def livros(self, termo=""):
        filtro = {}
        termo = normalizar(termo)
        if termo:
            filtro = {"busca": {"$regex": re.escape(termo)}}
        return [_livro(d) for d in self._col.find(filtro)]

    def livro(self, isbn):
        doc = self._col.find_one({"_id": isbn})
        return _livro(doc) if doc else None

    def estoque_do_livro(self, isbn):
        doc = self._col.find_one({"_id": isbn}, {"estoque": 1}) or {}
        return [ItemEstoque(isbn, loja, int(qtd)) for loja, qtd in doc.get("estoque", {}).items()]

    def existe(self, isbn):
        return self._col.count_documents({"_id": isbn}, limit=1) > 0

    def cadastrar(self, livro, estoque):
        self._col.insert_one(documento(livro.isbn, livro.titulo, livro.autor, livro.preco, estoque))

    def total(self):
        return self._col.count_documents({})
