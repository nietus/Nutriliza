"""Representação de um problema de Programação Linear (inteira ou não).

Todo problema é guardado na forma de minimização:

    min  c^T x
    s.a. A_i x  (>=, <=, =)  b_i      i = 1..m
         lb <= x <= ub

Problemas de maximização são convertidos trocando o sinal de c; o campo
``sinal`` guarda o fator (+1 ou -1) para devolver o valor no sentido original.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class ProblemaLP:
    c: np.ndarray
    A: np.ndarray
    sentidos: list[str]
    b: np.ndarray
    lb: np.ndarray
    ub: np.ndarray
    nomes_var: list[str]
    nomes_restr: list[str]
    sinal: int = 1  # +1 minimização, -1 maximização
    descricao: str = ""
    inteiro: bool = False
    meta: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.c)

    @property
    def m(self) -> int:
        return len(self.b)

    def valor(self, x: np.ndarray) -> float:
        """Valor da função objetivo no sentido original (min ou max)."""
        return float(self.sinal * self.c @ x)

    def violacao(self, x: np.ndarray) -> np.ndarray:
        """Violação de cada restrição, normalizada pelo lado direito."""
        ax = self.A @ x
        v = np.zeros(self.m)
        esc = np.maximum(np.abs(self.b), 1.0)
        for i, s in enumerate(self.sentidos):
            if s == ">=":
                v[i] = max(0.0, self.b[i] - ax[i])
            elif s == "<=":
                v[i] = max(0.0, ax[i] - self.b[i])
            else:
                v[i] = abs(ax[i] - self.b[i])
        return v / esc

    def factivel(self, x: np.ndarray, tol: float = 1e-6) -> bool:
        if np.any(x < self.lb - tol) or np.any(x > self.ub + tol):
            return False
        return bool(np.all(self.violacao(x) <= tol))

    def com_limites(self, lb: np.ndarray, ub: np.ndarray) -> "ProblemaLP":
        """Cópia rasa com novos limites de variável (usada no Branch and Bound)."""
        return ProblemaLP(self.c, self.A, self.sentidos, self.b, lb, ub,
                          self.nomes_var, self.nomes_restr, self.sinal,
                          self.descricao, self.inteiro, self.meta)


@dataclass
class Resultado:
    status: str                      # "otimo", "inviavel", "ilimitado", "limite"
    x: np.ndarray | None = None
    valor: float | None = None       # no sentido original do problema
    duais: np.ndarray | None = None  # preço-sombra de cada restrição (sentido original)
    iteracoes: int = 0
    tempo: float = 0.0
    metodo: str = ""
    extra: dict = field(default_factory=dict)
