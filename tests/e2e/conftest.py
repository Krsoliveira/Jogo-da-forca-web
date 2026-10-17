"""Infraestrutura dos testes de navegador: sobe o app num servidor real e abre o Playwright.

Rodar localmente:
    npm run build
    pip install -r requirements-dev.txt && playwright install chromium
    python -m pytest -m e2e

Para usar o Edge já instalado no Windows em vez de baixar o Chromium: E2E_CANAL=msedge.
"""

import os
import threading

import pytest
from werkzeug.serving import make_server

playwright = pytest.importorskip("playwright.sync_api")

from app import app  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def servidor():
    if not os.path.exists(os.path.join(RAIZ, "static", "js", "dist", "app.js")):
        pytest.fail("Interface não compilada: rode `npm run build` antes dos testes e2e.")
    app.config.update(TESTING=True)
    srv = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture(scope="session")
def navegador():
    with playwright.sync_playwright() as p:
        canal = os.environ.get("E2E_CANAL")
        nav = p.chromium.launch(channel=canal) if canal else p.chromium.launch()
        yield nav
        nav.close()


@pytest.fixture(params=[{"width": 1280, "height": 860}, {"width": 390, "height": 844}], ids=["desktop", "celular"])
def pagina(request, navegador, servidor):
    """Página nova por teste, em desktop e celular, coletando erros de JavaScript e de rede."""
    contexto = navegador.new_context(viewport=request.param, reduced_motion="reduce", base_url=servidor)
    pg = contexto.new_page()
    pg.erros = []
    pg.on("pageerror", lambda e: pg.erros.append(f"JS: {e}"))
    pg.on("console", lambda m: pg.erros.append(f"console: {m.text}") if m.type == "error" else None)
    yield pg
    contexto.close()
