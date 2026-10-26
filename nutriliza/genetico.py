"""Algoritmo Genético para o modelo inteiro (porções inteiras).

- Cromossomo: vetor de inteiros, um gene por alimento (número de porções).
- Restrições tratadas pelas regras de Deb (2000) no torneio, sem penalidade
  a calibrar: (1) solução factível vence infactível; (2) entre factíveis,
  vence o melhor objetivo; (3) entre infactíveis, vence a menor violação.
- Cruzamento uniforme, mutação +-1 porção (ou reinício do gene) e elitismo.
- Busca local (algoritmo memético) nos indivíduos de elite de cada geração:
  descida mais íngreme na vizinhança de +-1 porção e de troca de porções.
"""
from __future__ import annotations

import time

import numpy as np

from .problema import ProblemaLP, Resultado


def _avaliar(p: ProblemaLP, pop: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    f = pop @ p.c
    ax = pop @ p.A.T
    esc = np.maximum(np.abs(p.b), 1.0)
    v = np.zeros(len(pop))
    for i, s in enumerate(p.sentidos):
        if s == ">=":
            v += np.maximum(0.0, p.b[i] - ax[:, i]) / esc[i]
        elif s == "<=":
            v += np.maximum(0.0, ax[:, i] - p.b[i]) / esc[i]
        else:
            v += np.abs(ax[:, i] - p.b[i]) / esc[i]
    return f, v


def _melhor_que(f1, v1, f2, v2) -> bool:
    if v1 <= 1e-9 and v2 <= 1e-9:
        return f1 < f2
    if v1 <= 1e-9 or v2 <= 1e-9:
        return v1 <= 1e-9
    return v1 < v2


def _ordem(f: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Ordena pela regra de Deb: factíveis por f, depois infactíveis por v."""
    factivel = v <= 1e-9
    chave = np.where(factivel, f, np.inf)
    return np.lexsort((chave, np.where(factivel, 0.0, v)))


def _vizinhos(n: int) -> np.ndarray:
    """Movimentos da busca local: +-1 porção em um alimento ou troca de uma
    porção de um alimento por outro (-1 em j, +1 em k)."""
    I = np.eye(n)
    trocas = (I[:, None, :] - I[None, :, :]).reshape(n * n, n)
    trocas = trocas[np.any(trocas != 0, axis=1)]
    return np.vstack([I, -I, trocas])


def _busca_local(p: ProblemaLP, x: np.ndarray, f: float, v: float, movimentos: np.ndarray):
    """Melhor vizinho (descida mais íngreme) segundo as regras de Deb."""
    viz = x + movimentos
    ok = np.all((viz >= p.lb) & (viz <= p.ub), axis=1)
    viz = viz[ok]
    fv, vv = _avaliar(p, viz)
    k = _ordem(fv, vv)[0]
    if _melhor_que(fv[k], vv[k], f, v):
        return viz[k], fv[k], vv[k], True
    return x, f, v, False


def resolver(p: ProblemaLP, populacao: int = 200, geracoes: int = 500,
             taxa_cruzamento: float = 0.9, taxa_mutacao: float | None = None,
             elite: int = 6, semente: int = 0, busca_local: bool = True) -> Resultado:
    t0 = time.perf_counter()
    rng = np.random.default_rng(semente)
    n = p.n
    lb = p.lb.astype(int)
    ub = p.ub.astype(int)
    pm = taxa_mutacao if taxa_mutacao is not None else 1.5 / n

    movimentos = _vizinhos(n) if busca_local else None
    pop = rng.integers(lb, ub + 1, size=(populacao, n)).astype(float)
    f, v = _avaliar(p, pop)
    curva = []

    for g in range(geracoes):
        ordem = _ordem(f, v)
        pop, f, v = pop[ordem], f[ordem], v[ordem]
        if busca_local:
            for e in range(elite):
                for _ in range(n):
                    x, fx, vx, melhorou = _busca_local(p, pop[e], f[e], v[e], movimentos)
                    if not melhorou:
                        break
                    pop[e], f[e], v[e] = x, fx, vx
        curva.append((g, f[0] if v[0] <= 1e-9 else np.nan, v[0],
                      float(np.mean(v <= 1e-9))))

        nova = [pop[:elite].copy()]
        while sum(len(b) for b in nova) < populacao:
            pais = []
            for _ in range(2):  # torneio binário com regras de Deb
                a, b = rng.integers(0, populacao, 2)
                pais.append(a if _melhor_que(f[a], v[a], f[b], v[b]) else b)
            x1, x2 = pop[pais[0]].copy(), pop[pais[1]].copy()
            if rng.random() < taxa_cruzamento:
                mascara = rng.random(n) < 0.5
                x1[mascara], x2[mascara] = pop[pais[1]][mascara], pop[pais[0]][mascara]
            for x in (x1, x2):
                mut = rng.random(n) < pm
                passo = rng.choice([-1, 1], size=n)
                x[mut] += passo[mut]
                reinicio = rng.random(n) < pm / 4
                x[reinicio] = rng.integers(lb, ub + 1)[reinicio]
                np.clip(x, lb, ub, out=x)
            nova.append(np.vstack([x1, x2]))
        pop = np.vstack(nova)[:populacao]
        f, v = _avaliar(p, pop)

    ordem = _ordem(f, v)
    x = pop[ordem[0]]
    tempo = time.perf_counter() - t0
    factivel = v[ordem[0]] <= 1e-9
    return Resultado("factivel" if factivel else "infactivel", x=x,
                     valor=p.valor(x) if factivel else None, iteracoes=geracoes,
                     tempo=tempo, metodo="genetico",
                     extra={"curva": curva, "violacao": float(v[ordem[0]]),
                            "semente": semente})
