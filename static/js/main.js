document.addEventListener('DOMContentLoaded', () => {
  const elements = {
    mainContainer: document.querySelector('main'),
    dificuldadeContainer: document.getElementById('container-selecao-dificuldade'),
    categoriaContainer: document.getElementById('container-selecao-categoria'),
    jogoContainer: document.getElementById('container-jogo-principal'),
    botoesCategoria: document.getElementById('botoes-categoria'),
    palavraSecretaP: document.querySelector('#palavra-secreta p'),
    teclado: document.getElementById('teclado'),
    letrasUsadasSpan: document.getElementById('letras-usadas'),
    tentativasSpan: document.getElementById('tentativas-restantes'),
    pontuacaoSpan: document.getElementById('pontuacao-atual'),
    dificuldadeSpan: document.getElementById('dificuldade-atual'),
    dica1P: document.getElementById('dica1'),
    dica2P: document.getElementById('dica2'),
    partesDoCorpo: document.querySelectorAll('.figura-parte'),
    modalContainer: document.getElementById('modal-container'),
    modalTitulo: document.getElementById('modal-titulo'),
    modalMensagem: document.getElementById('modal-mensagem'),
    inputChute: document.getElementById('input-chute'),
    toastNotificacao: document.getElementById('toast-notificacao'),
    btnVerRanking: document.getElementById('btn-ver-ranking'),  // botão para ver ranking
    rankingContainer: document.getElementById('ranking-container') // container para exibir ranking
  };

  const LETRAS = 'abcdefghijklmnopqrstuvwxyz';
  let jogoAtivo = false;
  let dificuldadeSelecionada = null;
  let categoriasCarregadas = false;

  function mostrarTela(tela) {
    elements.dificuldadeContainer.classList.add('hidden');
    elements.categoriaContainer.classList.add('hidden');
    elements.jogoContainer.classList.add('hidden');
    if (elements.rankingContainer) elements.rankingContainer.classList.add('hidden');
    const container = elements[`${tela}Container`];
    if (container) container.classList.remove('hidden');
  }

  async function fetchWrapper(url, options = {}) {
    try {
      const res = await fetch(url, options);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      mostrarModal("Erro de Conexão", "Não foi possível comunicar com o servidor.");
      return null;
    }
  }

  async function selecionarDificuldade(diff) {
    dificuldadeSelecionada = diff;
    if (!categoriasCarregadas) {
      elements.botoesCategoria.innerHTML = '<p>A carregar categorias...</p>';
      const cats = await fetchWrapper('/categorias');
      if (cats) {
        elements.botoesCategoria.innerHTML = '';
        cats.forEach(cat => {
          const btn = document.createElement('button');
          btn.textContent = cat;
          btn.classList.add('btn-categoria');
          elements.botoesCategoria.appendChild(btn);
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
    const data = await fetchWrapper(
      `/novo_jogo?category=${encodeURIComponent(categoria)}&difficulty=${dificuldadeSelecionada}`
    );
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
    if (data.sem_mais_palavras) {
      mostrarModal("Parabéns!", "Você completou todas as palavras desta categoria!");
      return;
    }

    atualizarUICompleta(data);

    if (data.vitoria_rodada) {
      mostrarNotificacao(data.notificacao, data.notificacao.includes('aumentado'));
      await new Promise(r => setTimeout(r, 2500));
      const next = await fetchWrapper('/proxima_palavra');
      if (next) {
        if (next.sem_mais_palavras) {
          mostrarModal("Parabéns!", "Você completou todas as palavras desta categoria!");
        } else {
          resetarTecladoEDicas();
          atualizarUICompleta(next);
          jogoAtivo = true;
        }
      }
    } else if (!data.fim_de_jogo) {
      jogoAtivo = true;
    }
  }

  function fazerTentativa(letra) {
    const btn = [...elements.teclado.children].find(b =>
      b.textContent.toLowerCase() === letra
    );
    if (btn && !btn.disabled) {
      btn.disabled = true;
      fazerJogada('/tentativa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ letra })
      });
    }
  }

  function fazerChute() {
    const pal = elements.inputChute.value.trim();
    if (pal.length < 2) return;
    elements.inputChute.value = '';
    fazerJogada('/chute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ palavra: pal })
    });
  }

  function mostrarModal(titulo, mensagem) {
    elements.modalTitulo.textContent = titulo;
    elements.modalMensagem.innerHTML = mensagem;
    elements.modalContainer.classList.add('show');
  }

  function mostrarNotificacao(mensagem, levelup = false) {
    const toast = elements.toastNotificacao;
    toast.textContent = mensagem;
    toast.className = '';
    toast.classList.add('show');
    if (levelup) toast.classList.add('levelup');
    setTimeout(() => toast.classList.remove('show'), 2200);
  }

  function atualizarUICompleta(data) {
    elements.palavraSecretaP.textContent =
      data.palavra_oculta.toUpperCase().split('').join(' ');
    elements.dica1P.textContent = data.dicas?.[0] || '';
    elements.dica2P.textContent = data.dicas?.[1] || '';
    elements.dica2P.style.display = data.dicas?.[1] ? 'block' : 'none';
    elements.tentativasSpan.textContent = data.tentativas_restantes;
    elements.letrasUsadasSpan.textContent =
      data.letras_tentadas.join(', ').toUpperCase();
    elements.pontuacaoSpan.textContent = data.pontuacao;
    elements.dificuldadeSpan.textContent =
      data.dificuldade || dificuldadeSelecionada;
    elements.partesDoCorpo.forEach((p, i) =>
      p.style.opacity = i < data.erros ? '1' : '0'
    );

    // Marca teclas corretas e erradas
    Array.from(elements.teclado.children).forEach(botao => {
      const l = botao.textContent.toLowerCase();
      if (data.letras_tentadas.includes(l)) {
        botao.disabled = true;
        botao.classList.toggle('correta',
          data.palavra_oculta.toLowerCase().includes(l)
        );
        botao.classList.toggle('errada',
          !data.palavra_oculta.toLowerCase().includes(l)
        );
      }
    });

    if (data.fim_de_jogo && !data.vitoria_rodada) {
      setTimeout(() =>
        mostrarModal('Fim de Jogo!', data.mensagem_fim), 800
      );
    }
  }

  function resetarTecladoEDicas() {
    elements.letrasUsadasSpan.textContent = '';
    elements.teclado.querySelectorAll('.tecla').forEach(t => {
      t.disabled = false;
      t.classList.remove('correta', 'errada');
    });
  }

  function resetarUI() {
    resetarTecladoEDicas();
    elements.palavraSecretaP.innerHTML = '&#160;';
    elements.dica1P.innerHTML = '&#160;';
    elements.dica2P.innerHTML = '&#160;';
    elements.dica2P.style.display = 'block';
    elements.pontuacaoSpan.textContent = '0';
    elements.inputChute.value = '';
    elements.partesDoCorpo.forEach(p => p.style.opacity = '0');
    elements.modalContainer.classList.remove('show');
  }

  function voltarParaInicio() {
    resetarUI();
    mostrarTela('dificuldade');
    setTimeout(() => {
      const btn = document.querySelector('.btn-dificuldade');
      if (btn) btn.focus();
    }, 100);
  }

  async function exibirRanking() {
    const ranking = await fetchWrapper('/ranking');
    if (ranking) {
      let html = '<h2>Ranking - Top 10</h2><ol>';
      ranking.forEach(entry => {
        html += `<li>${entry.nome}: ${entry.pontuacao} pontos</li>`;
      });
      html += '</ol>';
      if (elements.rankingContainer) {
        elements.rankingContainer.innerHTML = html;
        mostrarTela('ranking');
      } else {
        // Se não houver container específico, exiba em um modal temporário.
        mostrarModal("Ranking", html);
      }
    }
  }

  elements.mainContainer.addEventListener('click', e => {
    if (e.target.matches('.btn-dificuldade'))
      selecionarDificuldade(e.target.dataset.difficulty);
    else if (e.target.matches('.btn-categoria'))
      iniciarNovoJogo(e.target.textContent);
    else if (e.target.matches('#btn-voltar-dificuldade'))
      mostrarTela('dificuldade');
    else if (e.target.matches('#btn-chutar'))
      fazerChute();
    else if (e.target.matches('.btn-restart'))
      voltarParaInicio();
  });

  elements.teclado.addEventListener('click', e => {
    if (e.target.matches('.tecla'))
      fazerTentativa(e.target.textContent.toLowerCase());
  });

  elements.modalContainer.addEventListener('click', e => {
    if (e.target.matches('#btn-jogar-novamente'))
      voltarParaInicio();
  });

  document.addEventListener('keydown', e => {
    if (!jogoAtivo) return;
    if (e.key === 'Enter' && document.activeElement === elements.inputChute) {
      e.preventDefault();
      fazerChute();
    } else if (LETRAS.includes(e.key.toLowerCase())) {
      fazerTentativa(e.key.toLowerCase());
    }
  });

  // Renderiza o teclado
  LETRAS.split('').forEach(l => {
    const btn = document.createElement('button');
    btn.textContent = l.toUpperCase();
    btn.classList.add('tecla');
    elements.teclado.appendChild(btn);
  });

  // Botão para ver ranking (caso exista no HTML)
  if (elements.btnVerRanking) {
    elements.btnVerRanking.addEventListener('click', exibirRanking);
  }

  mostrarTela('dificuldade');
});