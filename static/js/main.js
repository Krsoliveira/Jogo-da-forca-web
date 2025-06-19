// static/js/main.js (versão final, limpa e com a correção do bug das dicas)

document.addEventListener('DOMContentLoaded', () => {
    // --- SELETORES DE ELEMENTOS ---
    const elements = {
        dificuldadeContainer: document.getElementById('container-selecao-dificuldade'),
        categoriaContainer: document.getElementById('container-selecao-categoria'),
        jogoContainer: document.getElementById('container-jogo-principal'),
        botoesDificuldade: document.getElementById('botoes-dificuldade'),
        botoesCategoria: document.getElementById('botoes-categoria'),
        btnVoltarDificuldade: document.getElementById('btn-voltar-dificuldade'),
        palavraSecretaP: document.querySelector('#palavra-secreta p'),
        teclado: document.getElementById('teclado'),
        letrasUsadasSpan: document.getElementById('letras-usadas'),
        tentativasSpan: document.getElementById('tentativas-restantes'),
        dica1P: document.getElementById('dica1'),
        dica2P: document.getElementById('dica2'),
        partesDoCorpo: document.querySelectorAll('.figura-parte'),
        modalContainer: document.getElementById('modal-container'),
        modalTitulo: document.getElementById('modal-titulo'),
        modalMensagem: document.getElementById('modal-mensagem'),
        btnJogarNovamente: document.getElementById('btn-jogar-novamente'),
        inputChute: document.getElementById('input-chute'),
        btnChutar: document.getElementById('btn-chutar')
    };

    // --- VARIÁVEIS DE ESTADO ---
    const LETRAS = 'abcdefghijklmnopqrstuvwxyz';
    let jogoAtivo = false;
    let dificuldadeSelecionada = null;
    let categoriasCarregadas = false;

    // --- FUNÇÕES DE LÓGICA DE JOGO ---
    
    function mostrarTela(tela) {
        elements.dificuldadeContainer.classList.add('hidden');
        elements.categoriaContainer.classList.add('hidden');
        elements.jogoContainer.classList.add('hidden');
        
        const container = elements[`${tela}Container`];
        if (container) {
            container.classList.remove('hidden');
        }
    }
    
    async function fetchWrapper(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ erro: "Resposta do servidor inválida" }));
                throw new Error(errorData.erro || `Erro HTTP: ${response.status}`);
            }
            return response.json();
        } catch (error) {
            console.error("Erro na comunicação com o servidor:", error);
            mostrarModal("Erro de Conexão", `Não foi possível comunicar com o servidor. Verifique o terminal e tente novamente.`, false);
            return null;
        }
    }
    
    async function selecionarDificuldade(difficulty) {
        dificuldadeSelecionada = difficulty;
        if (!categoriasCarregadas) {
            elements.botoesCategoria.innerHTML = '<p>A carregar categorias...</p>';
            const categorias = await fetchWrapper('/categorias');
            if (categorias && Array.isArray(categorias)) {
                elements.botoesCategoria.innerHTML = '';
                categorias.forEach(cat => {
                    const botao = document.createElement('button');
                    botao.textContent = cat;
                    botao.classList.add('btn-categoria');
                    botao.addEventListener('click', () => iniciarNovoJogo(cat));
                    elements.botoesCategoria.appendChild(botao);
                });
                categoriasCarregadas = true;
            } else {
                elements.botoesCategoria.innerHTML = '<p style="color:var(--accent-pink)">Erro ao carregar. Clique em Voltar e tente novamente.</p>';
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

    async function fazerTentativa(letra) {
        if (!jogoAtivo) return;
        const botao = [...elements.teclado.children].find(b => b.textContent.toLowerCase() === letra);
        if (botao && !botao.disabled) {
            botao.disabled = true;
            const data = await fetchWrapper('/tentativa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ letra }) });
            if (data) {
                botao.classList.add(data.palavra_oculta.toLowerCase().includes(letra) ? 'correta' : 'errada');
                atualizarUICompleta(data);
            } else {
                botao.disabled = false;
            }
        }
    }
    
    async function fazerChute() {
        if (!jogoAtivo) return;
        const palavra = elements.inputChute.value;
        if (palavra.trim().length < 2) return;
        const data = await fetchWrapper('/chute', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ palavra }) });
        if (data) {
            elements.inputChute.value = '';
            atualizarUICompleta(data);
        }
    }

    // --- FUNÇÕES DE ATUALIZAÇÃO DA INTERFACE (UI) ---

    function atualizarForca(erros) {
        elements.partesDoCorpo.forEach((parte, index) => {
            parte.style.opacity = index < erros ? '1' : '0';
        });
    }

    function mostrarModal(titulo, mensagem, venceu) {
        jogoAtivo = false;
        elements.modalTitulo.textContent = titulo;
        elements.modalMensagem.innerHTML = mensagem;
        const modalEl = elements.modalContainer.querySelector('.modal');
        modalEl.className = 'modal'; 
        modalEl.classList.add(venceu ? 'venceu' : 'perdeu');
        elements.modalContainer.classList.add('show');
    }

    function atualizarUICompleta(data) {
        elements.palavraSecretaP.textContent = data.palavra_oculta.toUpperCase().split('').join(' ');
        
        // <<< CORREÇÃO DO BUG DAS DICAS >>>
        // Agora, as dicas só são atualizadas se a resposta do servidor
        // (apenas no início de um novo jogo) contiver a informação 'dicas'.
        // Nas outras jogadas, esta condição é falsa e as dicas não são apagadas.
        if (data.dicas && data.dicas.length >= 2) {
            elements.dica1P.textContent = data.dicas[0];
            elements.dica2P.textContent = data.dicas[1];
        }

        elements.tentativasSpan.textContent = data.tentativas_restantes;
        elements.letrasUsadasSpan.textContent = data.letras_tentadas.join(', ').toUpperCase();
        atualizarForca(data.erros);
        
        if (data.fim_de_jogo) {
            setTimeout(() => mostrarModal(data.venceu ? 'Você Venceu!' : 'Fim de Jogo!', data.mensagem_fim, data.venceu), 800);
        }
    }
    
    function resetarUI() {
        elements.palavraSecretaP.innerHTML = '&#160;';
        elements.dica1P.innerHTML = '&#160;';
        elements.dica2P.innerHTML = '&#160;';
        elements.letrasUsadasSpan.textContent = '';
        elements.tentativasSpan.textContent = '';
        elements.inputChute.value = '';
        elements.teclado.querySelectorAll('.tecla').forEach(b => { b.disabled = false; b.className = 'tecla'; });
        atualizarForca(0);
        elements.modalContainer.classList.remove('show');
    }

    // --- INICIALIZAÇÃO E EVENT LISTENERS ---

    elements.botoesDificuldade.addEventListener('click', (e) => {
        if (e.target.matches('.btn-dificuldade')) {
            selecionarDificuldade(e.target.dataset.difficulty);
        }
    });

    LETRAS.split('').forEach(letra => {
        const botao = document.createElement('button');
        botao.textContent = letra.toUpperCase();
        botao.classList.add('tecla');
        botao.addEventListener('click', () => fazerTentativa(letra));
        elements.teclado.appendChild(botao);
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

    elements.btnChutar.addEventListener('click', fazerChute);
    elements.btnVoltarDificuldade.addEventListener('click', () => mostrarTela('dificuldade'));
    elements.btnJogarNovamente.addEventListener('click', () => {
        resetarUI();
        mostrarTela('dificuldade');
    });
    
    mostrarTela('dificuldade');
});

