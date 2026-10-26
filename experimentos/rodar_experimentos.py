"""Roda todos os experimentos do trabalho e grava tabelas (resultados/) e figuras (figuras/).

Uso:
    python experimentos/rodar_experimentos.py            # tudo
    python experimentos/rodar_experimentos.py --rapido   # menos sementes do genético

Experimentos:
    E1  Modelo linear (Simplex próprio) para cada perfil x função objetivo.
    E2  Conflito entre funções objetivo (atleta): cada dieta avaliada em todos os critérios.
    E3  Preços-sombra (dual) da dieta de custo mínimo de cada perfil.
    E4  Fronteiras de Pareto pelo método epsilon-restrito e pela soma ponderada.
    E5  Modelo inteiro: Branch and Bound x Genético x CBC.
    E6  Convergência do Genético.
    E7  Cardápios (porções inteiras) de custo mínimo para cada perfil.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from nutriliza import (NUTRIENTES, OBJETIVOS, PERFIS, branch_and_bound, cardapio,  # noqa: E402
                       carregar_alimentos, construir, genetico, resumo_nutricional, simplex)
from nutriliza import referencia  # noqa: E402

RES = RAIZ / "resultados"
FIG = RAIZ / "figuras"
RES.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

# paleta categórica de referência, em ordem fixa
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
TINTA, TINTA2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": TINTA2,
    "axes.labelcolor": TINTA, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRADE, "grid.linewidth": 0.6, "legend.frameon": False,
    "figure.dpi": 150, "savefig.bbox": "tight",
})

PERFIS_CURTOS = {
    "referencia": "Referência", "sobrepeso": "Sobrepeso", "subpeso": "Subpeso",
    "atleta": "Atleta", "vegetariano": "Vegetariano", "vegano": "Vegano",
    "lactose": "Intol. lactose", "celiaco": "Celíaco", "atleta_vegetariano": "Atleta veget.",
}
OBJ_INTEIRO = ["custo", "sodio", "massa"]


def salvar(df: pd.DataFrame, nome: str) -> None:
    df.to_csv(RES / f"{nome}.csv", index=False, encoding="utf-8")
    print(f"  -> resultados/{nome}.csv ({len(df)} linhas)")


def e1_linear(alim: pd.DataFrame) -> pd.DataFrame:
    print("E1 modelo linear")
    linhas = []
    for perfil in PERFIS:
        for obj in OBJETIVOS:
            p = construir(perfil, obj, df=alim)
            r = simplex.resolver(p)
            cbc = referencia.resolver(p, inteiro=False)
            tot = resumo_nutricional(alim, r.x)
            ativas = [p.nomes_restr[i] for i in range(p.m) if abs(r.duais[i]) > 1e-7]
            linhas.append({"perfil": perfil, "objetivo": obj, "status": r.status,
                           "valor": r.valor, "valor_cbc": cbc.valor,
                           "iteracoes": r.iteracoes, "tempo_ms": r.tempo * 1000,
                           "n_alimentos": int((r.x > 1e-6).sum()),
                           "restricoes_ativas": ";".join(ativas), **tot})
    df = pd.DataFrame(linhas)
    salvar(df, "e1_linear")
    return df


def e2_conflito(alim: pd.DataFrame, e1: pd.DataFrame) -> pd.DataFrame:
    print("E2 conflito entre funções objetivo")
    df = e1[e1.perfil == "atleta"][["objetivo", "custo", "kcal", "proteina", "fibra",
                                    "sodio", "gordura", "massa", "n_alimentos"]]
    salvar(df, "e2_conflito_atleta")
    return df


def e3_duais(alim: pd.DataFrame) -> pd.DataFrame:
    print("E3 preços-sombra")
    linhas = []
    for perfil in PERFIS:
        p = construir(perfil, "custo", df=alim)
        r = simplex.resolver(p)
        for i, nome in enumerate(p.nomes_restr):
            if abs(r.duais[i]) > 1e-7:
                linhas.append({"perfil": perfil, "restricao": nome, "rhs": p.b[i],
                               "preco_sombra": r.duais[i]})
    df = pd.DataFrame(linhas)
    salvar(df, "e3_duais_custo")
    return df


def e4_pareto(alim: pd.DataFrame) -> dict:
    print("E4 fronteiras de Pareto")
    prot = alim["proteina_porcao"].to_numpy()
    sod = alim["sodio_porcao"].to_numpy()
    custo = alim["custo_porcao"].to_numpy()
    saida = {}
    linhas = []
    # (a) custo x proteína pelo epsilon-restrito: min custo s.a. proteína >= eps
    for perfil in ["atleta", "atleta_vegetariano", "vegano"]:
        lo, hi = PERFIS[perfil]["limites"]["proteina"]
        for eps in np.linspace(lo, hi, 21):
            p = construir(perfil, "custo", df=alim, limites_extra={"proteina": (eps, hi)})
            r = simplex.resolver(p)
            if r.status != "otimo":
                continue
            i = p.nomes_restr.index("proteina_min")
            linhas.append({"fronteira": "custo_proteina", "perfil": perfil, "eps": eps,
                           "custo": r.valor, "proteina": float(prot @ r.x),
                           "sodio": float(sod @ r.x), "dual": r.duais[i]})
    # (b) custo x sódio (referência): epsilon-restrito e soma ponderada
    p0 = construir("referencia", "sodio", df=alim)
    na_min = simplex.resolver(p0).valor
    for eps in np.geomspace(na_min, 2000, 30):
        p = construir("referencia", "custo", df=alim, limites_extra={"sodio": (None, eps)})
        r = simplex.resolver(p)
        linhas.append({"fronteira": "custo_sodio", "perfil": "referencia", "eps": eps,
                       "custo": r.valor, "proteina": float(prot @ r.x),
                       "sodio": float(sod @ r.x), "dual": np.nan})
    c_ref = simplex.resolver(construir("referencia", "custo", df=alim)).valor
    for w in np.linspace(0, 1, 11):
        c = w * custo / c_ref + (1 - w) * sod / na_min
        p = construir("referencia", f"ponderada_w{w:.1f}", df=alim, c_personalizado=c)
        r = simplex.resolver(p)
        linhas.append({"fronteira": "ponderada", "perfil": "referencia", "eps": w,
                       "custo": float(custo @ r.x), "proteina": float(prot @ r.x),
                       "sodio": float(sod @ r.x), "dual": np.nan})
    df = pd.DataFrame(linhas)
    salvar(df, "e4_pareto")

    fig, axs = plt.subplots(1, 2, figsize=(9, 3.4))
    ax = axs[0]
    for k, perfil in enumerate(["atleta", "atleta_vegetariano", "vegano"]):
        d = df[(df.fronteira == "custo_proteina") & (df.perfil == perfil)]
        ax.plot(d.proteina, d.custo, "-o", color=CORES[k], lw=2, ms=4,
                label=PERFIS_CURTOS.get(perfil, perfil))
    ax.set_xlabel("Proteína da dieta (g/dia)")
    ax.set_ylabel("Custo mínimo (R$/dia)")
    ax.set_title("(a) Custo × proteína (ε-restrito)", loc="left", fontsize=9)
    ax.legend()
    ax = axs[1]
    d = df[df.fronteira == "custo_sodio"]
    ax.plot(d.sodio, d.custo, "-", color=CORES[0], lw=2, label="ε-restrito")
    d = df[df.fronteira == "ponderada"]
    ax.plot(d.sodio, d.custo, "o", color=CORES[1], ms=6, mec="white", mew=1.5,
            label="Soma ponderada")
    ax.set_xscale("log")
    ax.set_xticks([25, 50, 100, 250, 500, 1000, 2000], ["25", "50", "100", "250", "500", "1.000", "2.000"])
    ax.minorticks_off()
    ax.set_xlabel("Sódio (mg/dia, escala log)")
    ax.set_ylabel("Custo (R$/dia)")
    ax.set_title("(b) Custo × sódio, adulto de referência", loc="left", fontsize=9)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "pareto.png")
    plt.close(fig)
    saida["pareto"] = df
    return saida


def e5_inteiro(alim: pd.DataFrame, sementes: int) -> tuple[pd.DataFrame, dict]:
    print("E5 modelo inteiro: B&B x Genético x CBC")
    linhas, curvas = [], {}
    for perfil in PERFIS:
        for obj in OBJ_INTEIRO:
            p = construir(perfil, obj, inteiro=True, df=alim)
            lp = simplex.resolver(p)
            bb = branch_and_bound.resolver(p, tempo_limite=120)
            cbc = referencia.resolver(p)
            ga_vals, ga_tempos = [], []
            for s in range(sementes):
                g = genetico.resolver(p, semente=s)
                ga_vals.append(g.valor if g.valor is not None else np.nan)
                ga_tempos.append(g.tempo)
                if perfil == "atleta" and obj == "custo":
                    curvas[s] = g.extra["curva"]
            ga = np.array(ga_vals)
            otimo = bb.valor
            linhas.append({
                "perfil": perfil, "objetivo": obj, "lp": lp.valor,
                "bb": bb.valor, "bb_status": bb.status, "bb_nos": bb.extra["nos"],
                "bb_tempo_s": bb.tempo, "cbc": cbc.valor,
                "ga_melhor": np.nanmin(ga), "ga_media": np.nanmean(ga), "ga_dp": np.nanstd(ga),
                "ga_pior": np.nanmax(ga), "ga_factiveis": int(np.isfinite(ga).sum()),
                "ga_otimo_pct": float(np.mean(np.abs(ga - otimo) <= 1e-6 * max(1, abs(otimo)))) * 100,
                "ga_gap_medio_pct": float(np.nanmean((ga - otimo) / abs(otimo))) * 100,
                "ga_tempo_s": float(np.mean(ga_tempos)),
                "gap_integralidade_pct": (bb.valor - lp.valor) / abs(bb.valor) * 100,
            })
            print(f"  {perfil:20s}{obj:7s} LP={lp.valor:9.3f} B&B={bb.valor:9.3f} "
                  f"({bb.extra['nos']} nós, {bb.tempo:.1f}s) CBC={cbc.valor:9.3f} "
                  f"GA={np.nanmean(ga):9.3f}±{np.nanstd(ga):.3f}", flush=True)
    df = pd.DataFrame(linhas)
    salvar(df, "e5_inteiro")

    fig, ax = plt.subplots(figsize=(9, 3.2))
    perfis = list(PERFIS)
    larg = 0.26
    xs = np.arange(len(perfis))
    for k, obj in enumerate(OBJ_INTEIRO):
        d = df[df.objetivo == obj].set_index("perfil").loc[perfis]
        ax.bar(xs + (k - 1) * larg, d.ga_gap_medio_pct, larg - 0.03, color=CORES[k],
               label=OBJETIVOS[obj][0], edgecolor="white", linewidth=1)
    ax.set_xticks(xs, [PERFIS_CURTOS[p] for p in perfis], rotation=20, ha="right")
    ax.set_ylabel("Desvio médio do Genético\nem relação ao ótimo (%)")
    ax.legend(ncols=3, loc="upper left")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(FIG / "gap_genetico.png")
    plt.close(fig)
    return df, curvas


def e6_convergencia(curvas: dict, otimo: float) -> None:
    print("E6 convergência do Genético")
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.2))
    for s, curva in curvas.items():
        c = np.array(curva, dtype=float)
        rotulo = "Sementes" if s == 0 else None
        axs[0].plot(c[:, 0], c[:, 1], color=CORES[0], lw=1, alpha=0.45, label=rotulo)
        axs[1].plot(c[:, 0], c[:, 3] * 100, color=CORES[0], lw=1, alpha=0.45, label=rotulo)
    axs[0].axhline(otimo, color=TINTA, lw=1.2, ls="--", label="Ótimo (Branch and Bound)")
    axs[0].set_xlabel("Geração")
    axs[0].set_ylabel("Custo do melhor factível (R$/dia)")
    axs[0].set_title("(a) Melhor indivíduo", loc="left", fontsize=9)
    axs[0].legend()
    axs[1].set_xlabel("Geração")
    axs[1].set_ylabel("População factível (%)")
    axs[1].set_title("(b) Factibilidade da população", loc="left", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "convergencia_genetico.png")
    plt.close(fig)


def e7_cardapios(alim: pd.DataFrame) -> pd.DataFrame:
    print("E7 cardápios de custo mínimo (porções inteiras)")
    linhas, md = [], ["# Cardápios de custo mínimo (porções inteiras)\n",
                      "Gerados por Branch and Bound sobre o modelo inteiro. "
                      "Valores diários; custos em R$ com as premissas de preço de data/alimentos.csv.\n"]
    grupos = sorted(alim.grupo.unique())
    comp = {}
    for perfil, cfg in PERFIS.items():
        p = construir(perfil, "custo", inteiro=True, df=alim)
        r = branch_and_bound.resolver(p, tempo_limite=120)
        card = cardapio(alim, r.x)
        tot = resumo_nutricional(alim, r.x)
        for _, row in card.iterrows():
            linhas.append({"perfil": perfil, **row.to_dict()})
        kc = alim["kcal_porcao"].to_numpy() * r.x
        comp[perfil] = {g: kc[(alim.grupo == g).to_numpy()].sum() for g in grupos}
        md.append(f"\n## {cfg['nome']}\n\n{cfg['descricao']}\n")
        md.append("| Alimento | Porções | Medida caseira | Gramas | Custo (R$) |")
        md.append("|---|---:|---|---:|---:|")
        for _, row in card.iterrows():
            md.append(f"| {row.nome} | {row.porcoes:.0f} | {row.medida} | {row.gramas:.0f} | "
                      f"{row.custo:.2f} |")
        md.append(f"\n**Total:** R$ {tot['custo']:.2f}; {tot['kcal']:.0f} kcal; "
                  f"proteína {tot['proteina']:.0f} g; carboidrato {tot['carboidrato']:.0f} g; "
                  f"gordura {tot['gordura']:.0f} g; fibra {tot['fibra']:.0f} g; "
                  f"cálcio {tot['calcio']:.0f} mg; ferro {tot['ferro']:.1f} mg; "
                  f"sódio {tot['sodio']:.0f} mg; vitamina C {tot['vitamina_c']:.0f} mg.\n")
    df = pd.DataFrame(linhas)
    salvar(df, "e7_cardapios")
    (RES / "cardapios.md").write_text("\n".join(md), encoding="utf-8")

    # composição energética por grupo (barras empilhadas, 2px de espaço entre segmentos)
    c = pd.DataFrame(comp).T.loc[list(PERFIS)]
    c = c.loc[:, c.sum() > 0]
    ordem = c.sum().sort_values(ascending=False).index
    principais = list(ordem[:7])
    c["outros"] = c.drop(columns=principais).sum(axis=1)
    c = c[principais + ["outros"]]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    base = np.zeros(len(c))
    ys = np.arange(len(c))
    for k, g in enumerate(c.columns):
        ax.barh(ys, c[g], left=base, color=CORES[k] if g != "outros" else "#b5b3ad",
                edgecolor="white", linewidth=1.5, label=g.capitalize(), height=0.7)
        base += c[g].to_numpy()
    ax.set_yticks(ys, [PERFIS_CURTOS[p] for p in c.index])
    ax.invert_yaxis()
    ax.set_xlabel("Energia (kcal/dia) por grupo de alimentos")
    ax.legend(ncols=4, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(FIG / "composicao_cardapios.png")
    plt.close(fig)
    return df


def figura_custos(e1: pd.DataFrame) -> None:
    d = e1[e1.objetivo == "custo"].set_index("perfil").loc[list(PERFIS)]
    fig, ax = plt.subplots(figsize=(6, 2.8))
    ys = np.arange(len(d))
    ax.barh(ys, d.custo, color=CORES[0], height=0.6)
    for y, v in zip(ys, d.custo):
        ax.text(v + 0.15, y, f"R$ {v:.2f}".replace(".", ","), va="center", color=TINTA2, fontsize=8)
    ax.set_yticks(ys, [PERFIS_CURTOS[p] for p in d.index])
    ax.invert_yaxis()
    ax.set_xlabel("Custo mínimo da dieta (R$/dia), modelo linear")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, d.custo.max() * 1.18)
    fig.tight_layout()
    fig.savefig(FIG / "custo_por_perfil.png")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapido", action="store_true", help="3 sementes no genético em vez de 10")
    args = ap.parse_args()
    alim = carregar_alimentos()
    e1 = e1_linear(alim)
    figura_custos(e1)
    e2_conflito(alim, e1)
    e3_duais(alim)
    e4_pareto(alim)
    e7_cardapios(alim)
    e5, curvas = e5_inteiro(alim, 3 if args.rapido else 10)
    otimo = float(e5[(e5.perfil == "atleta") & (e5.objetivo == "custo")].bb.iloc[0])
    e6_convergencia(curvas, otimo)
    resumo = {
        "simplex_igual_cbc": bool(np.allclose(e1.valor, e1.valor_cbc, rtol=1e-6)),
        "bb_igual_cbc": bool(np.allclose(e5.bb, e5.cbc, rtol=1e-6)),
        "ga_gap_medio_pct": float(e5.ga_gap_medio_pct.mean()),
        "ga_otimo_pct": float(e5.ga_otimo_pct.mean()),
    }
    (RES / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumo, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
