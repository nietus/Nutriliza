"""Método Simplex de duas fases (tableau), implementado do zero.

Etapas:
1. Desloca as variáveis pelos limites inferiores (x = lb + x') e transforma
   os limites superiores finitos em restrições x'_j <= ub_j - lb_j.
2. Deixa todo lado direito não negativo (invertendo a linha quando preciso)
   e acrescenta folgas, excessos e variáveis artificiais.
3. Fase 1 minimiza a soma das artificiais; se o mínimo for positivo, o
   problema é inviável. Fase 2 otimiza a função objetivo original.
4. Os preços-sombra (variáveis duais) saem de y = c_B B^-1 na base ótima.

Regra de entrada: Dantzig (custo reduzido mais negativo). Depois de uma
sequência de pivôs degenerados troca para a regra de Bland, que evita ciclos.
"""
from __future__ import annotations

import time

import numpy as np

from .problema import ProblemaLP, Resultado

EPS = 1e-9


class _Tableau:
    def __init__(self, T: np.ndarray, base: list[int]):
        self.T = T
        self.base = base
        self.iteracoes = 0

    def pivotear(self, linha: int, coluna: int) -> None:
        T = self.T
        T[linha] /= T[linha, coluna]
        col = T[:, coluna].copy()
        col[linha] = 0.0
        T -= np.outer(col, T[linha])
        self.base[linha] = coluna
        self.iteracoes += 1

    def otimizar(self, permitidas: np.ndarray, max_iter: int = 20000) -> str:
        """Itera até o ótimo. A última linha de T guarda os custos reduzidos."""
        T = self.T
        degenerados = 0
        while self.iteracoes < max_iter:
            custos = T[-1, :-1]
            candidatas = np.where((custos < -EPS) & permitidas)[0]
            if candidatas.size == 0:
                return "otimo"
            if degenerados > 50:          # regra de Bland: menor índice
                coluna = int(candidatas[0])
            else:                         # regra de Dantzig
                coluna = int(candidatas[np.argmin(custos[candidatas])])
            a = T[:-1, coluna]
            positivos = a > EPS
            if not positivos.any():
                return "ilimitado"
            razoes = np.full(a.shape, np.inf)
            razoes[positivos] = T[:-1, -1][positivos] / a[positivos]
            minimo = razoes.min()
            # desempate pelo menor índice de variável básica (Bland)
            empatadas = np.where(razoes <= minimo + EPS)[0]
            linha = int(min(empatadas, key=lambda r: self.base[r]))
            degenerados = degenerados + 1 if minimo <= EPS else 0
            self.pivotear(linha, coluna)
        return "limite"


def resolver(p: ProblemaLP, max_iter: int = 20000) -> Resultado:
    t0 = time.perf_counter()
    n = p.n
    lb = np.asarray(p.lb, float)
    ub = np.asarray(p.ub, float)
    if np.any(lb > ub + EPS):
        return Resultado("inviavel", metodo="simplex", tempo=time.perf_counter() - t0)

    # 1. restrições originais + limites superiores como linhas
    linhas_A = [p.A]
    linhas_b = [p.b - p.A @ lb]
    sentidos = list(p.sentidos)
    finitos = np.where(np.isfinite(ub))[0]
    if finitos.size:
        U = np.zeros((finitos.size, n))
        U[np.arange(finitos.size), finitos] = 1.0
        linhas_A.append(U)
        linhas_b.append(ub[finitos] - lb[finitos])
        sentidos += ["<="] * finitos.size
    A = np.vstack(linhas_A).astype(float)
    b = np.concatenate(linhas_b).astype(float)
    m = len(b)

    # 2. lado direito não negativo
    sinal_linha = np.ones(m)
    for i in range(m):
        if b[i] < 0:
            A[i] *= -1
            b[i] *= -1
            sinal_linha[i] = -1
            if sentidos[i] == ">=":
                sentidos[i] = "<="
            elif sentidos[i] == "<=":
                sentidos[i] = ">="

    n_folga = sum(s != "=" for s in sentidos)
    n_art = sum(s != "<=" for s in sentidos)
    N = n + n_folga + n_art
    M = np.zeros((m, N))
    M[:, :n] = A
    base = [0] * m
    artificiais = []
    k_f, k_a = n, n + n_folga
    for i, s in enumerate(sentidos):
        if s == "<=":
            M[i, k_f] = 1.0
            base[i] = k_f
            k_f += 1
        elif s == ">=":
            M[i, k_f] = -1.0
            k_f += 1
            M[i, k_a] = 1.0
            base[i] = k_a
            artificiais.append(k_a)
            k_a += 1
        else:
            M[i, k_a] = 1.0
            base[i] = k_a
            artificiais.append(k_a)
            k_a += 1

    T = np.zeros((m + 1, N + 1))
    T[:m, :N] = M
    T[:m, -1] = b
    tab = _Tableau(T, base)

    # 3. fase 1
    if artificiais:
        custo1 = np.zeros(N)
        custo1[artificiais] = 1.0
        T[-1, :N] = custo1
        T[-1, -1] = 0.0
        for i, j in enumerate(base):
            if custo1[j] != 0:
                T[-1] -= custo1[j] * T[i]
        status = tab.otimizar(np.ones(N, bool), max_iter)
        if status == "limite":
            return Resultado("limite", iteracoes=tab.iteracoes, metodo="simplex",
                             tempo=time.perf_counter() - t0)
        if -T[-1, -1] > 1e-7:
            return Resultado("inviavel", iteracoes=tab.iteracoes, metodo="simplex",
                             tempo=time.perf_counter() - t0)
        # tira da base as artificiais que ficaram no nível zero
        art = set(artificiais)
        for i in range(m):
            if tab.base[i] in art:
                cand = [j for j in range(n + n_folga) if abs(T[i, j]) > 1e-7]
                if cand:
                    tab.pivotear(i, cand[0])

    # 4. fase 2
    custo2 = np.zeros(N)
    custo2[:n] = p.c
    T[-1, :] = 0.0
    T[-1, :N] = custo2
    for i, j in enumerate(tab.base):
        if custo2[j] != 0:
            T[-1] -= custo2[j] * T[i]
    permitidas = np.ones(N, bool)
    permitidas[artificiais] = False
    status = tab.otimizar(permitidas, max_iter)
    tempo = time.perf_counter() - t0
    if status != "otimo":
        return Resultado(status, iteracoes=tab.iteracoes, metodo="simplex", tempo=tempo)

    xs = np.zeros(N)
    for i, j in enumerate(tab.base):
        xs[j] = T[i, -1]
    x = lb + xs[:n]

    # preços-sombra: B^T y = c_B
    B = M[:, tab.base]
    try:
        y = np.linalg.solve(B.T, custo2[tab.base])
    except np.linalg.LinAlgError:
        y = np.linalg.lstsq(B.T, custo2[tab.base], rcond=None)[0]
    y = y * sinal_linha * p.sinal  # volta ao sentido original de linha e de objetivo
    duais = y[: p.m]
    duais_limites = np.zeros(n)
    duais_limites[finitos] = y[p.m:]

    return Resultado("otimo", x=x, valor=p.valor(x), duais=duais,
                     iteracoes=tab.iteracoes, tempo=tempo, metodo="simplex",
                     extra={"duais_limite_superior": duais_limites})
