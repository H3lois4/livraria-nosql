"""Usuários no banco SQL (nos testes, SQLite em memória com o mesmo código SQLAlchemy)."""
import mongomock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from servidor import create_app


@pytest.fixture
def http(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    colecao = mongomock.MongoClient()["livraria"]["livros"]
    return create_app(tmp_path, colecao_livros=colecao, engine_usuarios=engine).test_client()


def test_quatro_usuarios_iniciais(http):
    usuarios = http.get("/api/usuarios").json
    assert len(usuarios) == 4
    assert usuarios[0]["nome"] == "Ana Souza" and usuarios[0]["loja_favorita"] == "paulista"
    assert http.get("/api").json["usuarios_cadastrados"] == 4


def test_cadastrar_buscar_atualizar_remover(http):
    r = http.post("/api/usuarios", json={"nome": "Elisa Prado", "email": "Elisa@Exemplo.com",
                                         "cidade": "Santos", "loja_favorita": "pinheiros"})
    assert r.status_code == 201 and r.json["email"] == "elisa@exemplo.com"
    uid = r.json["id"]
    assert http.get(f"/api/usuarios/{uid}").json["cidade"] == "Santos"
    assert http.put(f"/api/usuarios/{uid}", json={"telefone": "(13) 99999-0000"}).json["telefone"] == "(13) 99999-0000"
    assert http.delete(f"/api/usuarios/{uid}").status_code == 204
    assert http.get(f"/api/usuarios/{uid}").status_code == 404


@pytest.mark.parametrize("dados, erro", [
    ({"email": "x@exemplo.com"}, "obrigatórios"),
    ({"nome": "X", "email": "sem-arroba"}, "E-mail inválido"),
    ({"nome": "X", "email": "ana.souza@exemplo.com"}, "já cadastrado"),
    ({"nome": "X", "email": "x@exemplo.com", "loja_favorita": "centro"}, "Loja favorita"),
    ({"nome": "X", "email": "x@exemplo.com", "senha": "123"}, "Campo desconhecido"),
])
def test_validacao(http, dados, erro):
    r = http.post("/api/usuarios", json=dados)
    assert r.status_code == 400 and erro in r.json["erro"]


def test_email_duplicado_na_atualizacao(http):
    r = http.put("/api/usuarios/2", json={"email": "ana.souza@exemplo.com"})
    assert r.status_code == 400 and "já cadastrado" in r.json["erro"]
