"""Jogo da Forca: fábrica da aplicação Flask."""

from flask import Flask

from .config import MAX_PARTIDAS, PARTIDA_TTL_SEGUNDOS, configurar
from .partidas import ArmazenamentoDePartidas
from .rotas import bp


def create_app():
    # templates e estáticos ficam na raiz do projeto, fora do pacote
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    configurar(app)
    app.extensions["partidas"] = ArmazenamentoDePartidas(PARTIDA_TTL_SEGUNDOS, MAX_PARTIDAS)
    app.register_blueprint(bp)
    return app
