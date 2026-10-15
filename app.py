# app.py - Jogo da Forca (Flask)

import logging
import os
import random
import string

from flask import Flask, jsonify, render_template, request, session

from palavras import PALAVRAS_POR_CATEGORIA

logger = logging.getLogger(__name__)

app = Flask(__name__)

# A sessão é assinada com esta chave: quem a conhece consegue forjar pontuação.
# Em produção defina a variável de ambiente SECRET_KEY (ex.: no painel do Render).
# O Railway define RAILWAY_ENVIRONMENT; nesse caso a ausência da chave é erro fatal.
_secret = os.environ.get("SECRET_KEY")
EM_PRODUCAO = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
if not _secret:
    if EM_PRODUCAO:
        raise RuntimeError("SECRET_KEY é obrigatória em produção.")
    logger.warning("SECRET_KEY não definida; usando chave de desenvolvimento.")
app.secret_key = _secret or "dev-only-secret-key"
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=EM_PRODUCAO,  # cookie só trafega via HTTPS em produção
)

# --- CONFIGURAÇÕES DO JOGO ---
DIFICULDADES = ["facil", "medio", "dificil"]
DIFICULDADE_CONFIG = {"facil": 8, "medio": 6, "dificil": 4}
PONTOS_LETRA_CERTA = 10
PONTOS_VITORIA_BONUS = 50
PONTOS_POR_TENTATIVA_SOBRA = 5
PENALIDADE_CHUTE_ERRADO = 30
VITORIAS_PARA_SUBIR_NIVEL_DIFICULDADE = 5
XP_PARA_PROXIMO_NIVEL = 1000
LETRAS_VALIDAS = set(string.ascii_lowercase)


def _versao_assets():
    """Versão para cache busting baseada na data de modificação dos estáticos
    (muda só quando os arquivos mudam, permitindo cache do navegador)."""
    mtimes = [
        os.path.getmtime(os.path.join(root, f))
        for root, _, files in os.walk(os.path.join(app.root_path, "static"))
        for f in files
    ]
    return int(max(mtimes, default=0))


VERSAO_ASSETS = _versao_assets()


# --- HELPERS ---
def _erro(mensagem, status=400):
    return jsonify({"erro": mensagem}), status


def _dicas(categoria, palavra, dificuldade):
    dicas = PALAVRAS_POR_CATEGORIA[categoria][palavra]
    if dificuldade == "dificil":
        return [dicas[0], ""] if dicas else ["", ""]
    return dicas


def _campos_nivel():
    return {
        "nivel": session.get("nivel", 1),
        "xp_atual": session.get("xp_atual", 0),
        "xp_necessario": XP_PARA_PROXIMO_NIVEL,
    }


def _mascarar(palavra, letras_tentadas):
    return "".join(ch if not ch.isalpha() or ch in letras_tentadas else "_" for ch in palavra)


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
        "palavra_oculta": _mascarar(palavra, []),
        "dicas": _dicas(categoria, palavra, dificuldade),
        "tentativas_restantes": max_erros,
        "erros": 0,
        "letras_tentadas": [],
        "pontuacao": session.get("pontuacao_partida", 0),
        "dificuldade": dificuldade,
        **_campos_nivel(),
    }


# --- ROTAS ---
@app.route("/")
def pagina_inicial():
    return render_template("index.html", version=VERSAO_ASSETS)


@app.route("/health")
def health():
    """Usado pelo healthcheck do Railway para saber se o app está de pé."""
    return jsonify(status="ok")


@app.route("/categorias")
def get_categorias():
    return jsonify(list(PALAVRAS_POR_CATEGORIA.keys()))


@app.route("/novo_jogo")
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


@app.route("/proxima_palavra")
def proxima_palavra():
    categoria = session.get("categoria_atual")
    dificuldade = session.get("dificuldade_atual")
    if not categoria or not dificuldade:
        return _erro("Sessão inválida.")
    return jsonify(_servir_proxima_palavra(categoria, dificuldade))


def _registrar_vitoria(erros, max_erros):
    """Aplica pontos, XP, nível e dificuldade. Retorna (pontos, notificacao, levelup)."""
    pontos = session["pontos_rodada"] + PONTOS_VITORIA_BONUS + (max_erros - erros) * PONTOS_POR_TENTATIVA_SOBRA
    session["pontuacao_partida"] += pontos
    session["xp_atual"] += pontos
    session["vitorias_consecutivas"] += 1

    levelup = False
    while session["xp_atual"] >= XP_PARA_PROXIMO_NIVEL:
        levelup = True
        session["nivel"] += 1
        session["xp_atual"] -= XP_PARA_PROXIMO_NIVEL

    notificacao = f"LEVEL UP! Você alcançou o nível {session['nivel']}!" if levelup else f"+{pontos} Pontos!"

    if session["vitorias_consecutivas"] % VITORIAS_PARA_SUBIR_NIVEL_DIFICULDADE == 0:
        idx = DIFICULDADES.index(session["dificuldade_atual"])
        if idx < len(DIFICULDADES) - 1:
            session["dificuldade_atual"] = DIFICULDADES[idx + 1]
            aviso = f"Dificuldade aumentada para {session['dificuldade_atual'].upper()}!"
            notificacao = f"{notificacao} {aviso}" if levelup else aviso

    return pontos, notificacao, levelup


def processar_jogada(erros, pontos_ganhos, letras_tentadas):
    palavra = session["palavra"]
    max_erros = session.get("max_erros", 6)
    oculta = _mascarar(palavra, letras_tentadas)
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
            "mensagem_fim": f"Você perdeu! A palavra era: <strong>{palavra.upper()}</strong>.<br>Pontuação final: {pontuacao_final}",
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


@app.route("/tentativa", methods=["POST"])
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
            pontos_ganhos = PONTOS_LETRA_CERTA * palavra.count(letra)
        else:
            erros += 1
    return processar_jogada(erros, pontos_ganhos, letras_tentadas)


@app.route("/chute", methods=["POST"])
def chute():
    if not session.get("palavra"):
        return _erro("Jogo não iniciado.")
    chute_palavra = str((request.get_json(silent=True) or {}).get("palavra", "")).lower().strip()

    erros, palavra = session["erros"], session["palavra"]
    pontos_ganhos, letras_tentadas = 0, session["letras_tentadas"]

    if chute_palavra == palavra:
        pontos_ganhos = PONTOS_LETRA_CERTA * len([ch for ch in palavra if ch not in letras_tentadas])
        letras_tentadas = list(set(palavra))
    else:
        erros += 1
        session["pontuacao_partida"] = max(0, session.get("pontuacao_partida", 0) - PENALIDADE_CHUTE_ERRADO)

    return processar_jogada(erros, pontos_ganhos, letras_tentadas)


if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
