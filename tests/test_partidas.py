import base64
import json

import pytest

from app import app
from forca.partidas import ArmazenamentoDePartidas


class Relogio:
    def __init__(self):
        self.agora = 0.0

    def __call__(self):
        return self.agora


@pytest.fixture
def relogio():
    return Relogio()


@pytest.fixture
def armazenamento(relogio):
    return ArmazenamentoDePartidas(ttl_segundos=60, max_partidas=3, relogio=relogio)


def test_criar_e_obter(armazenamento):
    pid = armazenamento.criar({"palavra": "uva"})
    assert armazenamento.obter(pid) == {"palavra": "uva"}


def test_ids_sao_unicos_e_imprevisiveis(armazenamento):
    ids = {ArmazenamentoDePartidas(max_partidas=1000).criar({}) for _ in range(200)}
    assert len(ids) == 200
    assert all(len(pid) >= 43 for pid in ids)  # token_urlsafe(32) = 256 bits


@pytest.mark.parametrize("pid", [None, "", "inexistente", 123, ["x"]])
def test_obter_rejeita_ids_invalidos(armazenamento, pid):
    assert armazenamento.obter(pid) is None


def test_partida_expira_apos_o_prazo(armazenamento, relogio):
    pid = armazenamento.criar({"a": 1})
    relogio.agora = 61
    assert armazenamento.obter(pid) is None
    assert len(armazenamento) == 0


def test_usar_a_partida_renova_o_prazo(armazenamento, relogio):
    pid = armazenamento.criar({"a": 1})
    relogio.agora = 50
    assert armazenamento.obter(pid) is not None
    relogio.agora = 100  # 50s desde o último uso, dentro do prazo de 60s
    assert armazenamento.obter(pid) is not None


def test_teto_descarta_a_menos_usada_recentemente(armazenamento, relogio):
    a = armazenamento.criar({"n": "a"})
    relogio.agora = 1
    b = armazenamento.criar({"n": "b"})
    relogio.agora = 2
    c = armazenamento.criar({"n": "c"})
    relogio.agora = 3
    armazenamento.obter(a)  # a vira a mais recente
    d = armazenamento.criar({"n": "d"})
    assert len(armazenamento) == 3
    assert armazenamento.obter(b) is None  # b era a menos usada
    assert all(armazenamento.obter(x) is not None for x in (a, c, d))


def test_criar_expurga_partidas_vencidas(armazenamento, relogio):
    armazenamento.criar({})
    armazenamento.criar({})
    relogio.agora = 120
    armazenamento.criar({})
    assert len(armazenamento) == 1


def test_apagar(armazenamento):
    pid = armazenamento.criar({})
    armazenamento.apagar(pid)
    assert armazenamento.obter(pid) is None
    armazenamento.apagar(pid)  # apagar de novo não dá erro


# --- Segurança: a palavra secreta não pode vazar pelo cookie ---


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def _cookie_decodificado(client):
    cookie = client.get_cookie("session")
    assert cookie is not None
    payload = cookie.value.split(".")[0]
    payload += "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload).decode()


def test_cookie_guarda_so_o_identificador_e_nao_a_palavra(client):
    client.get("/novo_jogo", query_string={"category": "Frutas", "difficulty": "medio"})
    with client.session_transaction() as s:
        pid = s["pid"]
        assert set(s.keys()) == {"pid"}
    palavra = app.extensions["partidas"].obter(pid)["palavra"]
    bruto = _cookie_decodificado(client)
    assert palavra not in bruto
    assert set(json.loads(bruto)) == {"pid"}


def test_resposta_nao_revela_a_palavra_durante_a_rodada(client):
    dados = client.get("/novo_jogo", query_string={"category": "Frutas"}).get_json()
    assert set(dados["palavra_oculta"]) == {"_"}
    with client.session_transaction() as s:
        palavra = app.extensions["partidas"].obter(s["pid"])["palavra"]
    assert palavra not in json.dumps(dados)


def test_pid_forjado_nao_da_acesso(client):
    with client.session_transaction() as s:
        s["pid"] = "pid-que-nao-existe"
    assert client.post("/tentativa", json={"letra": "a"}).status_code == 400
    assert client.get("/proxima_palavra").status_code == 400


def test_partida_expirada_exige_novo_jogo(client):
    client.get("/novo_jogo", query_string={"category": "Frutas"})
    with client.session_transaction() as s:
        app.extensions["partidas"].apagar(s["pid"])  # simula expiração ou reinício do servidor
    assert client.post("/tentativa", json={"letra": "a"}).status_code == 400


def test_novo_jogo_descarta_a_partida_anterior(client):
    client.get("/novo_jogo", query_string={"category": "Frutas"})
    with client.session_transaction() as s:
        antigo = s["pid"]
    client.get("/novo_jogo", query_string={"category": "Animais"})
    with client.session_transaction() as s:
        assert s["pid"] != antigo
    assert app.extensions["partidas"].obter(antigo) is None


def _pid(cliente):
    with cliente.session_transaction() as s:
        return s["pid"]


def test_duas_pessoas_tem_partidas_independentes():
    app.config.update(TESTING=True)
    ana, bia = app.test_client(), app.test_client()
    ana.get("/novo_jogo", query_string={"category": "Frutas"})
    bia.get("/novo_jogo", query_string={"category": "Frutas"})
    pid_ana, pid_bia = _pid(ana), _pid(bia)
    assert pid_ana != pid_bia

    store = app.extensions["partidas"]
    letra = next(c for c in "abcdefghijklmnopqrstuvwxyz" if c not in store.obter(pid_ana)["palavra"])
    ana.post("/tentativa", json={"letra": letra})
    assert store.obter(pid_ana)["erros"] == 1
    assert store.obter(pid_bia)["erros"] == 0
