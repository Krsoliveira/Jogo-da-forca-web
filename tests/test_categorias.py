"""Regras de qualidade dos dados: qualquer palavra nova que quebrar uma delas falha no CI."""

import json
import os
import re
import unicodedata

import pytest

from forca.palavras import PASTA_CATEGORIAS, carregar_categorias

TAMANHO_MAX_DICA = 110  # cabe em duas linhas no celular
PALAVRA_VALIDA = re.compile(r"[a-z]+( [a-z]+)*")  # sem acento: o teclado só tem a-z; espaço entre palavras


def _normalizar(texto):
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if not unicodedata.combining(c))
    return sem_acento


def _arquivos():
    return sorted(f for f in os.listdir(PASTA_CATEGORIAS) if f.endswith(".json"))


def _ler(nome):
    with open(os.path.join(PASTA_CATEGORIAS, nome), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module", params=_arquivos())
def categoria(request):
    return request.param, _ler(request.param)


def test_estrutura_do_arquivo(categoria):
    nome, dados = categoria
    assert set(dados) == {"categoria", "ordem", "palavras"}
    assert isinstance(dados["categoria"], str) and dados["categoria"].strip() == dados["categoria"] != ""
    assert isinstance(dados["ordem"], int)
    assert dados["palavras"], "categoria vazia"


def test_nome_do_arquivo_corresponde_a_categoria(categoria):
    nome, dados = categoria
    esperado = _normalizar(dados["categoria"]).replace(" ", "-")
    assert nome == f"{esperado}.json"


def test_palavras_so_tem_letras_minusculas_sem_acento(categoria):
    _, dados = categoria
    invalidas = [p for p in dados["palavras"] if not PALAVRA_VALIDA.fullmatch(p) or not 3 <= len(p) <= 20]
    assert invalidas == []


def test_cada_palavra_tem_duas_dicas_diferentes_e_limpas(categoria):
    _, dados = categoria
    ruins = []
    for palavra, dicas in dados["palavras"].items():
        ok = (
            isinstance(dicas, list)
            and len(dicas) == 2
            and all(isinstance(d, str) and d == d.strip() and d for d in dicas)
            and dicas[0] != dicas[1]
            and all(len(d) <= TAMANHO_MAX_DICA for d in dicas)
        )
        if not ok:
            ruins.append(palavra)
    assert ruins == []


def test_dicas_nao_revelam_a_resposta(categoria):
    # nenhuma parte relevante (3+ letras) da resposta pode aparecer na dica, com ou sem acento
    _, dados = categoria
    vazadas = []
    for palavra, dicas in dados["palavras"].items():
        texto = _normalizar(" ".join(dicas))
        partes = [p for p in palavra.split() if len(p) >= 4] or [palavra]
        if any(p in texto for p in partes):
            vazadas.append(palavra)
    assert vazadas == []


def test_ordens_e_nomes_sao_unicos():
    todos = [_ler(n) for n in _arquivos()]
    assert len({d["ordem"] for d in todos}) == len(todos)
    assert len({d["categoria"] for d in todos}) == len(todos)


def test_carregador_respeita_a_ordem_dos_arquivos():
    esperadas = [d["categoria"] for d in sorted((_ler(n) for n in _arquivos()), key=lambda d: d["ordem"])]
    assert list(carregar_categorias()) == esperadas


def test_carregador_recusa_categoria_repetida(tmp_path):
    for i in (1, 2):
        (tmp_path / f"c{i}.json").write_text(json.dumps({"categoria": "Igual", "ordem": i, "palavras": {}}))
    with pytest.raises(ValueError, match="repetida"):
        carregar_categorias(str(tmp_path))
