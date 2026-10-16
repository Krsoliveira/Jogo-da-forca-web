"""Gera forca/dados/palavras_gerais.json a partir do Dicionário Aberto e de uma lista de frequência.

Uso (na raiz do projeto):
    pip install -r requirements-dados.txt
    python scripts/gerar_banco.py

Por que duas fontes:
- Dicionário Aberto (domínio público): diz quais palavras existem, a classe gramatical e traz a
  definição. Mas não mede frequência, e mistura palavras comuns com raríssimas.
- wordfreq: ordena por frequência de uso, para ficarmos só com palavras que as pessoas conhecem.
  É usado apenas aqui, na geração; seus dados não são redistribuídos com o jogo.

As definições saem na ortografia antiga e ainda não servem como dica; ficam em
`definicao_original` como apoio para a geração das dicas finais.
"""

import argparse
import glob
import hashlib
import json
import os
import re
import unicodedata
import urllib.request
import zipfile

# Fonte fixada num commit específico, com hash do arquivo, para o resultado ser reproduzível.
COMMIT_DICIONARIO = "e60a4f3dcbb70c70bc9b1d7cff9e87d53a9206aa"
URL_DICIONARIO = (
    f"https://raw.githubusercontent.com/ambs/Dicionario-Aberto/{COMMIT_DICIONARIO}/Resources/xmls.zip"
)
SHA256_DICIONARIO = "f7e8ca35715a22a5e9e7fdd9c795d367e3e41182d5366b257fe7d78b15412a38"

QUANTIDADE = 10_000
TAMANHO_MIN, TAMANHO_MAX = 4, 12
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOQUEADAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "palavras_bloqueadas.txt")
SAIDA = os.path.join(RAIZ, "forca", "dados", "palavras_gerais.json")

PADRAO_PALAVRA = re.compile(rf"[a-z]{{{TAMANHO_MIN},{TAMANHO_MAX}}}")
PADRAO_CLASSE = re.compile(r"(m|f|adj|v)\.")
PADRAO_DEFINICAO_FRACA = re.compile(r"(O mesmo que|Ant\.|V\.|Cf\.|Forma|Plural|Fem|Gerundio|Part)")
USOS_EXCLUIDOS = {"style", "geo", "time", "reg"}  # popular, provincial, desusado, regional etc.
# Sequências típicas da ortografia anterior à reforma (ex.: pharmacia, mathematica, commum).
SEQUENCIAS_ARCAICAS = ("ph", "th", "ff", "ll", "mm", "nn", "pp", "tt", "bb", "dd", "gg", "zz", "ck", "y")


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def carregar_bloqueadas(caminho=BLOQUEADAS):
    with open(caminho, encoding="utf-8") as f:
        return {linha.strip() for linha in f if linha.strip() and not linha.startswith("#")}


def classificar(palavra, posicao):
    """Dificuldade a partir do tamanho e da posição na lista de frequência (1 = mais comum)."""
    if len(palavra) <= 7 and posicao <= 5000:
        return "facil"
    if len(palavra) >= 10 or posicao > 8000:
        return "dificil"
    return "medio"


def aceitar_entrada(palavra, classe, usos, definicao, bloqueadas):
    """Decide se um verbete do dicionário serve para o jogo."""
    if not PADRAO_PALAVRA.fullmatch(palavra) or palavra in bloqueadas:
        return False
    if not PADRAO_CLASSE.match(classe):
        return False
    if classe.startswith("v.") and not palavra.endswith(("ar", "er", "ir", "or")):
        return False  # só verbos no infinitivo
    if any(tipo in USOS_EXCLUIDOS for tipo, _ in usos):
        return False
    if len(definicao) < 15 or PADRAO_DEFINICAO_FRACA.match(definicao):
        return False
    return palavra not in sem_acento(definicao).lower()  # a definição não pode entregar a palavra


