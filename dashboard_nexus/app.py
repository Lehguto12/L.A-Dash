import io
import os

import pandas as pd
from flask import Flask, jsonify, request, render_template, make_response
from flask_login import login_required, current_user

from config import Config, IS_PRODUCTION
from comandos import sincronizar_sheets_cmd
from extensions import db, migrate, login_manager, csrf
from auth import auth_bp
from uploads import dados_bp
from services.data_loader import carregar_dados_do_usuario
from services.kpi_calculator import calcular_kpis
from services.filtros import filtrar_dataframe
from services.chart_builder import (
    gerar_grafico_linha_tempo,
    gerar_grafico_roas_clientes,
    gerar_grafico_investimento_plataforma,
    gerar_grafico_funil
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # SECRET_KEY assina o cookie de sessão. Se vazar, qualquer um forja um login.
    if not app.config.get("SECRET_KEY"):
        if IS_PRODUCTION:
            raise RuntimeError("Defina a variável de ambiente SECRET_KEY no Render.")
        app.config["SECRET_KEY"] = "chave-apenas-para-desenvolvimento-local"

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.session_protection = "strong"

    app.register_blueprint(auth_bp)
    app.register_blueprint(dados_bp)
    app.cli.add_command(sincronizar_sheets_cmd)
    return app


app = create_app()


def _df_do_usuario() -> pd.DataFrame:
    """ÚNICO ponto por onde os dados entram nas rotas /api/*.

    O usuario_id vem de current_user (sessão assinada pelo servidor), nunca de
    request.args, request.form ou do JavaScript. Como todas as rotas passam por
    aqui, não existe caminho para ler dado de outro usuário."""
    return carregar_dados_do_usuario(current_user.id)


def _filtros_da_requisicao():
    """Filtros de tela (datas, cliente, plataforma). Estes SIM vêm da URL,
    mas só restringem ainda mais os dados do próprio usuário."""
    return (
        request.args.get('inicio'),
        request.args.get('fim'),
        request.args.get('cliente'),
        request.args.get('plataforma'),
    )


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/api/filtros-opcoes', methods=['GET'])
@login_required
def obter_filtros():
    df = _df_do_usuario()

    # Usuário sem planilha enviada: avisamos o front em vez de quebrar.
    if df.empty:
        return jsonify({
            'sem_dados': True,
            'clientes': [],
            'plataformas': [],
            'data_min': None,
            'data_max': None,
            'data_inicio_padrao': None
        })

    data_max = df['data'].max()
    data_min = df['data'].min()
    # Período padrão: últimos 90 dias, para sobrar histórico anterior para a comparação "vs ant."
    inicio_padrao = max(data_min, (pd.to_datetime(data_max) - pd.Timedelta(days=89)).strftime('%Y-%m-%d'))
    return jsonify({
        'sem_dados': False,
        'clientes': sorted(df['cliente'].unique().tolist()),
        'plataformas': sorted(df['plataforma'].unique().tolist()),
        'data_min': data_min,
        'data_max': data_max,
        'data_inicio_padrao': inicio_padrao
    })


@app.route('/api/kpis', methods=['GET'])
@login_required
def api_kpis():
    df = _df_do_usuario()
    inicio, fim, cliente, plataforma = _filtros_da_requisicao()
    return jsonify(calcular_kpis(df, inicio_str=inicio, fim_str=fim, cliente=cliente, plataforma=plataforma))


@app.route('/api/charts', methods=['GET'])
@login_required
def api_charts():
    """Endpoint que retorna todos os gráficos em JSON gerados pelo Plotly."""
    df = _df_do_usuario()
    inicio, fim, cliente, plataforma = _filtros_da_requisicao()

    return jsonify({
        'linha_tempo': gerar_grafico_linha_tempo(df, inicio, fim, cliente, plataforma),
        'roas_clientes': gerar_grafico_roas_clientes(df, inicio, fim, cliente, plataforma),
        'investimento_plataforma': gerar_grafico_investimento_plataforma(df, inicio, fim, cliente, plataforma),
        'funil': gerar_grafico_funil(df, inicio, fim, cliente, plataforma)
    })


@app.route('/api/tabela-campanhas', methods=['GET'])
@login_required
def api_tabela_campanhas():
    """Retorna os dados consolidados por campanha para preencher a tabela."""
    df = _df_do_usuario()
    inicio, fim, cliente, plataforma = _filtros_da_requisicao()

    df_f = filtrar_dataframe(df, inicio, fim, cliente, plataforma)
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
@login_required
def exportar_csv():
    """Exporta a tabela filtrada em formato CSV."""
    df = _df_do_usuario()
    inicio, fim, cliente, plataforma = _filtros_da_requisicao()

    df_f = filtrar_dataframe(df, inicio, fim, cliente, plataforma)
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


if __name__ == '__main__':
    # debug só liga se você pedir (FLASK_DEBUG=1). Em produção o gunicorn nem usa este bloco.
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="127.0.0.1", port=5000)