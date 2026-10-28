document.addEventListener("DOMContentLoaded", () => {
    carregarFiltrosOpcoes();

    document.getElementById("btn-filtrar").addEventListener("click", () => {
        carregarDashboard();
    });
});

function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor);
}

function formatarPercentual(valor) {
    return `${valor > 0 ? '+' : ''}${valor.toFixed(2)}%`;
}

async function carregarFiltrosOpcoes() {
    try {
        const response = await fetch('/api/filtros-opcoes');
        const data = await response.json();

        const selectCliente = document.getElementById("filtro-cliente");
        data.clientes.forEach(cliente => {
            const opt = document.createElement("option");
            opt.value = cliente;
            opt.textContent = cliente;
            selectCliente.appendChild(opt);
        });

        const selectPlataforma = document.getElementById("filtro-plataforma");
        data.plataformas.forEach(plat => {
            const opt = document.createElement("option");
            opt.value = plat;
            opt.textContent = plat;
            selectPlataforma.appendChild(opt);
        });

        document.getElementById("filtro-inicio").value = data.data_min;
        document.getElementById("filtro-fim").value = data.data_max;

        carregarDashboard();

    } catch (error) {
        console.error("Erro ao carregar opções de filtros:", error);
    }
}

function carregarDashboard() {
    carregarKPIs();
    carregarGraficos();
}

async function carregarKPIs() {
    const params = obterParametrosFiltro();
    try {
        const response = await fetch(`/api/kpis?${params}`);
        const data = await response.json();
        atualizarCardsKPI(data.kpis, data.variacoes_pct);
    } catch (error) {
        console.error("Erro ao carregar KPIs:", error);
    }
}

async function carregarGraficos() {
    const params = obterParametrosFiltro();
    try {
        const response = await fetch(`/api/charts?${params}`);
        const data = await response.json();

        // Configuração para ocultar a barra de ferramentas e a logo do Plotly
        const configGrafico = { displayModeBar: false };

        // Renderiza cada gráfico com a configuração limpa
        if (data.linha_tempo && Object.keys(data.linha_tempo).length > 0) {
            Plotly.react('chart-linha-tempo', data.linha_tempo.data, data.linha_tempo.layout, configGrafico);
        }
        if (data.roas_clientes && Object.keys(data.roas_clientes).length > 0) {
            Plotly.react('chart-roas-clientes', data.roas_clientes.data, data.roas_clientes.layout, configGrafico);
        }
        if (data.investimento_plataforma && Object.keys(data.investimento_plataforma).length > 0) {
            Plotly.react('chart-investimento-plataforma', data.investimento_plataforma.data, data.investimento_plataforma.layout, configGrafico);
        }
        if (data.funil && Object.keys(data.funil).length > 0) {
            Plotly.react('chart-funil', data.funil.data, data.funil.layout, configGrafico);
        }

    } catch (error) {
        console.error("Erro ao carregar gráficos:", error);
    }
}

function obterParametrosFiltro() {
    const cliente = document.getElementById("filtro-cliente").value;
    const plataforma = document.getElementById("filtro-plataforma").value;
    const inicio = document.getElementById("filtro-inicio").value;
    const fim = document.getElementById("filtro-fim").value;

    let query = `cliente=${encodeURIComponent(cliente)}&plataforma=${encodeURIComponent(plataforma)}`;
    if (inicio) query += `&inicio=${inicio}`;
    if (fim) query += `&fim=${fim}`;
    return query;
}

function atualizarCardsKPI(kpis, variacoes) {
    document.getElementById("kpi-investimento").textContent = formatarMoeda(kpis.investimento);
    document.getElementById("kpi-faturamento").textContent = formatarMoeda(kpis.faturamento);
    document.getElementById("kpi-roas").textContent = `${kpis.roas.toFixed(2)}x`;
    document.getElementById("kpi-cpl").textContent = formatarMoeda(kpis.cpl);
    document.getElementById("kpi-cpa").textContent = formatarMoeda(kpis.cpa);
    document.getElementById("kpi-ctr").textContent = `${kpis.ctr.toFixed(2)}%`;

    atualizarTrend("trend-investimento", variacoes.investimento, false);
    atualizarTrend("trend-faturamento", variacoes.faturamento, false);
    atualizarTrend("trend-roas", variacoes.roas, false);
    atualizarTrend("trend-cpl", variacoes.cpl, true);
    atualizarTrend("trend-cpa", variacoes.cpa, true);
    atualizarTrend("trend-ctr", variacoes.ctr, false);
}

