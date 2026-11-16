"""Regras de negócio do MVP, executadas somente no servidor."""
from .dominio import Livro, NaoEncontrado, normalizar


class DadosInvalidos(Exception):
    pass


class Livraria:
    def __init__(self, repositorio):
        self._repo = repositorio

    # US01 / US02 – buscar livro, ver estoque e preço
    def buscar_livros(self, termo=""):
        livros = self._repo.livros(termo)  # o filtro é feito no próprio banco
        return sorted(livros, key=lambda l: normalizar(l.titulo))

    def obter_livro(self, isbn):
        livro = self._repo.livro(isbn)
        if livro is None:
            raise NaoEncontrado("Livro não encontrado")
        return livro

    def disponibilidade(self, isbn, cliente_id=None):
        """Estoque por loja; a loja favorita do cliente aparece primeiro."""
        self.obter_livro(isbn)
        favorita = self.loja_favorita(cliente_id)
        itens = []
        for item in self._repo.estoque_do_livro(isbn):
            loja = self._repo.loja(item.loja_id)
            if loja:
                itens.append({"loja": loja, "quantidade": item.quantidade,
                              "disponivel": item.disponivel, "favorita": loja.id == favorita})
        return sorted(itens, key=lambda i: (not i["favorita"], i["loja"].nome))

    # US03 – horário e endereço
    def listar_lojas(self):
        return sorted(self._repo.lojas(), key=lambda l: l.nome)

    def obter_loja(self, loja_id):
        loja = self._repo.loja(loja_id)
        if loja is None:
            raise NaoEncontrado("Loja não encontrada")
        return loja

    # US04 – loja favorita
    def loja_favorita(self, cliente_id):
        return self._repo.loja_favorita(cliente_id) if cliente_id else None

    def definir_loja_favorita(self, cliente_id, loja_id):
        loja = self.obter_loja(loja_id)
        self._repo.salvar_loja_favorita(cliente_id, loja.id)
        return loja

    # Catálogo – cadastrar livro no banco NoSQL
    def cadastrar_livro(self, dados):
        isbn = "".join(c for c in str(dados.get("isbn", "")) if c.isdigit())
        titulo = str(dados.get("titulo", "")).strip()
        autor = str(dados.get("autor", "")).strip()
        preco, estoque = dados.get("preco"), dados.get("estoque", {})
        if len(isbn) != 13:
            raise DadosInvalidos("ISBN deve ter 13 dígitos")
        if not titulo or not autor:
            raise DadosInvalidos("Título e autor são obrigatórios")
        if isinstance(preco, bool) or not isinstance(preco, (int, float)) or preco < 0:
            raise DadosInvalidos("Preço inválido")
        if not isinstance(estoque, dict) or any(
                self._repo.loja(l) is None or isinstance(q, bool) or not isinstance(q, int) or q < 0
                for l, q in estoque.items()):
            raise DadosInvalidos("Estoque inválido: use {\"id_da_loja\": quantidade}")
        if self._repo.catalogo.existe(isbn):
            raise DadosInvalidos("Já existe um livro com este ISBN")
        livro = Livro(isbn, titulo, autor, float(preco))
        self._repo.catalogo.cadastrar(livro, estoque)
        return livro

    def total_livros(self):
        return self._repo.catalogo.total()

    def loja_existe(self, loja_id):
        return self._repo.loja(loja_id) is not None
