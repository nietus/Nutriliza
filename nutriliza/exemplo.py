"""Exemplo usado no texto: a porção mais fracionária da dieta linear do atleta.

O Branch and Bound ramifica primeiro nessa variável, então ela ilustra tanto a
diferença entre o modelo linear e o inteiro quanto o primeiro passo da árvore.
"""
from __future__ import annotations

import numpy as np

from . import simplex
from .modelo import carregar_alimentos, construir


def porcao_mais_fracionaria(perfil: str = "atleta", objetivo: str = "custo", df=None) -> dict:
    df = carregar_alimentos() if df is None else df
    r = simplex.resolver(construir(perfil, objetivo, df=df))
    frac = np.abs(r.x - np.round(r.x))
    j = int(np.argmin(np.abs(frac - 0.5) + (frac <= 1e-6) * 10))
    linha = df.iloc[j]
    return {"nome": linha["nome"], "valor": float(r.x[j]), "medida": linha["medida"],
            "piso": int(np.floor(r.x[j])), "teto": int(np.ceil(r.x[j])), "valor_lp": r.valor}
