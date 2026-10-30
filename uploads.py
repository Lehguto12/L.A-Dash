from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint, Response, current_app, flash, redirect, render_template,
    request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import FonteSheets, Registro
from services.importador import (
    COLUNAS_OBRIGATORIAS, ErroImportacao, gerar_modelo_csv, gerar_modelo_xlsx,
    importar_arquivo,
)
from services.sheets_service import extrair_ids, sincronizar_fonte

dados_bp = Blueprint("dados", __name__, url_prefix="/dados")

MODOS_VALIDOS = {"atualizar", "substituir"}

# Evita que o botão "Sincronizar agora" seja usado em sequência (cada clique
# faz o servidor baixar a planilha do Google).
INTERVALO_MIN_SYNC = timedelta(seconds=30)
FUSO_BR = timezone(timedelta(hours=-3))  # Brasil sem horário de verão desde 2019


def _resumo_do_usuario():
    """Estatísticas dos dados do usuário LOGADO (o filtro usa current_user.id)."""
    total, inicio, fim, clientes = db.session.execute(
        select(
            func.count(Registro.id),
            func.min(Registro.data),
            func.max(Registro.data),
            func.count(func.distinct(Registro.cliente)),
        ).where(Registro.usuario_id == current_user.id)
    ).one()
    return {"total": total, "inicio": inicio, "fim": fim, "clientes": clientes}


def _como_utc(momento):
    """O SQLite devolve datas sem fuso; no banco elas sempre foram gravadas em UTC."""
    if momento is not None and momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento


def _pagina(erros=None, status=200):
    # A fonte vem SEMPRE de current_user, nunca de um id enviado pelo formulário.
    fonte = current_user.fonte_sheets
    sync_txt = None
    if fonte is not None and fonte.ultima_sync is not None:
        sync_txt = _como_utc(fonte.ultima_sync).astimezone(FUSO_BR).strftime("%d/%m/%Y %H:%M")
    return render_template(
        "dados.html",
        resumo=_resumo_do_usuario(),
        erros=erros or [],
        colunas=COLUNAS_OBRIGATORIAS,
        fonte=fonte,
        sync_txt=sync_txt,
    ), status


@dados_bp.route("/", methods=["GET"])
@login_required
def pagina():
    return _pagina()


@dados_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    arquivo = request.files.get("arquivo")
    if arquivo is None or not arquivo.filename:
        return _pagina(["Escolha um arquivo .csv ou .xlsx para enviar."], 400)

    modo = request.form.get("modo", "atualizar")
    if modo not in MODOS_VALIDOS:
        modo = "atualizar"
    ignorar = request.form.get("ignorar_invalidas") == "on"

    try:
        # usuario_id = current_user.id: vem da sessão, nunca do formulário.
        resultado = importar_arquivo(
            arquivo,
            usuario_id=current_user.id,
            modo=modo,
            ignorar_invalidas=ignorar,
            max_linhas=current_app.config["MAX_LINHAS_IMPORTACAO"],
        )
    except ErroImportacao as erro:
        return _pagina(erro.mensagens, 400)

    flash(resultado.resumo(), "info")
    return redirect(url_for("dados.pagina"))


# ------------------------------------------------------- Google Sheets ---

@dados_bp.route("/sheets", methods=["POST"])
@login_required
def salvar_sheets():
    """Salva (ou troca) a planilha do usuário e já faz a primeira sincronização."""
    modo = request.form.get("modo", "substituir")
    if modo not in MODOS_VALIDOS:
        modo = "substituir"

    try:
        # Só o ID e o gid saem do link digitado; o resto do texto é descartado.
        sheet_id, gid = extrair_ids(request.form.get("link", ""))
    except ErroImportacao as erro:
        return _pagina(erro.mensagens, 400)

    try:
        fonte = current_user.fonte_sheets
        if fonte is None:
            fonte = FonteSheets(usuario_id=current_user.id)
            db.session.add(fonte)
        fonte.sheet_id = sheet_id
        fonte.gid = gid
        fonte.modo = modo
        fonte.ativa = True
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _pagina(["Conflito ao salvar (dois cliques ao mesmo tempo?). Tente novamente."], 400)

    ok, mensagem = sincronizar_fonte(fonte)
    flash(mensagem, "info" if ok else "erro")
    return redirect(url_for("dados.pagina"))


@dados_bp.route("/sheets/sincronizar", methods=["POST"])
@login_required
def sincronizar_sheets():
    fonte = current_user.fonte_sheets
    if fonte is None:
        return _pagina(["Você ainda não conectou uma planilha do Google Sheets."], 400)

    ultima = _como_utc(fonte.ultima_sync)
    if ultima and datetime.now(timezone.utc) - ultima < INTERVALO_MIN_SYNC:
        flash("Aguarde alguns segundos antes de sincronizar de novo.", "erro")
        return redirect(url_for("dados.pagina"))

    ok, mensagem = sincronizar_fonte(fonte)
    flash(mensagem, "info" if ok else "erro")
    return redirect(url_for("dados.pagina"))


@dados_bp.route("/sheets/remover", methods=["POST"])
@login_required
def remover_sheets():
    fonte = current_user.fonte_sheets
    if fonte is not None:
        db.session.delete(fonte)
        db.session.commit()
    flash("Planilha desconectada. Os dados já importados foram mantidos.", "info")
    return redirect(url_for("dados.pagina"))


# ---------------------------------------------------------------- modelos ---

@dados_bp.route("/modelo.csv")
@login_required
def modelo_csv():
    return Response(
        gerar_modelo_csv(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=modelo_nexus.csv"},
    )


@dados_bp.route("/modelo.xlsx")
@login_required
def modelo_xlsx():
    return Response(
        gerar_modelo_xlsx(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=modelo_nexus.xlsx"},
    )


@dados_bp.app_errorhandler(413)
def arquivo_grande(_erro):
    limite_mb = current_app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    flash(f"Arquivo grande demais. O limite é {limite_mb} MB.", "erro")
    return redirect(url_for("dados.pagina"))