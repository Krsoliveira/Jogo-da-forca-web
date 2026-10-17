// Página /beta: demonstra o design system e as animações antes de construirmos as telas.
import {
    animarAcerto,
    animarBarra,
    animarErro,
    contarAte,
    efeitoPressionar,
    entrarEmCascata,
    inclinarComPonteiro,
    ligarLetreiro,
    pulsar,
    revelarLetra,
} from "./lib/movimento.js";

const $ = (seletor, raiz = document) => raiz.querySelector(seletor);
const $$ = (seletor, raiz = document) => [...raiz.querySelectorAll(seletor)];

// Letreiro e entrada da página
ligarLetreiro($$("[data-letreiro] > span"));
entrarEmCascata($$("[data-entrada]"));
$$(".painel").forEach((painel) => inclinarComPonteiro(painel, { intensidade: 4 }));
$$(".btn, .tecla").forEach(efeitoPressionar);

// Teclado: algumas letras estão na palavra de demonstração, outras não
const PALAVRA = "NEON";
const casas = $$("[data-casa]");
const vidas = $("[data-vidas]");
let vidasRestantes = 6;

$$("[data-tecla]").forEach((tecla) => {
    tecla.addEventListener("click", async () => {
        const letra = tecla.dataset.tecla;
        tecla.disabled = true;
        if (PALAVRA.includes(letra)) {
            tecla.classList.add("tecla-certa");
            animarAcerto(tecla);
            casas.forEach((casa, i) => {
                if (PALAVRA[i] === letra) setTimeout(() => revelarLetra(casa, letra), i * 90);
            });
        } else {
            tecla.classList.add("tecla-errada");
            vidasRestantes = Math.max(0, vidasRestantes - 1);
            vidas.textContent = String(vidasRestantes);
            pulsar(vidas.parentElement);
            await animarErro($("[data-palavra]"));
        }
    });
});

$("[data-reiniciar]").addEventListener("click", () => {
    $$("[data-tecla]").forEach((t) => {
        t.disabled = false;
        t.classList.remove("tecla-certa", "tecla-errada");
    });
    casas.forEach((c) => {
        c.textContent = "";
        c.classList.remove("casa-revelada");
    });
    vidasRestantes = 6;
    vidas.textContent = "6";
});

// Experiência: soma XP com mola e contagem do número
const XP_MAXIMO = 1000;
let xp = 640;
const barra = $("[data-barra-xp]");
const textoXp = $("[data-texto-xp]");
animarBarra(barra, (xp / XP_MAXIMO) * 100);

$("[data-ganhar-xp]").addEventListener("click", () => {
    const anterior = xp;
    xp = xp + 120 >= XP_MAXIMO ? 0 : xp + 120;
    animarBarra(barra, (xp / XP_MAXIMO) * 100);
    contarAte(textoXp, anterior, xp);
    barra.parentElement.setAttribute("aria-valuenow", String(xp));
});
