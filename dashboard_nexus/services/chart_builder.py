import base64
import json
import math

import numpy as np
import plotly.graph_objects as go

from services.filtros import filtrar_dataframe

ROXO = '#7C3AED'
VERDE = '#10B981'
AZUL = '#3B82F6'
COR_PLATAFORMA = {'Google Ads': ROXO, 'Meta Ads': AZUL}

# Cores dos gráficos em cada tema. O fundo do gráfico acompanha o fundo do
# card (--bg-card) definido no CSS.
PALETAS = {
    'escuro': dict(
        bg='#131B2E', grid='#1E293B', texto='#F8FAFC', suave='#64748B',
        seletor='#1E293B', seletor_ativo='#7C3AED',
    ),
    'claro': dict(
        bg='#FFFFFF', grid='#E2E8F0', texto='#0F172A', suave='#64748B',
        seletor='#E2E8F0', seletor_ativo='#C4B5FD',
    ),
}

# Mantidos por compatibilidade (valores do tema escuro, o padrão).
PL_BG_COLOR = PALETAS['escuro']['bg']
GRID_COLOR = PALETAS['escuro']['grid']
TEXT_COLOR = PALETAS['escuro']['texto']


def _paleta(tema) -> dict:
    """Qualquer valor desconhecido cai no tema escuro (nunca quebra)."""
    return PALETAS.get(tema, PALETAS['escuro'])


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def _decodificar_bdata(obj):
    """
    O Plotly Python 6+ serializa arrays numpy como {"dtype": "f8", "bdata": "..."}.
    O Plotly.js 2.27 (usado no index.html) NÃO entende esse formato e acaba
    plotando o índice (0, 1, 2...) no lugar dos valores. Aqui convertemos de
    volta para listas normais antes de mandar o JSON ao navegador.
    """
    if isinstance(obj, dict):
        if 'bdata' in obj and 'dtype' in obj:
            arr = np.frombuffer(base64.b64decode(obj['bdata']), dtype=np.dtype(obj['dtype']))
            if 'shape' in obj:
                shape = [int(s) for s in str(obj['shape']).split(',')]
                arr = arr.reshape(shape)
            return arr.tolist()
        return {k: _decodificar_bdata(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decodificar_bdata(v) for v in obj]
    return obj


def _fig_para_dict(fig: go.Figure) -> dict:
    return _decodificar_bdata(json.loads(fig.to_json()))


def _fmt_int(n) -> str:
    return f"{int(n):,}".replace(',', '.')


def _fmt_dec(n, casas=2) -> str:
    return f"{n:.{casas}f}".replace('.', ',')


def _layout_base(titulo: str, p: dict, **extra) -> dict:
    layout = dict(
        title=dict(text=titulo, x=0.02, xanchor='left', font=dict(size=15)),
        paper_bgcolor=p['bg'],
        plot_bgcolor=p['bg'],
        font=dict(color=p['texto'], family='Inter, sans-serif'),
        separators=',.',  # pt-BR: vírgula decimal, ponto de milhar
    )
    layout.update(extra)
    return layout


# ---------------------------------------------------------------------------
# Gráficos (o último parâmetro, `tema`, é 'escuro' ou 'claro')
# ---------------------------------------------------------------------------
def gerar_grafico_linha_tempo(df, inicio, fim, cliente, plataforma, tema='escuro') -> dict:
    p = _paleta(tema)
    df_f = filtrar_dataframe(df, inicio, fim, cliente, plataforma)
    if df_f.empty:
        return {}

    d = df_f.groupby('data')[['investimento', 'faturamento']].sum().reset_index().sort_values('data')
    datas = d['data'].tolist()
    fat = [round(float(v), 2) for v in d['faturamento']]
    inv = [round(float(v), 2) for v in d['investimento']]

    fig = go.Figure()

    # Faturamento primeiro (fica atrás, com área suave)...
    fig.add_trace(go.Scatter(
        x=datas, y=fat, name='Faturamento',
        mode='lines',
        line=dict(color=VERDE, width=2),
        fill='tozeroy', fillcolor='rgba(16,185,129,0.10)',
        hovertemplate='R$ %{y:,.2f}'
    ))
    # ...e Investimento por último, para ser desenhado POR CIMA da linha verde.
    fig.add_trace(go.Scatter(
        x=datas, y=inv, name='Investimento',
        mode='lines',
        line=dict(color=ROXO, width=3),
        hovertemplate='R$ %{y:,.2f}'
    ))

    fig.update_layout(**_layout_base(
        'Evolução Diária: Investimento x Faturamento', p,
        autosize=True,
        margin=dict(t=100, b=40, l=70, r=20),
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, traceorder='reversed'),
        xaxis=dict(
            type='date', tickformat='%d/%m', hoverformat='%d/%m/%Y',
            showgrid=True, gridcolor=p['grid'], zeroline=False,
            rangeselector=dict(
                buttons=[
                    dict(count=7, label='7d', step='day', stepmode='backward'),
                    dict(count=30, label='30d', step='day', stepmode='backward'),
                    dict(step='all', label='Tudo'),
                ],
                bgcolor=p['seletor'], activecolor=p['seletor_ativo'],
                font=dict(color=p['texto']),
                x=0, y=1.02, yanchor='bottom',
            ),
        ),
        yaxis=dict(
            tickprefix='R$ ', tickformat=',.0f', showgrid=True,
            gridcolor=p['grid'], zeroline=False, rangemode='tozero',
            fixedrange=True,
        ),
    ))
    return _fig_para_dict(fig)


