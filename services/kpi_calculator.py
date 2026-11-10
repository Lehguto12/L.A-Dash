import pandas as pd

from services.filtros import filtrar_dataframe


def _metricas(df_f: pd.DataFrame) -> dict:
    inv = df_f['investimento'].sum()
    fat = df_f['faturamento'].sum()
    lea = df_f['leads'].sum()
    ven = df_f['vendas'].sum()
    imp = df_f['impressoes'].sum()
    cli = df_f['cliques'].sum()
    return {
        'investimento': inv,
        'faturamento': fat,
        'roas': fat / inv if inv > 0 else 0,
        'cpl': inv / lea if lea > 0 else 0,
        'cpa': inv / ven if ven > 0 else 0,
        'ctr': (cli / imp) * 100 if imp > 0 else 0,
    }


def _variacao(atual: float, anterior: float):
    """Variação % vs período anterior. Retorna None quando não há base de comparação."""
    if anterior is None or pd.isna(anterior) or anterior == 0:
        return None
    return round((atual - anterior) / anterior * 100, 2)


def calcular_kpis(df: pd.DataFrame, inicio_str: str = None, fim_str: str = None,
                  cliente: str = None, plataforma: str = None) -> dict:
    atual = _metricas(filtrar_dataframe(df, inicio_str, fim_str, cliente, plataforma))

    # Período anterior com o mesmo número de dias, logo antes do início do filtro
    df_ant = pd.DataFrame()
    if inicio_str and fim_str:
        dt_ini = pd.to_datetime(inicio_str)
        dt_fim = pd.to_datetime(fim_str)
        dias = (dt_fim - dt_ini).days + 1
        ant_ini = dt_ini - pd.Timedelta(days=dias)
        ant_fim = dt_ini - pd.Timedelta(days=1)
        df_ant = filtrar_dataframe(df, ant_ini.strftime('%Y-%m-%d'), ant_fim.strftime('%Y-%m-%d'),
                                   cliente, plataforma)

    if df_ant.empty:
        # Sem dados antes do período: devolve None (o front mostra "sem período anterior")
        # em vez de um 0,00% que parece um cálculo real.
        variacoes = {k: None for k in atual}
    else:
        ant = _metricas(df_ant)
        variacoes = {k: _variacao(atual[k], ant[k]) for k in atual}

    return {
        'kpis': {k: round(float(v), 2) for k, v in atual.items()},
        'variacoes_pct': variacoes,
    }
