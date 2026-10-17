"""Partida completa na nova interface (/beta), de ponta a ponta no navegador.

O servidor de teste roda no mesmo processo, então os testes leem a palavra sorteada direto do
armazenamento de partidas para jogar de forma determinística (ganhar ou perder de propósito).
"""

import re

import pytest
from playwright.sync_api import expect

from app import app

pytestmark = pytest.mark.e2e

ALFABETO = "abcdefghijklmnopqrstuvwxyz"


def palavra_atual():
    """Palavra da partida usada mais recentemente (a do teste em andamento)."""
    dados = app.extensions["partidas"]._dados
    _, estado = next(reversed(dados.values()))
    return estado["palavra"]


def comecar(pagina, dificuldade="Médio: 6 tentativas, 2 dicas", categoria="Frutas, 50 palavras"):
    pagina.goto("/beta")
    pagina.get_by_role("button", name="Jogar").click()
    pagina.get_by_role("listitem", name=dificuldade).click()
    if categoria == "aleatorio":
        pagina.locator("[data-lista=aleatorio] .opcao").click()
    else:
        pagina.get_by_role("listitem", name=categoria).click()
    expect(pagina.locator('[data-passo="jogo"]')).to_be_visible()
    expect(pagina.locator("[data-palavra] .casa").first).to_be_visible()
    return palavra_atual()


def letras_erradas(palavra):
    return [c for c in ALFABETO if c not in palavra]


def test_letra_certa_revela_casas_e_marca_a_tecla(pagina):
    palavra = comecar(pagina)
    letra = palavra[0]
    pagina.get_by_role("button", name=f"Letra {letra.upper()}", exact=True).click()
    expect(pagina.locator(f'[data-letra="{letra}"]')).to_have_class(re.compile(r"tecla-certa"))
    reveladas = pagina.locator("[data-palavra] .casa-revelada")
    expect(reveladas).to_have_count(palavra.count(letra))
    # pontos da letra ficam "em jogo": só viram pontos garantidos quando a palavra é acertada
    expect(pagina.locator("[data-hud-pontos]")).to_have_text("0")
    expect(pagina.locator("[data-hud-em-jogo]")).to_have_text(re.compile(r"^\+\d+ em jogo$"))
    assert pagina.erros == []


def test_letra_errada_tira_vida_e_desenha_a_forca(pagina):
    palavra = comecar(pagina)
    errada = letras_erradas(palavra)[0]
    pagina.get_by_role("button", name=f"Letra {errada.upper()}", exact=True).click()
    expect(pagina.locator("[data-vidas] .vida-perdida")).to_have_count(1)
    expect(pagina.locator("[data-forca]")).to_have_attribute("aria-label", "Forca: 1 de 6 erros")
    assert pagina.erros == []


def test_vencer_pelo_teclado_fisico_passa_para_a_proxima_palavra(pagina):
    palavra = comecar(pagina)
    for letra in sorted(set(c for c in palavra if c.isalpha())):
        pagina.keyboard.press(letra)
    expect(pagina.locator(".toast").first).to_be_visible()
    # depois da comemoração, uma nova palavra começa com o teclado limpo
    expect(pagina.locator("[data-teclado] .tecla:not([disabled])")).to_have_count(26, timeout=8000)
    expect(pagina.locator("[data-palavra] .casa-revelada")).to_have_count(0)
    assert int(pagina.locator("[data-hud-pontos]").inner_text()) > 0
    assert pagina.erros == []


def test_perder_abre_o_fim_de_jogo_com_a_palavra(pagina):
    palavra = comecar(pagina, dificuldade="Difícil: 4 tentativas, 1 dica")
    for letra in letras_erradas(palavra)[:4]:
        pagina.get_by_role("button", name=f"Letra {letra.upper()}", exact=True).click()
    dialogo = pagina.locator("[data-fim]")
    expect(dialogo).to_be_visible(timeout=8000)
    expect(dialogo.locator("[data-fim-palavra]")).to_have_text(palavra.upper())
    expect(pagina.locator("[data-teclado] .tecla:not([disabled])")).to_have_count(0)

    dialogo.get_by_role("button", name="Jogar de novo").click()
    expect(dialogo).to_be_hidden()
    expect(pagina.locator("[data-vidas] .vida-perdida")).to_have_count(0)
    assert pagina.erros == []


def test_chute_certo_com_acento_e_maiuscula_vence(pagina):
    palavra = comecar(pagina)
    pagina.get_by_role("button", name="Arriscar a palavra").click()
    campo = pagina.get_by_label("Qual é a palavra?")
    expect(campo).to_be_focused()
    campo.fill(palavra.upper().replace("A", "Á"))
    campo.press("Enter")
    expect(pagina.locator(".toast").first).to_be_visible()
    expect(pagina.locator("[data-vidas] .vida-perdida")).to_have_count(0)
    assert pagina.erros == []


