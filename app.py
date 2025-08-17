# app.py (versão com nível fixo e preparação para ranking)

from flask import Flask, render_template, jsonify, session, request
import random

try:
    from palavras import PALAVRAS_POR_CATEGORIA
except ImportError:
    exit("ERRO CRÍTICO: Arquivo 'palavras.py' não encontrado.")

app = Flask(__name__)
app.secret_key = 'versao-com-ranking-pessoal'

# --- CONFIGURAÇÕES DO JOGO ---
DIFICULDADES = ["facil", "medio", "dificil"]
DIFICULDADE_CONFIG = { "facil": 8, "medio": 6, "dificil": 4 }
PONTOS_LETRA_CERTA = 10
PONTOS_VITORIA_BONUS = 50
PONTOS_POR_TENTATIVA_SOBRA = 5
PENALIDADE_CHUTE_ERRADO = 30
VITORIAS_PARA_SUBIR_NIVEL_DIFICULDADE = 5
XP_PARA_PROXIMO_NIVEL = 1000 # --- REGRA DE NÍVEL ATUALIZADA ---

def _servir_proxima_palavra(categoria, dificuldade):
    palavras_disponiveis_geral = session.get('palavras_disponiveis_por_categoria', {})
    
    if categoria not in palavras_disponiveis_geral or not palavras_disponiveis_geral[categoria]:
        palavras_categoria = list(PALAVRAS_POR_CATEGORIA[categoria].keys())
        random.shuffle(palavras_categoria)
        palavras_disponiveis_geral[categoria] = palavras_categoria

    if not palavras_disponiveis_geral[categoria]:
        return {"sem_mais_palavras": True}

    palavra_sorteada = palavras_disponiveis_geral[categoria].pop()
    
    session.update(
        palavra=palavra_sorteada,
        letras_tentadas=[],
        erros=0,
        pontos_rodada=0, # Pontos apenas da palavra atual
        palavras_disponiveis_por_categoria=palavras_disponiveis_geral,
        max_erros=DIFICULDADE_CONFIG.get(dificuldade, 6)
    )
    
    dicas = PALAVRAS_POR_CATEGORIA[categoria][palavra_sorteada]
    if dificuldade == "dificil":
        dicas = [dicas[0], ""] if dicas else ["", ""]

    palavra_oculta = "".join("_" if ch.isalpha() else ch for ch in palavra_sorteada)
    
    return {
        'palavra_oculta': palavra_oculta, 'dicas': dicas,
        'tentativas_restantes': session['max_erros'], 'erros': 0, 'letras_tentadas': [],
        'pontuacao': session.get('pontuacao_partida', 0), 'dificuldade': dificuldade,
        'nivel': session.get('nivel', 1),
        'xp_atual': session.get('xp_atual', 0),
        'xp_necessario': XP_PARA_PROXIMO_NIVEL
    }

@app.route('/')
def pagina_inicial():
    # Adicionamos um cabeçalho para evitar cache de arquivos estáticos
    version = random.randint(1, 100000)
    return render_template('index.html', version=version)

@app.route('/categorias')
def get_categorias():
    return jsonify(list(PALAVRAS_POR_CATEGORIA.keys()))

@app.route('/novo_jogo')
def novo_jogo():
    session.clear()
    categoria_escolhida = request.args.get('category')
    dificuldade_escolhida = request.args.get('difficulty', 'medio')

    session.update(
        categoria_atual=categoria_escolhida,
        dificuldade_atual=dificuldade_escolhida,
        vitorias_consecutivas=0,
        pontuacao_partida=0, # Pontuação que será zerada ao perder
        nivel=1,
        xp_atual=0
    )
    return jsonify(_servir_proxima_palavra(categoria_escolhida, dificuldade_escolhida))

@app.route('/proxima_palavra')
def proxima_palavra():
    categoria = session.get('categoria_atual')
    dificuldade = session.get('dificuldade_atual')
    if not categoria or not dificuldade: return jsonify({"erro": "Sessão inválida."}), 400
    return jsonify(_servir_proxima_palavra(categoria, dificuldade))

