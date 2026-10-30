import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# O Render define RENDER="true" automaticamente. Usamos isso para saber se
# estamos em produção (e ativar regras mais rígidas de segurança).
IS_PRODUCTION = os.environ.get("RENDER") == "true"



def _montar_database_uri() -> str:
    """Escolhe o banco: PostgreSQL no Render ou SQLite local."""
    url = os.environ.get("DATABASE_URL")

    if not url:
        pasta = os.path.join(BASE_DIR, "instance")
        os.makedirs(pasta, exist_ok=True)
        return "sqlite:///" + os.path.join(pasta, "nexus.db")

    # Força o uso do driver psycopg2, já instalado no requirements.txt.
    if url.startswith("postgres://"):
        url = url.replace(
            "postgres://",
            "postgresql+psycopg2://",
            1
        )
    elif url.startswith("postgresql://"):
        url = url.replace(
            "postgresql://",
            "postgresql+psycopg2://",
            1
        )
    elif url.startswith("postgresql+psycopg://"):
        url = url.replace(
            "postgresql+psycopg://",
            "postgresql+psycopg2://",
            1
        )

    return url



class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")  # validado em create_app()

    SQLALCHEMY_DATABASE_URI = _montar_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Testa a conexão antes de usar (evita erro quando o PostgreSQL derruba
    # conexões ociosas).
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Cookies de sessão: o JavaScript não consegue lê-los (HTTPONLY) e, em
    # produção, só trafegam por HTTPS (SECURE).
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION

    # Upload: o Flask recusa (erro 413) qualquer requisição maior que isto,
    # ANTES de a nossa rota ler o arquivo.
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024        # 5 MB
    MAX_LINHAS_IMPORTACAO = 50_000

    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = IS_PRODUCTION
