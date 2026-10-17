// Ícones (Lucide, licença ISC). Importados um a um para o esbuild incluir só os usados.
import {
    Apple,
    ArrowLeft,
    Box,
    Briefcase,
    Building2,
    Cpu,
    createElement,
    Flame,
    Globe,
    HeartPulse,
    PawPrint,
    Play,
    Shuffle,
    Skull,
    Sparkles,
    Tag,
    Trophy,
    UtensilsCrossed,
} from "lucide";

const ICONES = { Apple, ArrowLeft, Box, Briefcase, Building2, Cpu, Flame, Globe, HeartPulse, PawPrint, Play, Shuffle, Skull, Sparkles, Tag, Trophy, UtensilsCrossed };

// Apresentação de cada categoria; uma categoria nova sem entrada aqui recebe o ícone genérico.
const ICONE_DA_CATEGORIA = {
    Frutas: "Apple",
    Países: "Globe",
    Cidades: "Building2",
    Animais: "PawPrint",
    Objetos: "Box",
    Comidas: "UtensilsCrossed",
    Profissões: "Briefcase",
    Esportes: "Trophy",
    "Corpo Humano": "HeartPulse",
    Tecnologia: "Cpu",
    Aleatório: "Shuffle",
};

export const ICONE_DA_DIFICULDADE = { facil: "Sparkles", medio: "Flame", dificil: "Skull" };

/** Cria o SVG de um ícone. Decorativo: o texto ao lado já descreve a ação. */
export function icone(nome) {
    const svg = createElement(ICONES[nome] ?? Tag);
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    return svg;
}

export const iconeDaCategoria = (categoria) => ICONE_DA_CATEGORIA[categoria] ?? "Tag";

/** Preenche todo elemento com data-icone="Nome" com o SVG correspondente. */
export function preencherIcones(raiz = document) {
    raiz.querySelectorAll("[data-icone]").forEach((el) => {
        if (!el.firstElementChild) el.prepend(icone(el.dataset.icone));
    });
}
