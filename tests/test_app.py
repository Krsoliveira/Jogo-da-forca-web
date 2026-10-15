import pytest

from app import app, PALAVRAS_POR_CATEGORIA


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def iniciar(client, dificuldade="medio", categoria="Frutas"):
    return client.get("/novo_jogo", query_string={"category": categoria, "difficulty": dificuldade})


def palavra_atual(client):
    with client.session_transaction() as s:
        return s["palavra"]


def tentar(client, letra):
    return client.post("/tentativa", json={"letra": letra})


def letra_errada(palavra):
    return next(c for c in "abcdefghijklmnopqrstuvwxyz" if c not in palavra)


def test_novo_jogo_rejeita_entrada_invalida(client):
    assert iniciar(client, categoria="Inexistente").status_code == 400
    assert iniciar(client, dificuldade="impossivel").status_code == 400


def test_novo_jogo_oculta_palavra(client):
    data = iniciar(client).get_json()
    assert set(data["palavra_oculta"]) == {"_"}
    assert data["tentativas_restantes"] == 6


@pytest.mark.parametrize("letra", ["", "ab", "1", "é", None, 5])
def test_tentativa_rejeita_letra_invalida(client, letra):
    iniciar(client)
    assert tentar(client, letra).status_code == 400


def test_tentativa_sem_json_ou_sem_jogo(client):
    assert tentar(client, "a").status_code == 400
    iniciar(client)
    assert client.post("/tentativa", data="lixo").status_code == 400


def test_letra_certa_pontua_e_errada_consome_tentativa(client):
    iniciar(client)
    palavra = palavra_atual(client)
    ok = tentar(client, palavra[0]).get_json()
    assert ok["erros"] == 0 and ok["pontuacao"] == 10 * palavra.count(palavra[0]) or ok.get("vitoria_rodada")
    if not ok.get("vitoria_rodada"):
        err = tentar(client, letra_errada(palavra)).get_json()
        assert err["erros"] == 1 and err["tentativas_restantes"] == 5


def test_letra_repetida_nao_penaliza(client):
    iniciar(client)
    errada = letra_errada(palavra_atual(client))
    tentar(client, errada)
    assert tentar(client, errada).get_json()["erros"] == 1


def test_derrota_encerra_rodada_e_bloqueia_novas_jogadas(client):
    iniciar(client, "dificil")
    palavra = palavra_atual(client)
    erradas = [c for c in "abcdefghijklmnopqrstuvwxyz" if c not in palavra][:4]
    for l in erradas:
        data = tentar(client, l).get_json()
    assert data["fim_de_jogo"] and data["pontuacao"] == 0
    assert tentar(client, palavra[0]).status_code == 400


def test_vitoria_nao_pode_ser_repetida_para_farmar_pontos(client):
    iniciar(client)
    palavra = palavra_atual(client)
    data = client.post("/chute", json={"palavra": palavra}).get_json()
    assert data["vitoria_rodada"]
    pontos = data["pontuacao"]
    assert client.post("/chute", json={"palavra": palavra}).status_code == 400
    assert client.get("/proxima_palavra").get_json()["pontuacao"] == pontos


def test_chute_errado_penaliza_e_consome_tentativa(client):
    iniciar(client)
    data = client.post("/chute", json={"palavra": "zzzz"}).get_json()
    assert data["erros"] == 1


def test_dificil_mostra_so_uma_dica(client):
    dicas = iniciar(client, "dificil").get_json()["dicas"]
    assert dicas[1] == ""


def test_palavras_nao_repetem_ate_esgotar_categoria(client):
    iniciar(client)
    vistas = {palavra_atual(client)}
    total = len(PALAVRAS_POR_CATEGORIA["Frutas"])
    for _ in range(total - 1):
        client.post("/chute", json={"palavra": palavra_atual(client)})
        client.get("/proxima_palavra")
        vistas.add(palavra_atual(client))
    assert len(vistas) == total
