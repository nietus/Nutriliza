"""Resolve o mesmo ProblemaLP com o CBC (via PuLP) para validar os solvers próprios."""
from __future__ import annotations

import time

import numpy as np
import pulp

from .problema import ProblemaLP, Resultado


def resolver(p: ProblemaLP, inteiro: bool | None = None, tempo_limite: int = 120) -> Resultado:
    inteiro = p.inteiro if inteiro is None else inteiro
    t0 = time.perf_counter()
    prob = pulp.LpProblem("dieta", pulp.LpMinimize)
    cat = pulp.LpInteger if inteiro else pulp.LpContinuous
    x = [pulp.LpVariable(f"x{j}", lowBound=p.lb[j], upBound=p.ub[j], cat=cat) for j in range(p.n)]
    prob += pulp.lpSum(p.c[j] * x[j] for j in range(p.n))
    for i in range(p.m):
        expr = pulp.lpSum(p.A[i, j] * x[j] for j in range(p.n) if p.A[i, j] != 0)
        if p.sentidos[i] == ">=":
            prob += expr >= p.b[i], f"r{i}"
        elif p.sentidos[i] == "<=":
            prob += expr <= p.b[i], f"r{i}"
        else:
            prob += expr == p.b[i], f"r{i}"
    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=tempo_limite))
    tempo = time.perf_counter() - t0
    st = pulp.LpStatus[prob.status]
    if st != "Optimal":
        return Resultado("inviavel" if st == "Infeasible" else st.lower(), tempo=tempo, metodo="cbc")
    xv = np.array([v.value() or 0.0 for v in x])
    duais = None
    if not inteiro:
        duais = np.array([prob.constraints[f"r{i}"].pi or 0.0 for i in range(p.m)]) * p.sinal
    return Resultado("otimo", x=xv, valor=p.valor(xv), duais=duais, tempo=tempo, metodo="cbc")
