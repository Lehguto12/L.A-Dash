"""Comandos de linha de comando do app (rodam com `flask <nome>`).

O Cron Job do Render (e o Agendador de Tarefas do Windows, se você quiser
automatizar localmente) chamam `flask sincronizar-sheets`: não há usuário
logado, o comando percorre as fontes ativas e sincroniza cada uma.
"""
import click
from flask.cli import with_appcontext

from services.sheets_service import sincronizar_todas


@click.command("sincronizar-sheets")
@with_appcontext
def sincronizar_sheets_cmd():
    """Sincroniza todas as planilhas do Google Sheets ativas."""
    total = sincronizar_todas()
    click.echo(
        f"Sincronização concluída: {total['ok']} com sucesso, "
        f"{total['erro']} com erro."
    )
    # Erro de UMA planilha (ex.: usuário deixou de compartilhar) não é falha do
    # job: o motivo fica registrado na própria fonte e aparece na tela do
    # usuário. Por isso o código de saída é sempre 0, exceto se o comando
    # quebrar de verdade (aí o Python sai com erro sozinho).