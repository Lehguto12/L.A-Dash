import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go

PL_BG_COLOR = '#131B2E'

def _filtrar_dataframe(df: pd.DataFrame, inicio_str: str = None, fim_str: str = None,
                       cliente: str = None, plataforma: str = None) -> pd.DataFrame:
    if df.empty:
        return df
    
    df_f = df.copy()
    df_f['data_dt'] = pd.to_datetime(df_f['data'])
    
    if cliente and cliente != 'Todos':
        df_f = df_f[df_f['cliente'] == cliente]
    if plataforma and plataforma != 'Todas':
        df_f = df_f[df_f['plataforma'] == plataforma]
        
    if inicio_str:
        df_f = df_f[df_f['data_dt'] >= pd.to_datetime(inicio_str)]
    if fim_str:
        df_f = df_f[df_f['data_dt'] <= pd.to_datetime(fim_str)]
        
    return df_f

from plotly.subplots import make_subplots

def gerar_grafico_linha_tempo(df: pd.DataFrame, inicio: str, fim: str, cliente: str, plataforma: str) -> dict:
    df_f = _filtrar_dataframe(df, inicio, fim, cliente, plataforma)
    if df_f.empty:
        return {}
        
    df_agrup = df_f.groupby('data')[['investimento', 'faturamento']].sum().reset_index()
    
    # Criamos o gráfico usando Graph Objects para ter total controle das duas linhas
    fig = go.Figure()

    # Linha de Investimento (Roxo)
    fig.add_trace(go.Scatter(
        x=df_agrup['data'], 
        y=df_agrup['investimento'],
        name='Investimento',
        mode='lines+markers',
        line=dict(color='#7C3AED', width=3)
    ))

    # Linha de Faturamento (Verde)
    fig.add_trace(go.Scatter(
        x=df_agrup['data'], 
        y=df_agrup['faturamento'],
        name='Faturamento',
        mode='lines+markers',
        line=dict(color='#10B981', width=3)
    ))
    
    fig.update_layout(
        title='Evolução Diária: Investimento x Faturamento',
        paper_bgcolor=PL_BG_COLOR,
        plot_bgcolor=PL_BG_COLOR,
        font_color='#F8FAFC',
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor='#1E293B'),
        yaxis=dict(showgrid=True, gridcolor='#1E293B')
    )
    return json.loads(fig.to_json())

def gerar_grafico_roas_clientes(df: pd.DataFrame, inicio: str, fim: str, cliente: str, plataforma: str) -> dict:
    df_f = _filtrar_dataframe(df, inicio, fim, cliente, plataforma)
    if df_f.empty:
        return {}
        
    df_agrup = df_f.groupby('cliente')[['investimento', 'faturamento']].sum().reset_index()
    df_agrup['roas'] = df_agrup.apply(lambda r: round(r['faturamento'] / r['investimento'], 2) if r['investimento'] > 0 else 0, axis=1)
    df_agrup = df_agrup.sort_values(by='roas', ascending=True)
    
    fig = px.bar(df_agrup, x='roas', y='cliente', orientation='h',
                 text='roas', labels={'roas': 'ROAS (x)', 'cliente': 'Cliente'},
                 color='roas', color_continuous_scale='Purples')
    
    fig.update_traces(texttemplate='%{text}x', textposition='outside')
    fig.update_layout(
        title='ROAS por Cliente',
        paper_bgcolor=PL_BG_COLOR,
        plot_bgcolor=PL_BG_COLOR,
        font_color='#F8FAFC',
        margin=dict(t=40, b=20, l=20, r=20),
        coloraxis_showscale=False
    )
    return json.loads(fig.to_json())

def gerar_grafico_investimento_plataforma(df: pd.DataFrame, inicio: str, fim: str, cliente: str, plataforma: str) -> dict:
    df_f = _filtrar_dataframe(df, inicio, fim, cliente, plataforma)
    if df_f.empty:
        return {}
        
    df_agrup = df_f.groupby('plataforma')['investimento'].sum().reset_index()
    
    fig = px.pie(df_agrup, names='plataforma', values='investimento', hole=0.5,
                 color_discrete_sequence=['#7C3AED', '#3B82F6', '#10B981'])
    
    fig.update_layout(
        title='Investimento por Plataforma',
        paper_bgcolor=PL_BG_COLOR,
        plot_bgcolor=PL_BG_COLOR,
        font_color='#F8FAFC',
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    return json.loads(fig.to_json())

def gerar_grafico_funil(df: pd.DataFrame, inicio: str, fim: str, cliente: str, plataforma: str) -> dict:
    df_f = _filtrar_dataframe(df, inicio, fim, cliente, plataforma)
    if df_f.empty:
        return {}
        
    etapas = ['Impressões', 'Cliques', 'Leads', 'Vendas']
    valores = [
        int(df_f['impressoes'].sum()),
        int(df_f['cliques'].sum()),
        int(df_f['leads'].sum()),
        int(df_f['vendas'].sum())
    ]
    
    fig = go.Figure(go.Funnel(
        y=etapas,
        x=valores,
        textinfo="value+percent initial",
        marker=dict(color=["#4C1D95", "#5B21B6", "#7C3AED", "#8B5CF6"])
    ))
    
    fig.update_layout(
        title='Funil de Conversão Geral',
        paper_bgcolor=PL_BG_COLOR,
        plot_bgcolor=PL_BG_COLOR,
        font_color='#F8FAFC',
        margin=dict(t=40, b=20, l=20, r=20)
    )
    return json.loads(fig.to_json())
