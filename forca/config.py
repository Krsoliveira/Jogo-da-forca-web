"""Configuração da aplicação e constantes das regras do jogo."""

import logging
import os
import string

logger = logging.getLogger(__name__)

# --- REGRAS DO JOGO ---
DIFICULDADES = ["facil", "medio", "dificil"]
DIFICULDADE_CONFIG = {"facil": 8, "medio": 6, "dificil": 4}
PONTOS_LETRA_CERTA = 10
PONTOS_VITORIA_BONUS = 50
PONTOS_POR_TENTATIVA_SOBRA = 5
PENALIDADE_CHUTE_ERRADO = 30
VITORIAS_PARA_SUBIR_NIVEL_DIFICULDADE = 5
XP_PARA_PROXIMO_NIVEL = 1000
LETRAS_VALIDAS = set(string.ascii_lowercase)


def versao_assets(static_dir):
    """Versão para cache busting baseada na data de modificação dos estáticos
    (muda só quando os arquivos mudam, permitindo cache do navegador)."""
    mtimes = [os.path.getmtime(os.path.join(raiz, f)) for raiz, _, arquivos in os.walk(static_dir) for f in arquivos]
    return int(max(mtimes, default=0))


def configurar(app):
    """Aplica segredo de sessão, cookies seguros e versão dos assets.

    A sessão é assinada com SECRET_KEY: quem a conhece consegue forjar pontuação.
    O Railway define RAILWAY_ENVIRONMENT; nesse caso a ausência da chave é erro fatal.
    """
    segredo = os.environ.get("SECRET_KEY")
    em_producao = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
    if not segredo:
        if em_producao:
            raise RuntimeError("SECRET_KEY é obrigatória em produção.")
        logger.warning("SECRET_KEY não definida; usando chave de desenvolvimento.")

    app.secret_key = segredo or "dev-only-secret-key"
    app.config.update(
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=em_producao,  # cookie só trafega via HTTPS em produção
        VERSAO_ASSETS=versao_assets(app.static_folder),
    )