def processar_jogada(erros, pontos_ganhos_na_jogada, letras_tentadas):
    palavra_correta, max_erros = session.get("palavra"), session.get("max_erros", 6)
    palavra_oculta = "".join(ch if not ch.isalpha() or ch in letras_tentadas else "_" for ch in palavra_correta)
    
    session['pontos_rodada'] = session.get('pontos_rodada', 0) + pontos_ganhos_na_jogada
    
    venceu = "_" not in palavra_oculta
    perdeu = erros >= max_erros
    
    if venceu:
        pontos_rodada_final = session['pontos_rodada'] + PONTOS_VITORIA_BONUS + (max_erros - erros) * PONTOS_POR_TENTATIVA_SOBRA
        session['pontuacao_partida'] += pontos_rodada_final
        session['xp_atual'] += pontos_rodada_final
        session['vitorias_consecutivas'] += 1
        
        levelup = False
        while session['xp_atual'] >= XP_PARA_PROXIMO_NIVEL:
            levelup = True
            session['nivel'] += 1
            session['xp_atual'] -= XP_PARA_PROXIMO_NIVEL

        notificacao = f"+{pontos_rodada_final} Pontos!"
        if levelup:
            notificacao = f"LEVEL UP! Você alcançou o nível {session['nivel']}!"
        
        if not levelup and session['vitorias_consecutivas'] > 0 and session['vitorias_consecutivas'] % VITORIAS_PARA_SUBIR_NIVEL_DIFICULDADE == 0:
            idx = DIFICULDADES.index(session['dificuldade_atual'])
            if idx < len(DIFICULDADES) - 1:
                session['dificuldade_atual'] = DIFICULDADES[idx + 1]
                notificacao = f"Nível de dificuldade aumentado para {session['dificuldade_atual'].upper()}!"
        
        return jsonify({
            'vitoria_rodada': True, 'palavra_oculta': palavra_correta,
            'notificacao': notificacao, 'pontuacao': session['pontuacao_partida'],
            'letras_tentadas': sorted(letras_tentadas), 'erros': erros,
            'tentativas_restantes': max_erros - erros, 'dificuldade': session['dificuldade_atual'],
            'nivel': session['nivel'],
            'xp_atual': session['xp_atual'],
            'xp_necessario': XP_PARA_PROXIMO_NIVEL,
            'levelup': levelup
        })

    if perdeu:
        pontuacao_final = session.get('pontuacao_partida', 0)
        session['vitorias_consecutivas'] = 0
        session['pontuacao_partida'] = 0 # Zera a pontuação para o ranking
        
        return jsonify({
            'fim_de_jogo': True, 'venceu': False, 'palavra_oculta': palavra_correta,
            'mensagem_fim': f"Você perdeu! A palavra era: <strong>{palavra_correta.upper()}</strong>.<br>Pontuação final: {pontuacao_final}",
            'pontuacao_final': pontuacao_final, # Enviamos a pontuação final para o JS salvar
            'tentativas_restantes': 0, 'letras_tentadas': sorted(letras_tentadas),
            'erros': erros, 'pontuacao': 0, 'dificuldade': session['dificuldade_atual'],
            'nivel': session['nivel'],
            'xp_atual': session['xp_atual'],
            'xp_necessario': XP_PARA_PROXIMO_NIVEL
        })

    session.update(erros=erros, letras_tentadas=letras_tentadas)
    dicas = PALAVRAS_POR_CATEGORIA[session['categoria_atual']][palavra_correta]
    if session['dificuldade_atual'] == 'dificil': dicas = [dicas[0], ""] if dicas else ["", ""]
        
    return jsonify({
        'fim_de_jogo': False, 'palavra_oculta': palavra_oculta,
        'tentativas_restantes': max_erros - erros, 'letras_tentadas': sorted(letras_tentadas),
        'erros': erros, 'pontuacao': session['pontuacao_partida'] + session['pontos_rodada'],
        'dificuldade': session['dificuldade_atual'],
        'dicas': dicas,
        'nivel': session['nivel'],
        'xp_atual': session['xp_atual'],
        'xp_necessario': XP_PARA_PROXIMO_NIVEL
    })

@app.route('/tentativa', methods=['POST'])
def tentativa():
    letra = request.json.get("letra", "").lower()
    if not session.get("palavra"): return jsonify({"erro": "Jogo não iniciado."}), 400
    
    letras_tentadas, erros, palavra = list(session["letras_tentadas"]), session["erros"], session["palavra"]
    pontos_ganhos = 0

    if letra not in letras_tentadas:
        letras_tentadas.append(letra)
        if letra in palavra:
            pontos_ganhos += PONTOS_LETRA_CERTA * palavra.count(letra)
        else:
            erros += 1
    return processar_jogada(erros, pontos_ganhos, letras_tentadas)

@app.route('/chute', methods=['POST'])
def chute():
    chute_palavra = request.json.get("palavra", "").lower().strip()
    if not session.get("palavra"): return jsonify({"erro": "Jogo não iniciado."}), 400
    
    erros, palavra = session["erros"], session["palavra"]
    pontos_ganhos, letras_tentadas = 0, session["letras_tentadas"]

    if chute_palavra == palavra:
        letras_nao_reveladas = [letra for letra in palavra if letra not in letras_tentadas]
        pontos_ganhos = PONTOS_LETRA_CERTA * len(letras_nao_reveladas)
        letras_tentadas = list(set(list(palavra)))
    else:
        erros += 1
        # A penalidade agora afeta a pontuação da partida
        session['pontuacao_partida'] = max(0, session.get('pontuacao_partida', 0) - PENALIDADE_CHUTE_ERRADO)
    
    return processar_jogada(erros, pontos_ganhos, letras_tentadas)

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)