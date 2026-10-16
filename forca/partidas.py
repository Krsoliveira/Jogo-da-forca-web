"""Armazenamento do estado das partidas no servidor.

O cookie de sessão guarda só um identificador aleatório; a palavra secreta, os erros e a
pontuação ficam aqui. A interface (criar/obter/salvar/apagar) é pequena de propósito: trocar
a memória por Redis no futuro não exige mexer nas rotas.

Limitações da implementação em memória: o estado não é compartilhado entre processos
(por isso o Procfile usa um único worker) e é perdido quando o servidor reinicia.
"""

import secrets
import threading
import time
from collections import OrderedDict


class ArmazenamentoDePartidas:
    def __init__(self, ttl_segundos=3600, max_partidas=5000, relogio=time.monotonic):
        self._ttl = ttl_segundos
        self._max = max_partidas
        self._relogio = relogio
        self._dados = OrderedDict()  # id -> (ultimo_acesso, estado), do menos ao mais recente
        self._trava = threading.Lock()

    def __len__(self):
        return len(self._dados)

    def criar(self, estado):
        """Guarda um estado novo e devolve o identificador (imprevisível, 256 bits)."""
        pid = secrets.token_urlsafe(32)
        with self._trava:
            self._expurgar()
            while len(self._dados) >= self._max:
                self._dados.popitem(last=False)  # descarta a partida menos usada recentemente
            self._dados[pid] = (self._relogio(), estado)
        return pid

    def obter(self, pid):
        """Devolve o estado da partida, ou None se não existe ou expirou."""
        if not isinstance(pid, str):
            return None
        with self._trava:
            item = self._dados.get(pid)
            if item is None:
                return None
            ultimo_acesso, estado = item
            if self._relogio() - ultimo_acesso > self._ttl:
                del self._dados[pid]
                return None
            self._dados[pid] = (self._relogio(), estado)  # renova o prazo ao usar
            self._dados.move_to_end(pid)
            return estado

    def salvar(self, pid, estado):
        with self._trava:
            if pid in self._dados:
                self._dados[pid] = (self._relogio(), estado)
                self._dados.move_to_end(pid)

    def apagar(self, pid):
        with self._trava:
            self._dados.pop(pid, None)

    def _expurgar(self):
        agora = self._relogio()
        # o dicionário está ordenado do menos ao mais recente: para no primeiro não expirado
        while self._dados:
            pid, (ultimo_acesso, _) = next(iter(self._dados.items()))
            if agora - ultimo_acesso <= self._ttl:
                break
            del self._dados[pid]
