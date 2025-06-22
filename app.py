# app.py (versão com diagnóstico para encontrar erros de inicialização)

# --- INÍCIO DO DIAGNÓSTICO ---
print("--- [PASSO 1 de 5] A iniciar o script 'app.py'...")
# Se você não vir esta mensagem, há um problema com a sua instalação do Python ou com o PowerShell.

try:
    from flask import Flask, render_template, jsonify, session, request
    import random
    from waitress import serve
    print("--- [PASSO 2 de 5] Bibliotecas (Flask, Waitress) importadas com sucesso.")
except ImportError as e:
    print(f"\n--- ERRO FATAL: Faltam bibliotecas essenciais: {e} ---")
    print("--> SOLUÇÃO: Execute 'pip install -r requirements.txt' no seu PowerShell.")
    exit() # Termina o script

try:
    from palavras import PALAVRAS_POR_CATEGORIA
    print("--- [PASSO 3 de 5] Banco de palavras importado com sucesso.")
except Exception as e:
    print(f"\n--- ERRO FATAL: O ficheiro 'palavras.py' contém um erro: {e} ---")
    print("--> SOLUÇÃO: Verifique o ficheiro 'palavras.py' em busca de erros de sintaxe (vírgulas, aspas, etc.).")
    exit()

app = Flask(__name__)
app.secret_key = 'diagnostico-final-de-bugs'

print("--- [PASSO 4 de 5] Aplicação Flask configurada.")

# --- Constantes e Lógica do Jogo ---

DIFICULDADES = ["facil", "medio", "dificil"]
DIFICULDADE_CONFIG = { "facil": 8, "medio": 6, "dificil": 4 }
PONTOS_LETRA_CERTA = 10
PONTOS_VITORIA_BONUS = 50
PONTOS_POR_TENTATIVA_SOBRA = 5
PENALIDADE_CHUTE_ERRADO = 30
VITORIAS_PARA_SUBIR_NIVEL = 5

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
        'pontuacao': session.get('pontuacao', 0), 'dificuldade': dificuldade
    }

# --- ROTAS DA API ---

@app.route('/')
def pagina_inicial():
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
        pontuacao=0
    )
    return jsonify(_servir_proxima_palavra(categoria_escolhida, dificuldade_escolhida))

@app.route('/proxima_palavra')
def proxima_palavra():
    categoria = session.get('categoria_atual')
    dificuldade = session.get('dificuldade_atual')
    if not categoria or not dificuldade: return jsonify({"erro": "Sessão inválida."}), 400
    return jsonify(_servir_proxima_palavra(categoria, dificuldade))

def processar_jogada(erros, pontuacao, letras_tentadas):
    palavra_correta, max_erros = session.get("palavra"), session.get("max_erros", 6)
    palavra_oculta = "".join(ch if not ch.isalpha() or ch in letras_tentadas else "_" for ch in palavra_correta)
    
    venceu = "_" not in palavra_oculta
    perdeu = erros >= max_erros
    
    if venceu:
        session['vitorias_consecutivas'] += 1
        pontuacao += PONTOS_VITORIA_BONUS + (max_erros - erros) * PONTOS_POR_TENTATIVA_SOBRA
        session['pontuacao'] = pontuacao
        notificacao = "Você acertou!"
        if session['vitorias_consecutivas'] > 0 and session['vitorias_consecutivas'] % VITORIAS_PARA_SUBIR_NIVEL == 0:
            idx = DIFICULDADES.index(session['dificuldade_atual'])
            if idx < len(DIFICULDADES) - 1:
                session['dificuldade_atual'] = DIFICULDADES[idx + 1]
                notificacao = f"Nível aumentado para {session['dificuldade_atual'].upper()}!"
        
        return jsonify({
            'vitoria_rodada': True, 'palavra_oculta': palavra_correta,
            'notificacao': notificacao, 'pontuacao': pontuacao,
            'letras_tentadas': sorted(letras_tentadas), 'erros': erros,
            'tentativas_restantes': max_erros - erros, 'dificuldade': session['dificuldade_atual']
        })

    if perdeu:
        session['vitorias_consecutivas'] = 0
        # <<< CORREÇÃO DEFINITIVA >>>: Adiciona a chave 'dicas' que estava em falta na resposta de derrota.
        return jsonify({
            'fim_de_jogo': True, 'venceu': False, 'palavra_oculta': palavra_correta,
            'mensagem_fim': f"Você perdeu! A palavra era: <strong>{palavra_correta.upper()}</strong>.<br>Pontuação final: {pontuacao}",
            'tentativas_restantes': 0, 'letras_tentadas': sorted(letras_tentadas),
            'erros': erros, 'pontuacao': pontuacao, 'dificuldade': session['dificuldade_atual'],
            'dicas': ["", ""] # Garante que a UI não falhe ao tentar ler as dicas.
        })

    session.update(erros=erros, pontuacao=pontuacao, letras_tentadas=letras_tentadas)
    dicas = PALAVRAS_POR_CATEGORIA[session['categoria_atual']][palavra_correta]
    if session['dificuldade_atual'] == 'dificil': dicas = [dicas[0], ""] if dicas else ["", ""]
        
    return jsonify({
        'fim_de_jogo': False, 'palavra_oculta': palavra_oculta,
        'tentativas_restantes': max_erros - erros, 'letras_tentadas': sorted(letras_tentadas),
        'erros': erros, 'pontuacao': pontuacao, 'dificuldade': session['dificuldade_atual'],
        'dicas': dicas
    })

@app.route('/tentativa', methods=['POST'])
def tentativa():
    letra = request.json.get("letra", "").lower()
    if not session.get("palavra"): return jsonify({"erro": "Jogo não iniciado."}), 400
    letras_tentadas, erros, pontuacao, palavra = list(session["letras_tentadas"]), session["erros"], session["pontuacao"], session["palavra"]
    if letra not in letras_tentadas:
        letras_tentadas.append(letra)
        if letra in palavra: pontuacao += PONTOS_LETRA_CERTA * palavra.count(letra)
        else: erros += 1
    return processar_jogada(erros, pontuacao, letras_tentadas)

@app.route('/chute', methods=['POST'])
def chute():
    chute_palavra = request.json.get("palavra", "").lower().strip()
    if not session.get("palavra"): return jsonify({"erro": "Jogo não iniciado."}), 400
    erros, pontuacao, palavra = session["erros"], session["pontuacao"], session["palavra"]
    if chute_palavra == palavra: letras_tentadas = list(set(list(palavra)))
    else:
        erros += 1
        pontuacao = max(0, pontuacao - PENALIDADE_CHUTE_ERRADO)
        letras_tentadas = session["letras_tentadas"]
    return processar_jogada(erros, pontuacao, letras_tentadas)

print("--- [PASSO 5 de 5] Definição de rotas concluída.")

if __name__ == "__main__":
    print("\n--- INICIANDO SERVIDOR WAITRESS ---")
    print("Acesse o jogo em http://127.0.0.1:8080")
    serve(app, host="0.0.0.0", port=8080)
