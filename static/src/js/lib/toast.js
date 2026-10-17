// Avisos curtos que aparecem no topo e somem sozinhos. O texto também vai para a região
// aria-live da página, para leitores de tela.
import { animate } from "motion";
import { reduzMovimento } from "./movimento.js";

const DURACAO_MS = 2400;

export function mostrarToast(texto, tipo = "info") {
    const area = document.querySelector("[data-toasts]");
    if (!area) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${tipo}`;
    toast.textContent = texto;
    area.append(toast);
    anunciar(texto);

    if (!reduzMovimento()) {
        animate(toast, { opacity: [0, 1], y: [-16, 0], scale: [0.9, 1] }, { type: "spring", stiffness: 420, damping: 24 });
    }
    setTimeout(async () => {
        if (!reduzMovimento()) {
            await animate(toast, { opacity: 0, y: -10, scale: 0.96 }, { duration: 0.25 }).finished;
        }
        toast.remove();
    }, DURACAO_MS);
}

/** Lê uma mensagem em voz para quem usa leitor de tela, sem mostrar nada na tela. */
export function anunciar(texto) {
    const regiao = document.querySelector("[data-anuncio]");
    if (!regiao) return;
    regiao.textContent = "";
    // um pequeno intervalo garante que mensagens iguais seguidas sejam lidas de novo
    setTimeout(() => { regiao.textContent = texto; }, 30);
}
