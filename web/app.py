"""Interface web do Nutriliza (FastAPI).

Executar a partir da raiz do projeto:  python web/app.py
Abre em http://localhost:8000
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from nutriliza import (NUTRIENTES, OBJETIVOS, PERFIS, branch_and_bound,  # noqa: E402
                       cardapio, carregar_alimentos, construir, genetico,
                       resumo_nutricional, simplex)

ESTATICO = Path(__file__).resolve().parent / "static"
ALIMENTOS = carregar_alimentos()
METODOS = {
    "simplex": "Simplex (PL contínua)",
    "branch_and_bound": "Branch and Bound (PL inteira)",
    "genetico": "Algoritmo genético (inteiro)",
}
TOL = 1e-6

app = FastAPI(title="Nutriliza")


class PedidoResolver(BaseModel):
    perfil: str
    objetivo: str = "custo"
    metodo: str = "simplex"
    limites: dict[str, list[float | None]] | None = None


class PedidoComparar(BaseModel):
    perfil: str
    objetivo: str = "custo"
    limites: dict[str, list[float | None]] | None = None


def _num(v):
    """Converte para float JSON-seguro (NaN/inf viram None)."""
    if v is None:
        return None
    v = float(v)
    return None if math.isnan(v) or math.isinf(v) else v


def _validar(perfil: str, objetivo: str, metodo: str | None = None):
    if perfil not in PERFIS:
        raise HTTPException(400, f"Perfil desconhecido: {perfil}")
    if objetivo not in OBJETIVOS:
        raise HTTPException(400, f"Objetivo desconhecido: {objetivo}")
    if metodo is not None and metodo not in METODOS:
        raise HTTPException(400, f"Método desconhecido: {metodo}")


def _limites_efetivos(perfil: str, extra: dict | None) -> tuple[dict, dict]:
    """Devolve (limites finais por nutriente, limites_extra para construir)."""
    lim = dict(PERFIS[perfil]["limites"])
    extra_ok = {}
    for nut, par in (extra or {}).items():
        if nut not in NUTRIENTES:
            raise HTTPException(400, f"Nutriente desconhecido: {nut}")
        lo, hi = (list(par) + [None, None])[:2]
        lo = None if lo is None else float(lo)
        hi = None if hi is None else float(hi)
        if lo is not None and hi is not None and lo > hi:
            raise HTTPException(400, f"{NUTRIENTES[nut][0]}: mínimo maior que o máximo")
        extra_ok[nut] = (lo, hi)
    lim.update(extra_ok)
    return lim, extra_ok


def _rodar(metodo: str, p):
    if metodo == "simplex":
        return simplex.resolver(p)
    if metodo == "branch_and_bound":
        return branch_and_bound.resolver(p, tempo_limite=30)
    return genetico.resolver(p, semente=0)


def _totais(x, limites: dict) -> list[dict]:
    tot = resumo_nutricional(ALIMENTOS, x)
    linhas = []
    for nut, (rotulo, unidade) in NUTRIENTES.items():
        lo, hi = limites.get(nut, (None, None))
        v = tot[nut]
        ok = (lo is None or v >= lo - 1e-4 * max(1, abs(lo))) and \
             (hi is None or v <= hi + 1e-4 * max(1, abs(hi)))
        linhas.append({"nutriente": nut, "rotulo": rotulo, "unidade": unidade,
                       "valor": _num(v), "min": lo, "max": hi, "ok": bool(ok)})
    return linhas


def _resultado_json(metodo: str, p, r, limites: dict, detalhado: bool = True) -> dict:
    tem_x = r.x is not None
    out = {
        "metodo": metodo,
        "metodo_rotulo": METODOS.get(metodo, metodo),
        "status": r.status,
        "valor": _num(r.valor),
        "tempo": _num(r.tempo),
        "iteracoes": int(r.iteracoes),
        "nos": r.extra.get("nos"),
        "gap": _num(r.extra.get("gap")),
        "factivel": bool(tem_x and p.factivel(r.x)),
    }
    if tem_x:
        tot = resumo_nutricional(ALIMENTOS, r.x)
        out["custo"] = _num(tot["custo"])
        out["massa"] = _num(tot["massa"])
        out["n_alimentos"] = int(np.sum(r.x > TOL))
    if metodo == "genetico":
        out["violacao"] = _num(r.extra.get("violacao"))
    if not detalhado:
        return out

    if tem_x:
        card = cardapio(ALIMENTOS, r.x)
        out["cardapio"] = [{k: (_num(v) if isinstance(v, (float, np.floating)) else v)
                            for k, v in linha.items()} for linha in card.to_dict("records")]
        out["totais"] = _totais(r.x, limites)
        out["frutas_hortalicas_g"] = _num(p.A[p.nomes_restr.index("frutas_hortalicas_min")] @ r.x)
    if metodo == "simplex" and r.duais is not None and tem_x:
        ax = p.A @ r.x
        precos = []
        for i, nome in enumerate(p.nomes_restr):
            d = float(r.duais[i])
            if abs(d) > 1e-7:
                precos.append({"restricao": nome, "preco_sombra": d,
                               "rhs": _num(p.b[i]), "sentido": p.sentidos[i],
                               "lhs": _num(ax[i])})
        out["precos_sombra"] = precos
    if metodo == "genetico":
        out["curva"] = [{"geracao": int(g), "melhor": _num(f), "violacao": _num(v),
                         "frac_factivel": _num(fr)} for g, f, v, fr in r.extra.get("curva", [])]
    return out


@app.get("/api/opcoes")
def opcoes():
    return {
        "perfis": [{"id": k, "nome": v["nome"], "descricao": v["descricao"],
                    "exclui": v["exclui"],
                    "limites": {n: list(v["limites"].get(n, (None, None))) for n in NUTRIENTES}}
                   for k, v in PERFIS.items()],
        "objetivos": [{"id": k, "rotulo": v[0], "sentido": v[1]} for k, v in OBJETIVOS.items()],
        "nutrientes": [{"id": k, "rotulo": v[0], "unidade": v[1]} for k, v in NUTRIENTES.items()],
        "metodos": [{"id": k, "rotulo": v} for k, v in METODOS.items()],
        "n_alimentos": int(len(ALIMENTOS)),
    }


@app.post("/api/resolver")
def resolver(ped: PedidoResolver):
    _validar(ped.perfil, ped.objetivo, ped.metodo)
    limites, extra = _limites_efetivos(ped.perfil, ped.limites)
    p = construir(ped.perfil, ped.objetivo, inteiro=ped.metodo != "simplex",
                  df=ALIMENTOS, limites_extra=extra)
    r = _rodar(ped.metodo, p)
    out = _resultado_json(ped.metodo, p, r, limites)
    out["descricao"] = p.descricao
    out["sentido"] = OBJETIVOS[ped.objetivo][1]
    return out


@app.post("/api/comparar")
def comparar(ped: PedidoComparar):
    _validar(ped.perfil, ped.objetivo)
    limites, extra = _limites_efetivos(ped.perfil, ped.limites)
    p_int = construir(ped.perfil, ped.objetivo, inteiro=True, df=ALIMENTOS, limites_extra=extra)
    linhas = []
    r_lp = simplex.resolver(p_int)  # relaxação linear do modelo inteiro
    d = _resultado_json("simplex", p_int, r_lp, limites, detalhado=False)
    d["metodo_rotulo"] = "Simplex (relaxação linear)"
    linhas.append(d)
    for m in ("branch_and_bound", "genetico"):
        linhas.append(_resultado_json(m, p_int, _rodar(m, p_int), limites, detalhado=False))
    # distância de cada método inteiro ao ótimo do B&B
    ref = linhas[1]["valor"]
    for d in linhas:
        d["dif_bb_pct"] = (None if ref in (None, 0) or d["valor"] is None
                           else 100 * (d["valor"] - ref) / abs(ref))
    return {"descricao": p_int.descricao, "sentido": OBJETIVOS[ped.objetivo][1],
            "objetivo": OBJETIVOS[ped.objetivo][0], "metodos": linhas}


@app.get("/")
def index():
    return FileResponse(ESTATICO / "index.html")


app.mount("/static", StaticFiles(directory=ESTATICO), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
