"use strict";
const $ = (id) => document.getElementById(id);
let OPC = null;
let grafico = null;

const UNID_OBJ = { custo: "R$", calorias: "kcal", proteina: "g", fibra: "g", sodio: "mg", gordura: "g", massa: "g" };
const STATUS = {
  otimo: ["Ótimo", "ok"], factivel: ["Factível", "ok"], infactivel: ["Infactível", "ruim"],
  inviavel: ["Inviável", "ruim"], limite: ["Limite atingido", "ruim"], ilimitado: ["Ilimitado", "ruim"],
};

const fmt = (v, d = 2) => v == null ? "—" :
  Number(v).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtObj = (v, obj) => v == null ? "—" :
  (UNID_OBJ[obj] === "R$" ? "R$ " + fmt(v) : fmt(v, 1) + " " + (UNID_OBJ[obj] || ""));
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const selo = (st) => { const [t, c] = STATUS[st] || [st, "ruim"]; return `<span class="selo ${c}">${t}</span>`; };
const seloOk = (ok) => ok ? '<span class="selo ok">ok</span>' : '<span class="selo ruim">violado</span>';

function nomeRestricao(nome) {
  if (nome === "frutas_hortalicas_min") return "Frutas e hortaliças (mín. 400 g)";
  const m = nome.match(/^(.*)_(min|max)$/);
  if (!m) return nome;
  const nut = OPC.nutrientes.find((n) => n.id === m[1]);
  return `${nut ? nut.rotulo : m[1]} (${m[2] === "min" ? "mínimo" : "máximo"})`;
}

async function api(url, corpo) {
  const init = corpo ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) } : {};
  const r = await fetch(url, init);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const det = d.detail ? (typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail)) : `Erro HTTP ${r.status}`;
    throw new Error(det);
  }
  return d;
}

function opcoesSelect(sel, itens, rot) {
  sel.innerHTML = itens.map((i) => `<option value="${i.id}">${esc(i[rot])}</option>`).join("");
}

function perfilAtual() { return OPC.perfis.find((p) => p.id === $("perfil").value); }

function preencherLimites() {
  const p = perfilAtual();
  $("perfil-desc").textContent = p.descricao + (p.exclui.length ? ` Exclui: ${p.exclui.join(", ")}.` : "");
  $("limites").innerHTML = OPC.nutrientes.map((n) => {
    const [lo, hi] = p.limites[n.id];
    return `<tr><td>${esc(n.rotulo)}</td>
      <td><input type="number" step="any" min="0" data-nut="${n.id}" data-lado="0" value="${lo ?? ""}" data-padrao="${lo ?? ""}" aria-label="${esc(n.rotulo)} mínimo"></td>
      <td><input type="number" step="any" min="0" data-nut="${n.id}" data-lado="1" value="${hi ?? ""}" data-padrao="${hi ?? ""}" aria-label="${esc(n.rotulo)} máximo"></td>
      <td>${esc(n.unidade)}</td></tr>`;
  }).join("");
}

function lerLimites() {
  const lim = {};
  for (const inp of document.querySelectorAll("#limites input")) {
    const nut = inp.dataset.nut;
    lim[nut] ??= [null, null];
    lim[nut][+inp.dataset.lado] = inp.value.trim() === "" ? null : Number(inp.value);
  }
  return lim;
}

function ocupado(sim, txt) {
  $("carregando").classList.toggle("oculto", !sim);
  $("carregando-txt").textContent = txt || "Resolvendo…";
  $("otimizar").disabled = $("comparar").disabled = sim;
  if (sim) $("erro").classList.add("oculto");
}

function mostrarErro(msg) { $("erro").textContent = msg; $("erro").classList.remove("oculto"); }

async function otimizar() {
  const metodo = $("metodo").value;
  ocupado(true, metodo === "simplex" ? "Resolvendo…"
    : "Resolvendo… (Branch and Bound e Algoritmo Genético podem levar alguns segundos)");
  $("cmp").classList.add("oculto");
  try {
    const d = await api("/api/resolver", { perfil: $("perfil").value, objetivo: $("objetivo").value, metodo, limites: lerLimites() });
    renderResultado(d);
  } catch (e) {
    mostrarErro(e.message);
    $("res").classList.add("oculto");
  } finally {
    ocupado(false);
  }
}

function kpi(r, v) { return `<div class="kpi"><div class="r">${r}</div><div class="v">${v}</div></div>`; }