def gerar_grafico_roas_clientes(df, inicio, fim, cliente, plataforma, tema='escuro') -> dict:
    p = _paleta(tema)
    df_f = filtrar_dataframe(df, inicio, fim, cliente, plataforma)
    if df_f.empty:
        return {}

    d = df_f.groupby('cliente')[['investimento', 'faturamento']].sum().reset_index()
    d['roas'] = d.apply(lambda r: r['faturamento'] / r['investimento'] if r['investimento'] > 0 else 0.0, axis=1)
    d = d.sort_values('roas', ascending=True)

    clientes = d['cliente'].tolist()
    roas = [round(float(v), 2) for v in d['roas']]
    rotulos = [f"{_fmt_dec(v)}x" for v in roas]

    fig = go.Figure(go.Bar(
        x=roas, y=clientes, orientation='h',
        text=rotulos, textposition='outside', cliponaxis=False,
        textfont=dict(color=p['texto'], size=11),
        marker=dict(color=roas, cmin=0, cmax=max(max(roas), 1),
                    colorscale=[[0, '#4C1D95'], [1, '#A78BFA']]),
        hovertemplate='%{y}<br>ROAS: %{x:.2f}x<extra></extra>'
    ))
    # Linha de referência: abaixo de 1x a campanha gasta mais do que fatura
    fig.add_vline(x=1, line_dash='dot', line_color='#F59E0B', line_width=1)

    fig.update_layout(**_layout_base(
        'ROAS por Cliente', p,
        margin=dict(t=40, b=40, l=10, r=50),
        showlegend=False,
        xaxis=dict(title='ROAS (x)', range=[0, max(roas) * 1.25 if max(roas) > 0 else 1],
                   showgrid=True, gridcolor=p['grid'], zeroline=False, fixedrange=True),
        yaxis=dict(automargin=True, showgrid=False, fixedrange=True),
    ))
    return _fig_para_dict(fig)


def gerar_grafico_investimento_plataforma(df, inicio, fim, cliente, plataforma, tema='escuro') -> dict:
    p = _paleta(tema)
    df_f = filtrar_dataframe(df, inicio, fim, cliente, plataforma)
    if df_f.empty:
        return {}

    d = df_f.groupby('plataforma')['investimento'].sum().reset_index()
    labels = d['plataforma'].tolist()
    valores = [round(float(v), 2) for v in d['investimento']]
    cores = [COR_PLATAFORMA.get(pl, VERDE) for pl in labels]
    total = sum(valores)

    fig = go.Figure(go.Pie(
        labels=labels, values=valores, hole=0.55, sort=False,
        marker=dict(colors=cores, line=dict(color=p['bg'], width=2)),
        textinfo='percent', textfont=dict(color='#FFFFFF', size=13),
        hovertemplate='%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'
    ))
    fig.update_layout(**_layout_base(
        'Investimento por Plataforma', p,
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation='h', yanchor='bottom', y=-0.12, xanchor='center', x=0.5),
        annotations=[dict(text=f"<b>R$ {_fmt_int(total)}</b><br><span style='font-size:11px'>total</span>",
                          x=0.5, y=0.5, showarrow=False, font=dict(size=15, color=p['texto']))],
    ))
    return _fig_para_dict(fig)


def gerar_grafico_funil(df, inicio, fim, cliente, plataforma, tema='escuro') -> dict:
    p = _paleta(tema)
    df_f = filtrar_dataframe(df, inicio, fim, cliente, plataforma)
    if df_f.empty:
        return {}

    etapas = ['Impressões', 'Cliques', 'Leads', 'Vendas']
    valores = [int(df_f[c].sum()) for c in ('impressoes', 'cliques', 'leads', 'vendas')]

    # Impressões são ~1000x maiores que Vendas: em escala linear as últimas
    # barras ficam invisíveis. Usamos escala logarítmica só na LARGURA das barras;
    # os números mostrados continuam sendo os valores reais.
    larguras = [math.log10(v + 1) for v in valores]

    textos = []
    for i, v in enumerate(valores):
        if i == 0 or valores[i - 1] == 0:
            textos.append(_fmt_int(v))
        else:
            taxa = v / valores[i - 1] * 100
            textos.append(f"{_fmt_int(v)}<br>{_fmt_dec(taxa)}% da etapa anterior")

    fig = go.Figure(go.Funnel(
        y=etapas, x=larguras,
        text=textos, textinfo='text', textposition='inside',
        textfont=dict(color='#FFFFFF', size=11),
        hovertext=[f"{e}: {_fmt_int(v)}" for e, v in zip(etapas, valores)], hoverinfo='text',
        marker=dict(color=['#4C1D95', '#5B21B6', '#7C3AED', '#8B5CF6']),
        connector=dict(line=dict(color=p['grid']))
    ))
    fig.update_layout(**_layout_base(
        'Funil de Conversão Geral', p,
        margin=dict(t=40, b=30, l=20, r=20),
        annotations=[dict(text='Largura das etapas em escala logarítmica', x=0.5, y=-0.07,
                          xref='paper', yref='paper', showarrow=False,
                          font=dict(size=10, color=p['suave']))],
    ))
    fig.update_xaxes(visible=False, fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return _fig_para_dict(fig)
