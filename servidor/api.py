"""Rotas HTTP do servidor. Toda resposta é JSON; o cliente decide como exibir."""
import os
from dataclasses import asdict
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .casos_de_uso import DadosInvalidos, Livraria
from .catalogo_mongo import CatalogoMongo, conectar_colecao
from .dominio import NaoEncontrado
from .repositorio import Repositorio
from .usuarios_sql import (RepositorioUsuarios, UsuarioInvalido, UsuarioNaoEncontrado,
                           criar_engine, descrever_banco)

PASTA_CLIENTE = Path(__file__).resolve().parent.parent / "cliente"


def _item_json(item):
    return {"loja": asdict(item["loja"]), "quantidade": item["quantidade"],
            "disponivel": item["disponivel"], "favorita": item["favorita"]}


def create_app(pasta_dados=None, servir_cliente=None, colecao_livros=None, engine_usuarios=None):
    pasta_dados = pasta_dados or os.environ.get("PASTA_DADOS", "data")
    if servir_cliente is None:
        servir_cliente = os.environ.get("SERVIR_CLIENTE", "true").lower() != "false"
    colecao = colecao_livros if colecao_livros is not None else conectar_colecao()
    livraria = Livraria(Repositorio(pasta_dados, CatalogoMongo(colecao)))
    engine = engine_usuarios if engine_usuarios is not None else criar_engine(pasta_dados)
    repo_usuarios = RepositorioUsuarios(engine, loja_existe=livraria.loja_existe)
    app = Flask(__name__, static_folder=None)

    def cliente_id():
        """O cliente se identifica pelo cabeçalho X-Cliente-Id (o servidor não guarda sessão)."""
        return request.headers.get("X-Cliente-Id") or None

    def exigir_cliente():
        cid = cliente_id()
        if not cid:
            return None, (jsonify(erro="Cabeçalho X-Cliente-Id é obrigatório"), 400)
        return cid, None

    @app.errorhandler(DadosInvalidos)
    def dados_invalidos(erro):
        return jsonify(erro=str(erro)), 400

    @app.errorhandler(UsuarioInvalido)
    def usuario_invalido(erro):
        return jsonify(erro=str(erro)), 400

    @app.errorhandler(UsuarioNaoEncontrado)
    def usuario_nao_encontrado(erro):
        return jsonify(erro=str(erro)), 404

    @app.errorhandler(NaoEncontrado)
    def nao_encontrado(erro):
        return jsonify(erro=str(erro)), 404

    @app.after_request
    def cors(resposta):
        # permite que o cliente seja hospedado em outro endereço
        resposta.headers["Access-Control-Allow-Origin"] = "*"
        resposta.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Cliente-Id"
        resposta.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return resposta

    # ---------- Livros ----------
    @app.get("/api/livros")
    def buscar_livros():
        return jsonify([asdict(l) for l in livraria.buscar_livros(request.args.get("q", ""))])

    @app.post("/api/livros")
    def cadastrar_livro():
        livro = livraria.cadastrar_livro(request.get_json(silent=True) or {})
        return jsonify(asdict(livro)), 201

    @app.get("/api/livros/<isbn>")
    def detalhe_livro(isbn):
        livro = livraria.obter_livro(isbn)
        itens = livraria.disponibilidade(isbn, cliente_id())
        return jsonify(livro=asdict(livro), disponibilidade=[_item_json(i) for i in itens])

    # ---------- Lojas ----------
    @app.get("/api/lojas")
    def listar_lojas():
        return jsonify([asdict(l) for l in livraria.listar_lojas()])

    @app.get("/api/lojas/<loja_id>")
    def detalhe_loja(loja_id):
        return jsonify(asdict(livraria.obter_loja(loja_id)))

    # ---------- Usuários (PostgreSQL) ----------
    @app.get("/api/usuarios")
    def listar_usuarios():
        return jsonify(repo_usuarios.listar())

    @app.get("/api/usuarios/<int:usuario_id>")
    def obter_usuario(usuario_id):
        return jsonify(repo_usuarios.obter(usuario_id))

    @app.post("/api/usuarios")
    def cadastrar_usuario():
        return jsonify(repo_usuarios.cadastrar(request.get_json(silent=True))), 201

    @app.put("/api/usuarios/<int:usuario_id>")
    def atualizar_usuario(usuario_id):
        return jsonify(repo_usuarios.atualizar(usuario_id, request.get_json(silent=True)))

    @app.delete("/api/usuarios/<int:usuario_id>")
    def remover_usuario(usuario_id):
        repo_usuarios.remover(usuario_id)
        return "", 204

    # ---------- Cliente ----------
    @app.get("/api/clientes/me/loja-favorita")
    def obter_favorita():
        return jsonify(loja_id=livraria.loja_favorita(cliente_id()))

    @app.put("/api/clientes/me/loja-favorita")
    def definir_favorita():
        cid, erro = exigir_cliente()
        if erro:
            return erro
        dados = request.get_json(silent=True) or {}
        loja = livraria.definir_loja_favorita(cid, dados.get("loja_id", ""))
        return jsonify(loja_id=loja.id, mensagem=f"{loja.nome} agora é sua loja favorita.")

    @app.get("/api")
    def raiz_api():
        return jsonify(servico="API da Livraria", banco=("Azure Cosmos DB for MongoDB" if os.environ.get("MONGODB_URI")
                              else "MongoDB em memória (MONGODB_URI não configurado)"),
                       livros_no_catalogo=livraria.total_livros(),
                       banco_usuarios=descrever_banco(engine),
                       usuarios_cadastrados=repo_usuarios.total(),
                       rotas=["/api/livros", "/api/lojas", "/api/usuarios",
                              "/api/clientes/me/loja-favorita"])

    @app.route("/api/<path:_>", methods=["OPTIONS"])
    def preflight(_):
        return "", 204

    # ---------- Arquivos do cliente (opcional: mesmo endereço para facilitar o deploy) ----------
    if servir_cliente:
        @app.get("/")
        def pagina_inicial():
            return send_from_directory(PASTA_CLIENTE, "index.html")

        @app.get("/<path:arquivo>")
        def arquivos_cliente(arquivo):
            return send_from_directory(PASTA_CLIENTE, arquivo)

    return app