function renderResultado(d) {
  const obj = $("objetivo").value;
  $("res").classList.remove("oculto");
  $("res-titulo").innerHTML = `${esc(d.metodo_rotulo)} <span class="dica">· ${esc(d.descricao)}</span>`;
  const k = [kpi("Status", selo(d.status)), kpi("Função objetivo", fmtObj(d.valor, obj)),
             kpi("Tempo", d.tempo < 1 ? fmt(d.tempo * 1000, 1) + " ms" : fmt(d.tempo, 2) + " s")];
  if (d.custo != null && obj !== "custo") k.push(kpi("Custo diário", "R$ " + fmt(d.custo)));
  if (d.metodo === "simplex") k.push(kpi("Iterações (pivôs)", d.iteracoes));
  if (d.metodo === "branch_and_bound") {
    k.push(kpi("Nós explorados", d.nos ?? "—"));
    k.push(kpi("Gap", d.gap == null ? "—" : fmt(d.gap * 100, 2) + " %"));
  }
  if (d.metodo === "genetico") {
    k.push(kpi("Gerações", d.iteracoes));
    k.push(kpi("Violação", fmt(d.violacao, 4)));
  }
  if (d.n_alimentos != null) k.push(kpi("Alimentos", d.n_alimentos));
  if (d.massa != null) k.push(kpi("Massa total", fmt(d.massa, 0) + " g"));
  $("kpis").innerHTML = k.join("");

  const temX = !!d.cardapio;
  for (const id of ["cardapio", "totais"]) $(id).closest(".painel").classList.toggle("oculto", !temX);
  if (temX) {
    renderCardapio(d.cardapio);
    renderTotais(d.totais, d.frutas_hortalicas_g);
  } else if (d.status === "inviavel") {
    mostrarErro("O problema é inviável com esses limites: nenhuma combinação de alimentos atende a todas as restrições. Tente afrouxar algum limite.");
  }

  $("bloco-precos").classList.toggle("oculto", !d.precos_sombra);
  if (d.precos_sombra) renderPrecos(d.precos_sombra, obj);

  $("bloco-curva").classList.toggle("oculto", !d.curva);
  if (d.curva) renderCurva(d.curva, obj);
}

function renderCardapio(linhas) {
  let g = 0, c = 0;
  const corpo = linhas.map((l) => {
    g += l.gramas; c += l.custo;
    return `<tr><td>${esc(l.nome)}</td><td>${esc(l.grupo)}</td>
      <td class="n">${fmt(l.porcoes, Math.abs(l.porcoes - Math.round(l.porcoes)) < 0.005 ? 0 : 2)}</td><td>${esc(l.medida)}</td>
      <td class="n">${fmt(l.gramas, 0)} g</td><td class="n">R$ ${fmt(l.custo)}</td></tr>`;
  }).join("");
  $("cardapio").innerHTML = `<thead><tr><th>Alimento</th><th>Grupo</th><th class="n">Porções</th><th>Medida da porção</th>
    <th class="n">Gramas</th><th class="n">Custo</th></tr></thead><tbody>${corpo}</tbody>
    <tfoot><tr><td colspan="4">Total</td><td class="n">${fmt(g, 0)} g</td><td class="n">R$ ${fmt(c)}</td></tr></tfoot>`;
}

function trilho(v, lo, hi, ok) {
  const topo = Math.max(hi ?? (lo ?? v) * 1.5, v, lo ?? 0) * 1.1 || 1;
  const pct = (x) => Math.min(100, Math.max(0, (x / topo) * 100));
  const a = pct(lo ?? 0), b = hi == null ? 100 : pct(hi);
  return `<div class="trilho"><div class="faixa" style="left:${a}%;width:${b - a}%"></div>
    <div class="marca ${ok ? "" : "ruim"}" style="left:${pct(v)}%"></div></div>`;
}

function renderTotais(tot, fh) {
  const linhas = tot.map((t) => `<tr><td>${esc(t.rotulo)}</td><td class="n">${fmt(t.valor, 1)} ${esc(t.unidade)}</td>
    <td class="n">${t.min == null ? "—" : fmt(t.min, 0)}</td><td class="n">${t.max == null ? "—" : fmt(t.max, 0)}</td>
    <td class="col-trilho">${trilho(t.valor, t.min, t.max, t.ok)}</td><td>${seloOk(t.ok)}</td></tr>`);
  if (fh != null) {
    const ok = fh >= 400 - 1e-3;
    linhas.push(`<tr><td>Frutas e hortaliças</td><td class="n">${fmt(fh, 0)} g</td><td class="n">400</td><td class="n">—</td>
      <td class="col-trilho">${trilho(fh, 400, null, ok)}</td><td>${seloOk(ok)}</td></tr>`);
  }
  $("totais").innerHTML = `<thead><tr><th>Nutriente</th><th class="n">Total</th><th class="n">Mín.</th><th class="n">Máx.</th>
    <th>Faixa permitida</th><th>Situação</th></tr></thead><tbody>${linhas.join("")}</tbody>`;
}

function renderPrecos(precos, obj) {
  const u = UNID_OBJ[obj] || "";
  if (!precos.length) {
    $("precos").innerHTML = `<tbody><tr><td class="dica">Nenhuma restrição ativa com preço-sombra não nulo.</td></tr></tbody>`;
    return;
  }
  precos.sort((a, b) => Math.abs(b.preco_sombra) - Math.abs(a.preco_sombra));
  const corpo = precos.map((p) => `<tr><td>${esc(nomeRestricao(p.restricao))}</td>
    <td class="n">${p.sentido === ">=" ? "≥" : p.sentido === "<=" ? "≤" : "="} ${fmt(p.rhs, 1)}</td>
    <td class="n">${fmt(p.lhs, 1)}</td><td class="n">${fmt(p.preco_sombra, 4)}</td></tr>`).join("");
  $("precos").innerHTML = `<thead><tr><th>Restrição</th><th class="n">Lado direito</th><th class="n">Valor na solução</th>
    <th class="n">Preço-sombra (${esc(u)} por unidade)</th></tr></thead><tbody>${corpo}</tbody>`;
}

