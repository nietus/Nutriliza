"""Perfis nutricionais (cenários) e funções objetivo disponíveis.

Os limites são diários e foram definidos a partir das Ingestões Dietéticas
de Referência (IOM, 2006), das recomendações da OMS para sódio e para
frutas e hortaliças (WHO, 2003; 2012) e das posições de consenso sobre
nutrição esportiva (Thomas, Erdman e Burke, 2016). São premissas didáticas
para o modelo e não substituem a prescrição de um nutricionista.

Formato: nutriente -> (mínimo, máximo); None significa sem limite.
"""
from __future__ import annotations

from copy import deepcopy

NUTRIENTES = {
    "kcal": ("Energia", "kcal"),
    "proteina": ("Proteína", "g"),
    "carboidrato": ("Carboidrato", "g"),
    "gordura": ("Gordura", "g"),
    "fibra": ("Fibra", "g"),
    "calcio": ("Cálcio", "mg"),
    "ferro": ("Ferro", "mg"),
    "sodio": ("Sódio", "mg"),
    "vitamina_c": ("Vitamina C", "mg"),
}

_BASE = {
    "kcal": (2000, 2400),
    "proteina": (60, 140),
    "carboidrato": (250, 360),
    "gordura": (45, 85),
    "fibra": (25, None),
    "calcio": (1000, 2500),
    "ferro": (8, 45),
    "sodio": (None, 2000),
    "vitamina_c": (75, 2000),
}


def _com(**mudancas):
    lim = deepcopy(_BASE)
    lim.update(mudancas)
    return lim


_ATLETA = _com(kcal=(3000, 3400), proteina=(130, 180), carboidrato=(400, 520),
               gordura=(60, 110), fibra=(30, None), sodio=(None, 3000),
               vitamina_c=(90, 2000))

PERFIS = {
    "referencia": {
        "nome": "Adulto de referência",
        "descricao": "Adulto saudável, 70 kg, atividade moderada; manutenção do peso.",
        "limites": _com(),
        "exclui": [],
    },
    "sobrepeso": {
        "nome": "Sobrepeso (emagrecimento)",
        "descricao": "Adulto com 95 kg; déficit de cerca de 500 kcal/dia, proteína "
                     "alta para preservar massa magra e gordura reduzida.",
        "limites": _com(kcal=(1500, 1700), proteina=(90, 130), carboidrato=(130, 200),
                        gordura=(35, 55), fibra=(30, None)),
        "exclui": [],
    },
    "subpeso": {
        "nome": "Subpeso (ganho de peso)",
        "descricao": "Adulto com 52 kg (IMC 17,5); superávit de cerca de 500 kcal/dia.",
        "limites": _com(kcal=(2800, 3200), proteina=(80, 140), carboidrato=(380, 480),
                        gordura=(75, 110), sodio=(None, 2300)),
        "exclui": [],
    },
    "atleta": {
        "nome": "Atleta (força)",
        "descricao": "Atleta de 80 kg em treino de força: proteína de 1,6 a 2,2 g/kg "
                     "e carboidrato de 5 a 6,5 g/kg.",
        "limites": _ATLETA,
        "exclui": [],
    },
    "vegetariano": {
        "nome": "Vegetariano (ovolactovegetariano)",
        "descricao": "Sem carnes e peixes; ferro mínimo 1,8 vez maior pela menor "
                     "biodisponibilidade do ferro vegetal.",
        "limites": _com(ferro=(14, 45)),
        "exclui": ["carne"],
    },
    "vegano": {
        "nome": "Vegano",
        "descricao": "Sem nenhum produto de origem animal; ferro mínimo ampliado.",
        "limites": _com(ferro=(14, 45)),
        "exclui": ["animal"],
    },
    "lactose": {
        "nome": "Intolerante à lactose",
        "descricao": "Exclui leite e derivados com lactose; cálcio vem de outras fontes.",
        "limites": _com(),
        "exclui": ["lactose"],
    },
    "celiaco": {
        "nome": "Celíaco",
        "descricao": "Exclui alimentos com glúten (trigo, aveia comum).",
        "limites": _com(),
        "exclui": ["gluten"],
    },
    "atleta_vegetariano": {
        "nome": "Atleta vegetariano",
        "descricao": "Restrições do atleta somadas à exclusão de carnes (restrições simultâneas).",
        "limites": {**_ATLETA, "ferro": (14, 45)},
        "exclui": ["carne"],
    },
}

# mínimo diário de frutas e hortaliças (OMS: 400 g)
FRUTAS_HORTALICAS_MIN_G = 400

# função objetivo: (rótulo, sentido, coluna da tabela ou "massa")
OBJETIVOS = {
    "custo": ("Minimizar custo (R$)", "min", "custo"),
    "calorias": ("Minimizar calorias (kcal)", "min", "kcal"),
    "proteina": ("Maximizar proteína (g)", "max", "proteina"),
    "fibra": ("Maximizar fibra (g)", "max", "fibra"),
    "sodio": ("Minimizar sódio (mg)", "min", "sodio"),
    "gordura": ("Minimizar gordura (g)", "min", "gordura"),
    "massa": ("Minimizar quantidade total (g)", "min", "massa"),
}
