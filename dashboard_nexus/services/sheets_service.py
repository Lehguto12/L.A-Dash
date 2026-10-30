"""Sincronização de planilhas do Google Sheets (Fase 2, etapa 2).

Fluxo:  extrair_ids()  ->  baixar_csv()  ->  _ler_csv()  ->  importar_dataframe()
        (tudo dentro de sincronizar_fonte(), que também registra o resultado).

Segurança (SSRF): o usuário digita um link, mas o servidor NUNCA busca esse link.
Extraímos só o ID da planilha e o gid (a aba) com regex rígida e montamos nós
mesmos a URL de docs.google.com. Os redirecionamentos (o Google manda a
exportação para *.googleusercontent.com) também são validados a cada salto.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import current_app
from sqlalchemy import select

from extensions import db
from models import FonteSheets
from services.importador import ErroImportacao, _ler_csv, importar_dataframe

ID_REGEX = re.compile(r"[A-Za-z0-9_-]{10,100}")
GID_REGEX = re.compile(r"\d{1,20}")
URL_ID_REGEX = re.compile(r"/spreadsheets/d/([A-Za-z0-9_-]{10,100})")
URL_GID_REGEX = re.compile(r"[#&?]gid=(\d{1,20})")

TIMEOUT_SEGUNDOS = 20
MAX_BYTES_DOWNLOAD = 5 * 1024 * 1024  # mesmo limite do upload manual (5 MB)
MSG_NAO_PUBLICA = (
    "Não consegui acessar a planilha. No Google Sheets, clique em Compartilhar "
    "e deixe o acesso como 'Qualquer pessoa com o link' (leitor)."
)


# ------------------------------------------------------------ extração ---

def extrair_ids(url_ou_id: str, gid_padrao: str = "0") -> tuple[str, str]:
    """Aceita o link completo ou só o ID. Devolve (sheet_id, gid) já validados."""
    texto = (url_ou_id or "").strip()
    if not texto:
        raise ErroImportacao("Cole o link da planilha do Google Sheets.")

    m = URL_ID_REGEX.search(texto)
    if m:
        sheet_id = m.group(1)
        g = URL_GID_REGEX.search(texto)
        gid = g.group(1) if g else gid_padrao
    elif ID_REGEX.fullmatch(texto):
        sheet_id, gid = texto, gid_padrao
    else:
        raise ErroImportacao(
            "Link inválido. Cole o endereço completo da planilha "
            "(https://docs.google.com/spreadsheets/d/...)."
        )

    gid = str(gid).strip()
    if not GID_REGEX.fullmatch(gid):
        raise ErroImportacao("O identificador da aba (gid) deve conter só números.")
    return sheet_id, gid


# ------------------------------------------------------------ download ---

def _validar_url(url: str) -> None:
    """Só https e só hosts do Google que servem a exportação."""
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if p.scheme != "https" or p.port not in (None, 443):
        raise ErroImportacao("Endereço não permitido para a sincronização.")
    if host == "docs.google.com" or host.endswith(".googleusercontent.com"):
        return
    if host.endswith("google.com") and host.startswith("accounts."):
        # Planilha privada: o Google redireciona para a tela de login.
        raise ErroImportacao(MSG_NAO_PUBLICA)
    raise ErroImportacao("A planilha redirecionou para um endereço não permitido.")


class _RedirectSeguro(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validar_url(newurl)  # cada salto passa pela mesma validação
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def baixar_csv(sheet_id: str, gid: str) -> bytes:
    """Baixa a aba como CSV. A URL é montada AQUI, só com o ID e o gid validados."""
    if not ID_REGEX.fullmatch(sheet_id) or not GID_REGEX.fullmatch(gid):
        raise ErroImportacao("Identificadores da planilha inválidos.")

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    _validar_url(url)

    opener = urllib.request.build_opener(_RedirectSeguro)
    req = urllib.request.Request(url, headers={"User-Agent": "NexusDashboard/1.0"})
    try:
        with opener.open(req, timeout=TIMEOUT_SEGUNDOS) as resp:
            if resp.headers.get_content_type() == "text/html":
                # O Google devolveu uma página em vez do CSV (normalmente login).
                raise ErroImportacao(MSG_NAO_PUBLICA)
            # Lê no máximo o limite + 1 byte: se passar, recusamos sem baixar o resto.
            conteudo = resp.read(MAX_BYTES_DOWNLOAD + 1)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ErroImportacao("Planilha ou aba não encontrada. Confira o link e o gid.")
        if e.code in (401, 403):
            raise ErroImportacao(MSG_NAO_PUBLICA)
        raise ErroImportacao(f"O Google Sheets respondeu com erro {e.code}. Tente novamente mais tarde.")
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErroImportacao("Não consegui falar com o Google Sheets agora. Tente novamente mais tarde.")

    if len(conteudo) > MAX_BYTES_DOWNLOAD:
        raise ErroImportacao("A planilha é grande demais (limite de 5 MB).")
    if not conteudo.strip():
        raise ErroImportacao("A planilha está vazia.")
    return conteudo


# ---------------------------------------------------------- sincronização ---

def _registrar(fonte: FonteSheets, status: str, mensagem: str) -> None:
    """Grava o resultado na fonte. Trunca em 500 (limite do VARCHAR no PostgreSQL)."""
    fonte.ultima_sync = datetime.now(timezone.utc)
    fonte.ultimo_status = status
    fonte.ultima_mensagem = mensagem[:500]
    db.session.commit()


def sincronizar_fonte(fonte: FonteSheets) -> tuple[bool, str]:
    """Baixa, valida e importa UMA fonte. Nunca levanta erro: devolve (ok, mensagem)
    e registra o resultado na própria fonte (para a tela e o Cron)."""
    max_linhas = current_app.config["MAX_LINHAS_IMPORTACAO"]
    try:
        conteudo = baixar_csv(fonte.sheet_id, fonte.gid)
        df = _ler_csv(conteudo, max_linhas)
        if len(df) > max_linhas:
            raise ErroImportacao(f"A planilha tem mais de {max_linhas:,} linhas.".replace(",", "."))
        # ignorar_invalidas=True: uma linha ruim não pode travar a sincronização
        # automática inteira. A quantidade ignorada aparece no resumo.
        resultado = importar_dataframe(
            df, fonte.usuario_id, modo=fonte.modo, ignorar_invalidas=True
        )
        mensagem = resultado.resumo()
        _registrar(fonte, "ok", mensagem)
        return True, mensagem
    except ErroImportacao as erro:
        db.session.rollback()
        mensagem = " ".join(erro.mensagens)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Falha ao sincronizar fonte_sheets id=%s", fonte.id)
        mensagem = "Erro inesperado ao sincronizar. Tente novamente mais tarde."

    _registrar(fonte, "erro", mensagem)
    return False, mensagem


def sincronizar_todas() -> dict[str, int]:
    """Usado pelo Cron (etapa 4): sincroniza todas as fontes ativas."""
    ids = db.session.scalars(
        select(FonteSheets.id).where(FonteSheets.ativa.is_(True))
    ).all()
    total = {"ok": 0, "erro": 0}
    for fonte_id in ids:
        fonte = db.session.get(FonteSheets, fonte_id)
        if fonte is None:
            continue
        ok, _ = sincronizar_fonte(fonte)
        total["ok" if ok else "erro"] += 1
    return total