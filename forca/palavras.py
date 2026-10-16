"""Carrega as categorias de palavras a partir de forca/dados/categorias/*.json.

Cada arquivo tem uma categoria:

    {"categoria": "Frutas", "ordem": 1, "palavras": {"morango": ["dica 1", "dica 2"], ...}}

`ordem` define a posição do botão na tela. As regras de qualidade (formato, dicas que não
entregam a resposta, repetições) são verificadas em tests/test_categorias.py.
"""

import json
import os

PASTA_CATEGORIAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados", "categorias")


def carregar_categorias(pasta=PASTA_CATEGORIAS):
    """Devolve {categoria: {palavra: [dica, dica]}} na ordem definida em cada arquivo."""
    arquivos = []
    for nome in os.listdir(pasta):
        if nome.endswith(".json"):
            with open(os.path.join(pasta, nome), encoding="utf-8") as f:
                arquivos.append(json.load(f))
    categorias = {}
    for dados in sorted(arquivos, key=lambda d: d["ordem"]):
        if dados["categoria"] in categorias:
            raise ValueError(f"Categoria repetida: {dados['categoria']}")
        categorias[dados["categoria"]] = dados["palavras"]
    return categorias


PALAVRAS_POR_CATEGORIA = carregar_categorias()
