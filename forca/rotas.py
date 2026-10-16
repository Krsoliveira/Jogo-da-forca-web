"""Rotas HTTP do jogo. O estado da partida vive na sessão (cookie assinado)."""

import random

from flask import Blueprint, current_app, jsonify, render_template, request, session

from . import regras
from .config import (
    DIFICULDADE_CONFIG,
    LETRAS_VALIDAS,
    PENALIDADE_CHUTE_ERRADO,
    XP_PARA_PROXIMO_NIVEL,
)
from .palavras import PALAVRAS_POR_CATEGORIA

bp = Blueprint("jogo", __name__)


def _erro(mensagem, status=400):
    return jsonify({"erro": mensagem}), status


def _dicas(categoria, palavra, dificuldade):
    return regras.dicas_para(PALAVRAS_POR_CATEGORIA[categoria][palavra], dificuldade)


def _campos_nivel():
    return {
        "nivel": session.get("nivel", 1),
        "xp_atual": session.get("xp_atual", 0),
        "xp_necessario": XP_PARA_PROXIMO_NIVEL,
    }


def _servir_proxima_palavra(categoria, dificuldade):
    disponiveis = session.get("palavras_disponiveis_por_categoria", {})

    # Quando o baralho da categoria acaba, embaralha de novo (jogo contínuo).
    if not disponiveis.get(categoria):
        palavras = list(PALAVRAS_POR_CATEGORIA[categoria].keys())
        random.shuffle(palavras)
        disponiveis[categoria] = palavras

    palavra = disponiveis[categoria].pop()
    max_erros = DIFICULDADE_CONFIG[dificuldade]

    session.update(
        palavra=palavra,
        letras_tentadas=[],
        erros=0,
        pontos_rodada=0,
        palavras_disponiveis_por_categoria=disponiveis,
        max_erros=max_erros,
    )

    return {
        "palavra_oculta": regras.mascarar(palavra, []),
        "dicas": _dicas(categoria, palavra, dificuldade),
        "tentativas_restantes": max_erros,
        "erros": 0,
        "letras_tentadas": [],
        "pontuacao": session.get("pontuacao_partida", 0),
        "dificuldade": dificuldade,
        **_campos_nivel(),
    }


@bp.route("/")
def pagina_inicial():
    return render_template("index.html", version=current_app.config["VERSAO_ASSETS"])


@bp.route("/health")
def health():
    """Usado pelo healthcheck do Railway para saber se o app está de pé."""
    return jsonify(status="ok")


@bp.route("/categorias")
def get_categorias():
    return jsonify(list(PALAVRAS_POR_CATEGORIA.keys()))


@bp.route("/novo_jogo")
def novo_jogo():
    categoria = request.args.get("category")
    dificuldade = request.args.get("difficulty", "medio")

    if categoria not in PALAVRAS_POR_CATEGORIA:
        return _erro("Categoria inválida.")
    if dificuldade not in DIFICULDADE_CONFIG:
        return _erro("Dificuldade inválida.")

    session.clear()
    session.update(
        categoria_atual=categoria,
        dificuldade_atual=dificuldade,
        vitorias_consecutivas=0,
        pontuacao_partida=0,
        nivel=1,
        xp_atual=0,
    )
    return jsonify(_servir_proxima_palavra(categoria, dificuldade))


@bp.route("/proxima_palavra")
def proxima_palavra():
    categoria = session.get("categoria_atual")
    dificuldade = session.get("dificuldade_atual")
    if not categoria or not dificuldade:
        return _erro("Sessão inválida.")
    return jsonify(_servir_proxima_palavra(categoria, dificuldade))


