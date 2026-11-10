import pandas as pd


def filtrar_dataframe(df: pd.DataFrame, inicio=None, fim=None,
                      cliente=None, plataforma=None) -> pd.DataFrame:
    """Filtro único usado por KPIs, gráficos e tabela (antes existia em 3 lugares)."""
    df_f = df.copy()
    df_f['data_dt'] = pd.to_datetime(df_f['data'])
    if cliente and cliente != 'Todos':
        df_f = df_f[df_f['cliente'] == cliente]
    if plataforma and plataforma != 'Todas':
        df_f = df_f[df_f['plataforma'] == plataforma]
    if inicio:
        df_f = df_f[df_f['data_dt'] >= pd.to_datetime(inicio)]
    if fim:
        df_f = df_f[df_f['data_dt'] <= pd.to_datetime(fim)]
    return df_f
