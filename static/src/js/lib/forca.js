// Desenho da forca em SVG. Cada erro avança o traço do boneco: com 6 tentativas cada erro desenha uma
// parte inteira; com 8, partes pela metade; com 4, uma parte e meia. Assim todo erro tem feedback visível.
import { animate } from "motion";
import { reduzMovimento } from "./movimento.js";

const TOTAL_PARTES = 6;
const limitar = (v, min, max) => Math.min(max, Math.max(min, v));

export function criarForca(svg) {
    const partes = [...svg.querySelectorAll("[data-parte]")];
    const boneco = svg.querySelector("[data-boneco]");
    const olhos = svg.querySelector("[data-olhos]");
    let progresso = 0; // em "partes", de 0 a 6

    function desenharAte(alvo, { duracao = 0.45 } = {}) {
        const anterior = progresso;
        progresso = alvo;
        partes.forEach((parte, i) => {
            const fracao = limitar(alvo - i, 0, 1);
            const deslocamento = 1 - fracao;
            if (fracao === 0) return; // parte ainda não alcançada continua escondida
            if (reduzMovimento()) {
                parte.style.visibility = "visible";
                parte.style.strokeDashoffset = String(deslocamento);
                return;
            }
            // a parte que estava sendo desenhada continua de onde parou; as seguintes esperam a vez
            const atraso = Math.max(0, i - Math.floor(anterior)) * duracao * 0.8;
            setTimeout(() => { parte.style.visibility = "visible"; }, atraso * 1000);
            animate(parte, { strokeDashoffset: deslocamento }, { duration: duracao, delay: atraso, ease: [0.65, 0, 0.35, 1] });
        });
    }

    return {
        atualizar(erros, maxErros) {
            desenharAte(limitar((erros / maxErros) * TOTAL_PARTES, 0, TOTAL_PARTES));
            const restantes = maxErros - erros;
            svg.classList.toggle("forca-perigo", erros > 0 && restantes <= 2);
            svg.setAttribute("aria-label", erros === 0 ? "Forca vazia" : `Forca: ${erros} de ${maxErros} erros`);
        },

        /** Boneco completo: os olhos viram X e ele balança como um pêndulo amortecido. */
        async derrota() {
            desenharAte(TOTAL_PARTES, { duracao: 0.3 });
            if (reduzMovimento()) {
                olhos.style.opacity = "1";
                return;
            }
            animate(olhos, { opacity: [0, 1] }, { duration: 0.3, delay: 0.35 });
            await animate(boneco, { rotate: [0, 12, -9, 6, -3.5, 1.5, 0] }, { duration: 2.4, ease: "easeInOut", delay: 0.2 }).finished;
        },

        /** Vitória: o boneco (ou o que existir dele) dá um pulinho de alívio. */
        comemorar() {
            if (reduzMovimento()) return;
            animate(boneco, { y: [0, -12, 0, -5, 0] }, { duration: 0.8, ease: "easeOut" });
        },

        /** Apaga o boneco de trás para frente para a próxima palavra. */
        reiniciar() {
            svg.classList.remove("forca-perigo");
            olhos.style.opacity = "0";
            boneco.style.transform = "";
            const esconder = (p) => {
                p.style.strokeDashoffset = "1";
                p.style.visibility = "hidden";
            };
            if (reduzMovimento()) {
                partes.forEach(esconder);
            } else {
                partes.forEach((p, i) => animate(p, { strokeDashoffset: 1 }, { duration: 0.35, ease: "easeIn" }).finished.then(() => {
                    // esconde só se um erro novo (já na palavra seguinte) não voltou a desenhar esta parte
                    if (limitar(progresso - i, 0, 1) === 0) esconder(p);
                }));
            }
            progresso = 0;
            svg.setAttribute("aria-label", "Forca vazia");
        },
    };
}
