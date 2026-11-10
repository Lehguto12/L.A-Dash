"""Painel administrativo: só quem tem is_admin = True entra."""
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Usuario
from services.planos import PLANOS, PLANO_PADRAO, obter_plano, contar_clientes

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    """Barra quem não é admin. Deve ficar DEPOIS do @login_required, porque
    ele assume que já existe um usuário logado."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


@admin_bp.route("/")
@login_required
@admin_required
def painel():
    usuarios = db.session.execute(
        db.select(Usuario).order_by(Usuario.criado_em)
    ).scalars().all()

    linhas = []
    for u in usuarios:
        plano = obter_plano(u)
        linhas.append({
            "id": u.id,
            "nome": u.nome,
            "email": u.email,
            "plano_chave": u.plano if u.plano in PLANOS else PLANO_PADRAO,
            "clientes": contar_clientes(u.id),
            "limite": plano["max_clientes"],   # None = ilimitado
            "criado_em": u.criado_em,
            "is_admin": u.is_admin,
        })

    opcoes_planos = [(chave, dados["nome"]) for chave, dados in PLANOS.items()]
    return render_template("admin.html", linhas=linhas, planos=opcoes_planos)


@admin_bp.route("/usuarios/<int:usuario_id>/plano", methods=["POST"])
@login_required
@admin_required
def alterar_plano(usuario_id: int):
    novo_plano = request.form.get("plano", "")

    # Nunca confie no que veio do formulário: só aceita planos que existem.
    if novo_plano not in PLANOS:
        abort(400)

    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        abort(404)

    usuario.plano = novo_plano
    db.session.commit()

    flash(f"Plano de {usuario.nome} alterado para {PLANOS[novo_plano]['nome']}.", "ok")
    return redirect(url_for("admin.painel"))