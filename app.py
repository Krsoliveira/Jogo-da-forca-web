# app.py (versão com níveis de dificuldade)

from flask import Flask, render_template, jsonify, session, request
import random

try:
    from palavras import PALAVRAS_POR_CATEGORIA
except ImportError:
    print("ERRO CRÍTICO: Arquivo 'palavras.py' não encontrado ou com estrutura incorreta.")
    exit()

app = Flask(__name__)
app.secret_key = 'dificuldades-exigem-chaves-mais-fortes'

# <<< NOVO >>>: Dicionário para configurar os níveis de dificuldade.
DIFICULDADE_CONFIG = {
    "facil": 8,
    "medio": 6,
    "dificil": 4
}

# --- ROTAS ---

@app.route('/')
def pagina_inicial():
    version = random.randint(1, 10000)
    return render_template('index.html', version=version)

@app.route('/categorias')
def get_categorias():
    categorias = list(PALAVRAS_POR_CATEGORIA.keys())
    return jsonify(categorias)

@app.route('/novo_jogo')
def novo_jogo():
    # <<< MUDANÇA >>>: Recebe a categoria E a dificuldade.
    categoria_escolhida = request.args.get('category')
    dificuldade_escolhida = request.args.get('difficulty', 'medio') # 'medio' como padrão

    if not categoria_escolhida or categoria_escolhida not in PALAVRAS_POR_CATEGORIA:
        return jsonify({"erro": "Categoria inválida"}), 400

    if 'palavras_disponiveis_por_categoria' not in session:
        session['palavras_disponiveis_por_categoria'] = {}

    palavras_disponiveis_geral = session.get('palavras_disponiveis_por_categoria')

    if categoria_escolhida not in palavras_disponiveis_geral or not palavras_disponiveis_geral[categoria_escolhida]:
        palavras_categoria = list(PALAVRAS_POR_CATEGORIA[categoria_escolhida].keys())
        random.shuffle(palavras_categoria)
        palavras_disponiveis_geral[categoria_escolhida] = palavras_categoria
    
    palavras_disponiveis_categoria = palavras_disponiveis_geral[categoria_escolhida]
    
    if not palavras_disponiveis_categoria:
         return jsonify({"erro": "Não há mais palavras nesta categoria. Parabéns!"}), 404

    palavra_sorteada = palavras_disponiveis_categoria.pop()
    
    # <<< MUDANÇA >>>: Define o número máximo de erros na sessão com base na dificuldade.
    max_erros = DIFICULDADE_CONFIG.get(dificuldade_escolhida, 6)
    session['max_erros'] = max_erros
    
    session['palavras_disponiveis_por_categoria'] = palavras_disponiveis_geral
    session['palavra'] = palavra_sorteada
    session['letras_tentadas'] = []
    session['erros'] = 0

    dicas = PALAVRAS_POR_CATEGORIA[categoria_escolhida][palavra_sorteada]
    palavra_oculta = "".join("_" if ch.isalpha() else ch for ch in palavra_sorteada)

    return jsonify({
        'palavra_oculta': palavra_oculta,
        'dicas': dicas,
        'tentativas_restantes': max_erros, # Envia o número correto de tentativas
        'erros': 0,
        'letras_tentadas': [],
        'fim_de_jogo': False
    })

def processar_jogada(erros):
    """Função auxiliar para evitar repetição de código em /tentativa e /chute."""
    palavra_correta = session.get("palavra")
    letras_tentadas = session.get("letras_tentadas", [])
    max_erros = session.get("max_erros", 6)

    palavra_oculta = "".join(ch if (not ch.isalpha() or ch in letras_tentadas) else "_" for ch in palavra_correta)
    
    session["erros"] = erros

    venceu = "_" not in palavra_oculta
    perdeu = erros >= max_erros
    fim_de_jogo = venceu or perdeu
    
    mensagem_fim = ""
    if fim_de_jogo:
        if venceu:
            mensagem_fim = "Parabéns, você venceu!"
        else:
            mensagem_fim = f"Você perdeu! A palavra era: <strong>{palavra_correta.upper()}</strong>"
            palavra_oculta = palavra_correta

    return jsonify({
        'palavra_oculta': palavra_oculta,
        'tentativas_restantes': max_erros - erros,
        'letras_tentadas': sorted(letras_tentadas),
        'erros': erros,
        'fim_de_jogo': fim_de_jogo,
        'venceu': venceu,
        'mensagem_fim': mensagem_fim
    })

@app.route('/tentativa', methods=['POST'])
def tentativa():
    letra = request.json.get("letra", "").lower()
    if not session.get("palavra"): return jsonify({"erro": "Jogo não iniciado"}), 400
        
    letras_tentadas = session.get("letras_tentadas", [])
    erros = session.get("erros", 0)

    if letra not in letras_tentadas:
        letras_tentadas.append(letra)
        if letra not in session.get("palavra"):
            erros += 1
    
    session["letras_tentadas"] = letras_tentadas
    return processar_jogada(erros)

@app.route('/chute', methods=['POST'])
def chute():
    chute_palavra = request.json.get("palavra", "").lower().strip()
    if not session.get("palavra"): return jsonify({"erro": "Jogo não iniciado"}), 400

    erros = session.get("erros", 0)
    
    if chute_palavra != session.get("palavra"):
        erros += 1
    else:
        # Se acertou, preenche as letras tentadas para a lógica de vitória funcionar
        session["letras_tentadas"] = list(set(list(session.get("palavra"))))

    return processar_jogada(erros)

if __name__ == "__main__":
    from waitress import serve
    print("Servidor de produção com NÍVEIS DE DIFICULDADE iniciado.")
    serve(app, host="0.0.0.0", port=8080)
