from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    # Guardamos só o HASH da senha, nunca a senha em texto puro.
    senha_hash = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Um usuário tem muitos registros. Se o usuário for apagado, os registros
    # dele vão junto (cascade), para não sobrar dado "órfão" no banco.
    registros = db.relationship(
        "Registro",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )

    # Nesta fase, no máximo UMA planilha do Google Sheets por usuário
    # (uselist=False devolve um objeto, não uma lista).
    fonte_sheets = db.relationship(
        "FonteSheets",
        back_populates="usuario",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def definir_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def conferir_senha(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)


class Registro(db.Model):
    """Uma linha da planilha do usuário (1 dia x 1 campanha)."""
    __tablename__ = "registros"

    id = db.Column(db.Integer, primary_key=True)

    # Dono do dado. Nas rotas, este valor virá SEMPRE de current_user.id.
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )

    data = db.Column(db.Date, nullable=False)
    cliente = db.Column(db.String(150), nullable=False)
    campanha = db.Column(db.String(150), nullable=False)
    plataforma = db.Column(db.String(150), nullable=False)

    investimento = db.Column(db.Float, nullable=False, default=0.0)
    impressoes = db.Column(db.Integer, nullable=False, default=0)
    cliques = db.Column(db.Integer, nullable=False, default=0)
    leads = db.Column(db.Integer, nullable=False, default=0)
    vendas = db.Column(db.Integer, nullable=False, default=0)
    faturamento = db.Column(db.Float, nullable=False, default=0.0)

    usuario = db.relationship("Usuario", back_populates="registros")

    __table_args__ = (
        # Chave natural: a mesma campanha não pode aparecer duas vezes no mesmo
        # dia para o mesmo usuário. É isso que permitirá "atualizar" no reenvio.
        db.UniqueConstraint(
            "usuario_id", "data", "cliente", "plataforma", "campanha",
            name="uq_registro_usuario_chave",
        ),
        # Quase toda consulta filtra por usuario_id (+ data ou cliente);
        # estes índices evitam varrer a tabela inteira conforme ela cresce.
        db.Index("ix_registros_usuario_data", "usuario_id", "data"),
        db.Index("ix_registros_usuario_cliente", "usuario_id", "cliente"),
    )


class FonteSheets(db.Model):
    """Planilha do Google Sheets que alimenta o painel de UM usuário.

    Guardamos só o ID da planilha (não a URL digitada): na hora de baixar,
    o servidor monta a URL de docs.google.com por conta própria. Assim o
    usuário nunca consegue mandar o servidor buscar um endereço qualquer.
    """
    __tablename__ = "fontes_sheets"

    id = db.Column(db.Integer, primary_key=True)

    # unique=True: uma planilha por usuário nesta fase.
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    sheet_id = db.Column(db.String(100), nullable=False)
    gid = db.Column(db.String(20), nullable=False, default="0")   # qual aba

    # "substituir": a planilha é a fonte da verdade (linhas apagadas nela
    # somem do painel). "atualizar": só insere/atualiza, nunca remove.
    modo = db.Column(db.String(20), nullable=False, default="substituir")

    # O Cron só sincroniza fontes ativas.
    ativa = db.Column(db.Boolean, nullable=False, default=True)

    # Resultado da última sincronização (para mostrar na tela).
    ultima_sync = db.Column(db.DateTime(timezone=True), nullable=True)
    ultimo_status = db.Column(db.String(10), nullable=True)       # "ok" | "erro"
    ultima_mensagem = db.Column(db.String(500), nullable=True)

    criado_em = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    usuario = db.relationship("Usuario", back_populates="fonte_sheets")


@login_manager.user_loader
def carregar_usuario(user_id: str):
    """A cada requisição o Flask-Login lê o id da sessão e chama esta função
    para obter o `current_user`. É a ÚNICA fonte do usuário logado."""
    try:
        return db.session.get(Usuario, int(user_id))
    except (TypeError, ValueError):
        return None