function renderCurva(curva, obj) {
  if (grafico) { grafico.destroy(); grafico = null; }
  if (typeof Chart === "undefined") {
    $("bloco-curva").querySelector(".grafico").innerHTML = '<p class="dica">Chart.js não carregou (sem internet?).</p>';
    return;
  }
  grafico = new Chart($("curva"), {
    type: "line",
    data: {
      labels: curva.map((c) => c.geracao),
      datasets: [
        { label: `Melhor valor factível (${UNID_OBJ[obj] || ""})`, data: curva.map((c) => c.melhor),
          borderColor: "#2f7a4f", backgroundColor: "#2f7a4f", pointRadius: 0, borderWidth: 2, yAxisID: "y" },
        { label: "Fração da população factível", data: curva.map((c) => c.frac_factivel),
          borderColor: "#c58b1b", backgroundColor: "#c58b1b", pointRadius: 0, borderWidth: 1.5, borderDash: [4, 3], yAxisID: "y2" },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { title: { display: true, text: "Geração" }, ticks: { maxTicksLimit: 10 } },
        y: { title: { display: true, text: "Função objetivo" } },
        y2: { position: "right", min: 0, max: 1, grid: { drawOnChartArea: false }, title: { display: true, text: "Fração factível" } },
      },
    },
  });
}

async function comparar() {
  ocupado(true, "Comparando os métodos… (pode levar uns 15 segundos)");
  $("res").classList.add("oculto");
  try {
    const d = await api("/api/comparar", { perfil: $("perfil").value, objetivo: $("objetivo").value, limites: lerLimites() });
    renderComparacao(d);
  } catch (e) {
    mostrarErro(e.message);
    $("cmp").classList.add("oculto");
  } finally {
    ocupado(false);
  }
}

function esforco(m) {
  if (m.metodo === "branch_and_bound") return m.nos == null ? "—" : `${m.nos} nós`;
  if (m.metodo === "genetico") return `${m.iteracoes} gerações`;
  return `${m.iteracoes} pivôs`;
}

function renderComparacao(d) {
  const obj = $("objetivo").value;
  $("cmp").classList.remove("oculto");
  $("cmp-titulo").innerHTML = `Comparação de métodos <span class="dica">· ${esc(d.descricao)}</span>`;
  const linhas = d.metodos.map((m) => `<tr class="${m.metodo === "branch_and_bound" ? "destaque" : ""}">
    <td>${esc(m.metodo_rotulo)}</td><td>${selo(m.status)}</td><td class="n">${fmtObj(m.valor, obj)}</td>
    <td class="n">${m.dif_bb_pct == null ? "—" : (m.dif_bb_pct >= 0 ? "+" : "") + fmt(m.dif_bb_pct, 2) + " %"}</td>
    <td class="n">${fmt(m.tempo, 3)} s</td><td class="n">${esforco(m)}</td>
    <td class="n">${m.n_alimentos ?? "—"}</td><td class="n">${m.custo == null ? "—" : "R$ " + fmt(m.custo)}</td></tr>`).join("");
  $("cmp-tabela").innerHTML = `<thead><tr><th>Método</th><th>Status</th><th class="n">Valor</th><th class="n">Dif. ao B&amp;B</th>
    <th class="n">Tempo</th><th class="n">Esforço</th><th class="n">Alimentos</th><th class="n">Custo</th></tr></thead><tbody>${linhas}</tbody>`;
}

async function iniciar() {
  try {
    OPC = await api("/api/opcoes");
  } catch (e) {
    mostrarErro("Não foi possível carregar as opções: " + e.message);
    return;
  }
  opcoesSelect($("perfil"), OPC.perfis, "nome");
  opcoesSelect($("objetivo"), OPC.objetivos, "rotulo");
  opcoesSelect($("metodo"), OPC.metodos, "rotulo");
  preencherLimites();
  $("perfil").addEventListener("change", preencherLimites);
  $("restaurar").addEventListener("click", preencherLimites);
  $("limites").addEventListener("input", (e) => {
    const i = e.target;
    i.classList.toggle("mudou", i.value !== i.dataset.padrao);
  });
  $("otimizar").addEventListener("click", otimizar);
  $("comparar").addEventListener("click", comparar);

  // ?perfil=atleta&objetivo=custo&metodo=simplex&executar=otimizar|comparar
  // abre a página já com um resultado (útil para apresentar)
  const q = new URLSearchParams(location.search);
  for (const campo of ["perfil", "objetivo", "metodo"]) {
    if (q.has(campo)) $(campo).value = q.get(campo);
  }
  if (q.has("perfil")) preencherLimites();
  if (q.get("executar") === "otimizar") otimizar();
  if (q.get("executar") === "comparar") comparar();
}

iniciar();
