"""Regras de negócio do servidor, sem HTTP."""
import pytest

import mongomock

from servidor.casos_de_uso import DadosInvalidos, Livraria
from servidor.catalogo_mongo import CatalogoMongo
from servidor.dominio import NaoEncontrado
from servidor.repositorio import Repositorio

DOM, HORA = "9788535902775", "9788501114775"


@pytest.fixture
def livraria(tmp_path):
    colecao = mongomock.MongoClient()["livraria"]["livros"]
    return Livraria(Repositorio(tmp_path, CatalogoMongo(colecao)))


def test_busca_sem_acentos_e_por_autor(livraria):
    assert [l.titulo for l in livraria.buscar_livros("postumas")] == ["Memórias Póstumas de Brás Cubas"]
    assert len(livraria.buscar_livros("MACHADO")) == 4


def test_estoque_por_loja(livraria):
    itens = {i["loja"].id: i for i in livraria.disponibilidade(DOM)}
    assert itens["paulista"]["quantidade"] == 3 and not itens["pinheiros"]["disponivel"]


def test_favorita_primeiro_por_cliente(livraria):
    livraria.definir_loja_favorita("ana", "pinheiros")
    assert livraria.disponibilidade(HORA, "ana")[0]["loja"].id == "pinheiros"
    assert livraria.disponibilidade(HORA, "bia")[0]["loja"].id == "paulista"


def test_erros(livraria):
    with pytest.raises(NaoEncontrado, match="Livro não encontrado"):
        livraria.obter_livro("000")
    with pytest.raises(NaoEncontrado, match="Loja não encontrada"):
        livraria.definir_loja_favorita("ana", "centro")


def test_dados_em_txt(livraria, tmp_path):
    livraria.definir_loja_favorita("ana", "paulista")
    assert (tmp_path / "preferencias.txt").read_text(encoding="utf-8") == "ana|paulista\n"
    assert "Livraria Paulista" in (tmp_path / "lojas.txt").read_text(encoding="utf-8")


def test_catalogo_inicial_tem_12_livros(livraria):
    assert livraria.total_livros() == 12 and len(livraria.buscar_livros("")) == 12


def test_cadastrar_livro(livraria):
    livro = livraria.cadastrar_livro({"isbn": "978-85-359-3010-5", "titulo": "Torto Arado",
                                      "autor": "Itamar Vieira Junior", "preco": 59.9,
                                      "estoque": {"paulista": 2}})
    assert livro.isbn == "9788535930105" and livraria.total_livros() == 13
    assert livraria.disponibilidade(livro.isbn)[0]["quantidade"] == 2


@pytest.mark.parametrize("dados, mensagem", [
    ({"isbn": "123", "titulo": "X", "autor": "Y", "preco": 1}, "ISBN"),
    ({"isbn": "9788535930105", "titulo": "", "autor": "Y", "preco": 1}, "obrigatórios"),
    ({"isbn": "9788535930105", "titulo": "X", "autor": "Y", "preco": -1}, "Preço"),
    ({"isbn": "9788535930105", "titulo": "X", "autor": "Y", "preco": 1, "estoque": {"centro": 1}}, "Estoque"),
    ({"isbn": "9788535902775", "titulo": "X", "autor": "Y", "preco": 1}, "Já existe"),
])
def test_cadastro_invalido(livraria, dados, mensagem):
    with pytest.raises(DadosInvalidos, match=mensagem):
        livraria.cadastrar_livro(dados)
