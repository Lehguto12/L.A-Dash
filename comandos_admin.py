"""Comandos de terminal para administrar o sistema.

Uso:
    python -m flask tornar-admin seu@email.com
"""
import click
from flask.cli import with_appcontext
from sqlalchemy import func

from extensions import db
from models import Usuario


@click.command("tornar-admin")
@click.argument("email")
@with_appcontext
def tornar_admin_cmd(email: str) -> None:
    """Marca o usuário com este e-mail como administrador."""
    email = email.strip().lower()

    usuario = db.session.execute(
        db.select(Usuario).where(func.lower(Usuario.email) == email)
    ).scalar_one_or_none()

    if usuario is None:
        click.echo(f"Nenhum usuário encontrado com o e-mail {email}.")
        click.echo("Crie a conta pela tela de cadastro primeiro e tente de novo.")
        raise SystemExit(1)

    if usuario.is_admin:
        click.echo(f"{usuario.nome} ({usuario.email}) já é administrador.")
        return

    usuario.is_admin = True
    db.session.commit()
    click.echo(f"Pronto: {usuario.nome} ({usuario.email}) agora é administrador.")