def test_chute_errado_custa_uma_vida(pagina):
    comecar(pagina)
    pagina.get_by_role("button", name="Arriscar a palavra").click()
    pagina.get_by_label("Qual é a palavra?").fill("zzzzzz")
    pagina.get_by_role("button", name="Confirmar").click()
    expect(pagina.locator("[data-vidas] .vida-perdida")).to_have_count(1)
    expect(pagina.get_by_label("Qual é a palavra?")).to_be_hidden()


def test_digitar_no_chute_nao_joga_letras(pagina):
    comecar(pagina)
    pagina.get_by_role("button", name="Arriscar a palavra").click()
    pagina.get_by_label("Qual é a palavra?").press_sequentially("xyz")
    pagina.keyboard.press("Escape")  # fecha o chute sem sair da partida
    expect(pagina.locator('[data-passo="jogo"]')).to_be_visible()
    expect(pagina.locator("[data-teclado] .tecla[disabled]")).to_have_count(0)


def test_palavra_com_varias_partes_mantem_os_grupos(pagina):
    comecar(pagina, categoria="Cidades, 50 palavras")
    palavra = palavra_atual()
    grupos = pagina.locator("[data-palavra] .palavra-grupo")
    expect(grupos).to_have_count(len(palavra.split(" ")))


def test_sessao_expirada_mostra_aviso_em_vez_de_quebrar(pagina):
    comecar(pagina)
    app.extensions["partidas"]._dados.clear()  # simula reinício do servidor
    pagina.get_by_role("button", name="Letra Q", exact=True).click()
    dialogo = pagina.locator("[data-fim]")
    expect(dialogo).to_be_visible()
    expect(dialogo.locator("[data-fim-titulo]")).to_have_text("Sua partida expirou")
    dialogo.get_by_role("button", name="Jogar de novo").click()
    expect(dialogo).to_be_hidden()
    expect(pagina.locator("[data-palavra] .casa").first).to_be_visible()


def test_sair_pelo_voltar_salva_os_pontos_garantidos_no_ranking(pagina):
    palavra = comecar(pagina)
    for letra in sorted(set(c for c in palavra if c.isalpha())):
        pagina.keyboard.press(letra)
    expect(pagina.locator("[data-teclado] .tecla:not([disabled])")).to_have_count(26, timeout=8000)
    pontos = int(pagina.locator("[data-hud-pontos]").inner_text())
    assert pontos > 0
    pagina.go_back()
    expect(pagina.locator('[data-passo="categoria"]')).to_be_visible()
    ranking = pagina.evaluate("JSON.parse(localStorage.getItem('rankingJogoDaForca'))")
    assert ranking == [pontos]


def test_tela_de_jogo_sem_estouro_horizontal(pagina):
    comecar(pagina, categoria="Esportes, 100 palavras")
    estouro = pagina.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert estouro == 0


def test_partida_com_animacoes_ligadas_vence_e_depois_perde(navegador, servidor):
    contexto = navegador.new_context(
        base_url=servidor, reduced_motion="no-preference", viewport={"width": 390, "height": 844}
    )
    pg = contexto.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)

    palavra = comecar(pg)
    for letra in sorted(set(c for c in palavra if c.isalpha())):
        pg.keyboard.press(letra)  # digitando rápido: a fila garante que nenhuma letra se perca
    expect(pg.locator(".toast").first).to_be_visible()
    expect(pg.locator("[data-teclado] .tecla:not([disabled])")).to_have_count(26, timeout=8000)

    proxima = palavra_atual()
    assert proxima != palavra
    for letra in letras_erradas(proxima)[:6]:
        pg.keyboard.press(letra)
    expect(pg.locator("[data-fim]")).to_be_visible(timeout=8000)
    expect(pg.locator("[data-fim-palavra]")).to_have_text(proxima.upper())
    assert erros == []
    contexto.close()


def test_letra_digitada_durante_a_vitoria_nao_conta_na_proxima_palavra(pagina):
    palavra = comecar(pagina)
    sobras = letras_erradas(palavra)[:3]
    # a última letra certa e, logo em seguida, letras erradas "atrasadas" na mesma rajada
    for letra in [*sorted(set(c for c in palavra if c.isalpha())), *sobras]:
        pagina.keyboard.press(letra)
    expect(pagina.locator(".toast").first).to_be_visible()
    expect(pagina.locator("[data-teclado] .tecla:not([disabled])")).to_have_count(26, timeout=8000)
    expect(pagina.locator("[data-vidas] .vida-perdida")).to_have_count(0)
    assert app.extensions["partidas"]._dados and palavra_atual() != palavra


def test_teclas_tem_a_mesma_largura_em_todas_as_linhas(pagina):
    comecar(pagina)
    larguras = pagina.evaluate(
        "[...document.querySelectorAll('[data-teclado] .tecla')].map(t => Math.round(t.getBoundingClientRect().width))"
    )
    assert max(larguras) - min(larguras) <= 1
