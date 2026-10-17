Jogo da Forca Web
Um clássico jogo da forca construído com um backend Python (Flask) e um frontend dinâmico em JavaScript puro, com um design moderno estilo neon.

![image](https://github.com/user-attachments/assets/7f77ff43-704a-4e67-9e16-8ba2a3eb0ee9)
![image](https://github.com/user-attachments/assets/fee9ca26-ad81-4412-b51e-c1613ee15381)
![image](https://github.com/user-attachments/assets/087119b5-a3f1-4253-b65c-ff1a337b568e)







Funcionalidades Principais ✨
Design Responsivo: Interface que se adapta perfeitamente a computadores, tablets e telemóveis.

Seleção de Dificuldade: O jogador pode escolher entre os modos Fácil, Médio e Difícil, que alteram o número de tentativas permitidas.

Categorias de Palavras: Desafie-se com 5 categorias diferentes: Frutas, Países, Cidades, Animais e Objetos.

Banco de Palavras Vasto: Mais de 250 palavras com dicas únicas para garantir que cada jogo seja diferente.

Jogabilidade Dupla:

Tente adivinhar letra por letra.

Arrisque tudo e chute a palavra inteira a qualquer momento!

Feedback Visual Imediato: O teclado virtual muda de cor para indicar letras certas e erradas.

Interface Dinâmica: Construído como uma Single-Page Application (SPA), onde o JavaScript manipula o jogo sem precisar de recarregar a página.

Tecnologias Utilizadas 🚀
Backend:

Python: Linguagem principal da lógica do servidor.

Flask: Micro-framework web para criar a API que serve o jogo e processa as jogadas.

Waitress: Servidor de produção WSGI para rodar a aplicação Flask.

Frontend:

HTML5: Estrutura semântica da página.

CSS3: Estilização completa, incluindo Flexbox para layouts responsivos e um tema neon moderno.

JavaScript (ES6+): Lógica do lado do cliente, manipulação do DOM, eventos e comunicação com o backend via fetch API (async/await).

Como Executar o Projeto Localmente
Para executar este projeto no seu próprio computador, siga estes passos:

Clone o repositório:

git clone https://github.com/Krsoliveira/Jogo-da-forca-web.git

Navegue para a pasta do projeto:

cd jogo-da-forca-web

(Opcional, mas recomendado) Crie um ambiente virtual:

python -m venv venv
venv\Scripts\activate  # No Windows
# source venv/bin/activate  # No macOS/Linux

Instale as dependências:

pip install -r requirements.txt

Execute a aplicação:

python app.py

Abra o seu navegador e aceda a http://127.0.0.1:8080.

Variáveis de Ambiente
SECRET_KEY: chave que assina a sessão do jogador. Defina um valor longo e aleatório em produção (ex.: no painel do Render). Sem ela o app usa uma chave de desenvolvimento e registra um aviso.
PORT: porta do servidor local (padrão 8080).

Testes
pip install -r requirements-dev.txt
python -m pytest

Fontes dos Dados
O banco de palavras gerais (forca/dados/palavras_gerais.json) é gerado por scripts/gerar_banco.py, que combina:
Dicionário Aberto (https://dicionario-aberto.net): lista de palavras, classe gramatical e definições. Domínio público.
wordfreq (https://github.com/rspeer/wordfreq): lista de frequência usada apenas na geração, para escolher palavras comuns. Código Apache-2.0; dados CC BY-SA 4.0 e Google Books Ngrams. Seus dados não são redistribuídos com o jogo.
Para regenerar: pip install -r requirements-dados.txt e python scripts/gerar_banco.py. A lista de palavras bloqueadas fica em scripts/palavras_bloqueadas.txt.

Fluxo de Trabalho
Como as mudanças são desenvolvidas, testadas (CI e ambiente de teste por Pull Request) e publicadas: docs/fluxo-de-trabalho.md
