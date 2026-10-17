// Controlador da partida: liga a tela de jogo à API. O servidor é a fonte da verdade (palavra, erros,
// pontos); a interface só desenha o que ele responde, então trapacear pelo navegador não adianta.
import { api } from "./api.js";
import { criarForca } from "./forca.js";
import { icone } from "./icones.js";
import {
    animarAcerto,
    animarBarra,
    animarErro,
    contarAte,
    efeitoPressionar,
    entradaCasas,
    entradaTeclas,
    ondaVitoria,
    pulsar,
    revelarLetra,
    saidaCasas,
} from "./movimento.js";
import { anunciar, mostrarToast } from "./toast.js";

const LINHAS_TECLADO = ["qwertyuiop", "asdfghjkl", "zxcvbnm"];
const NOME_DIFICULDADE = { facil: "Fácil", medio: "Médio", dificil: "Difícil" };
const CHAVE_RANKING = "rankingJogoDaForca"; // mesmo ranking da interface atual (5 melhores)
const PAUSA_ENTRE_PALAVRAS_MS = 1700;

const esperar = (ms) => new Promise((r) => { setTimeout(r, ms); });

/** Salva a pontuação no ranking local e diz se é um novo recorde. */
export function salvarNoRanking(pontos) {
    if (!(pontos > 0)) return false;
    let ranking = [];
    try { ranking = JSON.parse(localStorage.getItem(CHAVE_RANKING)) || []; } catch { ranking = []; }
    const anterior = Math.max(0, ...ranking.filter(Number.isFinite));
    const novo = [...ranking.filter(Number.isFinite), pontos].sort((a, b) => b - a).slice(0, 5);
    try { localStorage.setItem(CHAVE_RANKING, JSON.stringify(novo)); } catch { /* sem armazenamento */ }
    return pontos > anterior;
}

