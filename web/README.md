# Nutriliza — interface web

Interface simples (FastAPI + HTML) para demonstrar a otimização de dietas do pacote `nutriliza`.

## Como executar

Na raiz do projeto (a pasta que contém `nutriliza/` e `data/`):

```bash
pip install -r requirements.txt
python web/app.py
```

Depois abra <http://localhost:8000> no navegador. Para parar, use `Ctrl+C` no terminal.

O gráfico de convergência usa Chart.js carregado do cdnjs, então precisa de internet; sem ela, o resto da página funciona normalmente.

## O que dá para fazer

- Escolher **perfil**, **objetivo** e **método** (Simplex, Branch and Bound ou Algoritmo Genético).
- Editar os **limites mínimo e máximo** de cada nutriente (já vêm preenchidos com os do perfil; campo em branco = sem limite).
- **Otimizar**: mostra o cardápio do dia, os totais de nutrientes contra os limites, os preços-sombra (só no Simplex) e a curva de convergência (só no Algoritmo Genético).
- **Comparar métodos**: roda os três métodos sobre o modelo inteiro (o Simplex resolve a relaxação linear, que serve de limite) e mostra valor, diferença para o Branch and Bound, tempo e esforço.

O Branch and Bound tem limite de 30 s e o Algoritmo Genético roda 500 gerações (cerca de 10 s), então a comparação pode levar uns 15 s.

## API

| Método | Rota | Corpo |
|---|---|---|
| GET | `/api/opcoes` | — (perfis com limites padrão, objetivos, nutrientes, métodos) |
| POST | `/api/resolver` | `{"perfil": "atleta", "objetivo": "custo", "metodo": "simplex", "limites": {"proteina": [130, 180]}}` |
| POST | `/api/comparar` | `{"perfil": "atleta", "objetivo": "custo"}` (aceita `limites` também) |

A documentação interativa da API fica em <http://localhost:8000/docs>.

## Abrir já com um resultado (para apresentar)

Parâmetros na URL preenchem o formulário e disparam a otimização:

- `http://localhost:8000/?perfil=atleta&objetivo=custo&metodo=simplex&executar=otimizar`
- `http://localhost:8000/?perfil=vegano&objetivo=custo&executar=comparar`

Valores de `perfil`: referencia, sobrepeso, subpeso, atleta, vegetariano, vegano, lactose,
celiaco, atleta_vegetariano. `objetivo`: custo, calorias, proteina, fibra, sodio, gordura,
massa. `metodo`: simplex, branch_and_bound, genetico.
