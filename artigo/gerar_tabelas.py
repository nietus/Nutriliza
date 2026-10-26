"""Gera as tabelas LaTeX do artigo (artigo/tabelas/*.tex) a partir de resultados/."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from nutriliza import OBJETIVOS, PERFIS  # noqa: E402

RES = RAIZ / "resultados"
OUT = Path(__file__).resolve().parent / "tabelas"
OUT.mkdir(exist_ok=True)

CURTO = {"referencia": "Referência", "sobrepeso": "Sobrepeso", "subpeso": "Subpeso",
         "atleta": "Atleta", "vegetariano": "Vegetariano", "vegano": "Vegano",
         "lactose": "Intol. à lactose", "celiaco": "Celíaco", "atleta_vegetariano": "Atleta vegetariano"}


def br(v, casas=2):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", "{,}").replace("X", ".")


def lim(par):
    lo, hi = par
    if lo is None:
        return f"$\\leq$ {br(hi, 0)}"
    if hi is None:
        return f"$\\geq$ {br(lo, 0)}"
    return f"{br(lo, 0)}--{br(hi, 0)}"


def cientifico(v):
    """1,2 \\cdot 10^{-5} em LaTeX."""
    m, e = f"{v:.1e}".split("e")
    return f"${m.replace('.', '{,}')} \\cdot 10^{{{int(e)}}}$"


def escrever(nome, linhas):
    (OUT / f"{nome}.tex").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def perfis():
    exc = {"carne": "carnes", "animal": "prod. animais", "lactose": "lactose", "gluten": "glúten"}
    L = [r"\begin{tabular}{lcccccl}", r"\toprule",
         r"Perfil & Energia (kcal) & Prot. (g) & Carb. (g) & Gord. (g) & Ferro (mg) & Exclui \\",
         r"\midrule"]
    for k, cfg in PERFIS.items():
        l = cfg["limites"]
        L.append(f"{CURTO[k]} & {lim(l['kcal'])} & {lim(l['proteina'])} & {lim(l['carboidrato'])} & "
                 f"{lim(l['gordura'])} & {lim(l['ferro'])} & "
                 f"{exc[cfg['exclui'][0]] if cfg['exclui'] else '--'} \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    escrever("perfis", L)


def custo_lp():
    e1 = pd.read_csv(RES / "e1_linear.csv")
    d = e1[e1.objetivo == "custo"].set_index("perfil")
    L = [r"\begin{tabular}{lrrrrrrr}", r"\toprule",
         r"Perfil & Custo (R\$) & kcal & Prot. (g) & Fibra (g) & Ferro (mg) & Sódio (mg) & Pivôs \\",
         r"\midrule"]
    for p in PERFIS:
        r = d.loc[p]
        L.append(f"{CURTO[p]} & {br(r.custo)} & {br(r.kcal, 0)} & {br(r.proteina, 0)} & "
                 f"{br(r.fibra, 0)} & {br(r.ferro, 1)} & {br(r.sodio, 0)} & {r.iteracoes} \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    escrever("custo_lp", L)


def conflito():
    e2 = pd.read_csv(RES / "e2_conflito_atleta.csv")
    L = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
         r"Função objetivo & Custo (R\$) & kcal & Prot. (g) & Fibra (g) & Sódio (mg) & Peso (g) \\",
         r"\midrule"]
    for r in e2.itertuples():
        nome = OBJETIVOS[r.objetivo][0].split(" (")[0]
        L.append(f"{nome} & {br(r.custo)} & {br(r.kcal, 0)} & {br(r.proteina, 0)} & {br(r.fibra, 0)} & "
                 f"{br(r.sodio, 0)} & {br(r.massa, 0)} \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    escrever("conflito", L)


def duais():
    e3 = pd.read_csv(RES / "e3_duais_custo.csv")
    piv = e3.pivot_table(index="restricao", columns="perfil", values="preco_sombra")
    perfis_ = ["referencia", "sobrepeso", "atleta", "vegetariano", "vegano", "atleta_vegetariano"]
    rot = {"kcal_min": "Energia mín. (kcal)", "proteina_min": "Proteína mín. (g)",
           "carboidrato_max": "Carboidrato máx. (g)", "gordura_min": "Gordura mín. (g)",
           "calcio_min": "Cálcio mín. (mg)", "ferro_min": "Ferro mín. (mg)",
           "frutas_hortalicas_min": "Frutas e hortaliças (g)"}
    cab = " & ".join(["Restrição"] + [CURTO[p].replace("Atleta vegetariano", "Atl. veg.") for p in perfis_])
    L = [r"\begin{tabular}{lrrrrrr}", r"\toprule", cab + r" \\", r"\midrule"]
    for r, nome in rot.items():
        if r not in piv.index:
            continue
        vals = []
        for p in perfis_:
            v = piv.loc[r].get(p)
            if pd.isna(v):
                vals.append("--")
            elif abs(v) < 5e-5:
                vals.append("$<$0{,}0001")
            else:
                vals.append(br(v, 4))
        L.append(nome + " & " + " & ".join(vals) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    escrever("duais", L)


ROT_IMPACTO = {"kcal_min": "Energia mínima", "proteina_min": "Proteína mínima",
               "carboidrato_max": "Carboidrato máximo", "gordura_min": "Gordura mínima",
               "calcio_min": "Cálcio mínimo", "ferro_min": "Ferro mínimo",
               "frutas_hortalicas_min": "Frutas e hortaliças"}


def impacto():
    """Preço-sombra x limite: parcela do custo ótimo atribuída a cada restrição."""
    e3 = pd.read_csv(RES / "e3_duais_custo.csv")
    piv = e3.pivot_table(index="restricao", columns="perfil", values="impacto")
    perfis_ = ["referencia", "sobrepeso", "subpeso", "atleta", "vegetariano", "vegano"]
    L = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
         " & ".join(["Restrição"] + [CURTO[p] for p in perfis_]) + r" \\", r"\midrule"]
    for r, nome in ROT_IMPACTO.items():
        if r not in piv.index:
            continue
        L.append(nome + " & " + " & ".join(
            "--" if pd.isna(piv.loc[r].get(p)) else br(piv.loc[r][p]) for p in perfis_) + r" \\")
    # pela dualidade forte, custo = soma(y·b) + parcela dos limites de porção x_i <= M_i
    e1 = pd.read_csv(RES / "e1_linear.csv")
    custo = e1[e1.objetivo == "custo"].set_index("perfil").custo
    L.append("Limites de porção $M_i$ & " + " & ".join(br(custo[p] - piv[p].sum()) for p in perfis_) + r" \\")
    L += [r"\midrule", "Custo ótimo & " + " & ".join(br(custo[p]) for p in perfis_) + r" \\",
          r"\bottomrule", r"\end{tabular}"]
    escrever("impacto", L)


def inteiro():
    e5 = pd.read_csv(RES / "e5_inteiro.csv")
    d = e5[e5.objetivo == "custo"].set_index("perfil")
    L = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
         r"Perfil & LP & B\&B & Nós & B\&B (s) & AG média $\pm$ dp & AG no ótimo \\", r"\midrule"]
    for p in PERFIS:
        r = d.loc[p]
        L.append(f"{CURTO[p]} & {br(r.lp)} & {br(r.bb)} & {r.bb_nos} & {br(r.bb_tempo_s, 1)} & "
                 f"{br(r.ga_media)} $\\pm$ {br(r.ga_dp)} & {br(r.ga_otimo_pct, 0)}\\% \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    escrever("inteiro", L)

    # resumo por função objetivo (todas as 27 instâncias)
    nomes = {"custo": "Custo", "sodio": "Sódio", "massa": "Peso total"}
    L = [r"\begin{tabular}{lrrrrr}", r"\toprule",
         r"Objetivo & Integralidade & Nós B\&B & AG: desvio médio & AG: pior execução & AG no ótimo \\",
         r"\midrule"]
    for obj, nome in nomes.items():
        x = e5[e5.objetivo == obj]
        L.append(f"{nome} & {br(x.gap_integralidade_pct.mean(), 1)}\\% & {br(x.bb_nos.mean(), 0)} & "
                 f"{br(x.ga_gap_medio_pct.mean(), 1)}\\% & {br(x.ga_pior_gap_pct.max(), 1)}\\% & "
                 f"{br(x.ga_otimo_pct.mean(), 0)}\\% \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    escrever("inteiro_resumo", L)


def tempos():
    e1 = pd.read_csv(RES / "e1_linear.csv")
    e5 = pd.read_csv(RES / "e5_inteiro.csv")
    L = [r"\begin{tabular}{llrrrr}", r"\toprule",
         r"Método & Modelo & Execuções & Tempo médio & Tempo máximo & Ótimo atingido \\", r"\midrule",
         f"Simplex & linear & {len(e1)} & {br(e1.tempo_ms.mean(), 1)} ms & {br(e1.tempo_ms.max(), 1)} ms"
         r" & 100\% \\",
         f"Branch and Bound & inteiro & {len(e5)} & {br(e5.bb_tempo_s.mean(), 1)} s & "
         f"{br(e5.bb_tempo_s.max(), 1)} s" r" & 100\% \\",
         f"Algoritmo Genético & inteiro & {len(e5) * 10} & {br(e5.ga_tempo_s.mean(), 1)} s & "
         f"{br(e5.ga_tempo_s.max(), 1)} s & {br(e5.ga_otimo_pct.mean(), 0)}" r"\% \\",
         r"\bottomrule", r"\end{tabular}"]
    escrever("tempos", L)


def cardapio():
    e7 = pd.read_csv(RES / "e7_cardapios.csv")
    perfis_ = ["sobrepeso", "atleta", "vegano"]
    L = [r"\begin{tabular}{lll}", r"\toprule",
         " & ".join(CURTO[p] for p in perfis_) + r" \\", r"\midrule"]
    colunas = [[f"{int(round(r.porcoes))}$\\times$ {r.nome.lower()}" for r in e7[e7.perfil == p].itertuples()]
               for p in perfis_]
    for i in range(max(map(len, colunas))):
        L.append(" & ".join(c[i] if i < len(c) else "" for c in colunas) + r" \\")
    tot = e7.groupby("perfil").custo.sum()
    L += [r"\midrule", " & ".join(f"Total: R\\$ {br(tot[p])}" for p in perfis_) + r" \\",
          r"\bottomrule", r"\end{tabular}"]
    escrever("cardapio", L)


def preencher_texto():
    """Preenche os %%MARCADORES%% de artigo_modelo.tex e grava artigo.tex."""
    e1 = pd.read_csv(RES / "e1_linear.csv")
    e2 = pd.read_csv(RES / "e2_conflito_atleta.csv").set_index("objetivo")
    e3 = pd.read_csv(RES / "e3_duais_custo.csv")
    e5 = pd.read_csv(RES / "e5_inteiro.csv")
    c = e1[e1.objetivo == "custo"].set_index("perfil").custo
    piv = e3.pivot_table(index="restricao", columns="perfil", values="preco_sombra")
    dpa, dpv = piv.loc["proteina_min", "atleta"], piv.loc["proteina_min", "atleta_vegetariano"]
    imp = e3.pivot_table(index="restricao", columns="perfil", values="impacto")
    e4 = pd.read_csv(RES / "e4_pareto.csv")
    par = e4[e4.fronteira == "custo_proteina"]
    par_v, par_a = par[par.perfil == "vegano"], par[par.perfil == "atleta"]
    valores = {
        "GA_GAP": br(e5.ga_gap_medio_pct.mean(), 1), "GA_OTIMO": br(e5.ga_otimo_pct.mean(), 0),
        "GA_TEMPO": br(e5.ga_tempo_s.mean(), 1), "BB_NOS": br(e5.bb_nos.mean(), 0),
        "BB_TEMPO": br(e5.bb_tempo_s.mean(), 1), "GAP_INT": br(e5[e5.objetivo == "custo"].gap_integralidade_pct.mean(), 1),
        "PIVOS": br(e1.iteracoes.mean(), 0), "TEMPO_LP": br(e1.tempo_ms.mean(), 1),
        "CUSTO_REF": br(c["referencia"]), "CUSTO_ATL": br(c["atleta"]),
        "CUSTO_ATLV": br(c["atleta_vegetariano"]),
        "ATL_PCT": br((c["atleta"] / c["referencia"] - 1) * 100, 0),
        "CUSTO_PROT": br(e2.loc["proteina", "custo"]), "SODIO_MASSA": br(e2.loc["massa", "sodio"], 0),
        "DUAL_PROT_ATL": br(dpa, 3), "DUAL_PROT_ATLV": br(dpv, 3),
        "DUAL_PROT_PCT": br((dpv / dpa - 1) * 100, 0),
        "DUAL_FE_REF": br(piv.loc["ferro_min", "referencia"], 3),
        "DUAL_FE_VEG": br(piv.loc["ferro_min", "vegetariano"], 3),
        "GA_GAP_CUSTO": br(e5[e5.objetivo == "custo"].ga_gap_medio_pct.mean(), 1),
        "GA_GAP_SODIO": br(e5[e5.objetivo == "sodio"].ga_gap_medio_pct.mean(), 1),
        "GA_GAP_MASSA": br(e5[e5.objetivo == "massa"].ga_gap_medio_pct.mean(), 1),
        "GA_GAP_MAX": br(e5.ga_gap_medio_pct.max(), 1),
        "GA_EXEC": br(e5.ga_factiveis.sum(), 0),
        "BB_NOS_MAX": br(e5.bb_nos.max(), 0),
        "BB_TEMPO_MAX": br(e5.bb_tempo_s.max(), 1),
        "GAP_INT_TODOS": br(e5.gap_integralidade_pct.mean(), 1),
        "GA_PIOR_EXEC": br(e5.ga_pior_gap_pct.max(), 1),
        "BB_MAIS_RAPIDO": str(int((e5.bb_tempo_s < e5.ga_tempo_s).sum())),
        "DIF_VALOR_MAX": cientifico(e1.dif_valor_abs.max()),
        "DIF_DUAIS_MAX": cientifico(e1.dif_duais_abs.max()),
        "EN_REF_IMP": br(imp.loc["kcal_min", "referencia"]),
        "EN_REF_PCT": br(imp.loc["kcal_min", "referencia"] / c["referencia"] * 100, 0),
        "EN_SUB_IMP": br(imp.loc["kcal_min", "subpeso"]),
        "EN_SUB_PCT": br(imp.loc["kcal_min", "subpeso"] / c["subpeso"] * 100, 0),
        "FE_VEG_IMP": br(imp.loc["ferro_min", "vegetariano"]),
        "CA_VEG_IMP": br(imp.loc["calcio_min", "vegetariano"]),
        "FE_VGN_IMP": br(imp.loc["ferro_min", "vegano"]),
        "CA_VGN_IMP": br(imp.loc["calcio_min", "vegano"]),
        "PROT_ATL_IMP": br(imp.loc["proteina_min", "atleta"]),
        "PIVOS_REF": str(int(e1[(e1.perfil == "referencia") & (e1.objetivo == "custo")].iteracoes.iloc[0])),
        "PIVOS_VGN": str(int(e1[(e1.perfil == "vegano") & (e1.objetivo == "custo")].iteracoes.iloc[0])),
        "PIVOS_CEL": str(int(e1[(e1.perfil == "celiaco") & (e1.objetivo == "custo")].iteracoes.iloc[0])),
        "PARETO_VGN_INI": br(par_v.dual.min(), 3), "PARETO_VGN_FIM": br(par_v.dual.max(), 3),
        "PARETO_ATL_INI": br(par_a.dual.min(), 3), "PARETO_ATL_FIM": br(par_a.dual.max(), 3),
        "PARETO_VGN_C0": br(par_v.custo.min()), "PARETO_VGN_C1": br(par_v.custo.max()),
        "PARETO_VGN_P1": br(par_v.proteina.max(), 0),
    }
    pasta = Path(__file__).resolve().parent
    texto = (pasta / "artigo_modelo.tex").read_text(encoding="utf-8")
    for k, v in valores.items():
        texto = texto.replace(f"%%{k}%%", v)
    # no abstract (inglês) o separador decimal é ponto
    abstract_ini = texto.index(r"\begin{abstract}")
    abstract_fim = texto.index(r"\end{abstract}")
    trecho = texto[abstract_ini:abstract_fim].replace("{,}", ".")
    texto = texto[:abstract_ini] + trecho + texto[abstract_fim:]
    assert "%%" not in texto, "marcador sem valor"
    (pasta / "artigo.tex").write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    perfis(); custo_lp(); conflito(); duais(); impacto(); inteiro(); tempos(); cardapio()
    preencher_texto()
    print("tabelas e artigo.tex gerados em", OUT.parent)
