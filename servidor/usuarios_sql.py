"""Registro de usuários no banco SQL (Azure Database for PostgreSQL).

Tabela `usuarios`:

    id            SERIAL        PRIMARY KEY
    nome          VARCHAR(100)  NOT NULL
    email         VARCHAR(150)  NOT NULL UNIQUE
    telefone      VARCHAR(20)
    cidade        VARCHAR(80)
    loja_favorita VARCHAR(30)
    criado_em     TIMESTAMP     NOT NULL

A conexão vem da variável de ambiente DATABASE_URL, por exemplo:
    postgresql+psycopg://usuario:senha@servidor.postgres.database.azure.com:5432/livraria?sslmode=require
Sem ela, usa um arquivo SQLite local (testes e uso local), com o mesmo código SQL via SQLAlchemy.
"""
import os
import re
from datetime import datetime, timezone

from sqlalchemy import (Column, DateTime, Integer, MetaData, String, Table, create_engine,
                        func, insert, select, update, delete)
from sqlalchemy.exc import IntegrityError

metadata = MetaData()

usuarios = Table(
    "usuarios", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nome", String(100), nullable=False),
    Column("email", String(150), nullable=False, unique=True),
    Column("telefone", String(20)),
    Column("cidade", String(80)),
    Column("loja_favorita", String(30)),
    Column("criado_em", DateTime, nullable=False),
)

USUARIOS_INICIAIS = [
    {"nome": "Ana Souza", "email": "ana.souza@exemplo.com", "telefone": "(11) 91234-5678",
     "cidade": "São Paulo", "loja_favorita": "paulista"},
    {"nome": "Bruno Lima", "email": "bruno.lima@exemplo.com", "telefone": "(11) 92345-6789",
     "cidade": "São Paulo", "loja_favorita": "pinheiros"},
    {"nome": "Carla Mendes", "email": "carla.mendes@exemplo.com", "telefone": "(11) 93456-7890",
     "cidade": "Osasco", "loja_favorita": "paulista"},
    {"nome": "Diego Rocha", "email": "diego.rocha@exemplo.com", "telefone": "(11) 94567-8901",
     "cidade": "Guarulhos", "loja_favorita": None},
]

EMAIL_VALIDO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CAMPOS = ("nome", "email", "telefone", "cidade", "loja_favorita")


class UsuarioInvalido(Exception):
    pass


class UsuarioNaoEncontrado(Exception):
    pass


def criar_engine(pasta_dados="data"):
    url = os.environ.get("DATABASE_URL")
    if not url:
        os.makedirs(pasta_dados, exist_ok=True)
        url = f"sqlite:///{os.path.join(pasta_dados, 'usuarios.db')}"
    return create_engine(url, pool_pre_ping=True)


def descrever_banco(engine):
    return "Azure Database for PostgreSQL" if engine.dialect.name == "postgresql" \
        else f"{engine.dialect.name} local (DATABASE_URL não configurado)"


def _linha(r):
    d = dict(r._mapping)
    d["criado_em"] = d["criado_em"].strftime("%d/%m/%Y %H:%M")
    return d


class RepositorioUsuarios:
    def __init__(self, engine, loja_existe=lambda loja_id: True, popular=True):
        self._engine = engine
        self._loja_existe = loja_existe
        metadata.create_all(engine)  # CREATE TABLE IF NOT EXISTS
        if popular and self.total() == 0:
            for u in USUARIOS_INICIAIS:
                self.cadastrar(u)

    # ----- validação -----
    def _validar(self, dados, parcial=False):
        if not isinstance(dados, dict):
            raise UsuarioInvalido("Envie um corpo JSON")
        desconhecidos = set(dados) - set(CAMPOS)
        if desconhecidos:
            raise UsuarioInvalido(f"Campo desconhecido: {', '.join(sorted(desconhecidos))}")
        limpos = {}
        for campo in CAMPOS:
            if campo not in dados:
                continue
            valor = dados[campo]
            if valor is not None and not isinstance(valor, str):
                raise UsuarioInvalido(f"Valor inválido para {campo}")
            limpos[campo] = valor.strip() if isinstance(valor, str) and valor.strip() else None
        if not parcial:
            for obrigatorio in ("nome", "email"):
                if not limpos.get(obrigatorio):
                    raise UsuarioInvalido("Nome e e-mail são obrigatórios")
        if "nome" in limpos and not limpos["nome"]:
            raise UsuarioInvalido("Nome não pode ser vazio")
        if "email" in limpos:
            if not limpos["email"] or not EMAIL_VALIDO.match(limpos["email"]):
                raise UsuarioInvalido("E-mail inválido")
            limpos["email"] = limpos["email"].lower()
        if limpos.get("loja_favorita") and not self._loja_existe(limpos["loja_favorita"]):
            raise UsuarioInvalido("Loja favorita não existe")
        return limpos

    # ----- operações -----
    def listar(self):
        with self._engine.connect() as c:
            return [_linha(r) for r in c.execute(select(usuarios).order_by(usuarios.c.id))]

    def obter(self, usuario_id):
        with self._engine.connect() as c:
            r = c.execute(select(usuarios).where(usuarios.c.id == usuario_id)).first()
        if r is None:
            raise UsuarioNaoEncontrado("Usuário não encontrado")
        return _linha(r)

    def cadastrar(self, dados):
        valores = self._validar(dados)
        valores["criado_em"] = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            with self._engine.begin() as c:
                novo_id = c.execute(insert(usuarios).values(**valores)
                                    .returning(usuarios.c.id)).scalar_one()
        except IntegrityError:
            raise UsuarioInvalido("E-mail já cadastrado")
        return self.obter(novo_id)

    def atualizar(self, usuario_id, dados):
        self.obter(usuario_id)
        valores = self._validar(dados, parcial=True)
        if valores:
            try:
                with self._engine.begin() as c:
                    c.execute(update(usuarios).where(usuarios.c.id == usuario_id).values(**valores))
            except IntegrityError:
                raise UsuarioInvalido("E-mail já cadastrado")
        return self.obter(usuario_id)

    def remover(self, usuario_id):
        self.obter(usuario_id)
        with self._engine.begin() as c:
            c.execute(delete(usuarios).where(usuarios.c.id == usuario_id))

    def total(self):
        with self._engine.connect() as c:
            return c.execute(select(func.count()).select_from(usuarios)).scalar_one()
