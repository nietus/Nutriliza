"""Testes dos solvers próprios contra exemplos de livro e contra o CBC.

Rodar com:  python -m pytest -q
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nutriliza import PERFIS, branch_and_bound, carregar_alimentos, construir, genetico, simplex  # noqa: E402
from nutriliza import referencia  # noqa: E402
from nutriliza.problema import ProblemaLP  # noqa: E402


def _problema(c, A, sentidos, b, ub=None, sinal=1):
    n = len(c)
    return ProblemaLP(np.array(c, float), np.array(A, float), sentidos, np.array(b, float),
                      np.zeros(n), np.full(n, np.inf) if ub is None else np.array(ub, float),
                      [f"x{i}" for i in range(n)], [f"r{i}" for i in range(len(b))], sinal)


def test_simplex_max_classico():
    # max 3x + 5y s.a. x <= 4; 2y <= 12; 3x + 2y <= 18  (Hillier e Lieberman): ótimo 36 em (2, 6)
    p = _problema([-3, -5], [[1, 0], [0, 2], [3, 2]], ["<="] * 3, [4, 12, 18], sinal=-1)
    r = simplex.resolver(p)
    assert r.status == "otimo"
    assert r.valor == pytest.approx(36)
    np.testing.assert_allclose(r.x, [2, 6], atol=1e-9)
    # preços-sombra conhecidos: 0, 1.5, 1
    np.testing.assert_allclose(r.duais, [0, 1.5, 1], atol=1e-9)


def test_simplex_dieta_classica_com_maior_igual():
    # min 2x + 3y s.a. x + y >= 4; x + 3y >= 6  -> ótimo 9 em (3, 1)
    p = _problema([2, 3], [[1, 1], [1, 3]], [">=", ">="], [4, 6])
    r = simplex.resolver(p)
    assert r.valor == pytest.approx(9)
    np.testing.assert_allclose(r.duais, [1.5, 0.5], atol=1e-9)


def test_simplex_inviavel_e_ilimitado():
    assert simplex.resolver(_problema([1], [[1], [1]], [">=", "<="], [5, 3])).status == "inviavel"
    assert simplex.resolver(_problema([-1], [[1]], [">="], [1])).status == "ilimitado"


@pytest.fixture(scope="module")
def alimentos():
    return carregar_alimentos()


@pytest.mark.parametrize("perfil", list(PERFIS))
@pytest.mark.parametrize("objetivo", ["custo", "proteina", "sodio"])
def test_simplex_igual_cbc(alimentos, perfil, objetivo):
    p = construir(perfil, objetivo, df=alimentos)
    r, q = simplex.resolver(p), referencia.resolver(p, inteiro=False)
    assert r.valor == pytest.approx(q.valor, rel=1e-6)
    np.testing.assert_allclose(r.duais, q.duais, atol=1e-6)
    assert p.factivel(r.x)


@pytest.mark.parametrize("perfil", ["referencia", "vegano", "atleta"])
def test_branch_and_bound_igual_cbc(alimentos, perfil):
    p = construir(perfil, "custo", inteiro=True, df=alimentos)
    r, q = branch_and_bound.resolver(p), referencia.resolver(p)
    assert r.valor == pytest.approx(q.valor, rel=1e-6)
    assert np.allclose(r.x, np.round(r.x)) and p.factivel(r.x)


def test_genetico_factivel_e_nao_melhor_que_otimo(alimentos):
    p = construir("atleta", "custo", inteiro=True, df=alimentos)
    g = genetico.resolver(p, populacao=80, geracoes=150, semente=1)
    otimo = referencia.resolver(p).valor
    assert g.status == "factivel" and p.factivel(g.x)
    assert g.valor >= otimo - 1e-9


def test_exclusoes_respeitadas(alimentos):
    p = construir("vegano", "custo", df=alimentos)
    r = simplex.resolver(p)
    animal = alimentos["animal"].to_numpy() == 1
    assert np.all(r.x[animal] <= 1e-9)
