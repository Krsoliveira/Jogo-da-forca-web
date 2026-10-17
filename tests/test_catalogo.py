import pytest

from app import app
from forca import banco
from forca.config import ALEATORIO, DIFICULDADE_CONFIG, DIFICULDADES
from forca.palavras import PALAVRAS_POR_CATEGORIA


@pytest.fixture
def catalogo():
    app.config.update(TESTING=True)
    resposta = app.test_client().get("/api/catalogo")
    assert resposta.status_code == 200
    return resposta


def test_dificuldades_na_ordem_com_tentativas_e_dicas(catalogo):
    dificuldades = catalogo.get_json()["dificuldades"]
    assert [d["id"] for d in dificuldades] == DIFICULDADES
    assert all(d["tentativas"] == DIFICULDADE_CONFIG[d["id"]] for d in dificuldades)
    assert {d["id"]: d["dicas"] for d in dificuldades} == {"facil": 2, "medio": 2, "dificil": 1}


def test_categorias_com_quantidade_de_palavras_e_aleatorio_por_ultimo(catalogo):
    categorias = catalogo.get_json()["categorias"]
    normais, ultimo = categorias[:-1], categorias[-1]
    assert [c["nome"] for c in normais] == list(PALAVRAS_POR_CATEGORIA)
    assert all(c["palavras"] == len(PALAVRAS_POR_CATEGORIA[c["nome"]]) and not c["aleatorio"] for c in normais)
    assert ultimo["nome"] == ALEATORIO and ultimo["aleatorio"]
    assert ultimo["palavras"] == sum(len(banco.palavras(d)) for d in DIFICULDADES) == 10_000


def test_toda_categoria_do_catalogo_inicia_um_jogo(catalogo):
    # o menu só oferece o que o /novo_jogo aceita
    cliente = app.test_client()
    for categoria in catalogo.get_json()["categorias"]:
        resposta = cliente.get("/novo_jogo", query_string={"category": categoria["nome"], "difficulty": "facil"})
        assert resposta.status_code == 200, categoria["nome"]


def test_catalogo_pode_ficar_em_cache(catalogo):
    assert "max-age=300" in catalogo.headers["Cache-Control"]
