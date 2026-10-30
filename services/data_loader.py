"""Leitura dos dados do dashboard direto do banco.

Por que devolver um DataFrame igual ao de antes? Porque filtros, KPIs e
gráficos já trabalham com ele. Trocamos só a ORIGEM dos dados (CSV -> banco),
sem mexer no resto.

Este módulo não conhece Flask nem a sessão: quem chama (app.py) decide qual é
o usuario_id e o passa como argumento, sempre vindo de current_user.
"""
import pandas as pd
from sqlalchemy import select

from extensions import db
from models import Registro

COLUNAS = [
    "data", "cliente", "campanha", "plataforma",
    "investimento", "impressoes", "cliques", "leads", "vendas", "faturamento",
]

TIPOS = {
    "investimento": "float64", "faturamento": "float64",
    "impressoes": "int64", "cliques": "int64", "leads": "int64", "vendas": "int64",
}


def _df_vazio() -> pd.DataFrame:
    """DataFrame sem linhas, mas com as colunas e tipos certos.

    Usuário novo (ainda sem planilha) cai aqui. Com as colunas presentes, as
    somas dão 0 e nada quebra com KeyError."""
    return pd.DataFrame(columns=COLUNAS).astype(TIPOS)


def carregar_dados_do_usuario(usuario_id: int) -> pd.DataFrame:
    """Todas as linhas do usuário informado, e SOMENTE as dele."""
    consulta = (
        select(
            Registro.data, Registro.cliente, Registro.campanha, Registro.plataforma,
            Registro.investimento, Registro.impressoes, Registro.cliques,
            Registro.leads, Registro.vendas, Registro.faturamento,
        )
        .where(Registro.usuario_id == usuario_id)   # <- o filtro de segurança
        .order_by(Registro.data)
    )
    linhas = db.session.execute(consulta).all()
    if not linhas:
        return _df_vazio()

    df = pd.DataFrame(linhas, columns=COLUNAS)
    # O banco devolve datetime.date; o resto do código espera texto 'AAAA-MM-DD'.
    df["data"] = pd.to_datetime(df["data"]).dt.strftime("%Y-%m-%d")
    return df