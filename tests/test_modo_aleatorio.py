import json

import pytest

from app import app
from forca import banco, rotas
from forca.config import ALEATORIO

CAMINHO_BANCO = banco.CAMINHO


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def iniciar(client, dificuldade):
    return client.get("/novo_jogo", query_string={"category": ALEATORIO, "difficulty": dificuldade})


def palavra_atual(client):
    with client.session_transaction() as s:
        pid = s["pid"]
    return app.extensions["partidas"].obter(pid)["palavra"]


def dificuldade_no_banco(palavra):
    with open(CAMINHO_BANCO, encoding="utf-8") as f:
        return next(e["dificuldade"] for e in json.load(f) if e["palavra"] == palavra)


# --- Dicas montadas a partir do dicionário ---


def test_definicao_esconde_a_palavra_e_as_derivadas():
    texto = banco.esconder_palavra("rebeliao", "Acto de se rebelar; rebelião; revolta.")
    assert "rebel" not in texto.lower()
    assert texto.count(banco.ESCONDIDO) == 2


def test_definicao_esconde_a_palavra_mesmo_na_grafia_antiga():
    assert "effeito" not in banco.esconder_palavra("efeito", "O effeito do trabalho").lower()


def test_definicao_nao_esconde_palavras_sem_relacao():
    assert banco.esconder_palavra("rebeliao", "Acto de revolta") == "Acto de revolta"


def test_definicao_longa_e_cortada_sem_quebrar_palavra():
    longa = "Uma frase longa. " + "palavra " * 60
    resumo = banco._resumir(longa)
    assert len(resumo) <= banco.LIMITE_DEFINICAO + 1
    assert resumo.endswith(("…", "."))


@pytest.mark.parametrize(
    ("classe", "esperado"),
    [("m.", "substantivo masculino"), ("f.", "substantivo feminino"), ("adj.", "adjetivo"),
     ("v. t.", "verbo"), ("m.  e  adj.", "substantivo masculino"), ("", "palavra"), ("xyz.", "palavra")],
)
def test_classe_gramatical_legivel(classe, esperado):
    assert banco._classe_legivel(classe) == esperado


def test_nenhuma_dica_do_banco_revela_a_palavra():
    # varre as 10 mil entradas: a dica nunca pode conter a resposta (nem na grafia antiga)
    vazadas = []
    for dificuldade in ("facil", "medio", "dificil"):
        for palavra in banco.palavras(dificuldade):
            definicao, detalhe = banco.dicas(palavra)
            assert definicao and detalhe.startswith(f"{len(palavra)} letras")
            if banco.normalizar(palavra) in banco.normalizar(definicao):
                vazadas.append(palavra)
    assert vazadas == []


# --- Integração com o jogo ---


def test_aleatorio_aparece_nas_categorias(client):
    categorias = client.get("/categorias").get_json()
    assert categorias[-1] == ALEATORIO and "Frutas" in categorias


@pytest.mark.parametrize("dificuldade", ["facil", "medio", "dificil"])
def test_dificuldade_escolhe_o_grupo_de_palavras(client, dificuldade):
    for _ in range(5):
        dados = iniciar(client, dificuldade).get_json()
        assert dificuldade_no_banco(palavra_atual(client)) == dificuldade
        assert dados["dicas"][0]
    assert (dados["dicas"][1] == "") == (dificuldade == "dificil")


def test_subir_de_dificuldade_muda_o_grupo_sorteado(client):
    iniciar(client, "facil")
    for _ in range(5):
        palavra = palavra_atual(client)
        assert client.post("/chute", json={"palavra": palavra}).get_json()["vitoria_rodada"]
        proxima = client.get("/proxima_palavra").get_json()
    assert proxima["dificuldade"] == "medio"
    assert dificuldade_no_banco(palavra_atual(client)) == "medio"


def test_dicas_continuam_aparecendo_durante_a_rodada(client):
    iniciar(client, "medio")
    palavra = palavra_atual(client)
    errada = next(c for c in "abcdefghijklmnopqrstuvwxyz" if c not in palavra)
    dados = client.post("/tentativa", json={"letra": errada}).get_json()
    assert dados["dicas"] == banco.dicas(palavra)


def test_palavras_recentes_nao_se_repetem(monkeypatch):
    monkeypatch.setattr(banco, "palavras", lambda _dif: ["aaaa", "bbbb"])
    sorteios = iter(["aaaa", "aaaa", "bbbb"])
    monkeypatch.setattr(rotas.random, "choice", lambda _lista: next(sorteios))
    assert rotas._sortear_aleatoria({"palavras_recentes": ["aaaa"]}, "facil") == "bbbb"


def test_lista_de_recentes_tem_tamanho_limitado(monkeypatch):
    monkeypatch.setattr(banco, "palavras", lambda _dif: ["aaaa"])
    partida = {}
    for _ in range(rotas.PALAVRAS_RECENTES + 20):
        rotas._sortear_aleatoria(partida, "facil")
    assert len(partida["palavras_recentes"]) == rotas.PALAVRAS_RECENTES