def _registrar_vitoria(erros, max_erros):
    """Aplica pontos, XP, nível e dificuldade. Retorna (pontos, notificacao, levelup)."""
    pontos = regras.pontos_da_vitoria(session["pontos_rodada"], erros, max_erros)
    session["pontuacao_partida"] += pontos
    session["vitorias_consecutivas"] += 1
    session["nivel"], session["xp_atual"], levelup = regras.aplicar_xp(session["nivel"], session["xp_atual"], pontos)

    notificacao = f"LEVEL UP! Você alcançou o nível {session['nivel']}!" if levelup else f"+{pontos} Pontos!"

    nova = regras.proxima_dificuldade(session["dificuldade_atual"], session["vitorias_consecutivas"])
    if nova:
        session["dificuldade_atual"] = nova
        aviso = f"Dificuldade aumentada para {nova.upper()}!"
        notificacao = f"{notificacao} {aviso}" if levelup else aviso

    return pontos, notificacao, levelup


def processar_jogada(erros, pontos_ganhos, letras_tentadas):
    palavra = session["palavra"]
    max_erros = session.get("max_erros", 6)
    oculta = regras.mascarar(palavra, letras_tentadas)
    session["pontos_rodada"] = session.get("pontos_rodada", 0) + pontos_ganhos

    base = {
        "letras_tentadas": sorted(letras_tentadas),
        "erros": erros,
        "tentativas_restantes": max_erros - erros,
    }

    if "_" not in oculta:
        _, notificacao, levelup = _registrar_vitoria(erros, max_erros)
        session.pop("palavra")  # rodada encerrada: impede repetir a jogada para farmar pontos
        return jsonify({
            **base,
            "vitoria_rodada": True,
            "palavra_oculta": palavra,
            "notificacao": notificacao,
            "pontuacao": session["pontuacao_partida"],
            "dificuldade": session["dificuldade_atual"],
            "levelup": levelup,
            **_campos_nivel(),
        })

    if erros >= max_erros:
        pontuacao_final = session.get("pontuacao_partida", 0)
        session["vitorias_consecutivas"] = 0
        session["pontuacao_partida"] = 0
        session.pop("palavra")  # rodada encerrada: impede continuar chutando após perder
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
            "dificuldade": session["dificuldade_atual"],
            **_campos_nivel(),
        })

    session.update(erros=erros, letras_tentadas=letras_tentadas)
    return jsonify({
        **base,
        "fim_de_jogo": False,
        "palavra_oculta": oculta,
        "pontuacao": session["pontuacao_partida"] + session["pontos_rodada"],
        "dificuldade": session["dificuldade_atual"],
        "dicas": _dicas(session["categoria_atual"], palavra, session["dificuldade_atual"]),
        **_campos_nivel(),
    })


@bp.route("/tentativa", methods=["POST"])
def tentativa():
    if not session.get("palavra"):
        return _erro("Jogo não iniciado.")
    letra = str((request.get_json(silent=True) or {}).get("letra", "")).lower()
    if letra not in LETRAS_VALIDAS:
        return _erro("Letra inválida.")

    letras_tentadas, erros, palavra = list(session["letras_tentadas"]), session["erros"], session["palavra"]
    pontos_ganhos = 0

    if letra not in letras_tentadas:
        letras_tentadas.append(letra)
        if letra in palavra:
            pontos_ganhos = regras.pontos_da_letra(palavra, letra)
        else:
            erros += 1
    return processar_jogada(erros, pontos_ganhos, letras_tentadas)


@bp.route("/chute", methods=["POST"])
def chute():
    if not session.get("palavra"):
        return _erro("Jogo não iniciado.")
    chute_palavra = str((request.get_json(silent=True) or {}).get("palavra", "")).lower().strip()

    erros, palavra = session["erros"], session["palavra"]
    pontos_ganhos, letras_tentadas = 0, session["letras_tentadas"]

    if chute_palavra == palavra:
        pontos_ganhos = regras.pontos_do_chute(palavra, letras_tentadas)
        letras_tentadas = list(set(palavra))
    else:
        erros += 1
        session["pontuacao_partida"] = max(0, session.get("pontuacao_partida", 0) - PENALIDADE_CHUTE_ERRADO)

    return processar_jogada(erros, pontos_ganhos, letras_tentadas)
