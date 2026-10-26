"""Branch and Bound para o modelo inteiro (porções inteiras de cada alimento).

Cada nó é o mesmo problema com limites de variável mais apertados. A
relaxação linear de cada nó é resolvida pelo Simplex próprio (simplex.py).

- Ramificação: variável com parte fracionária mais próxima de 0,5.
- Exploração: mergulho em profundidade até achar a primeira solução inteira
  e, depois disso, melhor limite primeiro (best-bound).
- Poda: por inviabilidade, por limite (relaxação pior que a incumbente) e
  por integralidade.
- Heurística de arredondamento em cada nó para achar incumbentes cedo.
"""
from __future__ import annotations

import heapq
import itertools
import math
import time

import numpy as np

from . import simplex
from .problema import ProblemaLP, Resultado

TOL_INT = 1e-6


def _arredondar(p: ProblemaLP, x: np.ndarray) -> np.ndarray | None:
    """Tenta arredondar para o inteiro mais próximo; depois tenta para cima."""
    for funcao in (np.round, np.ceil):
        xr = np.clip(funcao(x - 1e-9), p.lb, p.ub)
        if p.factivel(xr):
            return xr
    return None


def resolver(p: ProblemaLP, tempo_limite: float = 60.0, max_nos: int = 200000,
             gap_relativo: float = 1e-6) -> Resultado:
    t0 = time.perf_counter()
    contador = itertools.count()
    melhor_x, melhor_f = None, math.inf      # f no sentido de minimização
    nos = 0
    iteracoes_lp = 0
    pilha: list = []   # mergulho inicial (profundidade)
    heap: list = []    # melhor limite primeiro
    historico = []     # (tempo, nós, incumbente, limite) para gráficos

    raiz = simplex.resolver(p)
    iteracoes_lp += raiz.iteracoes
    if raiz.status != "otimo":
        return Resultado(raiz.status, metodo="branch_and_bound",
                         tempo=time.perf_counter() - t0)
    f_raiz = float(p.c @ raiz.x)
    pilha.append((f_raiz, next(contador), p.lb.copy(), p.ub.copy(), raiz))

    def promissor(f: float) -> bool:
        """f ainda pode melhorar a incumbente (com tolerância relativa)?"""
        if melhor_x is None:
            return True
        return f < melhor_f - gap_relativo * max(1.0, abs(melhor_f))

    def limite_global() -> float:
        abertos = [f for f, *_ in pilha] + [f for f, *_ in heap]
        return min(abertos) if abertos else melhor_f

    status = "otimo"
    while pilha or heap:
        if time.perf_counter() - t0 > tempo_limite or nos >= max_nos:
            status = "limite"
            break
        if pilha:
            f_no, _, lb, ub, res = pilha.pop()
        else:
            f_no, _, lb, ub, res = heapq.heappop(heap)
        nos += 1
        if not promissor(f_no):
            continue  # poda por limite

        x = res.x
        frac = np.abs(x - np.round(x))
        if frac.max() <= TOL_INT:  # solução inteira
            xr = np.round(x)
            if f_no < melhor_f:
                melhor_x, melhor_f = xr, f_no
                historico.append((time.perf_counter() - t0, nos, melhor_f, limite_global()))
                pilha_restante = pilha
                pilha = []
                for item in pilha_restante:  # termina o mergulho
                    heapq.heappush(heap, item)
            continue

        xh = _arredondar(p.com_limites(lb, ub), x)
        if xh is not None:
            fh = float(p.c @ xh)
            if fh < melhor_f:
                melhor_x, melhor_f = xh, fh
                historico.append((time.perf_counter() - t0, nos, melhor_f, limite_global()))

        j = int(np.argmin(np.abs(frac - 0.5) + (frac <= TOL_INT) * 10))
        filhos = []
        ub_esq = ub.copy()
        ub_esq[j] = math.floor(x[j])
        lb_dir = lb.copy()
        lb_dir[j] = math.ceil(x[j])
        for nlb, nub in ((lb, ub_esq), (lb_dir, ub)):
            r = simplex.resolver(p.com_limites(nlb, nub))
            iteracoes_lp += r.iteracoes
            if r.status != "otimo":
                continue  # poda por inviabilidade
            f = float(p.c @ r.x)
            if promissor(f):
                filhos.append((f, next(contador), nlb, nub, r))
        if melhor_x is None:
            filhos.sort(key=lambda t: -t[0])  # o melhor filho é visitado primeiro
            pilha.extend(filhos)
        else:
            for item in filhos:
                heapq.heappush(heap, item)

    tempo = time.perf_counter() - t0
    if melhor_x is None:
        return Resultado("inviavel" if status == "otimo" else "limite",
                         metodo="branch_and_bound", tempo=tempo,
                         extra={"nos": nos, "iteracoes_lp": iteracoes_lp})
    limite = limite_global() if status == "limite" else melhor_f
    gap = abs(melhor_f - limite) / max(1e-9, abs(melhor_f))
    return Resultado(status, x=melhor_x, valor=p.valor(melhor_x), iteracoes=iteracoes_lp,
                     tempo=tempo, metodo="branch_and_bound",
                     extra={"nos": nos, "gap": gap, "limite_raiz": p.sinal * f_raiz,
                            "historico": historico})
