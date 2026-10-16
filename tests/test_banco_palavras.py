import json
import os
import re

import pytest

from scripts import gerar_banco as gb

CAMINHO = os.path.join(os.path.dirname(__file__), "..", "forca", "dados", "palavras_gerais.json")


@pytest.fixture(scope="module")
def banco():
    with open(CAMINHO, encoding="utf-8") as f:
        return json.load(f)


# --- O arquivo de dados gerado ---


def test_banco_tem_a_quantidade_esperada(banco):
    assert len(banco) == gb.QUANTIDADE


def test_todas_as_palavras_sao_validas_para_o_jogo(banco):
    # o jogo só aceita letras a-z, então qualquer outra coisa tornaria a palavra impossível de acertar
    invalidas = [p["palavra"] for p in banco if not re.fullmatch(r"[a-z]{4,12}", p["palavra"])]
    assert invalidas == []


def test_nao_ha_palavras_repetidas(banco):
    palavras = [p["palavra"] for p in banco]
    assert len(palavras) == len(set(palavras))


def test_dificuldades_sao_conhecidas_e_todas_usadas(banco):
    niveis = {p["dificuldade"] for p in banco}
    assert niveis == {"facil", "medio", "dificil"}


def test_nenhuma_palavra_bloqueada_entrou(banco):
    assert {p["palavra"] for p in banco} & gb.carregar_bloqueadas() == set()


def test_definicao_nunca_entrega_a_palavra(banco):
    vazadas = [p["palavra"] for p in banco if p["palavra"] in gb.sem_acento(p["definicao_original"]).lower()]
    assert vazadas == []


def test_sem_plurais_nem_grafia_antiga(banco):
    palavras = {p["palavra"] for p in banco}
    assert [p for p in palavras if p.endswith("s") and p[:-1] in palavras] == []
    assert [p for p in palavras if gb.tem_grafia_arcaica(p)] == []


def test_estrutura_dos_registros(banco):
    assert all(set(p) == {"palavra", "classe", "dificuldade", "definicao_original"} for p in banco)


# --- Regras do gerador ---


@pytest.mark.parametrize(
    ("palavra", "posicao", "esperado"),
    [
        ("casa", 10, "facil"),
        ("casa", 6000, "medio"),
        ("casa", 8500, "dificil"),
        ("cronologia", 100, "dificil"),
        ("estampar", 2000, "medio"),
    ],
)
def test_classificar_dificuldade(palavra, posicao, esperado):
    assert gb.classificar(palavra, posicao) == esperado


def test_sem_acento():
    assert gb.sem_acento("coração") == "coracao"
    assert gb.sem_acento("Ação") == "Acao"


BLOQ = {"puta"}
DEF = "Vegetal medicinal muito usado em chás."


@pytest.mark.parametrize(
    ("palavra", "classe", "usos", "definicao", "esperado"),
    [
        ("planta", "f.", [], DEF, True),
        ("plantar", "v. t.", [], DEF, True),
        ("plantou", "v. t.", [], DEF, False),  # verbo fora do infinitivo
        ("pla", "f.", [], DEF, False),  # curta demais
        ("planta-baixa", "f.", [], DEF, False),  # hífen
        ("planta", "adv.", [], DEF, False),  # classe que não serve
        ("planta", "f.", [("style", "Pop.")], DEF, False),  # uso marcado
        ("planta", "f.", [], "Curta.", False),  # definição fraca
        ("planta", "f.", [], "O mesmo que vegetal, erva.", False),  # remete a outro verbete
        ("planta", "f.", [], "Uma planta qualquer, de jardim.", False),  # a definição entrega a palavra
        ("puta", "f.", [], DEF, False),  # bloqueada
    ],
)
def test_aceitar_entrada(palavra, classe, usos, definicao, esperado):
    assert gb.aceitar_entrada(palavra, classe, usos, definicao, BLOQ) is esperado


def test_montar_banco_respeita_a_ordem_de_frequencia_e_o_limite():
    candidatas = {p: ("m.", "def") for p in ("casa", "bola", "mesa", "gato")}
    banco = gb.montar_banco(candidatas, ["bola", "xxxx", "casa", "bola", "mesa", "gato"], quantidade=3)
    assert [p["palavra"] for p in banco] == ["bola", "casa", "mesa"]


def test_montar_banco_descarta_plural_e_grafia_antiga():
    candidatas = {p: ("m.", "def") for p in ("indio", "indios", "pharmacia", "casa")}
    banco = gb.montar_banco(candidatas, ["indios", "indio", "pharmacia", "casa"], quantidade=10)
    assert [p["palavra"] for p in banco] == ["indio", "casa"]
