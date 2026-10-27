"use strict";
const $ = (id) => document.getElementById(id);
let OPC = null;
let graficos = [];
let relogio = null;

const UNID_OBJ = { custo: "R$", calorias: "kcal", proteina: "g", fibra: "g", sodio: "mg", gordura: "g", massa: "g" };
const STATUS = {
  otimo: ["Ótimo", "ok"], factivel: ["Factível", "ok"], infactivel: ["Infactível", "ruim"],
  inviavel: ["Inviável", "ruim"], limite: ["Limite atingido", "ruim"], ilimitado: ["Ilimitado", "ruim"],
};
// uma linha sobre cada método: o que faz, contínuo × inteiro, exato × heurístico
const DESC_METODO = {
  simplex: "Programação linear contínua: aceita frações de porção. Método exato e muito rápido; também dá os preços-sombra.",
  branch_and_bound: "Programação linear inteira: só porções inteiras. Divide o problema em ramos e usa o Simplex como limite; exato, mas mais lento.",
  genetico: "Heurística inspirada na evolução: uma população de cardápios inteiros se recombina e sofre mutações. Não garante o ótimo; neste problema é mais lenta que o Branch and Bound, mas não exige modelo linear.",
};
const EXCLUI = {
  carne: "carnes e peixes", animal: "todo produto de origem animal", lactose: "lactose", gluten: "glúten",
};
const TIPO_METODO = {
  simplex: "contínuo · exato", branch_and_bound: "inteiro · exato", genetico: "inteiro · heurístico",
};
const TEMPO_METODO = {
  simplex: "", branch_and_bound: " (costuma levar de 1 a 10 s; limite de 30 s)",
  genetico: " (costuma levar de 7 a 15 s)",
};

const fmt = (v, d = 2) => v == null ? "—" :
  Number(v).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtObj = (v, obj) => v == null ? "—" :
  (UNID_OBJ[obj] === "R$" ? "R$ " + fmt(v) : fmt(v, 1) + " " + (UNID_OBJ[obj] || ""));
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const selo = (st) => { const [t, c] = STATUS[st] || [st, "ruim"]; return `<span class="selo ${c}">${t}</span>`; };
// percentual sem ruído de ponto flutuante: |x| < 0,005 vira "0 %"
const fmtPct = (x, sinal = true) => {
  if (x == null) return "—";
  if (Math.abs(x) < 0.005) return "0 %";
  return (sinal ? (x > 0 ? "+" : "−") : "") + fmt(Math.abs(x), 2) + " %";
};
const fmtTempo = (t) => t == null ? "—" : t < 1 ? fmt(t * 1000, 1) + " ms" : fmt(t, 2) + " s";
const objAtual = () => OPC.objetivos.find((o) => o.id === $("objetivo").value);

function nomeRestricao(nome) {
  if (nome === "frutas_hortalicas_min") return "Frutas e hortaliças (mínimo)";
  const m = nome.match(/^(.*)_(min|max)$/);
  if (!m) return nome;
  const nut = OPC.nutrientes.find((n) => n.id === m[1]);
  return `${nut ? nut.rotulo : m[1]} (${m[2] === "min" ? "mínimo" : "máximo"})`;
}
function unidRestricao(nome) {
  if (nome === "frutas_hortalicas_min") return "g";
  const nut = OPC.nutrientes.find((n) => nome.startsWith(n.id + "_"));
  return nut ? nut.unidade : "";
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
  const ex = p.exclui.map((e) => EXCLUI[e] || e);
  $("perfil-desc").textContent = p.descricao + (ex.length ? ` Exclui: ${ex.join(", ")}.` : "");
  $("limites").innerHTML = OPC.nutrientes.map((n) => {
    const [lo, hi] = p.limites[n.id];
    return `<tr><td>${esc(n.rotulo)}</td>
      <td><input type="number" step="any" min="0" data-nut="${n.id}" data-lado="0" value="${lo ?? ""}" data-padrao="${lo ?? ""}" aria-label="${esc(n.rotulo)} mínimo"></td>
      <td><input type="number" step="any" min="0" data-nut="${n.id}" data-lado="1" value="${hi ?? ""}" data-padrao="${hi ?? ""}" aria-label="${esc(n.rotulo)} máximo"></td>
      <td>${esc(n.unidade)}</td></tr>`;
  }).join("");
}

function descreverMetodo() { $("metodo-desc").textContent = DESC_METODO[$("metodo").value] || ""; }

