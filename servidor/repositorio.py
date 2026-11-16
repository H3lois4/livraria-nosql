"""Camada de dados do servidor: lojas e preferências em arquivos TXT (campos separados por '|')."""
from pathlib import Path

from .dominio import Loja

LOJAS = [
    ["paulista", "Livraria Paulista", "Av. Paulista, 1000 – São Paulo",
     "Seg a sáb, 10h às 22h; dom, 12h às 20h"],
    ["pinheiros", "Livraria Pinheiros", "Rua dos Pinheiros, 500 – São Paulo",
     "Todos os dias, 9h às 21h"],
]
class ArquivoTxt:
    def __init__(self, caminho, inicial=None):
        self.caminho = Path(caminho)
        if inicial is not None and not self.caminho.exists():
            self.gravar(inicial)

    def ler(self):
        if not self.caminho.exists():
            return []
        return [l.split("|") for l in self.caminho.read_text(encoding="utf-8").splitlines() if l.strip()]

    def gravar(self, registros):
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        texto = "\n".join("|".join(str(c).replace("|", "/") for c in r) for r in registros)
        self.caminho.write_text(texto + ("\n" if registros else ""), encoding="utf-8")


class Repositorio:
    """Lojas e preferências em TXT; o catálogo de livros vem do banco NoSQL (CatalogoMongo)."""

    def __init__(self, pasta, catalogo):
        pasta = Path(pasta)
        self.catalogo = catalogo
        self._lojas = ArquivoTxt(pasta / "lojas.txt", LOJAS)
        self._prefs = ArquivoTxt(pasta / "preferencias.txt")

    def livros(self, termo=""):
        return self.catalogo.livros(termo)

    def livro(self, isbn):
        return self.catalogo.livro(isbn)

    def lojas(self):
        return [Loja(*c) for c in self._lojas.ler()]

    def loja(self, loja_id):
        return next((l for l in self.lojas() if l.id == loja_id), None)

    def estoque_do_livro(self, isbn):
        return self.catalogo.estoque_do_livro(isbn)

    def loja_favorita(self, cliente_id):
        return dict(self._prefs.ler()).get(cliente_id)

    def salvar_loja_favorita(self, cliente_id, loja_id):
        prefs = dict(self._prefs.ler())
        prefs[cliente_id] = loja_id
        self._prefs.gravar([[c, l] for c, l in prefs.items()])
