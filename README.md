# Nutriliza

Otimização de dietas para atletas e pessoas com restrições alimentares, com
Programação Linear e Inteira. Trabalho da disciplina **Otimização de Sistemas**
(Ciência da Computação, PUC Minas).

**Integrantes:** Antonio Soares Couto Neto, Rodrigo Drummond, Thales Matheus.

## O que tem aqui

| Pasta | Conteúdo |
|---|---|
| `nutriliza/` | Modelo e solvers: Simplex de duas fases com preços-sombra, Branch and Bound e Algoritmo Genético, todos implementados do zero |
| `data/alimentos.csv` | 37 alimentos com composição por 100 g (base TACO), porção caseira, preço e marcadores de restrição (carne, origem animal, lactose, glúten) |
| `experimentos/` | Script que roda todos os experimentos e gera tabelas e figuras |
| `resultados/` | Tabelas CSV, cardápios gerados (`cardapios.md`) e o log da execução |
| `figuras/` | Gráficos usados no artigo e na documentação |
| `artigo/` | Artigo no template da SBC (LaTeX) |
| `docs/` | Documentação completa no template da PUC Minas (`Nutriliza_Documentacao.docx`) e o script que a gera |
| `web/` | Interface web simples (front + API) para demonstrar os modelos |
| `tests/` | Testes dos solvers contra exemplos de livro e contra o CBC |

## Modelo

Variável de decisão: `x_i` = porções do alimento `i` por dia.

```
min/max  Z = Σ c_i x_i
s.a.     L_j ≤ Σ a_ji x_i ≤ U_j        para 9 nutrientes (energia, proteína, carboidrato,
                                        gordura, fibra, cálcio, ferro, sódio, vitamina C)
         Σ (frutas e hortaliças) ≥ 400 g
         0 ≤ x_i ≤ M_i,  x_i = 0 para alimentos excluídos pelo perfil
         x_i inteiro (no modelo de porções inteiras)
```

**Perfis (9):** adulto de referência, sobrepeso (emagrecimento), subpeso (ganho de peso),
atleta de força, vegetariano, vegano, intolerante à lactose, celíaco e atleta vegetariano.

**Funções objetivo (7 + combinações):** minimizar custo, calorias, sódio, gordura ou
quantidade total; maximizar proteína ou fibra; soma ponderada e método ε-restrito para
fronteiras de Pareto (custo × proteína, custo × sódio).

**Métodos de solução:**

1. **Simplex de duas fases** (tableau, regra de Dantzig com troca para Bland contra ciclagem),
   com extração das variáveis duais (preços-sombra) por `y = c_B B⁻¹`.
2. **Branch and Bound** para porções inteiras, usando o Simplex próprio nas relaxações
   (mergulho em profundidade até a primeira solução inteira e depois melhor limite primeiro).
3. **Algoritmo Genético** memético com regras de factibilidade de Deb no torneio,
   cruzamento uniforme, mutação ±1 porção, elitismo e busca local nos indivíduos de elite.

Os três são validados contra o CBC (via PuLP).

## Como rodar

```bash
pip install -r requirements.txt
python -m pytest -q                              # testes
python experimentos/rodar_experimentos.py        # todos os experimentos (~15 min)
python experimentos/rodar_experimentos.py --rapido
python docs/gerar_documentacao.py                # gera o .docx
python web/app.py                                # interface em http://localhost:8000
```

Uso direto no Python:

```python
from nutriliza import carregar_alimentos, construir, simplex, branch_and_bound, genetico, cardapio
alim = carregar_alimentos()
p = construir("atleta", "custo", inteiro=True, df=alim)
r = branch_and_bound.resolver(p)
print(r.valor, cardapio(alim, r.x))
```

## Artigo

O texto do artigo fica em `artigo/artigo_modelo.tex`; `python artigo/gerar_tabelas.py`
preenche os números a partir de `resultados/` e grava `artigo/artigo.tex` e `artigo/tabelas/`.
Os diagramas (metodologia, Simplex, árvore do Branch and Bound, fluxo e cromossomo do
Genético) estão em TikZ em `artigo/tikz/`; `artigo/tikz/figuras_png.tex` +
`artigo/tikz/exportar_png.py` geram as versões PNG usadas na documentação.

`artigo/artigo.tex` usa o template oficial da SBC (`sbc-template.sty` e `sbc.bst`).
Para compilar: `pdflatex artigo && bibtex artigo && pdflatex artigo && pdflatex artigo`
dentro de `artigo/`, ou suba a pasta `artigo/` junto com `figuras/` no Overleaf
(ajuste `\graphicspath` se mudar a estrutura).

## Observação

Os limites nutricionais vêm das DRIs (IOM), das diretrizes da OMS e de consensos de
nutrição esportiva, e os preços são premissas de mercado de Belo Horizonte em 2026.
São premissas didáticas: o modelo não substitui a orientação de um nutricionista.
