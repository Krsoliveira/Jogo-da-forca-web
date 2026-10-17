// Comunicação com o servidor. Toda falha vira um ErroApi com uma mensagem amigável e o status HTTP
// (0 quando nem chegou ao servidor), para a interface decidir o que mostrar.

export class ErroApi extends Error {
    constructor(mensagem, status) {
        super(mensagem);
        this.name = "ErroApi";
        this.status = status;
    }

    /** A partida não existe mais no servidor (expirou ou o servidor reiniciou). */
    get sessaoPerdida() {
        return this.status === 400 && /jogo não iniciado|sessão inválida/i.test(this.message);
    }
}

async function pedir(url, opcoes = {}) {
    let resposta;
    try {
        resposta = await fetch(url, {
            credentials: "same-origin",
            ...opcoes,
            headers: { Accept: "application/json", ...opcoes.headers },
        });
    } catch {
        throw new ErroApi("Sem conexão com o servidor.", 0);
    }
    let dados = null;
    try { dados = await resposta.json(); } catch { /* corpo vazio ou não JSON */ }
    if (!resposta.ok) throw new ErroApi(dados?.erro ?? `Erro ${resposta.status}`, resposta.status);
    return dados;
}

const enviar = (url, corpo) => pedir(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
});

export const api = {
    catalogo: () => pedir("/api/catalogo"),
    novoJogo: (categoria, dificuldade) =>
        pedir(`/novo_jogo?${new URLSearchParams({ category: categoria, difficulty: dificuldade })}`),
    proximaPalavra: () => pedir("/proxima_palavra"),
    tentativa: (letra) => enviar("/tentativa", { letra }),
    chute: (palavra) => enviar("/chute", { palavra }),
};
