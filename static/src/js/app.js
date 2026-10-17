// Nova interface: início → dificuldade → categoria → partida.
// Cada passo entra no histórico do navegador, então o "voltar" do celular volta um passo.
import { api } from "./lib/api.js";
import { icone, ICONE_DA_DIFICULDADE, iconeDaCategoria, preencherIcones } from "./lib/icones.js";
import { criarJogo } from "./lib/jogo.js";
import {
    brilhoSegueOPonteiro,
    cartoesEmCascata,
    confirmarEscolha,
    efeitoPressionar,
    entrarEmCascata,
    inclinarComPonteiro,
    ligarLetreiro,
    trocarPasso,
} from "./lib/movimento.js";

const $ = (seletor, raiz = document) => raiz.querySelector(seletor);
const $$ = (seletor, raiz = document) => [...raiz.querySelectorAll(seletor)];

const NOME_DIFICULDADE = { facil: "Fácil", medio: "Médio", dificil: "Difícil" };
const CHAVE_DIFICULDADE = "forca:dificuldade";
const CHAVE_RANKING = "rankingJogoDaForca"; // mesmo ranking da interface atual
const ORDEM = ["inicio", "dificuldade", "categoria", "jogo"];

const estado = { passo: "inicio", dificuldade: null, categoria: null, catalogo: null, ocupado: false };

// ───────── Armazenamento local (só conveniência; o jogo funciona sem ele) ─────────
function ler(chave) {
    try { return localStorage.getItem(chave); } catch { return null; }
}
function gravar(chave, valor) {
    try { localStorage.setItem(chave, valor); } catch { /* navegação privada ou bloqueado */ }
}

function mostrarRecorde() {
    let ranking = [];
    try { ranking = JSON.parse(ler(CHAVE_RANKING)) || []; } catch { ranking = []; }
    const melhor = Math.max(0, ...ranking.filter(Number.isFinite));
    if (melhor > 0) {
        $("[data-recorde-valor]").textContent = melhor.toLocaleString("pt-BR");
        $("[data-recorde]").hidden = false;
    }
}

// ───────── Catálogo (dificuldades e categorias) ─────────
async function carregarCatalogo() {
    estado.catalogo = await api.catalogo();
}

function criarOpcao({ titulo, meta, nomeIcone, classe = "", valor, rotulo }) {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = `opcao ${classe}`.trim();
    botao.dataset.valor = valor;
    botao.setAttribute("role", "listitem");
    botao.setAttribute("aria-label", rotulo);

    const caixaIcone = document.createElement("span");
    caixaIcone.className = "opcao-icone";
    caixaIcone.append(icone(nomeIcone));

    const textos = document.createElement("span");
    textos.className = "flex flex-col gap-1";
    const t = document.createElement("span");
    t.className = "opcao-titulo";
    t.textContent = titulo;
    const m = document.createElement("span");
    m.className = "opcao-meta";
    m.textContent = meta;
    textos.append(t, m);

    botao.append(caixaIcone, textos);
    brilhoSegueOPonteiro(botao);
    inclinarComPonteiro(botao, { intensidade: 7 });
    efeitoPressionar(botao);
    return botao;
}

function renderizarDificuldades() {
    const lista = $("[data-lista=dificuldades]");
    const lembrada = ler(CHAVE_DIFICULDADE);
    lista.replaceChildren(
        ...estado.catalogo.dificuldades.map((d) => {
            const dicas = d.dicas === 1 ? "1 dica" : `${d.dicas} dicas`;
            const opcao = criarOpcao({
                titulo: NOME_DIFICULDADE[d.id] ?? d.id,
                meta: `${d.tentativas} tentativas · ${dicas}`,
                nomeIcone: ICONE_DA_DIFICULDADE[d.id] ?? "Tag",
                classe: `opcao-${d.id}`,
                valor: d.id,
                rotulo: `${NOME_DIFICULDADE[d.id] ?? d.id}: ${d.tentativas} tentativas, ${dicas}`,
            });
            opcao.setAttribute("aria-pressed", String(d.id === lembrada));
            opcao.addEventListener("click", () => escolherDificuldade(opcao, d.id));
            return opcao;
        }),
    );
}

function renderizarCategorias() {
    const formatar = (n) => n.toLocaleString("pt-BR");
    const aleatorio = estado.catalogo.categorias.find((c) => c.aleatorio);
    const normais = estado.catalogo.categorias.filter((c) => !c.aleatorio);

    const lista = $("[data-lista=categorias]");
    lista.replaceChildren(
        ...normais.map((c) => {
            const opcao = criarOpcao({
                titulo: c.nome,
                meta: `${formatar(c.palavras)} palavras`,
                nomeIcone: iconeDaCategoria(c.nome),
                valor: c.nome,
                rotulo: `${c.nome}, ${formatar(c.palavras)} palavras`,
            });
            opcao.addEventListener("click", () => escolherCategoria(opcao, c.nome));
            return opcao;
        }),
    );

    const destaque = $("[data-lista=aleatorio]");
    destaque.replaceChildren();
    if (aleatorio) {
        const opcao = criarOpcao({
            titulo: "Aleatório",
            meta: `${formatar(aleatorio.palavras)} palavras do dicionário, sem tema`,
            nomeIcone: "Shuffle",
            classe: "opcao-destaque",
            valor: aleatorio.nome,
            rotulo: `Modo aleatório, ${formatar(aleatorio.palavras)} palavras sem tema`,
        });
        opcao.removeAttribute("role");
        opcao.addEventListener("click", () => escolherCategoria(opcao, aleatorio.nome));
        destaque.append(opcao);
    }
}

