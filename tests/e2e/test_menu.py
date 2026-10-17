"""Fluxo do menu da nova interface (/beta), de ponta a ponta no navegador."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def passo_visivel(pagina, nome):
    expect(pagina.locator(f'[data-passo="{nome}"]')).to_be_visible()


def test_fluxo_completo_ate_o_resumo(pagina):
    pagina.goto("/beta")
    passo_visivel(pagina, "inicio")
    pagina.get_by_role("button", name="Jogar").click()

    passo_visivel(pagina, "dificuldade")
    expect(pagina.get_by_role("heading", name="Escolha a dificuldade")).to_be_focused()
    expect(pagina.locator("[data-lista=dificuldades] .opcao")).to_have_count(3)
    pagina.get_by_role("listitem", name="Difícil: 4 tentativas, 1 dica").click()

    passo_visivel(pagina, "categoria")
    expect(pagina.locator("[data-resumo-dificuldade]").first).to_have_text("Difícil")
    expect(pagina.locator("[data-lista=categorias] .opcao")).to_have_count(10)
    pagina.get_by_role("listitem", name="Frutas, 50 palavras").click()

    passo_visivel(pagina, "pronto")
    expect(pagina.locator("[data-resumo-categoria]")).to_have_text("Frutas")
    expect(pagina.locator("[data-resumo-tentativas]")).to_have_text("4")
    assert pagina.erros == []


def test_modo_aleatorio_aparece_em_destaque(pagina):
    pagina.goto("/beta")
    pagina.get_by_role("button", name="Jogar").click()
    pagina.get_by_role("listitem", name="Médio: 6 tentativas, 2 dicas").click()
    destaque = pagina.locator("[data-lista=aleatorio] .opcao-destaque")
    expect(destaque).to_contain_text("10.000 palavras")
    destaque.click()
    expect(pagina.locator("[data-resumo-categoria]")).to_have_text("Modo aleatório")
    assert pagina.erros == []


def test_voltar_do_navegador_e_tecla_esc_voltam_um_passo(pagina):
    pagina.goto("/beta")
    pagina.get_by_role("button", name="Jogar").click()
    pagina.get_by_role("listitem", name="Fácil: 8 tentativas, 2 dicas").click()
    passo_visivel(pagina, "categoria")

    pagina.go_back()  # o "voltar" do navegador/celular
    passo_visivel(pagina, "dificuldade")
    expect(pagina.locator('[data-passo="categoria"]')).to_be_hidden()

    pagina.keyboard.press("Escape")
    passo_visivel(pagina, "inicio")
    assert pagina.erros == []


def test_dificuldade_escolhida_e_lembrada(pagina):
    pagina.goto("/beta")
    pagina.get_by_role("button", name="Jogar").click()
    pagina.get_by_role("listitem", name="Médio: 6 tentativas, 2 dicas").click()
    passo_visivel(pagina, "categoria")

    pagina.goto("/beta")
    pagina.get_by_role("button", name="Jogar").click()
    medio = pagina.get_by_role("listitem", name="Médio: 6 tentativas, 2 dicas")
    expect(medio).to_have_attribute("aria-pressed", "true")


def test_menu_funciona_so_com_teclado(pagina):
    pagina.goto("/beta")
    pagina.get_by_role("button", name="Jogar").focus()
    pagina.keyboard.press("Enter")
    passo_visivel(pagina, "dificuldade")
    pagina.keyboard.press("Tab")  # botão voltar
    pagina.keyboard.press("Tab")  # primeira dificuldade
    pagina.keyboard.press("Enter")
    passo_visivel(pagina, "categoria")


def test_recorde_da_interface_atual_aparece_no_inicio(pagina):
    pagina.goto("/beta")
    pagina.evaluate("localStorage.setItem('rankingJogoDaForca', JSON.stringify([340, 1250, 90]))")
    pagina.reload()
    expect(pagina.locator("[data-recorde]")).to_be_visible()
    expect(pagina.locator("[data-recorde-valor]")).to_have_text("1.250")


def test_falha_ao_carregar_catalogo_mostra_erro_e_permite_tentar_de_novo(pagina):
    falhar = {"ativo": True}

    def interceptar(rota):
        if falhar["ativo"]:
            rota.fulfill(status=503, body="indisponível")
        else:
            rota.continue_()

    pagina.route("**/api/catalogo", interceptar)
    pagina.goto("/beta")
    pagina.get_by_role("button", name="Jogar").click()
    passo_visivel(pagina, "erro")

    falhar["ativo"] = False
    pagina.get_by_role("button", name="Tentar de novo").click()
    passo_visivel(pagina, "dificuldade")


def test_sem_estouro_horizontal_em_nenhum_passo(pagina):
    pagina.goto("/beta")
    estouros = []
    pagina.get_by_role("button", name="Jogar").click()
    passo_visivel(pagina, "dificuldade")
    estouros.append(pagina.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"))
    pagina.locator("[data-lista=dificuldades] .opcao").first.click()
    passo_visivel(pagina, "categoria")
    estouros.append(pagina.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"))
    assert estouros == [0, 0]


def test_com_animacoes_ligadas_o_fluxo_tambem_funciona(navegador, servidor):
    contexto = navegador.new_context(base_url=servidor, reduced_motion="no-preference")
    pg = contexto.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto("/beta")
    pg.get_by_role("button", name="Jogar").click()
    pg.get_by_role("listitem", name="Fácil: 8 tentativas, 2 dicas").click()
    pg.get_by_role("listitem", name="Animais, 49 palavras").click()
    expect(pg.locator("[data-resumo-categoria]")).to_have_text("Animais")
    # depois da transição, o passo anterior fica escondido e o atual totalmente opaco
    expect(pg.locator('[data-passo="categoria"]')).to_be_hidden()
    pg.wait_for_function("getComputedStyle(document.querySelector('[data-passo=pronto]')).opacity === '1'")
    assert erros == []
    contexto.close()