export function criarJogo(raiz, { aoVoltarAoMenu }) {
    const $ = (s) => raiz.querySelector(s);
    const forca = criarForca($("[data-forca]"));
    const palavraEl = $("[data-palavra]");
    const teclado = $("[data-teclado]");
    const formChute = $("[data-chute-form]");
    const campoChute = formChute.querySelector("input");
    const dialogo = document.querySelector("[data-fim]");

    const estado = {
        categoria: null,
        dificuldadeEscolhida: null,
        dificuldade: null,
        maxErros: 6,
        erros: 0,
        pontos: 0,
        nivel: 1,
        xp: 0,
        xpNecessario: 1000,
        oculta: "",
        casas: [], // uma por caractere da palavra (null para espaços)
        encerrada: true,
        rodada: 0, // muda a cada palavra; jogadas de uma rodada antiga são descartadas
        fila: Promise.resolve(),
    };

    // ───────── Montagem ─────────
    function montarTeclado() {
        teclado.replaceChildren(
            ...LINHAS_TECLADO.map((linha) => {
                const div = document.createElement("div");
                div.className = "teclado-linha";
                for (const letra of linha) {
                    const tecla = document.createElement("button");
                    tecla.type = "button";
                    tecla.className = "tecla";
                    tecla.dataset.letra = letra;
                    tecla.textContent = letra.toUpperCase();
                    tecla.setAttribute("aria-label", `Letra ${letra.toUpperCase()}`);
                    tecla.addEventListener("click", () => jogarLetra(letra));
                    efeitoPressionar(tecla);
                    div.append(tecla);
                }
                return div;
            }),
        );
    }

    const tecla = (letra) => teclado.querySelector(`[data-letra="${letra}"]`);
    const teclas = () => [...teclado.querySelectorAll(".tecla")];

    function montarPalavra(oculta) {
        estado.casas = [];
        const grupos = [];
        let grupo = null;
        [...oculta].forEach((ch) => {
            if (ch === " ") {
                grupo = null;
                estado.casas.push(null);
                return;
            }
            if (!grupo) {
                grupo = document.createElement("span");
                grupo.className = "palavra-grupo";
                grupos.push(grupo);
            }
            const casa = document.createElement("span");
            casa.className = "casa";
            if (ch !== "_") {
                casa.textContent = ch.toUpperCase();
                casa.classList.add(/[a-z]/.test(ch) ? "casa-revelada" : "casa-fixa");
            }
            grupo.append(casa);
            estado.casas.push(casa);
        });
        palavraEl.replaceChildren(...grupos);
        estado.oculta = oculta;
        descreverPalavra();
        entradaCasas(estado.casas.filter(Boolean));
    }

    function descreverPalavra() {
        const letras = [...estado.oculta].filter((c) => c !== " ").length;
        const palavras = estado.oculta.split(" ").length;
        const leitura = [...estado.oculta].map((c) => (c === "_" ? "vazio" : c === " " ? "espaço" : c)).join(", ");
        palavraEl.setAttribute("aria-label", `Palavra secreta: ${leitura}`);
        $("[data-hud-tamanho]").textContent = palavras > 1 ? `${palavras} palavras · ${letras} letras` : `${letras} letras`;
    }

    /** Mostra as letras que o servidor acabou de revelar, uma depois da outra. */
    function revelar(oculta, { classe = null } = {}) {
        let ordem = 0;
        [...oculta].forEach((ch, i) => {
            const casa = estado.casas[i];
            if (!casa || ch === "_" || estado.oculta[i] === ch) return;
            const atraso = ordem++ * 70;
            setTimeout(() => {
                revelarLetra(casa, ch.toUpperCase());
                if (classe) casa.classList.add(classe);
            }, atraso);
        });
        estado.oculta = oculta;
        descreverPalavra();
    }

    function desenharVidas() {
        const area = $("[data-vidas]");
        const restantes = estado.maxErros - estado.erros;
        const atuais = area.children.length;
        if (atuais !== estado.maxErros) {
            area.replaceChildren(...Array.from({ length: estado.maxErros }, () => {
                const v = document.createElement("span");
                v.className = "vida";
                v.append(icone("Heart"));
                return v;
            }));
        }
        [...area.children].forEach((vida, i) => {
            const perdida = i >= restantes;
            if (perdida && !vida.classList.contains("vida-perdida")) pulsar(vida);
            vida.classList.toggle("vida-perdida", perdida);
        });
    }

    /** Pontos garantidos em destaque; os da palavra atual aparecem à parte, porque só contam se ela for acertada. */
    function atualizarHud(d, { animar = true } = {}) {
        if (d.pontos_garantidos !== undefined && d.pontos_garantidos !== estado.pontos) {
            if (animar) contarAte($("[data-hud-pontos]"), estado.pontos, d.pontos_garantidos);
            else $("[data-hud-pontos]").textContent = String(d.pontos_garantidos);
            estado.pontos = d.pontos_garantidos;
        }
        if (d.pontos_em_jogo !== undefined) {
            const emJogo = $("[data-hud-em-jogo]");
            emJogo.textContent = `+${d.pontos_em_jogo} em jogo`;
            if (emJogo.hidden && d.pontos_em_jogo > 0) pulsar(emJogo);
            emJogo.hidden = d.pontos_em_jogo === 0;
        }
        if (d.dificuldade && d.dificuldade !== estado.dificuldade) {
            if (estado.dificuldade) pulsar($("[data-hud-dificuldade]"));
            estado.dificuldade = d.dificuldade;
            $("[data-hud-dificuldade]").textContent = NOME_DIFICULDADE[d.dificuldade] ?? d.dificuldade;
        }
        if (d.nivel !== undefined) {
            const subiu = d.nivel > estado.nivel;
            estado.nivel = d.nivel;
            estado.xp = d.xp_atual;
            estado.xpNecessario = d.xp_necessario;
            $("[data-hud-nivel]").textContent = String(d.nivel);
            $("[data-hud-xp-texto]").textContent = `${d.xp_atual}/${d.xp_necessario}`;
            const barra = $("[data-hud-xp-barra]");
            barra.setAttribute("aria-valuemax", String(d.xp_necessario));
            barra.setAttribute("aria-valuenow", String(d.xp_atual));
            animarBarra($("[data-hud-xp]"), (d.xp_atual / d.xp_necessario) * 100);
            if (subiu) pulsar($("[data-hud-nivel]").parentElement);
        }
    }

    function mostrarDicas(dicas) {
        if (!dicas) return;
        $('[data-dica="0"]').textContent = dicas[0] || "";
        const segunda = $('[data-dica="1"]');
        segunda.textContent = dicas[1] || "";
        segunda.hidden = !dicas[1];
    }

    function prepararRodada(d) {
        estado.rodada += 1;
        estado.erros = d.erros;
        estado.maxErros = d.erros + d.tentativas_restantes;
        estado.encerrada = false;
        montarPalavra(d.palavra_oculta);
        mostrarDicas(d.dicas);
        desenharVidas();
        forca.reiniciar();
        teclas().forEach((t) => {
            t.disabled = false;
            t.classList.remove("tecla-certa", "tecla-errada", "tecla-pendente");
        });
        entradaTeclas(teclas());
        fecharChute();
    }

    // ───────── Jogadas ─────────
    function jogarLetra(letra) {
        const t = tecla(letra);
        if (estado.encerrada || !t || t.disabled) return;
        t.disabled = true;
        t.classList.add("tecla-pendente");
        // Em fila: digitando rápido, cada letra espera a resposta da anterior e nenhuma se perde.
        // A rodada vai junto para uma letra digitada no fim de uma palavra não cair na seguinte.
        const rodada = estado.rodada;
        estado.fila = estado.fila.then(() => enviarLetra(letra, rodada));
    }

    async function enviarLetra(letra, rodada) {
        const t = tecla(letra);
        if (estado.encerrada || rodada !== estado.rodada) {
            t.classList.remove("tecla-pendente");
            return;
        }
        let d;
        try {
            d = await api.tentativa(letra);
        } catch (erro) {
            t.classList.remove("tecla-pendente");
            t.disabled = false;
            tratarErro(erro);
            return;
        }
        t.classList.remove("tecla-pendente");
        const certa = d.palavra_oculta.includes(letra);
        t.classList.add(certa ? "tecla-certa" : "tecla-errada");
        if (certa) animarAcerto(t);
        await aplicar(d, { descricao: `Letra ${letra.toUpperCase()}: ${certa ? "certa" : "errada"}` });
    }

    async function enviarChute(valor) {
        let d;
        try {
            d = await api.chute(valor);
        } catch (erro) {
            tratarErro(erro);
            return;
        }
        fecharChute();
        const acertou = Boolean(d.vitoria_rodada);
        if (!acertou) mostrarToast("Não é essa palavra", "erro");
        await aplicar(d, { descricao: acertou ? "Você acertou a palavra" : "Chute errado" });
    }

    async function aplicar(d, { descricao }) {
        const errou = d.erros > estado.erros;
        estado.erros = d.erros;
        estado.maxErros = d.erros + d.tentativas_restantes;
        desenharVidas();
        forca.atualizar(estado.erros, estado.maxErros);
        if (errou) animarErro(palavraEl);

        // Vitória e derrota seguem fora da fila: a comemoração não pode segurar as próximas jogadas.
        if (d.vitoria_rodada) {
            vencer(d);
            return;
        }
        if (d.fim_de_jogo) {
            perder(d);
            return;
        }

        revelar(d.palavra_oculta);
        atualizarHud(d);
        mostrarDicas(d.dicas);
        const restantes = d.tentativas_restantes;
        anunciar(`${descricao}. ${restantes} ${restantes === 1 ? "tentativa restante" : "tentativas restantes"}.`);
    }

    async function vencer(d) {
        estado.encerrada = true;
        const rodada = estado.rodada;
        revelar(d.palavra_oculta);
        await esperar(Math.min(600, estado.casas.length * 70));
        ondaVitoria(estado.casas.filter(Boolean));
        forca.comemorar();
        atualizarHud(d);
        mostrarToast(d.notificacao ?? "Acertou!", d.levelup ? "nivel" : "sucesso");
        teclas().forEach((t) => { t.disabled = true; });

        await esperar(PAUSA_ENTRE_PALAVRAS_MS);
        if (raiz.hidden || rodada !== estado.rodada) return; // saiu ou recomeçou durante a comemoração
        await saidaCasas(estado.casas.filter(Boolean));
        try {
            prepararRodada(await api.proximaPalavra());
        } catch (erro) {
            tratarErro(erro);
        }
    }

    async function perder(d) {
        estado.encerrada = true;
        teclas().forEach((t) => { t.disabled = true; });
        revelar(d.palavra_oculta, { classe: "casa-perdida" });
        atualizarHud({ ...d, pontos_garantidos: d.pontuacao_final }, { animar: false });
        const recorde = salvarNoRanking(d.pontuacao_final);
        estado.pontos = 0;
        anunciar(`Fim de jogo. A palavra era ${d.palavra_oculta}.`);
        await forca.derrota();
        abrirFim({ palavra: d.palavra_oculta, pontos: d.pontuacao_final, recorde });
    }

    function tratarErro(erro) {
        if (erro.sessaoPerdida) {
            estado.encerrada = true;
            abrirFim({ expirada: true, pontos: estado.pontos, recorde: salvarNoRanking(estado.pontos) });
            return;
        }
        mostrarToast(erro.status === 0 ? "Sem conexão. Tente de novo." : "Algo deu errado. Tente de novo.", "erro");
    }

    // ───────── Chute ─────────
    function abrirChute() {
        if (estado.encerrada) return;
        formChute.hidden = false;
        $("[data-chute-abrir-area]").hidden = true;
        campoChute.value = "";
        campoChute.focus();
    }

    function fecharChute() {
        formChute.hidden = true;
        $("[data-chute-abrir-area]").hidden = false;
    }

    $("[data-chute-abrir]").addEventListener("click", abrirChute);
    $("[data-chute-cancelar]").addEventListener("click", fecharChute);
    formChute.addEventListener("submit", (e) => {
        e.preventDefault();
        const valor = campoChute.value.trim();
        if (!valor) {
            animarErro(campoChute);
            campoChute.focus();
            return;
        }
        const rodada = estado.rodada;
        estado.fila = estado.fila.then(() => (rodada === estado.rodada && !estado.encerrada ? enviarChute(valor) : null));
    });
    campoChute.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            e.stopPropagation();
            fecharChute();
            $("[data-chute-abrir]").focus();
        }
    });

    // ───────── Fim de jogo ─────────
    function abrirFim({ palavra = "", pontos = 0, recorde = false, expirada = false }) {
        dialogo.querySelector("[data-fim-rotulo]").textContent = expirada ? "Partida encerrada" : "Fim de jogo";
        dialogo.querySelector("[data-fim-titulo]").textContent = expirada ? "Sua partida expirou" : "A forca venceu";
        dialogo.querySelector("[data-fim-palavra-area]").hidden = expirada;
        dialogo.querySelector("[data-fim-palavra]").textContent = palavra.toUpperCase();
        dialogo.querySelector("[data-fim-recorde]").hidden = !recorde;
        dialogo.querySelector("[data-fim-pontos]").textContent = "0";
        dialogo.showModal();
        contarAte(dialogo.querySelector("[data-fim-pontos]"), 0, pontos);
        dialogo.querySelector("[data-jogar-de-novo]").focus();
    }

    dialogo.querySelector("[data-jogar-de-novo]").addEventListener("click", async () => {
        dialogo.close();
        try {
            await iniciar(estado.categoria, estado.dificuldadeEscolhida);
        } catch (erro) {
            tratarErro(erro);
        }
    });
    const irAoMenu = () => {
        if (dialogo.open) dialogo.close();
        aoVoltarAoMenu();
    };
    dialogo.querySelector("[data-fim-menu]").addEventListener("click", irAoMenu);
    dialogo.addEventListener("cancel", (e) => {
        e.preventDefault(); // Esc no diálogo leva ao menu, como o botão
        irAoMenu();
    });

    // ───────── API pública ─────────
    async function iniciar(categoria, dificuldade) {
        const d = await api.novoJogo(categoria, dificuldade);
        estado.categoria = categoria;
        estado.dificuldadeEscolhida = dificuldade;
        estado.dificuldade = null;
        estado.pontos = 0;
        estado.nivel = d.nivel;
        estado.fila = Promise.resolve();
        $("[data-hud-categoria]").textContent = categoria;
        $("[data-hud-pontos]").textContent = "0";
        atualizarHud(d, { animar: false });
        prepararRodada(d);
    }

    /** Sair no meio da partida: guarda os pontos feitos até aqui, como a interface atual. */
    function sair() {
        if (!estado.encerrada) salvarNoRanking(estado.pontos);
        estado.encerrada = true;
        if (dialogo.open) dialogo.close();
    }

    /** Teclado físico: letras (com ou sem acento) jogam; o resto é ignorado. */
    function teclaFisica(e) {
        if (raiz.hidden || dialogo.open || e.ctrlKey || e.metaKey || e.altKey) return false;
        if (e.target instanceof HTMLInputElement) return false;
        const letra = e.key.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
        if (!/^[a-z]$/.test(letra)) return false;
        jogarLetra(letra);
        return true;
    }

    raiz.querySelector("[data-sair]").addEventListener("click", aoVoltarAoMenu);
    montarTeclado();
    return { iniciar, sair, teclaFisica };
}
