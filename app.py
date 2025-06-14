# app.py (versão com servidor de produção waitress)

from flask import Flask, render_template, jsonify, session, request
import random
# A importação do 'os' não é mais necessária se não usarmos os caminhos absolutos,
# mas mantê-la não prejudica em nada.

# Tenta importar a lista de palavras do arquivo palavras.py
try:
    from palavras import PALAVRAS_COM_DICAS
except ImportError:
    print("ERRO CRÍTICO: Arquivo 'palavras.py' não encontrado ou está vazio.")
    print("Certifique-se de que 'palavras.py' existe na mesma pasta e contém o dicionário 'PALAVRAS_COM_DICAS'.")
    # Em um cenário real, poderíamos ter uma lista de palavras padrão aqui como fallback.
    # Para este projeto, vamos encerrar se o arquivo principal não for encontrado.
    exit()

# Configuração do Flask
app = Flask(__name__)
# Chave secreta para gerenciar a sessão de cada usuário de forma segura
app.secret_key = 'uma-chave-secreta-muito-dificil-de-adivinhar'

# Constantes do Jogo
MAX_ERROS = 7

# Definição das Rotas (Endpoints da API)

@app.route('/')
def pagina_inicial():
    """Serve a página principal do jogo."""
    return render_template('index.html')

@app.route('/novo_jogo')
def novo_jogo():
    """Inicia uma nova rodada do jogo."""
    # Se for o primeiro jogo do usuário nesta sessão, cria a lista de palavras disponíveis.
    if 'palavras_disponiveis' not in session or not session['palavras_disponiveis']:
        palavras_disponiveis = list(PALAVRAS_COM_DICAS.keys())
        random.shuffle(palavras_disponiveis)
        print("--- LISTA DE PALAVRAS EMBARALHADA PARA A SESSÃO ---")
    else:
        palavras_disponiveis = session.get('palavras_disponiveis')

    # Retira a última palavra da lista embaralhada.
    palavra_sorteada = palavras_disponiveis.pop()
    
    # Salva a lista (agora menor) de volta na sessão.
    session['palavras_disponiveis'] = palavras_disponiveis

    # Inicia as variáveis do jogo na sessão.
    session['palavra'] = palavra_sorteada
    session['letras_tentadas'] = []
    session['erros'] = 0

    dicas = PALAVRAS_COM_DICAS[palavra_sorteada]
    palavra_oculta = "".join("_" if ch.isalpha() else ch for ch in palavra_sorteada)

    print(f"--- NOVO JOGO: {palavra_sorteada.upper()} --- Restam {len(palavras_disponiveis)} palavras.")
    
    return jsonify({
        'palavra_oculta': palavra_oculta,
        'dicas': dicas,
        'tentativas_restantes': MAX_ERROS - session['erros'],
        'erros': 0,
        'letras_tentadas': [],
        'fim_de_jogo': False
    })

@app.route('/tentativa', methods=['POST'])
def tentativa():
    """Processa a tentativa de uma letra pelo jogador."""
    letra = request.json.get("letra", "").lower()
    if not letra.isalpha() or len(letra) != 1:
        return jsonify({"erro": "Tentativa inválida"}), 400

    palavra = session.get("palavra")
    letras_tentadas = session.get("letras_tentadas", [])
    erros = session.get("erros", 0)

    if letra not in letras_tentadas:
        letras_tentadas.append(letra)
        if letra not in palavra:
            erros += 1

    palavra_oculta = "".join(
        ch if (not ch.isalpha() or ch in letras_tentadas) else "_"
        for ch in palavra
    )

    fim_de_jogo = "_" not in palavra_oculta or erros >= MAX_ERROS
    venceu = "_" not in palavra_oculta
    mensagem_fim = ""
    if fim_de_jogo:
        if venceu:
            mensagem_fim = "Parabéns, você venceu!"
        else:
            mensagem_fim = f"Você perdeu! A palavra era: {palavra.upper()}"
            palavra_oculta = palavra

    session["letras_tentadas"] = letras_tentadas
    session["erros"] = erros

    return jsonify({
        'palavra_oculta': palavra_oculta,
        'tentativas_restantes': MAX_ERROS - erros,
        'letras_tentadas': sorted(letras_tentadas),
        'erros': erros,
        'fim_de_jogo': fim_de_jogo,
        'venceu': venceu,
        'mensagem_fim': mensagem_fim
    })

# Ponto de entrada da aplicação
if __name__ == "__main__":
    # Importa o 'serve' do waitress para rodar em modo de produção
    from waitress import serve
    
    # Mensagens para o console
    print(f"Total de palavras carregadas no jogo: {len(PALAVRAS_COM_DICAS)}")
    print("Servidor de produção iniciado. Acesse em:")
    print("http://127.0.0.1:8080 ou http://localhost:8080")
    
    # Inicia o servidor waitress na porta 8080
    serve(app, host="0.0.0.0", port=8080)