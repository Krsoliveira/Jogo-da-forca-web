// Animações reutilizáveis da interface, construídas com a biblioteca Motion (molas físicas,
// sequências e escalonamento). Quem ativa "reduzir movimento" no sistema recebe o estado
// final imediatamente, sem animação.
import { animate, stagger } from "motion";

export const reduzMovimento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const MOLA = { type: "spring", stiffness: 260, damping: 22 };
const MOLA_RAPIDA = { type: "spring", stiffness: 520, damping: 26 };

/** Entrada em cascata: sobe, ganha nitidez e aparece, um elemento depois do outro. */
export function entrarEmCascata(elementos, { atraso = 0 } = {}) {
    if (reduzMovimento()) {
        elementos.forEach((el) => { el.style.opacity = "1"; });
        return;
    }
    animate(elementos, { opacity: [0, 1], y: [28, 0], filter: ["blur(10px)", "blur(0px)"] }, {
        duration: 0.7,
        delay: stagger(0.08, { startDelay: atraso }),
        ease: [0.16, 1, 0.3, 1],
    });
}

/** Liga um letreiro neon letra por letra, com pequenas falhas de energia. */
export function ligarLetreiro(letras) {
    if (reduzMovimento()) {
        letras.forEach((l) => { l.style.opacity = "1"; });
        return;
    }
    animate(letras, { opacity: [0, 1, 0.3, 1, 0.6, 1] }, {
        duration: 0.9,
        delay: stagger(0.09, { startDelay: 0.15 }),
        ease: "linear",
    });
}

/** Inclina o elemento em 3D seguindo o ponteiro (só em dispositivos com mouse). */
export function inclinarComPonteiro(el, { intensidade = 6 } = {}) {
    if (reduzMovimento() || !window.matchMedia("(hover: hover)").matches) return;
    el.addEventListener("pointermove", (e) => {
        const r = el.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        animate(el, { rotateY: px * intensidade, rotateX: -py * intensidade }, MOLA);
    });
    el.addEventListener("pointerleave", () => animate(el, { rotateY: 0, rotateX: 0 }, MOLA));
}

/** Afunda ao pressionar e volta com mola, como um botão físico. */
export function efeitoPressionar(el) {
    if (reduzMovimento()) return;
    el.addEventListener("pointerdown", () => animate(el, { scale: 0.93, y: 2 }, MOLA_RAPIDA));
    const soltar = () => animate(el, { scale: 1, y: 0 }, { type: "spring", stiffness: 400, damping: 12 });
    el.addEventListener("pointerup", soltar);
    el.addEventListener("pointerleave", soltar);
}

/** Acerto: a tecla cresce, passa do ponto e assenta, com um pulso de brilho. */
export function animarAcerto(el) {
    if (reduzMovimento()) return;
    animate(el, { scale: [1, 1.28, 1], rotate: [0, -6, 0] }, { duration: 0.5, ease: [0.34, 1.56, 0.64, 1] });
}

/** Erro: tremida amortecida para os lados. */
export function animarErro(el) {
    if (reduzMovimento()) return Promise.resolve();
    return animate(el, { x: [0, -10, 9, -7, 5, -3, 0], rotate: [0, -2, 2, -1, 1, 0, 0] }, {
        duration: 0.5,
        ease: "easeOut",
    }).finished;
}

/** Revela uma letra da palavra girando a casa no eixo X, como uma placa virando. */
export function revelarLetra(casa, letra) {
    casa.textContent = letra;
    casa.classList.add("casa-revelada");
    if (reduzMovimento()) return;
    animate(casa, { rotateX: [-95, 12, 0], y: [-6, 0], opacity: [0.2, 1] }, { duration: 0.65, ease: [0.22, 1.2, 0.36, 1] });
}

/** Anima a largura de uma barra de progresso com mola. */
export function animarBarra(preenchimento, percentual) {
    const alvo = `${Math.max(0, Math.min(100, percentual))}%`;
    if (reduzMovimento()) {
        preenchimento.style.width = alvo;
        return;
    }
    animate(preenchimento, { width: alvo }, { type: "spring", stiffness: 120, damping: 18 });
}

/** Conta de um número até outro, atualizando o texto do elemento. */
export function contarAte(el, de, ate, { sufixo = "" } = {}) {
    if (reduzMovimento()) {
        el.textContent = `${ate}${sufixo}`;
        return;
    }
    animate(de, ate, {
        duration: 0.9,
        ease: [0.16, 1, 0.3, 1],
        onUpdate: (v) => { el.textContent = `${Math.round(v)}${sufixo}`; },
    });
}

/** Pulso curto para chamar atenção (ex.: vida perdida). */
export function pulsar(el) {
    if (reduzMovimento()) return;
    animate(el, { scale: [1, 1.35, 1] }, { duration: 0.4, ease: "easeOut" });
}