def ler_verbetes(pasta_xml):
    from defusedxml import ElementTree as ET  # parser seguro; só necessário para gerar o banco

    for arquivo in sorted(glob.glob(os.path.join(pasta_xml, "*.xml"))):
        if arquivo.endswith(("Geo.xml", "Names.xml")):  # lugares e nomes próprios
            continue
        for e in ET.parse(arquivo).getroot().iter("entry"):
            orth = (e.findtext("form/orth") or "").strip()
            sentidos = e.findall("sense")
            if not orth or not sentidos:
                continue
            s = sentidos[0]
            d = s.find("def")
            definicao = " ".join("".join(d.itertext()).split()) if d is not None else ""
            usos = [(u.get("type"), (u.text or "").strip()) for u in s.findall("usg")]
            yield sem_acento(orth).lower(), (s.findtext("gramGrp") or "").strip(), usos, definicao


def baixar_dicionario(cache):
    os.makedirs(cache, exist_ok=True)
    zip_path = os.path.join(cache, "xmls.zip")
    if not os.path.exists(zip_path):
        print(f"Baixando {URL_DICIONARIO}")
        urllib.request.urlretrieve(URL_DICIONARIO, zip_path)  # noqa: S310 # nosec B310 (URL fixa, https)
    with open(zip_path, "rb") as f:
        if hashlib.sha256(f.read()).hexdigest() != SHA256_DICIONARIO:
            raise SystemExit("Hash do dicionário não confere; arquivo corrompido ou adulterado.")
    pasta = os.path.join(cache, "dicionario")
    if not os.path.isdir(pasta):
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(pasta)  # noqa: S202 # nosec B202 (arquivo verificado por hash acima)
    return os.path.join(pasta, "xmls")


def tem_grafia_arcaica(palavra):
    return any(seq in palavra for seq in SEQUENCIAS_ARCAICAS)


def eh_plural_de_outra(palavra, candidatas):
    """'indios' é plural de 'indio': fica só o singular, que é o que se espera numa forca."""
    return palavra.endswith("s") and palavra[:-1] in candidatas


def montar_banco(candidatas, frequencia, quantidade=QUANTIDADE):
    """Cruza as candidatas com a lista de frequência e devolve as `quantidade` mais comuns."""
    banco, vistas = [], set()
    for palavra in frequencia:
        if tem_grafia_arcaica(palavra) or eh_plural_de_outra(palavra, candidatas):
            continue
        if palavra in candidatas and palavra not in vistas:
            vistas.add(palavra)
            classe, definicao = candidatas[palavra]
            posicao = len(banco) + 1
            banco.append({
                "palavra": palavra,
                "classe": classe,
                "dificuldade": classificar(palavra, posicao),
                "definicao_original": definicao,
            })
            if len(banco) == quantidade:
                break
    return banco


def main():
    from wordfreq import top_n_list  # só necessário para gerar; fica fora do jogo e do CI

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", default=os.path.join(RAIZ, ".cache"))
    args = parser.parse_args()

    bloqueadas = carregar_bloqueadas()
    candidatas = {}
    for palavra, classe, usos, definicao in ler_verbetes(baixar_dicionario(args.cache)):
        if aceitar_entrada(palavra, classe, usos, definicao, bloqueadas):
            candidatas.setdefault(palavra, (classe, definicao))

    frequencia = [sem_acento(w) for w in top_n_list("pt", 80_000) if re.fullmatch(r"[a-zà-ú]+", w)]
    banco = montar_banco(candidatas, frequencia)
    if len(banco) < QUANTIDADE:
        raise SystemExit(f"Só {len(banco)} palavras; esperado {QUANTIDADE}.")

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
        json.dump(banco, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    por_nivel = {n: sum(1 for p in banco if p["dificuldade"] == n) for n in ("facil", "medio", "dificil")}
    print(f"{len(banco)} palavras gravadas em {os.path.relpath(SAIDA, RAIZ)} | {por_nivel}")


if __name__ == "__main__":
    main()
