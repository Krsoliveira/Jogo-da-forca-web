"""Rotas HTTP do jogo.

O cookie de sessão guarda só o identificador da partida (`pid`). O estado completo (palavra
secreta, erros, pontuação) fica no servidor, em `forca.partidas`, e nunca é enviado ao navegador.
"""

import random

from flask import Blueprint, current_app, g, jsonify, render_template, request, session

from . import banco, regras
from .config import (
    ALEATORIO,
    DIFICULDADE_CONFIG,
    DIFICULDADES,
    LETRAS_VALIDAS,
    PALAVRAS_RECENTES,
    PENALIDADE_CHUTE_ERRADO,
    XP_PARA_PROXIMO_NIVEL,
)
from .palavras import PALAVRAS_POR_CATEGORIA

bp = Blueprint("jogo", __name__)

CATEGORIAS = [*PALAVRAS_POR_CATEGORIA, ALEATORIO]


def _armazenamento():
    return current_app.extensions["partidas"]


def _partida():
    """Estado da partida do cookie atual, ou None se não houver partida válida."""
    pid = session.get("pid")
    estado = _armazenamento().obter(pid) if pid else None
    if estado is not None:
        g.pid, g.partida = pid, estado
    return estado


@bp.after_request
def _persistir_partida(resposta):
    # Salva o estado alterado ao fim da requisição (necessário se o armazenamento for externo).
    if "partida" in g:
        _armazenamento().salvar(g.pid, g.partida)
    return resposta


def _erro(mensagem, status=400):
    return jsonify({"erro": mensagem}), status


def _dicas(categoria, palavra, dificuldade):
    base = banco.dicas(palavra) if categoria == ALEATORIO else PALAVRAS_POR_CATEGORIA[categoria][palavra]
    return regras.dicas_para(base, dificuldade)


def _pontos(garantidos, em_jogo):
    """Pontos já garantidos (palavras acertadas) e os da palavra atual, que só contam se ela for acertada.

    A interface mostra os dois separados; `pontuacao` (a soma) continua existindo para a versão atual.
    """
    return {"pontos_garantidos": garantidos, "pontos_em_jogo": em_jogo}


def _campos_nivel(partida):
    return {
        "nivel": partida.get("nivel", 1),
        "xp_atual": partida.get("xp_atual", 0),
        "xp_necessario": XP_PARA_PROXIMO_NIVEL,
    }


def _sortear_da_categoria(partida, categoria):
    disponiveis = partida.setdefault("palavras_disponiveis_por_categoria", {})

    # Quando o baralho da categoria acaba, embaralha de novo (jogo contínuo).
    if not disponiveis.get(categoria):
        palavras = list(PALAVRAS_POR_CATEGORIA[categoria].keys())
        random.shuffle(palavras)
        disponiveis[categoria] = palavras

    return disponiveis[categoria].pop()


def _sortear_aleatoria(partida, dificuldade):
    """Sorteia do banco geral na dificuldade atual, evitando as últimas palavras jogadas.

    Guardar só as recentes (e não um baralho de milhares de palavras) mantém o estado da partida
    pequeno; com milhares de candidatas, dez tentativas bastam para fugir das repetições.
    """
    candidatas = banco.palavras(dificuldade)
    recentes = partida.setdefault("palavras_recentes", [])
    # S311/B311: sorteio de jogo, não é segredo
    for _ in range(10):
        palavra = random.choice(candidatas)  # noqa: S311 # nosec B311
        if palavra not in recentes:
            break
    recentes.append(palavra)
    del recentes[:-PALAVRAS_RECENTES]
    return palavra


def _servir_proxima_palavra(partida, categoria, dificuldade):
    if categoria == ALEATORIO:
        palavra = _sortear_aleatoria(partida, dificuldade)
    else:
        palavra = _sortear_da_categoria(partida, categoria)
    max_erros = DIFICULDADE_CONFIG[dificuldade]

    partida.update(
        palavra=palavra,
        letras_tentadas=[],
        erros=0,
        pontos_rodada=0,
        max_erros=max_erros,
    )

    return {
        "palavra_oculta": regras.mascarar(palavra, []),
        "dicas": _dicas(categoria, palavra, dificuldade),
        "tentativas_restantes": max_erros,
        "erros": 0,
        "letras_tentadas": [],
        "pontuacao": partida.get("pontuacao_partida", 0),
        **_pontos(partida.get("pontuacao_partida", 0), 0),
        "dificuldade": dificuldade,
        **_campos_nivel(partida),
    }


