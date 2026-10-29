import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'dados_demo.csv')

CLIENTES = [
    'Nexus Mentoria',
    'Empório Gourmet',
    'Aura Skincare',
    'TechCourses Brasil',
    'FitLife Academia',
    'Construtora Horizon'
]

CAMPANHAS_POR_CLIENTE = {
    'Nexus Mentoria': [
        ('Meta Ads', 'Mentoria_Conversao_LAL1%'),
        ('Google Ads', 'Mentoria_Search_Institucional')
    ],
    'Empório Gourmet': [
        ('Meta Ads', 'Ecom_Vinhos_Remarketing'),
        ('Meta Ads', 'Ecom_Kits_Interesses'),
        ('Google Ads', 'Ecom_Shopping_Produtos')
    ],
    'Aura Skincare': [
        ('Meta Ads', 'Lançamento_Sérum_Topo'),
        ('Google Ads', 'Search_Skincare_Antialias')
    ],
    'TechCourses Brasil': [
        ('Meta Ads', 'LeadGen_Ebook_Python'),
        ('Meta Ads', 'Remarketing_Carrinho'),
        ('Google Ads', 'PerformanceMax_Cursos')
    ],
    'FitLife Academia': [
        ('Meta Ads', 'Matriculas_Geolocalizado'),
        ('Google Ads', 'Search_Academia_Proxima')
    ],
    'Construtora Horizon': [
        ('Meta Ads', 'Lançamento_Residencial_AltoPadrão'),
        ('Google Ads', 'Search_Imoveis_Luxo')
    ]
}

def gerar_dados_ficticios() -> pd.DataFrame:
    """
    Gera um dataset de 180 dias com dados realistas de tráfego pago,
    respeitando variação nos fins de semana e comportamentos por nicho.
    """
    np.random.seed(42)  # Mantém reprodutibilidade nos dados
    data_fim = datetime.now().date()
    data_inicio = data_fim - timedelta(days=179)
    datas = [data_inicio + timedelta(days=i) for i in range(180)]

    registros = []

    for d in datas:
        dia_semana = d.weekday()  # 5=Sábado, 6=Domingo
        fator_fim_semana = 0.65 if dia_semana in [5, 6] else 1.0

        for cliente, campanhas in CAMPANHAS_POR_CLIENTE.items():
            for plataforma, campanha in campanhas:
                # Fator aleatório do dia (+/- 25%)
                ruido = np.random.uniform(0.75, 1.25)

                investimento = round(np.random.uniform(50, 350) * fator_fim_semana * ruido, 2)
                cpc = np.random.uniform(1.20, 4.50)
                cliques = int(investimento / cpc) if cpc > 0 else 0
                ctr = np.random.uniform(0.015, 0.045)
                impressoes = int(cliques / ctr) if ctr > 0 else 0

                # Taxa de conversão de lead e venda
                taxa_lead = np.random.uniform(0.08, 0.22)
                leads = int(cliques * taxa_lead)

                taxa_venda = np.random.uniform(0.05, 0.18)
                vendas = int(leads * taxa_venda)

                # Ticket médio variado por nicho
                ticket_medio = 450.0 if 'Mentoria' in cliente else (2500.0 if 'Construtora' in cliente else 180.0)
                faturamento = round(vendas * ticket_medio * np.random.uniform(0.85, 1.15), 2)

                registros.append({
                    'data': d.strftime('%Y-%m-%d'),
                    'cliente': cliente,
                    'campanha': campanha,
                    'plataforma': plataforma,
                    'investimento': investimento,
                    'impressoes': impressoes,
                    'cliques': cliques,
                    'leads': leads,
                    'vendas': vendas,
                    'faturamento': faturamento
                })

    df = pd.DataFrame(registros)
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    df.to_csv(DATA_PATH, index=False, encoding='utf-8')
    return df

def carregar_dados() -> pd.DataFrame:
    """Carrega os dados do CSV de forma segura. Se não existir ou corromper, gera o demo."""
    if not os.path.exists(DATA_PATH):
        return gerar_dados_ficticios()
    
    try:
        df = pd.read_csv(DATA_PATH)
        # Valida se as colunas essenciais existem
        colunas_obrigatorias = ['data', 'cliente', 'campanha', 'plataforma', 'investimento', 'impressoes', 'cliques', 'leads', 'vendas', 'faturamento']
        if not all(col in df.columns for col in colunas_obrigatorias):
            print("⚠️ Aviso: O CSV atual está fora do padrão. Regenerando dados demo...")
            return gerar_dados_ficticios()
            
        df['data'] = pd.to_datetime(df['data'], errors='coerce').dt.strftime('%Y-%m-%d')
        df = df.dropna(subset=['data'])
        return df
    except Exception as e:
        print(f"❌ Erro ao ler o arquivo de dados: {e}. Usando dados de fallback.")
        return gerar_dados_ficticios()