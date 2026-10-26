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
- **Otimizar**: mostra o cardápio do dia, os totais de nutrientes contra os limites, os preços-sombra com o impacto de cada restrição no ótimo (só no Simplex) e as curvas de convergência e de fração factível (só no Algoritmo Genético).
- **Comparar métodos**: roda os três métodos sobre o modelo inteiro (o Simplex resolve a relaxação linear, que serve de limite) e mostra valor, diferença para o Branch and Bound, tempo e esforço.

Cada método e cada bloco de resultado tem uma linha explicando o que mostra (para apresentar sem precisar
de slide). Na tabela de nutrientes, **no mínimo / no máximo** marca as restrições ativas; na comparação, o
melhor método inteiro fica destacado e o Simplex aparece como limite teórico. **Enter** em qualquer campo
roda **Otimizar**; durante o cálculo os botões ficam desabilitados e um contador mostra os segundos.

O Branch and Bound tem limite de 30 s, mas costuma resolver em cerca de 1 s; o Algoritmo Genético roda 500 gerações (uns 4 a 5 s), e a comparação leva uns 6 s.

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
