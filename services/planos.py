"""Planos do sistema: os limites de cada plano ficam SÓ neste arquivo.

Se um dia você mudar um limite ou um preço, é aqui que mexe. O resto do
sistema (upload, Sheets, exportação, tela) apenas pergunta para as funções
abaixo, nunca escreve "3 clientes" no meio do código.
"""
from sqlalchemy import func

from extensions import db
from models import Registro

PLANO_PADRAO = "starter"

# max_clientes = None significa ilimitado.
PLANOS = {
    "starter": {
        "nome": "Starter",
        "preco": 147,
        "max_clientes": 5,
        "exportacao_avancada": False,
    },
    "professional": {
        "nome": "Professional",
        "preco": 297,
        "max_clientes": 15,
        "exportacao_avancada": True,
    },
    "whitelabel": {
        "nome": "White-label",
        "preco": 597,
        "max_clientes": None,
        "exportacao_avancada": True,
    },
}


def obter_plano(usuario) -> dict:
    """Devolve as regras do plano do usuário. Se o valor gravado no banco for
    desconhecido (erro de digitação, plano antigo), cai no plano padrão em vez
    de quebrar o sistema."""
    return PLANOS.get(usuario.plano, PLANOS[PLANO_PADRAO])


def contar_clientes(usuario_id: int) -> int:
    """Quantos valores DISTINTOS da coluna 'cliente' o usuário tem no banco."""
    total = (
        db.session.query(func.count(func.distinct(Registro.cliente)))
        .filter(Registro.usuario_id == usuario_id)
        .scalar()
    )
    return total or 0


def cabe_no_limite(usuario, qtd_clientes: int) -> bool:
    """True se `qtd_clientes` clientes distintos cabem no plano do usuário."""
    limite = obter_plano(usuario)["max_clientes"]
    return limite is None or qtd_clientes <= limite


def pode_exportar(usuario) -> bool:
    return obter_plano(usuario)["exportacao_avancada"]


def resumo_uso(usuario) -> dict:
    """Tudo que a tela 'Meus dados' vai precisar mostrar."""
    plano = obter_plano(usuario)
    return {
        "plano": plano["nome"],
        "clientes_usados": contar_clientes(usuario.id),
        "clientes_limite": plano["max_clientes"],  # None = ilimitado
        "exportacao_avancada": plano["exportacao_avancada"],
    }