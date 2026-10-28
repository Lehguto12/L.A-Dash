import pandas as pd
from datetime import datetime, timedelta

def _safe_div(num: float, den: float, default: float = 0.0) -> float:
    """Auxiliar para tratar divisão por zero sem quebrar o código."""
    if den is None or den == 0 or pd.isna(den) or pd.isna(num):
        return default
    return float(num / den)

def _calc_variacao(atual: float, anterior: float, inverter_sinal: bool = False) -> float:
    """
    Calcula a variação percentual.
    Para CPL, CPA e CPC, inverter_sinal=True ajuda o frontend a interpretar queda como ganho.
    """
    if anterior == 0 or pd.isna(anterior) or pd.isna(atual):
        return 0.0
    var = ((atual - anterior) / anterior) * 100
    return round(var, 2)

def calcular_kpis(df: pd.DataFrame, inicio_str: str = None, fim_str: str = None,
                   cliente: str = None, plataforma: str = None) -> dict:
    """
    Filtra o DataFrame e calcula KPIs do período selecionado e do período anterior equivalente.
    """
    if df.empty:
        return {}

    df['data_dt'] = pd.to_datetime(df['data'])

    # Datas padrão (últimos 30 dias do dataset se não informado)
    data_max = df['data_dt'].max()
    data_min = df['data_dt'].min()

    dt_fim = pd.to_datetime(fim_str) if fim_str else data_max
    dt_inicio = pd.to_datetime(inicio_str) if inicio_str else (dt_fim - timedelta(days=29))

    # Aplica filtros gerais
    df_filtrado = df.copy()
    if cliente and cliente != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['cliente'] == cliente]
    if plataforma and plataforma != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['plataforma'] == plataforma]

    # Período Atual
    df_atual = df_filtrado[(df_filtrado['data_dt'] >= dt_inicio) & (df_filtrado['data_dt'] <= dt_fim)]

    # Período Anterior (mesmo número de dias)
    dias_duracao = (dt_fim - dt_inicio).days + 1
    dt_fim_ant = dt_inicio - timedelta(days=1)
    dt_inicio_ant = dt_fim_ant - timedelta(days=dias_duracao - 1)

    df_anterior = df_filtrado[(df_filtrado['data_dt'] >= dt_inicio_ant) & (df_filtrado['data_dt'] <= dt_fim_ant)]

    def agregar(sub_df):
        inv = sub_df['investimento'].sum()
        fat = sub_df['faturamento'].sum()
        imp = sub_df['impressoes'].sum()
        cli = sub_df['cliques'].sum()
        lea = sub_df['leads'].sum()
        ven = sub_df['vendas'].sum()

        return {
            'investimento': inv,
            'faturamento': fat,
            'impressoes': imp,
            'cliques': cli,
            'leads': lea,
            'vendas': ven,
            'roas': _safe_div(fat, inv),
            'cpl': _safe_div(inv, lea),
            'cpa': _safe_div(inv, ven),
            'ctr': _safe_div(cli, imp) * 100,
            'cpc': _safe_div(inv, cli),
            'taxa_conversao': _safe_div(ven, lea) * 100
        }

    kpi_atu = agregar(df_atual)
    kpi_ant = agregar(df_anterior)

    # Variações percentuais
    variacoes = {
        'investimento': _calc_variacao(kpi_atu['investimento'], kpi_ant['investimento']),
        'faturamento': _calc_variacao(kpi_atu['faturamento'], kpi_ant['faturamento']),
        'roas': _calc_variacao(kpi_atu['roas'], kpi_ant['roas']),
        'cpl': _calc_variacao(kpi_atu['cpl'], kpi_ant['cpl']),
        'cpa': _calc_variacao(kpi_atu['cpa'], kpi_ant['cpa']),
        'ctr': _calc_variacao(kpi_atu['ctr'], kpi_ant['ctr']),
        'cpc': _calc_variacao(kpi_atu['cpc'], kpi_ant['cpc']),
        'taxa_conversao': _calc_variacao(kpi_atu['taxa_conversao'], kpi_ant['taxa_conversao'])
    }

    return {
        'periodo_atual': {
            'inicio': dt_inicio.strftime('%Y-%m-%d'),
            'fim': dt_fim.strftime('%Y-%m-%d')
        },
        'periodo_anterior': {
            'inicio': dt_inicio_ant.strftime('%Y-%m-%d'),
            'fim': dt_fim_ant.strftime('%Y-%m-%d')
        },
        'kpis': {
            'investimento': round(kpi_atu['investimento'], 2),
            'faturamento': round(kpi_atu['faturamento'], 2),
            'roas': round(kpi_atu['roas'], 2),
            'cpl': round(kpi_atu['cpl'], 2),
            'cpa': round(kpi_atu['cpa'], 2),
            'ctr': round(kpi_atu['ctr'], 2),
            'cpc': round(kpi_atu['cpc'], 2),
            'taxa_conversao': round(kpi_atu['taxa_conversao'], 2),
            'leads': int(kpi_atu['leads']),
            'vendas': int(kpi_atu['vendas']),
            'cliques': int(kpi_atu['cliques']),
            'impressoes': int(kpi_atu['impressoes'])
        },
        'variacoes_pct': variacoes
    }