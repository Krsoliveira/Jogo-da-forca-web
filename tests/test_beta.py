from html.parser import HTMLParser

import pytest

from app import app


@pytest.fixture
def html():
    app.config.update(TESTING=True)
    resposta = app.test_client().get("/beta")
    assert resposta.status_code == 200
    return resposta.get_data(as_text=True)


def test_beta_tem_idioma_titulo_e_viewport(html):
    assert '<html lang="pt-br"' in html
    assert "<title>" in html
    assert 'name="viewport"' in html


class _ColetorInline(HTMLParser):
    """Encontra o que um CSP estrito bloquearia. O parser normaliza tags e atributos
    para minúsculas, então <SCRIPT> e STYLE= também são pegos."""

    def __init__(self):
        super().__init__()
        self.problemas = []

    def handle_starttag(self, tag, attrs):
        nomes = {nome for nome, _ in attrs}
        if tag == "script" and "src" not in nomes:
            self.problemas.append("script inline")
        if tag == "style":
            self.problemas.append("bloco <style>")
        if "style" in nomes:
            self.problemas.append(f"atributo style em <{tag}>")
        self.problemas += [f"evento {n} em <{tag}>" for n in nomes if n.startswith("on")]


def _inline(html):
    coletor = _ColetorInline()
    coletor.feed(html)
    return coletor.problemas


def test_beta_nao_usa_script_estilo_nem_evento_inline(html):
    # Pré-requisito para um CSP estrito (sem 'unsafe-inline').
    assert _inline(html) == []


@pytest.mark.parametrize(
    "trecho",
    [
        "<SCRIPT>alert(1)</SCRIPT>",
        "<script>x()</script>",
        '<div STYLE="color:red">',
        "<Style>a{}</Style>",
        '<img OnError="x()">',
    ],
)
def test_detector_de_inline_pega_variacoes_de_maiusculas(trecho):
    assert _inline(trecho) != []


def test_beta_nao_depende_de_servidores_externos(html):
    assert "googleapis" not in html
    assert "cdn." not in html


def test_beta_tem_acessibilidade_basica(html):
    assert "Ir para o conteúdo" in html  # link para pular a navegação
    assert 'role="progressbar"' in html
    assert 'aria-label="Experiência"' in html
    assert 'role="group"' in html  # o teclado é anunciado como um grupo


@pytest.mark.parametrize(
    "caminho",
    ["img/favicon.svg"],
)
def test_arquivos_estaticos_da_interface_existem(caminho):
    resposta = app.test_client().get(f"/static/{caminho}")
    assert resposta.status_code == 200


def test_beta_carrega_o_bundle_e_o_css_compilados(html):
    # gerados por `npm run build` (fora do git); o CI confere que o build produz os arquivos
    assert "js/dist/beta.js" in html
    assert "css/app.css" in html


def test_interface_atual_continua_em_raiz():
    resposta = app.test_client().get("/")
    assert resposta.status_code == 200
    assert "Jogo da Forca" in resposta.get_data(as_text=True)