function lerLimites() {
  const lim = {};
  for (const inp of document.querySelectorAll("#limites input")) {
    const nut = inp.dataset.nut;
    lim[nut] ??= [null, null];
    lim[nut][+inp.dataset.lado] = inp.value.trim() === "" ? null : Number(inp.value);
  }
  return lim;
}

// liga/desliga o estado "ocupado": botões desabilitados e contador de segundos
function ocupado(sim, txt, nota = "") {
  clearInterval(relogio);
  $("carregando").classList.toggle("oculto", !sim);
  $("otimizar").disabled = $("comparar").disabled = sim;
  $("config").setAttribute("aria-busy", sim ? "true" : "false");
  if (!sim) return;
  $("erro").classList.add("oculto");
  $("vazio").classList.add("oculto");
  rolarAte($("carregando"));
  const t0 = Date.now();
  const tique = () => {
    const s = Math.floor((Date.now() - t0) / 1000);
    $("carregando-txt").textContent = `${txt}… ${s} s${nota}`;
  };
  tique();
  relogio = setInterval(tique, 1000);
}

// em tela estreita os resultados ficam abaixo do formulário: rola só se o bloco estiver fora de vista
function rolarAte(el) {
  const r = el.getBoundingClientRect();
  if (r.top > innerHeight * 0.5 || r.bottom < 0) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

// depois de terminar (aviso de progresso já escondido), mostra o resultado ou o erro
function rolarAoResultado() {
  const el = ["erro", "res", "cmp"].map($).find((e) => !e.classList.contains("oculto"));
  if (el) rolarAte(el);
}

function mostrarErro(msg) { $("erro").textContent = msg; $("erro").classList.remove("oculto"); }

async function otimizar() {
  if ($("otimizar").disabled) return;
  const metodo = $("metodo").value;
  ocupado(true, `Resolvendo com ${OPC.metodos.find((m) => m.id === metodo).rotulo}`, TEMPO_METODO[metodo]);
  $("cmp").classList.add("oculto");
  $("res").classList.add("oculto");
  try {
    const d = await api("/api/resolver", { perfil: $("perfil").value, objetivo: $("objetivo").value, metodo, limites: lerLimites() });
    renderResultado(d);
  } catch (e) {
    mostrarErro(e.message);
  } finally {
    ocupado(false);
    rolarAoResultado();
  }
}

function kpi(r, v, t) {
  return `<div class="kpi"${t ? ` title="${esc(t)}"` : ""}><div class="r">${r}</div><div class="v">${v}</div></div>`;
}

function renderResultado(d) {
  const obj = $("objetivo").value;
  $("res").classList.remove("oculto");
  $("res-titulo").innerHTML = `${esc(d.metodo_rotulo)} <span class="dica">· ${esc(d.descricao)}</span>`;
  const resumo = {
    simplex: "Ótimo da versão contínua: as porções podem ser fracionárias.",
    branch_and_bound: d.status === "otimo" ? "Ótimo inteiro comprovado: nenhum cardápio com porções inteiras é melhor."
      : "O tempo limite acabou antes de provar o ótimo; o gap mostra a distância máxima até ele.",
    genetico: "Melhor cardápio inteiro encontrado pela heurística; pode não ser o ótimo (compare com o Branch and Bound).",
  }[d.metodo] || "";
  const semSolucao = ["inviavel", "infactivel", "ilimitado"].includes(d.status);
  $("res-resumo").textContent = semSolucao ? "" : resumo;
  $("res-resumo").classList.toggle("oculto", semSolucao);

  const k = [kpi("Status", selo(d.status)), kpi(esc(objAtual().rotulo), fmtObj(d.valor, obj)),
             kpi("Tempo", fmtTempo(d.tempo))];
  if (d.custo != null && obj !== "custo") k.push(kpi("Custo diário", "R$ " + fmt(d.custo)));
  if (d.metodo === "simplex") k.push(kpi("Iterações (pivôs)", d.iteracoes, "Trocas de base feitas pelo Simplex"));
  if (d.metodo === "branch_and_bound") {
    k.push(kpi("Nós explorados", d.nos ?? "—", "Subproblemas resolvidos na árvore de busca"));
    k.push(kpi("Gap", d.gap == null ? "—" : fmtPct(d.gap * 100, false), "Distância entre a melhor solução e o limite; 0 % = ótimo provado"));
  }
  if (d.metodo === "genetico") {
    k.push(kpi("Gerações", d.iteracoes));
    k.push(kpi("Violação", fmt(d.violacao, 4), "Soma do quanto as restrições foram desrespeitadas; 0 = factível"));
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
  if (d.precos_sombra) renderPrecos(d.precos_sombra, obj, d.sentido, d.valor);

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
  return `<div class="trilho" aria-hidden="true"><div class="faixa" style="left:${a}%;width:${b - a}%"></div>
    <div class="marca ${ok ? "" : "ruim"}" style="left:${pct(v)}%"></div></div>`;
}

// restrição ativa = total igual ao limite (tolerância relativa pequena)
const encosta = (v, lim) => lim != null && Math.abs(v - lim) <= 1e-3 * Math.max(1, Math.abs(lim));

function situacao(v, lo, hi, ok) {
  if (!ok) return '<span class="selo ruim">violado</span>';
  if (encosta(v, lo)) return '<span class="selo ativa">no mínimo</span>';
  if (encosta(v, hi)) return '<span class="selo ativa">no máximo</span>';
  return '<span class="selo ok">ok</span>';
}

function renderTotais(tot, fh) {
  const linha = (rot, v, unid, lo, hi, ok) => {
    const ativa = ok && (encosta(v, lo) || encosta(v, hi));
    return `<tr class="${ativa ? "ativa" : ""}"><td>${esc(rot)}</td><td class="n">${fmt(v, 1)} ${esc(unid)}</td>
      <td class="n">${lo == null ? "—" : fmt(lo, 0)}</td><td class="n">${hi == null ? "—" : fmt(hi, 0)}</td>
      <td class="col-trilho">${trilho(v, lo, hi, ok)}</td><td>${situacao(v, lo, hi, ok)}</td></tr>`;
  };
  const linhas = tot.map((t) => linha(t.rotulo, t.valor, t.unidade, t.min, t.max, t.ok));
  if (fh != null) linhas.push(linha("Frutas e hortaliças", fh, "g", 400, null, fh >= 400 - 1e-3));
  $("totais").innerHTML = `<thead><tr><th>Nutriente</th><th class="n">Total</th><th class="n">Mín.</th><th class="n">Máx.</th>
    <th>Faixa permitida</th><th>Situação</th></tr></thead><tbody>${linhas.join("")}</tbody>`;
}

function renderPrecos(precos, obj, sentido, valor) {
  const u = UNID_OBJ[obj] || "";
  const fmtU = (v, d = 4) => u === "R$" ? "R$ " + fmt(Math.abs(v), d) : fmt(Math.abs(v), d) + " " + u;
  if (!precos.length) {
    $("precos-exemplo").textContent = "";
    $("precos").innerHTML = `<tbody><tr><td class="dica">Nenhuma restrição ativa com preço-sombra não nulo.</td></tr></tbody>`;
    return;
  }
  // impacto = preço-sombra × lado direito: mostra quais restrições pesam mais no valor ótimo
  for (const p of precos) p.impacto = p.preco_sombra * (p.rhs ?? 0);
  precos.sort((a, b) => Math.abs(b.impacto) - Math.abs(a.impacto));
  const p0 = precos[0];
  const un0 = unidRestricao(p0.restricao);
  const piora = (sentido === "min") === (p0.preco_sombra > 0);
  $("precos-exemplo").innerHTML = `Exemplo: a restrição que mais pesa é <b>${esc(nomeRestricao(p0.restricao))}</b>.
    Cada ${esc(un0)} a mais no limite ${p0.preco_sombra > 0 ? "aumenta" : "diminui"} o valor ótimo em só ${fmtU(p0.preco_sombra)},
    mas o limite é ${fmt(p0.rhs, 0)} ${esc(un0)}: ${fmtU(p0.preco_sombra)} × ${fmt(p0.rhs, 0)} ≈ <b>${fmtU(p0.impacto, 2)}</b>
    de impacto no ótimo${piora ? " (afrouxar esse limite melhoraria a dieta)" : ""}.`;

  // o resto vem dos limites de porção x_i <= M_i, cujos duais a API não devolve; pela dualidade forte
  // (valor ótimo = soma de preço × lado direito de todas as restrições) a diferença é exatamente a parte deles
  const sinal = (v) => Math.abs(v) < 0.005 ? "" : v > 0 ? "+" : "−";
  let rodape = "";
  if (valor != null) {
    const resto = valor - precos.reduce((s, p) => s + p.impacto, 0);
    rodape = `<tfoot>${Math.abs(resto) >= 0.005 ? `<tr class="resto"><td>Limites de porção Mᵢ</td><td class="n">xᵢ ≤ Mᵢ</td>
      <td class="n">—</td><td class="n">${sinal(resto)}${fmtU(resto, 2)}</td></tr>` : ""}
      <tr><td colspan="3">Valor ótimo <span class="dica">(a soma fecha pela dualidade forte)</span></td>
      <td class="n">${fmtU(valor, 2)}</td></tr></tfoot>`;
  }
  const corpo = precos.map((p) => `<tr><td>${esc(nomeRestricao(p.restricao))}</td>
    <td class="n">${p.sentido === ">=" ? "≥" : p.sentido === "<=" ? "≤" : "="} ${fmt(p.rhs, 1)} ${esc(unidRestricao(p.restricao))}</td>
    <td class="n">${p.preco_sombra > 0 ? "+" : "−"}${fmtU(p.preco_sombra)}</td>
    <td class="n"><b>${p.impacto > 0 ? "+" : "−"}${fmtU(p.impacto, 2)}</b></td></tr>`).join("");
  $("precos").innerHTML = `<thead><tr><th>Restrição ativa</th><th class="n">Limite</th>
    <th class="n">Efeito de +1 unidade no limite</th><th class="n">Impacto no ótimo (preço × limite)</th></tr></thead><tbody>${corpo}</tbody>${rodape}`;
}

// eixo x logarítmico (geração + 1): a melhora quase toda acontece nas primeiras gerações
function graficoLinha(canvas, curva, campo, cor, rotuloY, extraY) {
  const ultimo = curva.length ? curva[curva.length - 1].geracao + 1 : 1;
  return new Chart(canvas, {
    type: "line",
    data: {
      datasets: [{ label: rotuloY, data: curva.map((c) => ({ x: c.geracao + 1, y: c[campo] })), borderColor: cor,
                   backgroundColor: cor, pointRadius: 0, borderWidth: 2 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false, parsing: false,
      interaction: { mode: "nearest", axis: "x", intersect: false },
      plugins: { legend: { display: false },
                 tooltip: { callbacks: { title: (it) => `Geração ${it[0].parsed.x - 1}` } } },
      scales: {
        x: { type: "logarithmic", min: 1, max: ultimo,
             title: { display: true, text: "Geração + 1 (escala logarítmica)" },
             afterBuildTicks: (ax) => { ax.ticks = [1, 10, 100, 500, 1000].filter((v) => v <= ultimo).map((v) => ({ value: v })); },
             ticks: { callback: (v) => String(v) } },
        y: { title: { display: true, text: rotuloY }, ...extraY },
      },
    },
  });
}

function renderCurva(curva, obj) {
  graficos.forEach((g) => g.destroy());
  graficos = [];
  if (typeof Chart === "undefined") {
    for (const el of $("bloco-curva").querySelectorAll(".grafico"))
      el.innerHTML = '<p class="dica">Chart.js não carregou (sem internet?).</p>';
    return;
  }
  const u = UNID_OBJ[obj] || "";
  graficos.push(graficoLinha($("curva"), curva, "melhor", "#2f7a4f", `Melhor valor (${u})`, {}));
  graficos.push(graficoLinha($("curva-frac"), curva, "frac_factivel", "#8a5a00", "Fração factível", { min: 0, max: 1 }));
}

async function comparar() {
  if ($("comparar").disabled) return;
  ocupado(true, "Comparando os três métodos", " (costuma levar de 10 a 25 s)");
  $("res").classList.add("oculto");
  $("cmp").classList.add("oculto");
  try {
    const d = await api("/api/comparar", { perfil: $("perfil").value, objetivo: $("objetivo").value, limites: lerLimites() });
    renderComparacao(d);
  } catch (e) {
    mostrarErro(e.message);
  } finally {
    ocupado(false);
    rolarAoResultado();
  }
}

function esforco(m) {
  if (m.metodo === "branch_and_bound") return m.nos == null ? "—" : `${m.nos} nós`;
  if (m.metodo === "genetico") return `${m.iteracoes} gerações`;
  return `${m.iteracoes} pivôs`;
}

function difBB(m, bb, obj, sentido) {
  if (m.metodo === "branch_and_bound") return "0 % (referência)";
  if (m.metodo === "simplex") {
    // a relaxação é só um limite: mostra a distância absoluta, não um % (evita duas bases diferentes)
    if (!bb || bb.valor == null || m.valor == null) return "—";
    const dif = bb.valor - m.valor;
    if (Math.abs(dif) < 1e-6) return "limite teórico: igual";
    const lado = m.valor < bb.valor ? "abaixo" : "acima";
    return `limite teórico: ${fmtObj(Math.abs(dif), obj)} ${lado}`;
  }
  return fmtPct(m.dif_bb_pct);
}

function renderComparacao(d) {
  const obj = $("objetivo").value;
  $("cmp").classList.remove("oculto");
  $("cmp-titulo").innerHTML = `Comparação de métodos <span class="dica">· ${esc(d.descricao)}</span>`;
  // melhor valor entre os métodos inteiros factíveis (o Simplex é só o limite)
  const inteiros = d.metodos.filter((m) => m.metodo !== "simplex" && m.valor != null && m.factivel);
  const melhor = inteiros.length ? (d.sentido === "min" ? Math.min : Math.max)(...inteiros.map((m) => m.valor)) : null;
  const bbRef = d.metodos.find((m) => m.metodo === "branch_and_bound");
  const linhas = d.metodos.map((m) => {
    const eMelhor = m.metodo !== "simplex" && melhor != null && m.factivel && Math.abs(m.valor - melhor) < 1e-6;
    const marca = m.metodo === "simplex" ? '<span class="selo limite">limite teórico</span>'
      : eMelhor ? '<span class="selo ok">melhor inteiro</span>' : "";
    return `<tr class="${eMelhor ? "destaque" : ""}">
      <td class="metodo"><b>${esc(m.metodo_rotulo)}</b><br><span class="dica">${TIPO_METODO[m.metodo] || ""}</span> ${marca}</td>
      <td>${selo(m.status)}</td><td class="n"><b>${fmtObj(m.valor, obj)}</b></td>
      <td class="n">${difBB(m, bbRef, obj, d.sentido)}</td><td class="n">${fmtTempo(m.tempo)}</td><td class="n">${esforco(m)}</td>
      <td class="n">${m.n_alimentos ?? "—"}</td>${obj === "custo" ? "" : `<td class="n">${m.custo == null ? "—" : "R$ " + fmt(m.custo)}</td>`}</tr>`;
  }).join("");
  $("cmp-tabela").innerHTML = `<thead><tr><th>Método</th><th>Status</th><th class="n">${esc(d.objetivo)}</th>
    <th class="n">Dif. ao B&amp;B</th><th class="n">Tempo</th><th class="n">Esforço</th><th class="n">Alimentos</th>
    ${obj === "custo" ? "" : '<th class="n">Custo</th>'}</tr></thead><tbody>${linhas}</tbody>`;

  const [lp, bb, ga] = ["simplex", "branch_and_bound", "genetico"].map((id) => d.metodos.find((m) => m.metodo === id));
  const partes = [];
  if (bb && bb.valor != null && lp && lp.valor != null) {
    // relativo ao valor contínuo (Simplex), não ao B&B
    const dl = lp.valor === 0 ? 0 : Math.abs((bb.valor - lp.valor) / Math.abs(lp.valor) * 100);
    partes.push(dl < 0.005 ? "Exigir porções inteiras não mudou o valor em relação à versão contínua (Simplex)."
      : `Exigir porções inteiras piora o valor em ${fmt(dl, 2)} % em relação à versão contínua (Simplex).`);
  }
  if (ga && ga.dif_bb_pct != null && bb && bb.tempo != null && ga.tempo != null) {
    const dg = Math.abs(ga.dif_bb_pct);
    partes.push((dg < 0.005 ? "O Algoritmo Genético encontrou o mesmo valor ótimo inteiro"
      : `O Algoritmo Genético ficou a ${fmt(dg, 2)} % do ótimo inteiro`)
      + ` em ${fmtTempo(ga.tempo)}, contra ${fmtTempo(bb.tempo)} do Branch and Bound.`);
  }
  $("cmp-conclusao").textContent = partes.join(" ");
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
  descreverMetodo();
  $("perfil").addEventListener("change", preencherLimites);
  $("metodo").addEventListener("change", descreverMetodo);
  $("restaurar").addEventListener("click", preencherLimites);
  $("limites").addEventListener("input", (e) => {
    const i = e.target;
    i.classList.toggle("mudou", i.value !== i.dataset.padrao);
  });
  // Enter em qualquer campo (ou o botão Otimizar) envia o formulário
  $("config").addEventListener("submit", (e) => { e.preventDefault(); otimizar(); });
  $("comparar").addEventListener("click", comparar);

  // ?perfil=atleta&objetivo=custo&metodo=simplex&executar=otimizar|comparar
  // abre a página já com um resultado (útil para apresentar)
  const q = new URLSearchParams(location.search);
  for (const campo of ["perfil", "objetivo", "metodo"]) {
    // valor inválido na URL é ignorado (fica o padrão)
    if (q.has(campo) && [...$(campo).options].some((o) => o.value === q.get(campo))) $(campo).value = q.get(campo);
  }
  preencherLimites();
  descreverMetodo();
  if (q.get("executar") === "otimizar") otimizar();
  if (q.get("executar") === "comparar") comparar();
}

iniciar();
