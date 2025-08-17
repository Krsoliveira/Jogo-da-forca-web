// static/js/main.js (versão final com ranking pessoal)

document.addEventListener('DOMContentLoaded', () => {
    // --- SELETORES DE ELEMENTOS ---
    const elements = {
        mainContainer: document.querySelector('main'),
        dificuldadeContainer: document.getElementById('container-selecao-dificuldade'),
        categoriaContainer: document.getElementById('container-selecao-categoria'),
        jogoContainer: document.getElementById('container-jogo-principal'),
        rankingContainer: document.getElementById('container-ranking'), // NOVO
        botoesCategoria: document.getElementById('botoes-categoria'),
        palavraSecretaP: document.querySelector('#palavra-secreta p'),
        teclado: document.getElementById('teclado'),
        letrasUsadasSpan: document.getElementById('letras-usadas'),
        tentativasSpan: document.getElementById('tentativas-restantes'),
        pontuacaoSpan: document.getElementById('pontuacao-atual'),
        dificuldadeSpan: document.getElementById('dificuldade-texto'),
        dica1P: document.getElementById('dica1'),
        dica2P: document.getElementById('dica2'),
        partesDoCorpo: document.querySelectorAll('.figura-parte'),
        modalContainer: document.getElementById('modal-container'),
        modalTitulo: document.getElementById('modal-titulo'),
        modalMensagem: document.getElementById('modal-mensagem'),
        inputChute: document.getElementById('input-chute'),
        toastNotificacao: document.getElementById('toast-notificacao'),
        nivelAtualSpan: document.getElementById('nivel-atual'),
        xpBarFill: document.getElementById('xp-bar-fill'),
        xpTextoSpan: document.getElementById('xp-texto'),
        listaRanking: document.getElementById('lista-ranking') // NOVO
    };

    // --- VARIÁVEIS DE ESTADO ---
    const LETRAS = 'abcdefghijklmnopqrstuvwxyz';
    const RANKING_KEY = 'rankingJogoDaForca'; // Chave para o localStorage
    let jogoAtivo = false;
    let dificuldadeSelecionada = null;
    let categoriasCarregadas = false;

    // --- LÓGICA DE RANKING ---
    function salvarPontuacao(pontuacaoFinal) {
        if (pontuacaoFinal <= 0) return; // Não salva pontuação zerada

        const ranking = JSON.parse(localStorage.getItem(RANKING_KEY)) || [];
        ranking.push(pontuacaoFinal);
        ranking.sort((a, b) => b - a); // Ordena do maior para o menor
        const novoRanking = ranking.slice(0, 5); // Pega apenas os 5 melhores
        localStorage.setItem(RANKING_KEY, JSON.stringify(novoRanking));
    }

    function exibirRanking() {
        elements.modalContainer.classList.remove('show');
        mostrarTela('ranking');

        const ranking = JSON.parse(localStorage.getItem(RANKING_KEY)) || [];
        elements.listaRanking.innerHTML = ''; // Limpa a lista antes de preencher

        if (ranking.length === 0) {
            elements.listaRanking.innerHTML = '<li>Nenhuma pontuação registrada ainda. Jogue uma partida!</li>';
        } else {
            ranking.forEach(pontos => {
                const li = document.createElement('li');
                li.textContent = `${pontos} Pontos`;
                elements.listaRanking.appendChild(li);
            });
        }
    }

    // --- FUNÇÕES DE LÓGICA DE JOGO ---
    function mostrarTela(tela) {
        elements.dificuldadeContainer.classList.add('hidden');
        elements.categoriaContainer.classList.add('hidden');
        elements.jogoContainer.classList.add('hidden');
        elements.rankingContainer.classList.add('hidden'); // Esconde a tela de ranking
        
        const container = elements[`${tela}Container`];
        if (container) container.classList.remove('hidden');
    }

    async function fetchWrapper(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) throw new Error(`Erro HTTP: ${response.status}`);
            return response.json();
        } catch (error) {
            mostrarModal("Erro de Conexão", `Não foi possível comunicar com o servidor.`);
            return null;
        }
    }
    
    async function selecionarDificuldade(difficulty) {
        dificuldadeSelecionada = difficulty;
        if (!categoriasCarregadas) {
            elements.botoesCategoria.innerHTML = '<p>A carregar categorias...</p>';
            const categorias = await fetchWrapper('/categorias');
            if (categorias) {
                elements.botoesCategoria.innerHTML = '';
                categorias.forEach(cat => {
                    const botao = document.createElement('button');
                    botao.textContent = cat;
                    botao.classList.add('btn-categoria');
                    elements.botoesCategoria.appendChild(botao);
                });
                categoriasCarregadas = true;
            }
        }
        mostrarTela('categoria');
    }

    async function iniciarNovoJogo(categoria) {
        resetarUI();
        mostrarTela('jogo');
        elements.palavraSecretaP.textContent = "A CARREGAR...";
        const url = `/novo_jogo?category=${encodeURIComponent(categoria)}&difficulty=${dificuldadeSelecionada}`;
        const data = await fetchWrapper(url);
        if (data) {
            atualizarUICompleta(data);
            jogoAtivo = true;
        }
    }
    
    async function fazerJogada(url, options) {
        if (!jogoAtivo) return;
        jogoAtivo = false;

        const data = await fetchWrapper(url, options);
        if (!data) {
            jogoAtivo = true;
            return;
        }

        atualizarUICompleta(data);

        if (data.vitoria_rodada) {
            mostrarNotificacao(data.notificacao, data.levelup);
            await new Promise(resolve => setTimeout(resolve, 2500));
            
            const proximaPalavraData = await fetchWrapper('/proxima_palavra');
            if (proximaPalavraData) {
                if (proximaPalavraData.sem_mais_palavras) {
                    mostrarModal("Parabéns!", "Você completou todas as palavras desta categoria!");
                } else {
                    resetarTecladoEDicas();
                    atualizarUICompleta(proximaPalavraData);
                    jogoAtivo = true;
                }
            }
        } else if (data.fim_de_jogo) {
            salvarPontuacao(data.pontuacao_final); // SALVA A PONTUAÇÃO AO PERDER
        } else {
            jogoAtivo = true;
        }
    }

    function fazerTentativa(letra) {
        const botao = [...elements.teclado.children].find(b => b.textContent.toLowerCase() === letra);
        if (botao && !botao.disabled) {
            botao.disabled = true;
            fazerJogada('/tentativa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ letra }) });
        }
    }
    
    function fazerChute() {
        const palavra = elements.inputChute.value;
        if (palavra.trim().length < 2) return;
        elements.inputChute.value = '';
        fazerJogada('/chute', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ palavra }) });
    }

    // --- FUNÇÕES DE UI ---
    function mostrarModal(titulo, mensagem) {
        elements.modalTitulo.textContent = titulo;
        elements.modalMensagem.innerHTML = mensagem;
        elements.modalContainer.classList.add('show');
    }

    function mostrarNotificacao(mensagem, levelup = false) {
        const toast = elements.toastNotificacao;
        toast.textContent = mensagem;
        toast.className = 'toast show';
        if (levelup) {
            toast.classList.add('levelup');
        }
        setTimeout(() => {
            toast.classList.remove('show');
        }, 2200);
    }
    
    function atualizarUICompleta(data) {
        elements.palavraSecretaP.textContent = data.palavra_oculta.toUpperCase().split('').join(' ');
        elements.dica1P.textContent = data.dicas ? data.dicas[0] : ' ';
        elements.dica2P.style.display = (data.dicas && data.dicas[1]) ? 'block' : 'none';
        elements.dica2P.textContent = (data.dicas && data.dicas[1]) ? data.dicas[1] : '';
        elements.tentativasSpan.textContent = data.tentativas_restantes;
        elements.letrasUsadasSpan.textContent = data.letras_tentadas.join(', ').toUpperCase();
        elements.pontuacaoSpan.textContent = data.pontuacao;
        elements.dificuldadeSpan.textContent = data.dificuldade || dificuldadeSelecionada;
        elements.partesDoCorpo.forEach((p, i) => p.style.opacity = i < data.erros ? '1' : '0');

        if (data.nivel !== undefined) {
            elements.nivelAtualSpan.textContent = data.nivel;
            elements.xpTextoSpan.textContent = `${data.xp_atual}/${data.xp_necessario}`;
            const xpPercent = data.xp_necessario > 0 ? (data.xp_atual / data.xp_necessario) * 100 : 0;
            elements.xpBarFill.style.width = `${xpPercent}%`;
        }

        if (data.fim_de_jogo && !data.vitoria_rodada) {
            setTimeout(() => mostrarModal('Fim de Jogo!', data.mensagem_fim), 800);
        }
    }
    
    function resetarTecladoEDicas() {
        elements.letrasUsadasSpan.textContent = '';
        elements.teclado.querySelectorAll('.tecla').forEach(tecla => tecla.disabled = false);
    }

    function resetarUI() {
        resetarTecladoEDicas();
        elements.palavraSecretaP.innerHTML = '&#160;';
        elements.dica1P.innerHTML = '&#160;';
        elements.dica2P.innerHTML = '&#160;';
        elements.pontuacaoSpan.textContent = '0';
        elements.inputChute.value = '';
        elements.partesDoCorpo.forEach(p => p.style.opacity = '0');
        elements.modalContainer.classList.remove('show');
        elements.xpBarFill.style.width = '0%';
    }

    // --- INICIALIZAÇÃO E EVENT LISTENERS ---
    elements.mainContainer.addEventListener('click', (e) => {
        const target = e.target;
        if (target.matches('.btn-dificuldade')) selecionarDificuldade(target.dataset.difficulty);
        else if (target.matches('.btn-categoria')) iniciarNovoJogo(target.textContent);
        else if (target.matches('#btn-voltar-dificuldade')) mostrarTela('dificuldade');
        else if (target.matches('#btn-chutar')) fazerChute();
        else if (target.matches('.btn-restart')) {
            resetarUI();
            mostrarTela('dificuldade');
        } else if (target.matches('#btn-voltar-menu-ranking')) { // NOVO
            resetarUI();
            mostrarTela('dificuldade');
        } else if (target.matches('#btn-ver-ranking')) { // NOVO
            exibirRanking();
        }
    });

    elements.teclado.addEventListener('click', e => {
        if(e.target.matches('.tecla')) fazerTentativa(e.target.textContent.toLowerCase());
    });

    // Listener de clique para o modal foi mesclado ao listener principal
    // para os botões 'jogar novamente' e 'ver ranking'
    elements.modalContainer.addEventListener('click', (e) => {
        if (e.target.matches('#btn-jogar-novamente')) {
            resetarUI();
            mostrarTela('dificuldade');
        } else if (e.target.matches('#btn-ver-ranking')) {
            exibirRanking();
        }
    });
    
    document.addEventListener('keydown', (e) => {
        if (!jogoAtivo) return;
        if (e.key === 'Enter' && document.activeElement === elements.inputChute) { 
            e.preventDefault(); 
            fazerChute();
        } else if (LETRAS.includes(e.key.toLowerCase())) {
            fazerTentativa(e.key.toLowerCase());
        }
    });

    LETRAS.split('').forEach(letra => {
        const botao = document.createElement('button');
        botao.textContent = letra.toUpperCase();
        botao.classList.add('tecla');
        elements.teclado.appendChild(botao);
    });
    
    mostrarTela('dificuldade');
});