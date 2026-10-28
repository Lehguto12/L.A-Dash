import io
import pandas as pd
from flask import Flask, jsonify, request, render_template, make_response
from services.data_loader import carregar_dados
from services.kpi_calculator import calcular_kpis
from services.chart_builder import (
    gerar_grafico_linha_tempo,
    gerar_grafico_roas_clientes,
    gerar_grafico_investimento_plataforma,
    gerar_grafico_funil
)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/filtros-opcoes', methods=['GET'])
def obter_filtros():
    df = carregar_dados()
    return jsonify({
        'clientes': sorted(df['cliente'].unique().tolist()),
        'plataformas': sorted(df['plataforma'].unique().tolist()),
        'data_min': df['data'].min(),
        'data_max': df['data'].max()
    })

@app.route('/api/kpis', methods=['GET'])
def api_kpis():
    df = carregar_dados()
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')
    cliente = request.args.get('cliente')
    plataforma = request.args.get('plataforma')
    return jsonify(calcular_kpis(df, inicio_str=inicio, fim_str=fim, cliente=cliente, plataforma=plataforma))

@app.route('/api/charts', methods=['GET'])
def api_charts():
    """Endpoint que retorna todos os gráficos em JSON gerados pelo Plotly."""
    df = carregar_dados()
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')
    cliente = request.args.get('cliente')
    plataforma = request.args.get('plataforma')

    return jsonify({
        'linha_tempo': gerar_grafico_linha_tempo(df, inicio, fim, cliente, plataforma),
        'roas_clientes': gerar_grafico_roas_clientes(df, inicio, fim, cliente, plataforma),
        'investimento_plataforma': gerar_grafico_investimento_plataforma(df, inicio, fim, cliente, plataforma),
        'funil': gerar_grafico_funil(df, inicio, fim, cliente, plataforma)
    })

@app.route('/api/tabela-campanhas', methods=['GET'])
def api_tabela_campanhas():
    """Retorna os dados consolidados por campanha para preencher a tabela."""
    df = carregar_dados()
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')
    cliente = request.args.get('cliente')
    plataforma = request.args.get('plataforma')

    df_f = _filtrar_dataframe_aux(df, inicio, fim, cliente, plataforma)
    if df_f.empty:
        return jsonify([])

    # Agrupa por cliente, plataforma e campanha
    df_agrup = df_f.groupby(['cliente', 'plataforma', 'campanha']).agg({
        'investimento': 'sum',
        'leads': 'sum',
        'vendas': 'sum',
        'faturamento': 'sum'
    }).reset_index()

    # Calcula KPIs por linha
    resultado = []
    for _, row in df_agrup.iterrows():
        inv = row['investimento']
        fat = row['faturamento']
        lea = row['leads']
        ven = row['vendas']

        roas = round(fat / inv, 2) if inv > 0 else 0.0
        cpl = round(inv / lea, 2) if lea > 0 else 0.0
        cpa = round(inv / ven, 2) if ven > 0 else 0.0

        resultado.append({
            'cliente': row['cliente'],
            'plataforma': row['plataforma'],
            'campanha': row['campanha'],
            'investimento': round(inv, 2),
            'leads': int(lea),
            'vendas': int(ven),
            'faturamento': round(fat, 2),
            'roas': roas,
            'cpl': cpl,
            'cpa': cpa
        })

    return jsonify(resultado)

@app.route('/api/exportar-csv', methods=['GET'])
def exportar_csv():
    """Exporta a tabela filtrada em formato CSV."""
    df = carregar_dados()
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')
    cliente = request.args.get('cliente')
    plataforma = request.args.get('plataforma')

    df_f = _filtrar_dataframe_aux(df, inicio, fim, cliente, plataforma)
    if df_f.empty:
        return "Nenhum dado encontrado para exportar", 404

    df_agrup = df_f.groupby(['cliente', 'plataforma', 'campanha']).agg({
        'investimento': 'sum',
        'leads': 'sum',
        'vendas': 'sum',
        'faturamento': 'sum'
    }).reset_index()

    df_agrup['roas'] = df_agrup.apply(lambda r: round(r['faturamento'] / r['investimento'], 2) if r['investimento'] > 0 else 0.0, axis=1)
    df_agrup['cpl'] = df_agrup.apply(lambda r: round(r['investimento'] / r['leads'], 2) if r['leads'] > 0 else 0.0, axis=1)
    df_agrup['cpa'] = df_agrup.apply(lambda r: round(r['investimento'] / r['vendas'], 2) if r['vendas'] > 0 else 0.0, axis=1)

    # Gera o CSV em memória
    output = io.StringIO()
    df_agrup.to_csv(output, index=False, encoding='utf-8-sig', sep=';')
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=relatorio_campanhas_nexus.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    return response

def _filtrar_dataframe_aux(df, inicio, fim, cliente, plataforma):
    """Função auxiliar de filtro para a tabela."""
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

if __name__ == '__main__':
    print("🚀 Iniciando servidor Nexus Dashboard (Fase 4)...")
    app.run(debug=True, host='0.0.0.0', port=5000)