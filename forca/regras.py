"""Regras puras do jogo: sem Flask e sem sessão, fáceis de testar isoladamente."""

from .config import (
    DIFICULDADES,
    PONTOS_LETRA_CERTA,
    PONTOS_POR_TENTATIVA_SOBRA,
    PONTOS_VITORIA_BONUS,
    VITORIAS_PARA_SUBIR_NIVEL_DIFICULDADE,
    XP_PARA_PROXIMO_NIVEL,
)


def mascarar(palavra, letras_tentadas):
    """Mostra as letras já descobertas e '_' nas demais (não-letras aparecem sempre)."""
    return "".join(ch if not ch.isalpha() or ch in letras_tentadas else "_" for ch in palavra)


def dicas_para(dicas, dificuldade):
    """No modo difícil só a primeira dica é exibida."""
    if dificuldade == "dificil":
        return [dicas[0], ""] if dicas else ["", ""]
    return dicas


def pontos_da_letra(palavra, letra):
    """Pontos por acertar uma letra: vale por cada ocorrência na palavra."""
    return PONTOS_LETRA_CERTA * palavra.count(letra)


def pontos_do_chute(palavra, letras_tentadas):
    """Pontos por acertar a palavra inteira: só as letras ainda não reveladas contam."""
    return PONTOS_LETRA_CERTA * len([ch for ch in palavra if ch not in letras_tentadas])


def pontos_da_vitoria(pontos_rodada, erros, max_erros):
    """Pontos da rodada somados ao bônus de vitória e às tentativas que sobraram."""
    return pontos_rodada + PONTOS_VITORIA_BONUS + (max_erros - erros) * PONTOS_POR_TENTATIVA_SOBRA


def aplicar_xp(nivel, xp, ganho):
    """Soma XP e sobe de nível quantas vezes for preciso. Retorna (nivel, xp, subiu)."""
    xp += ganho
    subiu = False
    while xp >= XP_PARA_PROXIMO_NIVEL:
        subiu = True
        nivel += 1
        xp -= XP_PARA_PROXIMO_NIVEL
    return nivel, xp, subiu


def proxima_dificuldade(atual, vitorias_consecutivas):
    """Dificuldade seguinte a cada N vitórias seguidas; None se não houver mudança."""
    if vitorias_consecutivas % VITORIAS_PARA_SUBIR_NIVEL_DIFICULDADE != 0:
        return None
    idx = DIFICULDADES.index(atual)
    return DIFICULDADES[idx + 1] if idx < len(DIFICULDADES) - 1 else None
