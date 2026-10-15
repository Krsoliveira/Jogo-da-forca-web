import pytest

from forca import regras
from forca.config import XP_PARA_PROXIMO_NIVEL


def test_mascarar_esconde_letras_e_preserva_nao_letras():
    assert regras.mascarar("sao paulo", ["a", "o"]) == "_ao _a__o"
    assert regras.mascarar("abc", []) == "___"
    assert regras.mascarar("abc", ["a", "b", "c"]) == "abc"


def test_dicas_no_modo_dificil_mostram_so_a_primeira():
    dicas = ["primeira", "segunda"]
    assert regras.dicas_para(dicas, "dificil") == ["primeira", ""]
    assert regras.dicas_para(dicas, "facil") == dicas
    assert regras.dicas_para([], "dificil") == ["", ""]


def test_pontos_da_letra_contam_cada_ocorrencia():
    assert regras.pontos_da_letra("banana", "a") == 30
    assert regras.pontos_da_letra("banana", "b") == 10


def test_pontos_do_chute_contam_so_letras_nao_reveladas():
    assert regras.pontos_do_chute("uva", []) == 30
    assert regras.pontos_do_chute("uva", ["u", "v"]) == 10
    assert regras.pontos_do_chute("uva", ["u", "v", "a"]) == 0


def test_pontos_da_vitoria_somam_bonus_e_tentativas_que_sobraram():
    # 20 da rodada + 50 de bônus + 4 tentativas sobrando x 5
    assert regras.pontos_da_vitoria(20, 2, 6) == 90


def test_aplicar_xp_sobe_varios_niveis_de_uma_vez():
    assert regras.aplicar_xp(1, 0, 100) == (1, 100, False)
    assert regras.aplicar_xp(1, 950, 100) == (2, 50, True)
    assert regras.aplicar_xp(1, 0, 2 * XP_PARA_PROXIMO_NIVEL + 10) == (3, 10, True)


@pytest.mark.parametrize(
    ("atual", "vitorias", "esperado"),
    [
        ("facil", 5, "medio"),
        ("medio", 10, "dificil"),
        ("dificil", 5, None),  # já está no máximo
        ("facil", 4, None),  # ainda não completou a sequência
        ("facil", 6, None),
    ],
)
def test_proxima_dificuldade(atual, vitorias, esperado):
    assert regras.proxima_dificuldade(atual, vitorias) == esperado