@bp.route("/")
def pagina_inicial():
    return render_template("index.html", version=current_app.config["VERSAO_ASSETS"])


@bp.route("/beta")
def beta():
    """Nova interface, em construção. A interface atual continua em `/`."""
    return render_template("app.html", version=current_app.config["VERSAO_ASSETS"])


@bp.route("/beta/estilo")
def beta_estilo():
    """Guia de estilo da nova interface (cores, componentes e animações)."""
    return render_template("estilo.html", version=current_app.config["VERSAO_ASSETS"])


@bp.route("/health")
def health():
    """Usado pelo healthcheck do Railway para saber se o app está de pé."""
    return jsonify(status="ok")


@bp.route("/categorias")
def get_categorias():
    return jsonify(CATEGORIAS)


@bp.route("/api/catalogo")
def catalogo():
    """Opções do menu: dificuldades com tentativas e categorias com a quantidade de palavras."""
    dificuldades = [
        {"id": d, "tentativas": DIFICULDADE_CONFIG[d], "dicas": 1 if d == "dificil" else 2}  # difícil esconde a 2ª dica
        for d in DIFICULDADES
    ]
    categorias = [
        {"nome": nome, "palavras": len(palavras), "aleatorio": False}
        for nome, palavras in PALAVRAS_POR_CATEGORIA.items()
    ]
    total_banco = sum(len(banco.palavras(d)) for d in DIFICULDADES)
    categorias.append({"nome": ALEATORIO, "palavras": total_banco, "aleatorio": True})
    resposta = jsonify(dificuldades=dificuldades, categorias=categorias)
    resposta.cache_control.public = True
    resposta.cache_control.max_age = 300  # muda só a cada deploy
    return resposta


@bp.route("/novo_jogo")
def novo_jogo():
    categoria = request.args.get("category")
    dificuldade = request.args.get("difficulty", "medio")

    if categoria not in CATEGORIAS:
        return _erro("Categoria inválida.")
    if dificuldade not in DIFICULDADE_CONFIG:
        return _erro("Dificuldade inválida.")

    antigo = session.get("pid")
    if antigo:
        _armazenamento().apagar(antigo)

    partida = {
        "categoria_atual": categoria,
        "dificuldade_atual": dificuldade,
        "vitorias_consecutivas": 0,
        "pontuacao_partida": 0,
        "nivel": 1,
        "xp_atual": 0,
    }
    resposta = _servir_proxima_palavra(partida, categoria, dificuldade)

    session.clear()
    session["pid"] = _armazenamento().criar(partida)
    return jsonify(resposta)


@bp.route("/proxima_palavra")
def proxima_palavra():
    partida = _partida()
    if not partida or not partida.get("categoria_atual"):
        return _erro("Sessão inválida.")
    return jsonify(_servir_proxima_palavra(partida, partida["categoria_atual"], partida["dificuldade_atual"]))


def _registrar_vitoria(partida, erros, max_erros):
    """Aplica pontos, XP, nível e dificuldade. Retorna (pontos, notificacao, levelup)."""
    pontos = regras.pontos_da_vitoria(partida["pontos_rodada"], erros, max_erros)
    partida["pontuacao_partida"] += pontos
    partida["vitorias_consecutivas"] += 1
    partida["nivel"], partida["xp_atual"], levelup = regras.aplicar_xp(partida["nivel"], partida["xp_atual"], pontos)

    notificacao = f"LEVEL UP! Você alcançou o nível {partida['nivel']}!" if levelup else f"+{pontos} Pontos!"

    nova = regras.proxima_dificuldade(partida["dificuldade_atual"], partida["vitorias_consecutivas"])
    if nova:
        partida["dificuldade_atual"] = nova
        aviso = f"Dificuldade aumentada para {nova.upper()}!"
        notificacao = f"{notificacao} {aviso}" if levelup else aviso

    return pontos, notificacao, levelup


