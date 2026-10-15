"""Jogo da Forca: fábrica da aplicação Flask."""

from flask import Flask

from .config import configurar
from .rotas import bp


def create_app():
    # templates e estáticos ficam na raiz do projeto, fora do pacote
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    configurar(app)
    app.register_blueprint(bp)
    return app