// ───────── Escolhas ─────────
async function escolherDificuldade(opcao, id) {
    if (estado.ocupado) return;
    estado.dificuldade = id;
    gravar(CHAVE_DIFICULDADE, id);
    $$("[data-lista=dificuldades] .opcao").forEach((o) => o.setAttribute("aria-pressed", String(o === opcao)));
    await confirmarEscolha(opcao, $$("[data-lista=dificuldades] .opcao").filter((o) => o !== opcao));
    irPara("categoria");
}

async function escolherCategoria(opcao, nome) {
    if (estado.ocupado) return;
    estado.categoria = nome;
    const todas = $$("[data-passo=categoria] .opcao");
    await confirmarEscolha(opcao, todas.filter((o) => o !== opcao));
    irPara("jogo");
}

function preencherResumo() {
    $$("[data-resumo-dificuldade]").forEach((el) => { el.textContent = NOME_DIFICULDADE[estado.dificuldade] ?? ""; });
}

// ───────── Navegação entre passos ─────────
/** Um passo só pode ser exibido se as escolhas anteriores existirem. */
function passoValido(passo) {
    if (passo === "categoria") return Boolean(estado.dificuldade);
    if (passo === "jogo") return Boolean(estado.dificuldade && estado.categoria);
    return true;
}

async function mostrar(passo, direcao) {
    if (passo !== "inicio" && passo !== "erro" && !estado.catalogo) {
        try {
            await carregarCatalogo();
        } catch {
            passo = "erro";
        }
    }
    if (estado.passo === "jogo" && passo !== "jogo") jogo.sair();
    if (passo === "dificuldade") renderizarDificuldades();
    if (passo === "categoria") {
        renderizarCategorias();
        preencherResumo();
    }
    if (passo === "jogo") {
        try {
            await jogo.iniciar(estado.categoria, estado.dificuldade);
        } catch {
            passo = "erro";
        }
    }

    estado.ocupado = true;
    const atual = $(`[data-passo="${estado.passo}"]`);
    const proximo = $(`[data-passo="${passo}"]`);
    estado.passo = passo;
    await trocarPasso(atual === proximo ? null : atual, proximo, direcao);
    estado.ocupado = false;

    cartoesEmCascata($$(".opcao", proximo));
    $("h1, h2", proximo)?.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
}

function direcaoEntre(de, para) {
    return ORDEM.indexOf(para) >= ORDEM.indexOf(de) ? 1 : -1;
}

function irPara(passo) {
    if (estado.ocupado || !passoValido(passo)) return;
    history.pushState({ passo }, "", passo === "inicio" ? location.pathname : `#${passo}`);
    mostrar(passo, direcaoEntre(estado.passo, passo));
}

function voltar() {
    if (estado.ocupado || estado.passo === "inicio") return;
    history.back();
}

window.addEventListener("popstate", (e) => {
    let passo = e.state?.passo ?? "inicio";
    if (!passoValido(passo)) passo = "inicio";
    mostrar(passo, direcaoEntre(estado.passo, passo));
});

// ───────── Ligações ─────────
document.addEventListener("click", (e) => {
    const alvo = e.target.closest("[data-ir], [data-voltar], [data-tentar-de-novo]");
    if (!alvo) return;
    if (alvo.matches("[data-voltar]")) voltar();
    else if (alvo.matches("[data-tentar-de-novo]")) {
        estado.catalogo = null;
        mostrar("dificuldade", 1);
    } else irPara(alvo.dataset.ir);
});

document.addEventListener("keydown", (e) => {
    if (estado.passo === "jogo") {
        if (jogo.teclaFisica(e)) e.preventDefault();
        return; // na partida, Esc não sai: só fecha o chute (tratado no próprio campo)
    }
    if (e.key === "Escape") voltar();
});

const jogo = criarJogo($('[data-passo="jogo"]'), {
    // o menu da partida volta para a escolha de categoria, que é o passo anterior no histórico
    aoVoltarAoMenu: () => voltar(),
});

// ───────── Início ─────────
history.replaceState({ passo: "inicio" }, "", location.pathname); // recarregar sempre volta ao início
preencherIcones();
mostrarRecorde();
ligarLetreiro($$("[data-letreiro] > span"));
entrarEmCascata($$("[data-passo=inicio] [data-entrada]"), { atraso: 0.35 });
$$("[data-passo=inicio] .btn").forEach(efeitoPressionar);
carregarCatalogo().catch(() => { /* tentado de novo ao clicar em Jogar */ });
