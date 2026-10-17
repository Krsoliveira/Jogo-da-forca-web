"""Banco de palavras gerais (modo Aleatório): carrega o JSON, agrupa por dificuldade e monta as dicas.

As palavras não pertencem a uma categoria; a dificuldade do jogo escolhe de qual grupo sai o sorteio.
As dicas são montadas na hora a partir da definição do dicionário (ortografia antiga) e da classe
gramatical, sem revelar a própria palavra.
"""

import json
import os
import re
import unicodedata
from functools import lru_cache

CAMINHO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados", "palavras_gerais.json")
LIMITE_DEFINICAO = 140  # a dica precisa caber na tela, inclusive no celular
ESCONDIDO = "____"
_LETRAS = re.compile(r"[^\W\d_]+")
_CLASSES = {"m": "substantivo masculino", "f": "substantivo feminino", "adj": "adjetivo", "v": "verbo"}


@lru_cache(maxsize=1)
def _carregar():
    with open(CAMINHO, encoding="utf-8") as arquivo:
        entradas = json.load(arquivo)
    por_palavra = {e["palavra"]: e for e in entradas}
    por_dificuldade = {}
    for e in entradas:
        por_dificuldade.setdefault(e["dificuldade"], []).append(e["palavra"])
    return por_palavra, por_dificuldade


def palavras(dificuldade):
    """Palavras do banco para a dificuldade informada (lista vazia se não houver)."""
    return _carregar()[1].get(dificuldade, [])


def dicas(palavra):
    """[definição sem a palavra, 'N letras · classe'] para uma palavra do banco."""
    entrada = _carregar()[0][palavra]
    definicao = _resumir(esconder_palavra(palavra, entrada["definicao_original"]))
    return [definicao, f"{len(palavra)} letras · {_classe_legivel(entrada['classe'])}"]


def normalizar(texto):
    """Minúsculas, sem acentos e sem letras dobradas: 'Effeito' e 'efeito' ficam iguais.

    O dicionário usa a grafia antiga (effeito, tranquillo), então comparar texto cru deixaria
    a palavra aparecer na própria dica.
    """
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if not unicodedata.combining(c))
    return re.sub(r"(.)\1+", r"\1", sem_acento)


def esconder_palavra(palavra, definicao):
    """Troca por '____' toda palavra da definição que comece com o radical da resposta."""
    base = normalizar(palavra)
    radical = base[: max(4, len(base) - 3)]  # pega também derivadas (rebelar, rebelião)
    return _LETRAS.sub(lambda m: ESCONDIDO if normalizar(m.group()).startswith(radical) else m.group(), definicao)


def _resumir(definicao):
    """Limpa espaços, corta em ponto/ponto e vírgula ou, no limite, em fim de palavra."""
    texto = " ".join(definicao.split())
    if len(texto) > LIMITE_DEFINICAO:
        corte = texto[:LIMITE_DEFINICAO]
        fim = max(corte.rfind("."), corte.rfind(";"))
        texto = corte[: fim + 1] if fim > 40 else corte.rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return texto[:1].upper() + texto[1:]


def _classe_legivel(classe):
    primeiro = classe.split()[0].rstrip(".,").lower() if classe.split() else ""
    return _CLASSES.get(primeiro, "palavra")