function atualizarTrend(elementId, valor, inverterRegra) {
    const el = document.getElementById(elementId);
    let positivo = valor >= 0;
    if (inverterRegra) positivo = !positivo;

    el.className = `kpi-trend ${positivo ? 'positive' : 'negative'}`;
    const icone = valor >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
    el.innerHTML = `<i class="fa-solid ${icone}"></i> ${formatarPercentual(valor)} vs ant.`;
}

// Adicione dentro de carregarDashboard() existente:
function carregarDashboard() {
    carregarKPIs();
    carregarGraficos();
    carregarTabelaCampanhas();
}

// Event listener para o botão de exportar CSV
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("btn-exportar").addEventListener("click", () => {
        const params = obterParametrosFiltro();
        window.location.href = `/api/exportar-csv?${params}`;
    });
});

async function carregarTabelaCampanhas() {
    const params = obterParametrosFiltro();
    try {
        const response = await fetch(`/api/tabela-campanhas?${params}`);
        const dados = await response.json();
        
        const tbody = document.getElementById("tabela-corpo");
        tbody.innerHTML = "";

        dados.forEach(item => {
            const tr = document.createElement("tr");
            
            // Destaca em vermelho suave campanhas com ROAS abaixo de 1
            if (item.roas < 1.0) {
                tr.className = "row-warning";
            }

            tr.innerHTML = `
                <td>${item.cliente}</td>
                <td>${item.plataforma}</td>
                <td>${item.campanha}</td>
                <td>${formatarMoeda(item.investimento)}</td>
                <td>${item.leads}</td>
                <td>${item.vendas}</td>
                <td>${item.roas.toFixed(2)}x</td>
                <td>${formatarMoeda(item.cpl)}</td>
                <td>${formatarMoeda(item.cpa)}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error("Erro ao carregar tabela de campanhas:", error);
    }
}

// Função simples para ordenação de colunas da tabela
function ordenarTabela(colIndex) {
    const tabela = document.getElementById("tabela-campanhas");
    let switching = true;
    let dir = "asc";
    let switchCount = 0;

    while (switching) {
        switching = false;
        const linhas = tabela.rows;

        for (let i = 1; i < (linhas.length - 1); i++) {
            let shouldSwitch = false;
            const x = linhas[i].getElementsByTagName("TD")[colIndex];
            const y = linhas[i + 1].getElementsByTagName("TD")[colIndex];

            let valX = x.innerHTML.replace("R$", "").replace(/\./g, "").replace(",", ".").trim();
            let valY = y.innerHTML.replace("R$", "").replace(/\./g, "").replace(",", ".").trim();

            let numX = parseFloat(valX);
            let numY = parseFloat(valY);

            if (!isNaN(numX) && !isNaN(numY)) {
                if (dir === "asc" && numX > numY) { shouldSwitch = true; break; }
                else if (dir === "desc" && numX < numY) { shouldSwitch = true; break; }
            } else {
                if (dir === "asc" && valX.toLowerCase() > valY.toLowerCase()) { shouldSwitch = true; break; }
                else if (dir === "desc" && valX.toLowerCase() < valY.toLowerCase()) { shouldSwitch = true; break; }
            }
        }

        if (shouldSwitch) {
            linhas[i].parentNode.insertBefore(linhas[i + 1], linhas[i]);
            switching = true;
            switchCount++;
        } else {
            if (switchCount === 0 && dir === "asc") {
                dir = "desc";
                switching = true;
            }
        }
    }
}