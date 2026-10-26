"""Monta o problema de dieta a partir da tabela de alimentos e de um perfil.

Variável de decisão: x_i = número de porções do alimento i (contínua no
modelo linear, inteira no modelo inteiro). As restrições são

    L_j <= sum_i a_ji x_i <= U_j      para cada nutriente j
    sum_{i em frutas/hortaliças} g_i x_i >= 400 g
    0 <= x_i <= M_i,   x_i = 0 para alimentos excluídos pelo perfil

em que a_ji é a quantidade do nutriente j em uma porção do alimento i.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .perfis import FRUTAS_HORTALICAS_MIN_G, NUTRIENTES, OBJETIVOS, PERFIS
from .problema import ProblemaLP

RAIZ = Path(__file__).resolve().parent.parent
TABELA_PADRAO = RAIZ / "data" / "alimentos.csv"


def carregar_alimentos(caminho: Path | str = TABELA_PADRAO) -> pd.DataFrame:
    df = pd.read_csv(caminho, encoding="utf-8")
    fator = df["porcao_g"] / 100.0
    for col in list(NUTRIENTES) + ["custo_100g"]:
        df[col + "_porcao"] = df[col] * fator
    df["custo_porcao"] = df["custo_100g_porcao"]
    return df


def coeficientes_objetivo(df: pd.DataFrame, objetivo: str) -> tuple[np.ndarray, int]:
    """Devolve (c por porção, sinal) com c sempre no sentido de minimização."""
    _, sentido, coluna = OBJETIVOS[objetivo]
    if coluna == "massa":
        c = df["porcao_g"].to_numpy(float)
    elif coluna == "custo":
        c = df["custo_porcao"].to_numpy(float)
    else:
        c = df[coluna + "_porcao"].to_numpy(float)
    sinal = 1 if sentido == "min" else -1
    return sinal * c, sinal


def construir(perfil: str, objetivo: str = "custo", inteiro: bool = False,
              df: pd.DataFrame | None = None, limites_extra: dict | None = None,
              c_personalizado: np.ndarray | None = None,
              restricoes_extra: list | None = None) -> ProblemaLP:
    """Cria o ProblemaLP para um perfil e uma função objetivo.

    limites_extra substitui limites de nutrientes do perfil (análise de
    sensibilidade). restricoes_extra recebe tuplas (nome, vetor, sentido, rhs)
    já por porção (usado no método epsilon-restrito).
    """
    if df is None:
        df = carregar_alimentos()
    cfg = PERFIS[perfil]
    limites = dict(cfg["limites"])
    if limites_extra:
        limites.update(limites_extra)

    linhas, sentidos, rhs, nomes = [], [], [], []
    for nut, (lo, hi) in limites.items():
        a = df[nut + "_porcao"].to_numpy(float)
        if lo is not None:
            linhas.append(a); sentidos.append(">="); rhs.append(lo); nomes.append(f"{nut}_min")
        if hi is not None:
            linhas.append(a); sentidos.append("<="); rhs.append(hi); nomes.append(f"{nut}_max")
    fh = df["grupo"].isin(["frutas", "hortaliças"]).to_numpy() * df["porcao_g"].to_numpy(float)
    linhas.append(fh); sentidos.append(">="); rhs.append(FRUTAS_HORTALICAS_MIN_G)
    nomes.append("frutas_hortalicas_min")
    for nome, vetor, sentido, valor in restricoes_extra or []:
        linhas.append(np.asarray(vetor, float)); sentidos.append(sentido)
        rhs.append(valor); nomes.append(nome)

    if c_personalizado is not None:
        c, sinal = np.asarray(c_personalizado, float), 1
    else:
        c, sinal = coeficientes_objetivo(df, objetivo)

    ub = df["max_porcoes"].to_numpy(float).copy()
    for tag in cfg["exclui"]:
        ub[df[tag].to_numpy() == 1] = 0.0
    lb = np.zeros(len(df))

    rotulo = OBJETIVOS[objetivo][0] if objetivo in OBJETIVOS else objetivo
    return ProblemaLP(c=c, A=np.array(linhas), sentidos=sentidos, b=np.array(rhs, float),
                      lb=lb, ub=ub, nomes_var=list(df["id"]), nomes_restr=nomes,
                      sinal=sinal, descricao=f"{cfg['nome']} | {rotulo}", inteiro=inteiro,
                      meta={"perfil": perfil, "objetivo": objetivo})


def resumo_nutricional(df: pd.DataFrame, x: np.ndarray) -> dict:
    """Totais diários da dieta x (porções)."""
    tot = {nut: float(df[nut + "_porcao"].to_numpy() @ x) for nut in NUTRIENTES}
    tot["custo"] = float(df["custo_porcao"].to_numpy() @ x)
    tot["massa"] = float(df["porcao_g"].to_numpy() @ x)
    return tot


def cardapio(df: pd.DataFrame, x: np.ndarray, tol: float = 1e-6) -> pd.DataFrame:
    """Tabela legível da dieta: alimento, porções, medida caseira, gramas e custo."""
    sel = x > tol
    out = df.loc[sel, ["nome", "grupo", "medida", "porcao_g", "custo_porcao"]].copy()
    out["porcoes"] = x[sel]
    out["gramas"] = out["porcoes"] * out["porcao_g"]
    out["custo"] = out["porcoes"] * out["custo_porcao"]
    return out[["nome", "grupo", "porcoes", "medida", "gramas", "custo"]].reset_index(drop=True)
