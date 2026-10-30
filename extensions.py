"""Extensões criadas "vazias" aqui e ligadas ao app em app.py (create_app).

Separar em um arquivo próprio evita importação circular: models.py e
auth.py podem importar `db` sem precisar importar o app.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()