def processar_jogada(partida, erros, pontos_ganhos, letras_tentadas):
    palavra = partida["palavra"]
    max_erros = partida.get("max_erros", 6)
    oculta = regras.mascarar(palavra, letras_tentadas)
    partida["pontos_rodada"] = partida.get("pontos_rodada", 0) + pontos_ganhos

    base = {
        "letras_tentadas": sorted(letras_tentadas),
        "erros": erros,
        "tentativas_restantes": max_erros - erros,
    }

    if "_" not in oculta:
        _, notificacao, levelup = _registrar_vitoria(partida, erros, max_erros)
        partida.pop("palavra")  # rodada encerrada: impede repetir a jogada para farmar pontos
        return jsonify({
            **base,
            "vitoria_rodada": True,
            "palavra_oculta": palavra,
            "notificacao": notificacao,
            "pontuacao": partida["pontuacao_partida"],
            **_pontos(partida["pontuacao_partida"], 0),
            "dificuldade": partida["dificuldade_atual"],
            "levelup": levelup,
            **_campos_nivel(partida),
        })

    if erros >= max_erros:
        pontuacao_final = partida.get("pontuacao_partida", 0)
        partida["vitorias_consecutivas"] = 0
        partida["pontuacao_partida"] = 0
        partida.pop("palavra")  # rodada encerrada: impede continuar chutando após perder
        return jsonify({
            **base,
            "fim_de_jogo": True,
            "venceu": False,
            "palavra_oculta": palavra,
            "mensagem_fim": (
                f"Você perdeu! A palavra era: <strong>{palavra.upper()}</strong>.<br>"
                f"Pontuação final: {pontuacao_final}"
            ),
            "pontuacao_final": pontuacao_final,
            "pontuacao": 0,
            **_pontos(0, 0),
            "dificuldade": partida["dificuldade_atual"],
            **_campos_nivel(partida),
        })

    partida.update(erros=erros, letras_tentadas=letras_tentadas)
    return jsonify({
        **base,
        "fim_de_jogo": False,
        "palavra_oculta": oculta,
        "pontuacao": partida["pontuacao_partida"] + partida["pontos_rodada"],
        **_pontos(partida["pontuacao_partida"], partida["pontos_rodada"]),
        "dificuldade": partida["dificuldade_atual"],
        "dicas": _dicas(partida["categoria_atual"], palavra, partida["dificuldade_atual"]),
        **_campos_nivel(partida),
    })


@bp.route("/tentativa", methods=["POST"])
def tentativa():
    partida = _partida()
    if not partida or not partida.get("palavra"):
        return _erro("Jogo não iniciado.")
    letra = str((request.get_json(silent=True) or {}).get("letra", "")).lower()
    if letra not in LETRAS_VALIDAS:
        return _erro("Letra inválida.")

    letras_tentadas, erros, palavra = list(partida["letras_tentadas"]), partida["erros"], partida["palavra"]
    pontos_ganhos = 0

    if letra not in letras_tentadas:
        letras_tentadas.append(letra)
        if letra in palavra:
            pontos_ganhos = regras.pontos_da_letra(palavra, letra)
        else:
            erros += 1
    return processar_jogada(partida, erros, pontos_ganhos, letras_tentadas)


@bp.route("/chute", methods=["POST"])
def chute():
    partida = _partida()
    if not partida or not partida.get("palavra"):
        return _erro("Jogo não iniciado.")
    chute_palavra = regras.normalizar_chute((request.get_json(silent=True) or {}).get("palavra", ""))

    erros, palavra = partida["erros"], partida["palavra"]
    pontos_ganhos, letras_tentadas = 0, partida["letras_tentadas"]

    if chute_palavra == palavra:
        pontos_ganhos = regras.pontos_do_chute(palavra, letras_tentadas)
        letras_tentadas = list(set(palavra))
    else:
        erros += 1
        partida["pontuacao_partida"] = max(0, partida.get("pontuacao_partida", 0) - PENALIDADE_CHUTE_ERRADO)

    return processar_jogada(partida, erros, pontos_ganhos, letras_tentadas)
