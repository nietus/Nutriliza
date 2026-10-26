"""Gera docs/Nutriliza_Documentacao.docx no template da PUC Minas, com os números
lidos de resultados/ (rode experimentos/rodar_experimentos.py antes)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "docs"))

from modelo_docx import Documento  # noqa: E402
from nutriliza import NUTRIENTES, OBJETIVOS, PERFIS, carregar_alimentos  # noqa: E402

RES, FIG = RAIZ / "resultados", RAIZ / "figuras"
INTEGRANTES = ["Antonio Soares Couto Neto", "Rodrigo Drummond", "Thales Matheus"]
PROFESSOR = "[nome do professor]"


def br(v, casas=2):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def rs(v):
    return "R$ " + br(v)


ROTULO_RESTR = {
    "kcal_min": "Energia mínima", "kcal_max": "Energia máxima", "proteina_min": "Proteína mínima",
    "proteina_max": "Proteína máxima", "carboidrato_min": "Carboidrato mínimo",
    "carboidrato_max": "Carboidrato máximo", "gordura_min": "Gordura mínima",
    "gordura_max": "Gordura máxima", "fibra_min": "Fibra mínima", "calcio_min": "Cálcio mínimo",
    "calcio_max": "Cálcio máximo", "ferro_min": "Ferro mínimo", "ferro_max": "Ferro máximo",
    "sodio_max": "Sódio máximo", "vitamina_c_min": "Vitamina C mínima",
    "vitamina_c_max": "Vitamina C máxima", "frutas_hortalicas_min": "Frutas e hortaliças (g)",
}
UNID_RESTR = {"kcal": "kcal", "proteina": "g", "carboidrato": "g", "gordura": "g", "fibra": "g",
              "calcio": "mg", "ferro": "mg", "sodio": "mg", "vitamina": "mg", "frutas": "g"}


def lim(par):
    lo, hi = par
    if lo is None:
        return f"≤ {br(hi, 0)}"
    if hi is None:
        return f"≥ {br(lo, 0)}"
    return f"{br(lo, 0)}–{br(hi, 0)}"


def main():
    alim = carregar_alimentos()
    e1 = pd.read_csv(RES / "e1_linear.csv")
    e2 = pd.read_csv(RES / "e2_conflito_atleta.csv")
    e3 = pd.read_csv(RES / "e3_duais_custo.csv")
    e4 = pd.read_csv(RES / "e4_pareto.csv")
    e5 = pd.read_csv(RES / "e5_inteiro.csv")
    e7 = pd.read_csv(RES / "e7_cardapios.csv")
    resumo = json.loads((RES / "resumo.json").read_text(encoding="utf-8"))
    custo = e1[e1.objetivo == "custo"].set_index("perfil")

    d = Documento(
        titulo="Nutriliza", subtitulo="Otimização de Nutrientes em Atletas e Pessoas com Restrições Alimentares",
        integrantes=INTEGRANTES, disciplina="Otimização de Sistemas", professor=PROFESSOR,
        descricao="Trabalho apresentado à disciplina Otimização de Sistemas, do curso de Ciência da "
                  "Computação da Pontifícia Universidade Católica de Minas Gerais, como requisito parcial "
                  "de avaliação. Atividade: modelagem e resolução de um problema de otimização de dietas "
                  "por Programação Linear e Inteira.")

    # 1 ---------------------------------------------------------------
    d.secao("1. Introdução")
    d.paragrafo(
        "A alimentação adequada exige atender ao mesmo tempo a valores mínimos e máximos de energia, "
        "macronutrientes, vitaminas e minerais. Como muitas combinações de alimentos satisfazem essas "
        "exigências, o planejamento alimentar pode ser tratado como um problema de otimização: as "
        "quantidades de cada alimento são as variáveis de decisão, as recomendações nutricionais são as "
        "restrições e um critério, como custo ou aporte de proteína, define a melhor dieta entre as "
        "possíveis. Esse é o clássico problema da dieta, formulado por Stigler (1945) e um dos primeiros "
        "resolvidos pelo método Simplex (DANTZIG, 1990).")
    d.paragrafo(
        "O Nutriliza aplica essa ideia a pessoas com necessidades específicas: atletas, pessoas com "
        "sobrepeso ou subpeso, vegetarianos, veganos, intolerantes à lactose e celíacos. Este documento "
        "descreve o modelo, os dados, os três métodos de solução implementados pelo grupo (Simplex, "
        "Branch and Bound e Algoritmo Genético) e os resultados dos experimentos. O código, os dados e "
        "os resultados estão no repositório github.com/nietus/Nutriliza.")
    d.subsecao("1.1 Respostas aos comentários do professor")
    d.tabela("Como o trabalho atende aos comentários da proposta",
             ["Comentário", "O que foi feito", "Onde está"],
             [["Várias receitas para várias demandas (sobrepeso, subpeso, vegetarianismo, atleta)",
               "Nove perfis nutricionais, cada um com seus limites e exclusões, e um cardápio diário em "
               "porções caseiras gerado para cada perfil",
               "Seções 3.3 e 6.6; resultados/cardapios.md"],
              ["Mais de uma possibilidade de função objetivo",
               "Sete funções objetivo simples, soma ponderada e método ε-restrito com fronteiras de Pareto",
               "Seções 3.4, 6.2 e 6.4"],
              ["Outro método de solução além do Simplex",
               "Branch and Bound e Algoritmo Genético, ambos implementados do zero, comparados com o "
               "Simplex e com o resolvedor CBC",
               "Seções 4.2, 4.3 e 6.5"]],
             [3, 5, 2.4], tipo="Quadro")

    # 2 ---------------------------------------------------------------
    d.secao("2. Objetivos")
    d.lista([
        "**Objetivo geral:** formular, resolver e analisar um modelo de Programação Linear e Inteira para "
        "otimização de dietas destinadas a atletas e pessoas com restrições alimentares.",
        "**Restrições nutricionais:** garantir valores mínimos e máximos de energia e de oito nutrientes "
        "para cada perfil, além de excluir alimentos incompatíveis com cada restrição alimentar.",
        "**Critérios de otimização:** comparar funções objetivo de custo, calorias, proteína, fibra, "
        "sódio, gordura e quantidade total, e o compromisso entre dois critérios.",
        "**Métodos:** implementar o Simplex de duas fases com análise dual, o Branch and Bound para "
        "porções inteiras e um Algoritmo Genético, e comparar qualidade e tempo das soluções.",
    ])

    # 3 ---------------------------------------------------------------
    d.secao("3. Modelagem matemática")
    d.subsecao("3.1 Dados")
    d.paragrafo(
        f"A base tem {len(alim)} alimentos comuns no Brasil, com composição por 100 g retirada da Tabela "
        "Brasileira de Composição de Alimentos (TACO, NEPA-UNICAMP, 2011) e, para tofu, bebida de soja e "
        "whey, de rótulos de mercado. Cada alimento tem uma porção caseira (por exemplo, 1 concha de "
        "feijão = 140 g), um número máximo de porções por dia, um preço por 100 g (premissa de mercado "
        "de Belo Horizonte em 2026) e quatro marcadores: carne ou peixe, origem animal, lactose e glúten. "
        "A Tabela 1 mostra um recorte.")
    amostra = alim[alim.id.isin(["arroz_branco", "feijao", "frango", "ovo", "leite_integral", "tofu",
                                 "aveia", "banana", "brocolis", "whey"])]
    d.tabela("Recorte da base de alimentos (valores por porção)",
             ["Alimento", "Porção", "Custo", "kcal", "Prot. (g)", "Carb. (g)", "Gord. (g)", "Ca (mg)",
              "Fe (mg)", "Na (mg)", "Restrições"],
             [[r.nome, r.medida, rs(r.custo_porcao), br(r.kcal_porcao, 0), br(r.proteina_porcao, 1),
               br(r.carboidrato_porcao, 1), br(r.gordura_porcao, 1), br(r.calcio_porcao, 0),
               br(r.ferro_porcao, 1), br(r.sodio_porcao, 0),
               ", ".join(t for t, c in [("carne", r.carne), ("animal", r.animal), ("lactose", r.lactose),
                                        ("glúten", r.gluten)] if c) or "–"]
              for r in amostra.itertuples()],
             [2.1, 1.6, 1.1, 0.6, 0.8, 0.8, 0.8, 0.7, 0.7, 0.7, 1.3],
             fonte="Fonte: TACO (NEPA-UNICAMP, 2011); preços: premissas do grupo. Base completa em "
                   "data/alimentos.csv.", alinhar_direita={2, 3, 4, 5, 6, 7, 8, 9})

    d.subsecao("3.2 Variáveis, restrições e função objetivo")
    d.paragrafo("Considere n alimentos e m requisitos nutricionais. A variável de decisão é o número de "
                "porções diárias de cada alimento:")
    d.equacao("xᵢ = porções do alimento i por dia,   i = 1, …, n")
    d.paragrafo("Sendo aⱼᵢ a quantidade do nutriente j em uma porção do alimento i e Lⱼ e Uⱼ os limites "
                "mínimo e máximo do perfil, o modelo é:")
    d.equacao("min ou max  Z = Σᵢ cᵢ xᵢ")
    d.equacao("sujeito a   Lⱼ ≤ Σᵢ aⱼᵢ xᵢ ≤ Uⱼ,   j = 1, …, m")
    d.equacao("Σᵢ∈FH gᵢ xᵢ ≥ 400 g        0 ≤ xᵢ ≤ Mᵢ        xᵢ = 0 se o alimento i é proibido")
    d.paragrafo(
        "A segunda restrição exige pelo menos 400 g de frutas e hortaliças por dia, recomendação da OMS "
        "(WHO, 2003), em que gᵢ é o peso da porção. Mᵢ limita as porções de cada alimento e evita dietas "
        "monótonas. No modelo linear as porções são contínuas; no modelo inteiro xᵢ ∈ ℤ, o que gera "
        "porções que podem ser servidas (um ovo, dois copos de leite). Os nove nutrientes são energia, "
        "proteína, carboidrato, gordura, fibra, cálcio, ferro, sódio e vitamina C, o que dá até 17 "
        "restrições nutricionais por perfil.")

    d.subsecao("3.3 Perfis nutricionais")
    d.paragrafo(
        "Os limites foram definidos a partir das Ingestões Dietéticas de Referência (IOM, 2006), do "
        "limite de sódio da OMS (WHO, 2012), do consenso de nutrição esportiva de Thomas, Erdman e "
        "Burke (2016) e da posição sobre dietas vegetarianas de Melina, Craig e Levin (2016). Para "
        "vegetarianos o ferro mínimo é 1,8 vez maior, porque o ferro de origem vegetal é menos "
        "absorvido. O Quadro 2 resume os perfis.")
    linhas = []
    for k, cfg in PERFIS.items():
        l = cfg["limites"]
        linhas.append([cfg["nome"], lim(l["kcal"]), lim(l["proteina"]), lim(l["carboidrato"]),
                       lim(l["gordura"]), lim(l["fibra"]), lim(l["ferro"]), lim(l["sodio"]),
                       {"carne": "carnes e peixes", "animal": "todo produto animal",
                        "lactose": "lactose", "gluten": "glúten"}.get(cfg["exclui"][0], "–")
                       if cfg["exclui"] else "–"])
    d.tabela("Perfis nutricionais e limites diários",
             ["Perfil", "Energia (kcal)", "Proteína (g)", "Carb. (g)", "Gordura (g)", "Fibra (g)",
              "Ferro (mg)", "Sódio (mg)", "Exclui"],
             linhas, [2.4, 1.1, 1, 1, 0.9, 0.7, 0.8, 0.8, 1.3], tipo="Quadro",
             fonte="Fonte: elaboração do grupo com base em IOM (2006), WHO (2012), Thomas, Erdman e Burke "
                   "(2016). Todos os perfis exigem também cálcio de 1.000 a 2.500 mg, vitamina C ≥ 75 mg "
                   "(≥ 90 mg para atletas) e 400 g de frutas e hortaliças.")

    d.subsecao("3.4 Funções objetivo")
    d.paragrafo("O vetor c muda conforme o critério. Foram implementadas sete funções objetivo simples e "
                "duas formas de combinar critérios:")
    d.lista([f"**{rot}:** cᵢ = {'preço da porção' if col == 'custo' else 'peso da porção' if col == 'massa' else 'teor do nutriente na porção'}."
             for rot, _, col in OBJETIVOS.values()] + [
        "**Soma ponderada:** Z = w·custo/custo* + (1 − w)·sódio/sódio*, em que os asteriscos são os "
        "ótimos individuais, usados para normalizar as escalas.",
        "**Método ε-restrito** (HAIMES; LASDON; WISMER, 1971): minimiza o custo com o outro critério "
        "transformado em restrição (proteína ≥ ε ou sódio ≤ ε) e varia ε para traçar a fronteira de "
        "Pareto.",
    ])

    d.subsecao("3.5 Forma matricial e problema dual")
    d.paragrafo("Escrevendo as restrições de máximo como −Σ aⱼᵢ xᵢ ≥ −Uⱼ, o problema de custo mínimo fica "
                "na forma primal padrão, e o dual associa uma variável yⱼ a cada restrição:")
    d.equacao("Primal:  min cᵀx   s.a.  Ax ≥ b,  x ≥ 0")
    d.equacao("Dual:    max bᵀy   s.a.  Aᵀy ≤ c,  y ≥ 0")
    d.paragrafo(
        "No ótimo, yⱼ é o preço-sombra da restrição j: quanto o custo mínimo sobe se o limite bⱼ aumentar "
        "uma unidade. Pela folga complementar, só as restrições ativas (atendidas no limite) têm "
        "preço-sombra diferente de zero, o que mostra quais exigências realmente encarecem a dieta.")

    # 4 ---------------------------------------------------------------
    d.secao("4. Métodos de solução")
    d.paragrafo("Os três métodos foram implementados do zero em Python e NumPy (pasta nutriliza/). O "
                "resolvedor CBC, chamado pela biblioteca PuLP, foi usado só para conferir os resultados.")
    d.subsecao("4.1 Simplex de duas fases")
    d.lista([
        "**Padronização:** as variáveis são deslocadas pelo limite inferior, os limites superiores viram "
        "restrições, os lados direitos negativos têm a linha invertida e entram folgas, excessos e "
        "variáveis artificiais.",
        "**Fase 1:** minimiza a soma das artificiais. Se o mínimo for positivo, o perfil é inviável (não "
        "existe dieta que cumpra todas as restrições).",
        "**Fase 2:** otimiza a função objetivo a partir da base factível. A coluna que entra é a de "
        "custo reduzido mais negativo (regra de Dantzig); após 50 pivôs degenerados seguidos passa a "
        "valer a regra de Bland (1977), que impede ciclos.",
        "**Dual:** os preços-sombra saem de y = c_B B⁻¹, resolvendo Bᵀy = c_B com a base ótima, e são "
        "convertidos de volta ao sentido original de cada restrição.",
    ])
    d.subsecao("4.2 Branch and Bound")
    d.paragrafo(
        "Para o modelo de porções inteiras, o Branch and Bound (LAND; DOIG, 1960) resolve a relaxação "
        "linear de cada nó com o Simplex próprio. Se uma porção xⱼ sai fracionária, o nó é dividido em "
        "dois: xⱼ ≤ ⌊xⱼ⌋ e xⱼ ≥ ⌈xⱼ⌉. A variável escolhida é a mais fracionária. A busca mergulha em "
        "profundidade até achar a primeira solução inteira e depois passa a explorar o nó de melhor "
        "limite. Nós são podados por inviabilidade, por limite (relaxação pior que a melhor solução já "
        "achada) e por integralidade. Em cada nó, uma heurística de arredondamento tenta gerar soluções "
        "inteiras cedo, o que acelera as podas.")
    d.subsecao("4.3 Algoritmo Genético")
    d.paragrafo("O Algoritmo Genético (HOLLAND, 1975; GOLDBERG, 1989) trabalha diretamente com porções "
                "inteiras:")
    d.lista([
        "**Cromossomo:** vetor de inteiros com o número de porções de cada alimento, dentro de [0, Mᵢ].",
        "**Restrições:** regras de Deb (2000) no torneio binário. Solução factível vence infactível; "
        "entre factíveis vence o melhor objetivo; entre infactíveis vence a menor violação "
        "normalizada. Não há peso de penalidade para calibrar.",
        "**Operadores:** cruzamento uniforme (taxa 0,9), mutação de ±1 porção (taxa 1,5/n) com reinício "
        "ocasional do gene, e elitismo dos 6 melhores.",
        "**Busca local:** os indivíduos de elite passam por descida na vizinhança de ±1 porção e de "
        "troca de uma porção entre dois alimentos (algoritmo memético).",
        "**Parâmetros:** população de 200, 500 gerações e 10 sementes aleatórias por caso.",
    ])

    # 5 ---------------------------------------------------------------
    d.secao("5. Implementação")
    d.tabela("Organização do repositório",
             ["Pasta ou arquivo", "Conteúdo"],
             [["nutriliza/problema.py", "Estrutura do problema (c, A, b, sentidos, limites) e do resultado"],
              ["nutriliza/simplex.py", "Simplex de duas fases e cálculo dos preços-sombra"],
              ["nutriliza/branch_and_bound.py", "Branch and Bound sobre o Simplex próprio"],
              ["nutriliza/genetico.py", "Algoritmo Genético memético com regras de Deb"],
              ["nutriliza/modelo.py, perfis.py", "Leitura da base, perfis, funções objetivo e montagem do modelo"],
              ["nutriliza/referencia.py", "Mesmo modelo no CBC (PuLP), para validação"],
              ["experimentos/rodar_experimentos.py", "Experimentos, tabelas (resultados/) e figuras (figuras/)"],
              ["web/", "Interface web simples para demonstrar os modelos"],
              ["tests/", "35 testes: exemplos de livro com ótimo e duais conhecidos e comparação com o CBC"]],
             [3, 7])
    d.paragrafo("Os testes incluem o exemplo de Hillier e Lieberman (2013), cujo ótimo (Z = 36) e "
                "preços-sombra (0; 1,5; 1) são conhecidos, além de casos inviável e ilimitado.")
    d.subsecao("5.1 Interface web")
    d.paragrafo(
        "Para demonstrar o modelo, o grupo fez uma interface web simples: uma API em FastAPI "
        "(web/app.py) que chama os três métodos e uma página sem framework (web/static/). O usuário "
        "escolhe perfil, função objetivo e método, pode editar os limites de cada nutriente e vê o "
        "cardápio, os nutrientes contra os limites, os preços-sombra (no Simplex) e a convergência "
        "(no Genético). O botão Comparar métodos roda os três métodos no modelo inteiro. Para abrir, "
        "basta executar python web/app.py e acessar http://localhost:8000; parâmetros na URL, como "
        "?perfil=atleta&metodo=simplex&executar=otimizar, abrem a página já com um resultado.")
    d.figura(FIG / "web_simplex.png", "Interface web: atleta, custo mínimo, Simplex", largura_cm=9)

    # 6 ---------------------------------------------------------------
    d.secao("6. Resultados")
    d.subsecao("6.1 Dieta de custo mínimo por perfil (modelo linear)")
    d.paragrafo(
        f"O Simplex próprio resolveu os 63 casos do modelo linear (9 perfis × 7 funções objetivo) com o "
        f"mesmo valor ótimo e os mesmos preços-sombra do CBC (diferença máxima abaixo de 10⁻⁶), em média "
        f"{br(e1.iteracoes.mean(), 0)} pivôs e {br(e1.tempo_ms.mean(), 1)} ms por caso. A Tabela "
        f"{d.n_tab + 1} e a Figura {d.n_fig + 1} mostram a dieta de custo mínimo de cada perfil.")
    d.tabela("Dieta de custo mínimo por perfil (modelo linear, Simplex)",
             ["Perfil", "Custo/dia", "kcal", "Prot. (g)", "Fibra (g)", "Ferro (mg)", "Sódio (mg)",
              "Alimentos", "Pivôs"],
             [[PERFIS[p]["nome"], rs(r.custo), br(r.kcal, 0), br(r.proteina, 0), br(r.fibra, 0),
               br(r.ferro, 1), br(r.sodio, 0), r.n_alimentos, r.iteracoes]
              for p, r in custo.iterrows()],
             [2.6, 1, 0.8, 0.8, 0.8, 0.9, 0.9, 0.9, 0.7], alinhar_direita={1, 2, 3, 4, 5, 6, 7, 8})
    d.figura(FIG / "custo_por_perfil.png", "Custo mínimo diário por perfil", largura_cm=13)
    ref, at, atv = custo.loc["referencia", "custo"], custo.loc["atleta", "custo"], custo.loc["atleta_vegetariano", "custo"]
    d.paragrafo(
        f"A dieta mais barata é a do adulto de referência ({rs(ref)} por dia). Ela já não tem glúten, "
        f"por isso o perfil celíaco custa o mesmo: excluir um alimento só encarece a dieta se ele "
        f"estiver na solução ótima. O atleta custa {rs(at)}, {br((at / ref - 1) * 100, 0)}% a mais, "
        f"principalmente pela energia e pela proteína mínimas mais altas. Somar a exclusão de carnes ao "
        f"perfil de atleta eleva o custo para {rs(atv)}. O Simplex precisa de mais pivôs nos perfis "
        f"vegetariano e vegano, porque as exclusões tornam a base inicial mais distante do ótimo.")

    d.subsecao("6.2 Comparação entre funções objetivo")
    d.paragrafo(f"A Tabela {d.n_tab + 1} mostra, para o atleta, a dieta ótima de cada função objetivo avaliada em "
                "todos os critérios. A diagonal (em cada linha, o critério otimizado) é o melhor valor "
                "possível daquele critério.")
    d.tabela("Atleta: dieta ótima de cada função objetivo avaliada em todos os critérios",
             ["Função objetivo", "Custo", "kcal", "Proteína (g)", "Fibra (g)", "Sódio (mg)",
              "Gordura (g)", "Peso total (g)"],
             [[OBJETIVOS[r.objetivo][0], rs(r.custo), br(r.kcal, 0), br(r.proteina, 0), br(r.fibra, 0),
               br(r.sodio, 0), br(r.gordura, 0), br(r.massa, 0)] for r in e2.itertuples()],
             [2.8, 1, 0.8, 1, 0.8, 0.9, 0.9, 1], alinhar_direita={1, 2, 3, 4, 5, 6, 7})
    linha = e2.set_index("objetivo")
    d.paragrafo(
        f"Os critérios conflitam. Maximizar proteína leva ao teto de 180 g, mas custa "
        f"{rs(linha.loc['proteina', 'custo'])} contra {rs(linha.loc['custo', 'custo'])} da dieta mais "
        f"barata. Minimizar o peso total produz a dieta mais concentrada "
        f"({br(linha.loc['massa', 'massa'], 0)} g), mas com {br(linha.loc['massa', 'sodio'], 0)} mg de "
        f"sódio. Minimizar calorias ou gordura apenas encosta nos limites mínimos do perfil, o que mostra "
        f"que, nesses casos, a escolha do critério importa menos que os próprios limites.")

    d.subsecao("6.3 Análise dual: preços-sombra")
    d.paragrafo(f"A Tabela {d.n_tab + 1} traz os preços-sombra das restrições ativas na dieta de custo mínimo. O valor "
                "indica quanto o custo diário sobe por unidade a mais exigida.")
    piv = e3.pivot_table(index="restricao", columns="perfil", values="preco_sombra")
    perfis_dual = ["referencia", "sobrepeso", "atleta", "vegetariano", "vegano", "atleta_vegetariano"]
    ordem = ["kcal_min", "proteina_min", "carboidrato_max", "gordura_min", "calcio_min", "ferro_min",
             "frutas_hortalicas_min"]
    d.tabela("Preços-sombra na dieta de custo mínimo (R$ por unidade da restrição)",
             ["Restrição", "Referência", "Sobrepeso", "Atleta", "Vegetariano", "Vegano", "Atleta veg."],
             [[ROTULO_RESTR[r]] + [("–" if pd.isna(piv.loc[r].get(p)) else br(piv.loc[r][p], 4))
                                   for p in perfis_dual] for r in ordem if r in piv.index],
             [2.4, 1, 1, 1, 1, 1, 1], alinhar_direita={1, 2, 3, 4, 5, 6},
             fonte="Fonte: elaboração do grupo. “–”: restrição não ativa (preço-sombra zero).")
    pa, pav = piv.loc["proteina_min", "atleta"], piv.loc["proteina_min", "atleta_vegetariano"]
    fr, fv = piv.loc["ferro_min", "referencia"], piv.loc["ferro_min", "vegetariano"]
    d.lista([
        f"**Proteína do atleta:** cada grama a mais custa {rs(pa)}, ou {rs(pa * 10)} por 10 g. Sem "
        f"carnes, o preço sobe para {rs(pav)} por grama ({br((pav / pa - 1) * 100, 0)}% a mais), porque "
        f"as fontes vegetais trazem menos proteína por real.",
        f"**Ferro:** no adulto de referência, 1 mg a mais custa {rs(fr)}; no vegetariano, "
        f"{rs(fv)}. A exigência de ferro é a restrição que mais pesa para quem não come carne.",
        "**Carboidrato no sobrepeso:** o preço-sombra do teto de carboidrato é negativo. Afrouxar esse "
        "limite deixaria a dieta mais barata, porque os alimentos baratos (arroz, feijão, macarrão) são "
        "ricos em carboidrato.",
        "**Energia:** o preço-sombra da energia mínima é baixo em todos os perfis (menos de R$ 0,003 por "
        "kcal): calorias são baratas, o que encarece a dieta são proteína, ferro, cálcio e gordura "
        "de qualidade.",
    ])

    d.subsecao("6.4 Fronteiras de Pareto")
    d.paragrafo(
        f"A Figura {d.n_fig + 1}(a) aplica o método ε-restrito: minimiza o custo exigindo proteína ≥ ε, para ε "
        "variando entre os limites de cada perfil. As curvas são lineares por partes, e a inclinação de "
        "cada trecho é exatamente o preço-sombra da proteína naquele intervalo. A curva do vegano cresce "
        "mais rápido, sinal de que proteína sem produtos animais fica cara depois de certo ponto. A "
        f"Figura {d.n_fig + 1}(b) compara o ε-restrito com a soma ponderada para custo × sódio: a soma ponderada só "
        "encontra os vértices da fronteira, enquanto o ε-restrito traça a curva inteira.")
    d.figura(FIG / "pareto.png", "Fronteiras de Pareto: (a) custo × proteína; (b) custo × sódio")

    d.subsecao("6.5 Modelo inteiro: Branch and Bound × Algoritmo Genético")
    d.paragrafo(
        f"O modelo de porções inteiras foi resolvido para os 9 perfis com três funções objetivo (custo, "
        f"sódio e peso total), em 27 casos. O Branch and Bound chegou ao ótimo em todos, com o mesmo "
        f"valor do CBC, em média {br(e5.bb_nos.mean(), 0)} nós e {br(e5.bb_tempo_s.mean(), 1)} s. O "
        f"Algoritmo Genético achou soluções factíveis em todas as {int(e5.ga_factiveis.sum())} execuções, "
        f"mas ficou em média {br(e5.ga_gap_medio_pct.mean(), 1)}% acima do ótimo e chegou ao ótimo em "
        f"{br(e5.ga_otimo_pct.mean(), 0)}% das execuções, com {br(e5.ga_tempo_s.mean(), 1)} s por "
        f"execução. A Tabela {d.n_tab + 1} resume os casos de custo mínimo.")
    c5 = e5[e5.objetivo == "custo"].set_index("perfil")
    d.tabela("Custo mínimo com porções inteiras: Simplex (relaxação), Branch and Bound e Genético",
             ["Perfil", "Relaxação LP", "B&B (ótimo)", "Nós", "Tempo B&B", "AG média ± dp", "AG melhor",
              "AG no ótimo"],
             [[PERFIS[p]["nome"], rs(r.lp), rs(r.bb), r.bb_nos, br(r.bb_tempo_s, 1) + " s",
               f"{rs(r.ga_media)} ± {br(r.ga_dp)}", rs(r.ga_melhor), br(r.ga_otimo_pct, 0) + "%"]
              for p, r in c5.iterrows()],
             [2.4, 1.1, 1.1, 0.7, 0.9, 1.6, 1, 0.9], alinhar_direita={1, 2, 3, 4, 5, 6, 7},
             fonte="Fonte: elaboração do grupo. AG: 10 sementes por perfil. O CBC confirmou os ótimos do "
                   "Branch and Bound em todos os casos.")
    d.paragrafo(
        f"Exigir porções inteiras encarece a dieta em média {br(e5.gap_integralidade_pct.mean(), 1)}% em "
        f"relação à relaxação linear (gap de integralidade), porque não é possível servir, por exemplo, "
        f"0,37 copo de leite. A Figura {d.n_fig + 1} mostra o desvio médio do Genético em cada caso e a "
        f"Figura {d.n_fig + 2}, a convergência no caso do atleta.")
    d.figura(FIG / "gap_genetico.png", "Desvio médio do Algoritmo Genético em relação ao ótimo")
    d.figura(FIG / "convergencia_genetico.png", "Convergência do Algoritmo Genético (atleta, custo mínimo)")
    d.paragrafo(
        "O Genético encontra dietas factíveis rapidamente, mas tende a parar em ótimos locais quando a "
        "região factível é estreita, como no perfil de sobrepeso com sódio mínimo, em que energia, "
        "proteína e carboidrato apertam ao mesmo tempo. Para um problema deste tamanho (37 variáveis e "
        "até 18 restrições), o Branch and Bound é a melhor escolha: garante o ótimo em poucos segundos. "
        "O Genético ganha interesse quando o modelo deixa de ser linear, por exemplo com preferências "
        "de sabor, regras de combinação entre alimentos ou objetivos não lineares, casos em que o "
        "Simplex e o Branch and Bound não se aplicam diretamente.")

    d.subsecao("6.6 Cardápios gerados")
    d.paragrafo(f"A Figura {d.n_fig + 1} mostra de onde vem a energia de cada cardápio de custo mínimo "
                f"com porções inteiras, e as Tabelas {d.n_tab + 1} a {d.n_tab + 4} mostram quatro deles em "
                "medidas caseiras. Os cardápios dos nove perfis estão em resultados/cardapios.md.")
    d.figura(FIG / "composicao_cardapios.png", "Energia por grupo de alimentos nos cardápios de custo mínimo")
    from nutriliza import resumo_nutricional  # noqa: E402
    for p in ["sobrepeso", "subpeso", "atleta", "vegano"]:
        c = e7[e7.perfil == p]
        porcoes = alim.nome.map(dict(zip(c.nome, c.porcoes))).fillna(0).to_numpy()
        tot = resumo_nutricional(alim, porcoes)
        d.tabela(f"Cardápio de custo mínimo – {PERFIS[p]['nome']}",
                 ["Alimento", "Porções", "Medida caseira", "Gramas", "Custo"],
                 [[r.nome, br(r.porcoes, 0), r.medida, br(r.gramas, 0), rs(r.custo)] for r in c.itertuples()]
                 + [["Total", "", "", br(tot["massa"], 0), rs(tot["custo"])]],
                 [3, 1, 2.6, 1, 1], alinhar_direita={1, 3, 4},
                 fonte=f"Fonte: elaboração do grupo. Totais: {br(tot['kcal'], 0)} kcal; proteína "
                       f"{br(tot['proteina'], 0)} g; carboidrato {br(tot['carboidrato'], 0)} g; gordura "
                       f"{br(tot['gordura'], 0)} g; fibra {br(tot['fibra'], 0)} g; ferro {br(tot['ferro'], 1)} mg; "
                       f"sódio {br(tot['sodio'], 0)} mg.")
    d.paragrafo(
        "Os cardápios lembram a alimentação básica brasileira: arroz, feijão, leite e laranja aparecem "
        "em quase todos, porque são fontes baratas de energia, proteína, cálcio e vitamina C. O fígado "
        "bovino aparece nos perfis com mais exigência de proteína e ferro por ser a fonte animal mais "
        "barata desses nutrientes. Como todo modelo de custo mínimo, o resultado tende à monotonia: "
        "os alimentos baratos chegam ao limite máximo de porções. Os limites Mᵢ e a exigência de frutas "
        "e hortaliças reduzem esse efeito, e o modelo aceita restrições de variedade adicionais.")

    # 7 ---------------------------------------------------------------
    d.secao("7. Limitações")
    d.lista([
        "Os limites nutricionais e os preços são premissas didáticas; o modelo não substitui a "
        "prescrição de um nutricionista.",
        "A base tem 37 alimentos e 9 nutrientes. Vitaminas do complexo B, zinco e ômega-3, importantes "
        "para veganos, ficaram fora.",
        "Não há preferência de sabor nem divisão em refeições; o cardápio é diário.",
        "Biodisponibilidade, perdas no preparo e interações entre nutrientes são tratadas só de forma "
        "aproximada (fator 1,8 do ferro para vegetarianos).",
    ])

    # 8 ---------------------------------------------------------------
    d.secao("8. Conclusão")
    d.paragrafo(
        "O trabalho formulou o problema da dieta para nove perfis com necessidades distintas e o "
        "resolveu por três métodos implementados pelo grupo. O Simplex de duas fases resolve o modelo "
        "linear em milissegundos e, pela análise dual, mostra o que encarece cada dieta: proteína para "
        "o atleta, ferro para o vegetariano, o teto de carboidrato no emagrecimento. O Branch and Bound "
        "transforma a solução em porções que podem ser servidas, com garantia de otimalidade, ao custo "
        "de alguns centésimos de real por dia. O Algoritmo Genético encontra dietas factíveis sem "
        "precisar de linearidade, mas fica alguns por cento acima do ótimo neste problema.")
    d.paragrafo(
        "A comparação entre funções objetivo mostrou que custo, proteína, sódio e peso total conflitam, "
        "e as fronteiras de Pareto deixam essa troca visível para quem monta a dieta. Como próximos "
        "passos, o grupo propõe ampliar a base de alimentos e de nutrientes, dividir o cardápio em "
        "refeições e incluir preferências do usuário, caso em que o Genético passa a ter vantagem "
        "sobre os métodos exatos.")

    # Referências ------------------------------------------------------
    d.secao("Referências")
    for ref in [
        "BLAND, R. G. New finite pivoting rules for the simplex method. *Mathematics of Operations Research*, v. 2, n. 2, p. 103–107, 1977.",
        "DANTZIG, G. B. The diet problem. *Interfaces*, v. 20, n. 4, p. 43–47, 1990.",
        "DEB, K. An efficient constraint handling method for genetic algorithms. *Computer Methods in Applied Mechanics and Engineering*, v. 186, n. 2–4, p. 311–338, 2000.",
        "FORREST, J.; LOUGEE-HEIMER, R. CBC user guide. In: *INFORMS Tutorials in Operations Research*. INFORMS, 2005. p. 257–277.",
        "GOLDBERG, D. E. *Genetic algorithms in search, optimization and machine learning*. Reading: Addison-Wesley, 1989.",
        "HAIMES, Y. Y.; LASDON, L. S.; WISMER, D. A. On a bicriterion formulation of the problems of integrated system identification and system optimization. *IEEE Transactions on Systems, Man, and Cybernetics*, v. SMC-1, n. 3, p. 296–297, 1971.",
        "HILLIER, F. S.; LIEBERMAN, G. J. *Introdução à pesquisa operacional*. 9. ed. Porto Alegre: AMGH, 2013.",
        "HOLLAND, J. H. *Adaptation in natural and artificial systems*. Ann Arbor: University of Michigan Press, 1975.",
        "INSTITUTE OF MEDICINE. *Dietary reference intakes: the essential guide to nutrient requirements*. Washington, DC: The National Academies Press, 2006.",
        "LAND, A. H.; DOIG, A. G. An automatic method of solving discrete programming problems. *Econometrica*, v. 28, n. 3, p. 497–520, 1960.",
        "MELINA, V.; CRAIG, W.; LEVIN, S. Position of the Academy of Nutrition and Dietetics: vegetarian diets. *Journal of the Academy of Nutrition and Dietetics*, v. 116, n. 12, p. 1970–1980, 2016.",
        "MITCHELL, S.; O'SULLIVAN, M.; DUNNING, I. *PuLP: a linear programming toolkit for Python*. Auckland: The University of Auckland, 2011.",
        "NEPA-UNICAMP. *Tabela brasileira de composição de alimentos – TACO*. 4. ed. Campinas: NEPA-UNICAMP, 2011.",
        "STIGLER, G. J. The cost of subsistence. *Journal of Farm Economics*, v. 27, n. 2, p. 303–314, 1945.",
        "THOMAS, D. T.; ERDMAN, K. A.; BURKE, L. M. American College of Sports Medicine joint position statement: nutrition and athletic performance. *Medicine & Science in Sports & Exercise*, v. 48, n. 3, p. 543–568, 2016.",
        "WORLD HEALTH ORGANIZATION. *Diet, nutrition and the prevention of chronic diseases*. Geneva: WHO, 2003. (WHO Technical Report Series, 916).",
        "WORLD HEALTH ORGANIZATION. *Guideline: sodium intake for adults and children*. Geneva: WHO, 2012.",
    ]:
        d.referencia(ref)

    saida = RAIZ / "docs" / "Nutriliza_Documentacao.docx"
    d.salvar(saida)
    print(f"gerado: {saida}")


if __name__ == "__main__":
    main()
