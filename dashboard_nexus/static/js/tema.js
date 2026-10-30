/* Alterna entre tema claro e escuro.
 *
 * Carregue este arquivo no <head>, SEM defer: o tema é aplicado antes de a
 * página aparecer, para não piscar o tema errado.
 *
 * Ordem de decisão: escolha salva pelo usuário > configuração do sistema.
 */
(function () {
    var CHAVE = "nexus-tema";
    var raiz = document.documentElement;

    var ICONE_SOL =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<circle cx="12" cy="12" r="4"/>' +
        '<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>' +
        "</svg>";
    var ICONE_LUA =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>' +
        "</svg>";

    function lerSalvo() {
        try {
            var v = localStorage.getItem(CHAVE);
            return v === "claro" || v === "escuro" ? v : null;
        } catch (e) {
            return null; // navegador bloqueou o armazenamento: segue o sistema
        }
    }

    function gravar(tema) {
        try { localStorage.setItem(CHAVE, tema); } catch (e) { /* sem persistência */ }
    }

    function doSistema() {
        return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
            ? "claro" : "escuro";
    }

    function atual() {
        return raiz.getAttribute("data-tema") === "claro" ? "claro" : "escuro";
    }

    var botao = null;

    function atualizarBotao() {
        if (!botao) return;
        var claro = atual() === "claro";
        // Mostra o ícone do tema PARA O QUAL o clique vai trocar.
        botao.innerHTML = claro ? ICONE_LUA : ICONE_SOL;
        var texto = claro ? "Mudar para o tema escuro" : "Mudar para o tema claro";
        botao.setAttribute("aria-label", texto);
        botao.setAttribute("title", texto);
    }

    function aplicar(tema, avisar) {
        raiz.setAttribute("data-tema", tema);
        atualizarBotao();
        if (avisar) {
            // O dashboard escuta isto para redesenhar os gráficos nas cores novas.
            document.dispatchEvent(new CustomEvent("tema-alterado", { detail: { tema: tema } }));
        }
    }

    // 1) Aplica já, durante o carregamento do <head>.
    aplicar(lerSalvo() || doSistema(), false);

    // 2) Se o usuário nunca escolheu, acompanha o sistema quando ele mudar.
    if (window.matchMedia) {
        var consulta = window.matchMedia("(prefers-color-scheme: light)");
        var aoMudarSistema = function () {
            if (!lerSalvo()) aplicar(doSistema(), true);
        };
        if (consulta.addEventListener) consulta.addEventListener("change", aoMudarSistema);
        else if (consulta.addListener) consulta.addListener(aoMudarSistema);
    }

    // 3) Cria o botão quando o HTML estiver pronto.
    function criarBotao() {
        botao = document.createElement("button");
        botao.type = "button";
        botao.id = "btn-tema";
        botao.className = "btn-tema";
        botao.addEventListener("click", function () {
            var novo = atual() === "claro" ? "escuro" : "claro";
            gravar(novo);
            aplicar(novo, true);
        });

        var cabecalho = document.querySelector(".logo-area");
        if (cabecalho) {
            botao.classList.add("btn-tema--cabecalho");
            cabecalho.appendChild(botao);
        } else {
            botao.classList.add("btn-tema--fixo");
            document.body.appendChild(botao);
        }
        atualizarBotao();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", criarBotao);
    } else {
        criarBotao();
    }
})();
