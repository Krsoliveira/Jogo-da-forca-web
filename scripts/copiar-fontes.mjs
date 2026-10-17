// Copia as fontes variáveis (subconjunto latino) para static/fonts, servidas pelo próprio app.
// Evita depender do Google Fonts: mais rápido, sem rastreamento de terceiros e compatível com CSP estrito.
import { copyFileSync, mkdirSync } from "node:fs";

const destino = "static/fonts";
const arquivos = [
  "node_modules/@fontsource-variable/orbitron/files/orbitron-latin-wght-normal.woff2",
  "node_modules/@fontsource-variable/space-grotesk/files/space-grotesk-latin-wght-normal.woff2",
  "node_modules/@fontsource-variable/jetbrains-mono/files/jetbrains-mono-latin-wght-normal.woff2",
];

mkdirSync(destino, { recursive: true });
for (const origem of arquivos) {
  copyFileSync(origem, `${destino}/${origem.split("/").pop()}`);
}
console.log(`${arquivos.length} fontes copiadas para ${destino}`);
