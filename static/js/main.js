// arquivo: static/js/main.js (versão com correção de cache e forca robusta)

document.addEventListener('DOMContentLoaded', () => {
    const palavraSecretaEl = document.querySelector('#palavra-secreta p');
    const tecladoEl = document.getElementById('teclado');
    const letrasUsadasEl = document.getElementById('letras-usadas');
    const tentativasEl = document.getElementById('tentativas-restantes');
    const dica1El = document.getElementById('dica1');
    const dica2El = document.getElementById('dica2');
    const partesDoCorpo = document.querySelectorAll('.figura-parte');
    const modalContainerEl = document.getElementById('modal-container');
    const modalTituloEl = document.getElementById('modal-titulo');
    const modalMensagemEl = document.getElementById('modal-mensagem');
    const btnJogarNovamenteEl = document.getElementById('btn-jogar-novamente');

    const LETRAS = 'abcdefghijklmnopqrstuvwxyz';
    let maxErros = 7; 

    function atualizarForca(erros) {
        partesDoCorpo.forEach((parte, index) => {
            if (index < erros) {
                parte.classList.add('visivel');
            } else {
                parte.classList.remove('visivel');
            }
        });
    }
    
    function mostrarModal(titulo, mensagem, venceu) {
        modalTituloEl.textContent = titulo;
        modalMensagemEl.textContent = mensagem;
        const modalEl = document.querySelector('.modal');
        modalEl.classList.remove('venceu', 'perdeu');
        if (venceu) {
            modalEl.classList.add('venceu');
        } else {
            modalEl.classList.add('perdeu');
        }
        modalContainerEl.classList.add('show');
    }

    function atualizarUI(data) {
        palavraSecretaEl.textContent = data.palavra_oculta.split('').join(' ');
        letrasUsadasEl.textContent = `Letras usadas: ${data.letras_tentadas.join(', ').toUpperCase()}`;
        tentativasEl.textContent = data.tentativas_restantes;
        atualizarForca(data.erros);
    }

    async function iniciarNovoJogo() {
        modalContainerEl.classList.remove('show');
        
        // <<< MUDANÇA: Adicionando um parâmetro aleatório para evitar o cache do navegador
        const url = `/novo_jogo?timestamp=${new Date().getTime()}`;
        const response = await fetch(url);
        
        const data = await response.json();
        maxErros = data.tentativas_restantes;
        
        atualizarUI(data);
        dica1El.textContent = data.dicas[0];
        dica2El.textContent = data.dicas[1];
        
        document.querySelectorAll('.tecla').forEach(botao => botao.disabled = false);
    }

    async function fazerTentativa(letra) {
        const botaoClicado = [...tecladoEl.children].find(b => b.textContent.toLowerCase() === letra);
        if (botaoClicado && !botaoClicado.disabled) {
            botaoClicado.disabled = true;

            const response = await fetch('/tentativa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ letra: letra })
            });
            const data = await response.json();

            atualizarUI(data);

            if (data.fim_de_jogo) {
                setTimeout(() => {
                    mostrarModal(
                        data.venceu ? 'Você Venceu!' : 'Fim de Jogo!',
                        data.mensagem_fim,
                        data.venceu
                    );
                }, 500);
            }
        }
    }

    function criarTeclado() {
        for (const letra of LETRAS) {
            const botao = document.createElement('button');
            botao.textContent = letra.toUpperCase();
            botao.classList.add('tecla');
            botao.addEventListener('click', () => fazerTentativa(letra));
            tecladoEl.appendChild(botao);
        }
    }

    btnJogarNovamenteEl.addEventListener('click', iniciarNovoJogo);
    criarTeclado();
    iniciarNovoJogo();
});