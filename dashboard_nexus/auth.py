import re
from urllib.parse import urlparse

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError

from extensions import db, login_manager
from models import Usuario

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SENHA_MIN = 8
SENHA_MAX = 128  # limite evita enviar senhas gigantes só para travar o servidor


def _destino_seguro(destino):
    """Aceita só caminhos internos (ex.: /dashboard). Bloqueia links para
    outros sites no parâmetro ?next= (ataque de 'open redirect')."""
    if not destino or not destino.startswith("/"):
        return None
    if destino.startswith("//") or "\\" in destino:
        return None
    partes = urlparse(destino)
    if partes.scheme or partes.netloc:
        return None
    return destino


@login_manager.unauthorized_handler
def nao_autorizado():
    # Chamadas do JavaScript (/api/...) recebem 401 em JSON; o navegador
    # recebe o redirecionamento para a tela de login.
    if request.path.startswith("/api/"):
        return jsonify({"erro": "Não autenticado"}), 401
    flash("Faça login para acessar o painel.", "aviso")
    return redirect(url_for("auth.login", next=request.path))


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    erros = []
    nome = email = ""

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        confirmar = request.form.get("confirmar", "")

        if not (2 <= len(nome) <= 100):
            erros.append("Informe seu nome (2 a 100 caracteres).")
        if len(email) > 255 or not EMAIL_REGEX.match(email):
            erros.append("Informe um e-mail válido.")
        if not (SENHA_MIN <= len(senha) <= SENHA_MAX):
            erros.append(f"A senha deve ter entre {SENHA_MIN} e {SENHA_MAX} caracteres.")
        if senha != confirmar:
            erros.append("As senhas não conferem.")

        if not erros:
            usuario = Usuario(nome=nome, email=email)
            usuario.definir_senha(senha)
            db.session.add(usuario)
            try:
                db.session.commit()
            except IntegrityError:
                # O índice UNIQUE do banco é a garantia final contra e-mail
                # duplicado, mesmo se dois cadastros chegarem ao mesmo tempo.
                db.session.rollback()
                erros.append("Já existe uma conta com este e-mail.")
            else:
                login_user(usuario)
                return redirect(url_for("index"))

    return render_template("cadastro.html", erros=erros, nome=nome, email=email)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    erros = []
    email = ""
    destino = _destino_seguro(request.values.get("next"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        lembrar = request.form.get("lembrar") == "on"

        usuario = Usuario.query.filter_by(email=email).first()

        # Mensagem única: não revelamos se o e-mail existe ou se a senha errou.
        if usuario is None or not usuario.conferir_senha(senha):
            erros.append("E-mail ou senha incorretos.")
        else:
            login_user(usuario, remember=lembrar)
            return redirect(destino or url_for("index"))

    return render_template("login.html", erros=erros, email=email, next=destino)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    # POST + token CSRF: impede que outro site deslogue o usuário por um <img>.
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))