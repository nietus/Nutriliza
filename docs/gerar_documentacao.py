"""Gera docs/Nutriliza_Documentacao.docx no template da PUC Minas, com os números
lidos de resultados/ (rode experimentos/rodar_experimentos.py antes).

A documentação é a versão direta do trabalho: o que foi feito, como e o que
saiu. O detalhamento fica no artigo (artigo/).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "docs"))

from modelo_docx import Documento  # noqa: E402
from nutriliza import OBJETIVOS, PERFIS  # noqa: E402

RES, FIG = RAIZ / "resultados", RAIZ / "figuras"
INTEGRANTES = ["Antonio Soares Couto Neto", "Rodrigo Drummond", "Thales Matheus"]
PROFESSOR = "Maury Gouvêa"


def br(v, casas=2):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def rs(v):
    return "R$ " + br(v)


def lim(par):
    lo, hi = par
    if lo is None:
        return f"≤ {br(hi, 0)}"
    if hi is None:
        return f"≥ {br(lo, 0)}"
    return f"{br(lo, 0)}–{br(hi, 0)}"


EXCLUI = {"carne": "carnes e peixes", "animal": "todo produto animal", "lactose": "lactose",
          "gluten": "glúten"}


def main():
    e1 = pd.read_csv(RES / "e1_linear.csv")
    e2 = pd.read_csv(RES / "e2_conflito_atleta.csv").set_index("objetivo")
    e3 = pd.read_csv(RES / "e3_duais_custo.csv")
    e5 = pd.read_csv(RES / "e5_inteiro.csv")
    e7 = pd.read_csv(RES / "e7_cardapios.csv")
    custo = e1[e1.objetivo == "custo"].set_index("perfil")
    piv = e3.pivot_table(index="restricao", columns="perfil", values="preco_sombra")
    imp = e3.pivot_table(index="restricao", columns="perfil", values="impacto")

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
        "Montar uma dieta é escolher quanto comer de cada alimento para atender a limites mínimos e "
        "máximos de energia e nutrientes. Como muitas combinações atendem a esses limites, dá para "
        "tratar o problema como otimização: as porções são as variáveis, as recomendações são as "
        "restrições e um critério, como o custo, escolhe a melhor dieta. É o clássico problema da dieta "
        "(STIGLER, 1945; DANTZIG, 1990).")
    d.paragrafo(
        "O Nutriliza aplica esse modelo a perfis com necessidades diferentes, como atletas, pessoas com "
        "sobrepeso ou subpeso, vegetarianos e pessoas com restrições alimentares, e o resolve por três "
        "métodos: Simplex, Branch and Bound e Algoritmo Genético. O código, os dados e os resultados "
        "estão em github.com/nietus/Nutriliza.")

    # 2 ---------------------------------------------------------------
    d.secao("2. Objetivos")
    d.lista([
        "Formular o problema da dieta por Programação Linear e Inteira para perfis com restrições "
        "diferentes.",
        "Comparar funções objetivo diferentes (custo, proteína, sódio, entre outras).",
        "Resolver o modelo pelo Simplex, por Branch and Bound e por um Algoritmo Genético, e comparar os "
        "resultados.",
        "Usar a análise dual para entender quais exigências encarecem cada dieta.",
    ])

    # 3 ---------------------------------------------------------------
    d.secao("3. Modelo")
    d.paragrafo(
        "A base tem 37 alimentos comuns no Brasil, com composição da tabela TACO (NEPA-UNICAMP, 2011), "
        "porção caseira, preço e marcadores de carne, origem animal, lactose e glúten. A variável xᵢ é o "
        "número de porções do alimento i por dia, e aⱼᵢ é a quantidade do nutriente j em uma porção:")
    d.equacao("min ou max  Z = Σᵢ cᵢ xᵢ")
    d.equacao("sujeito a   Lⱼ ≤ Σᵢ aⱼᵢ xᵢ ≤ Uⱼ   (9 nutrientes)")
    d.equacao("frutas e hortaliças ≥ 400 g,   0 ≤ xᵢ ≤ Mᵢ,   xᵢ = 0 para alimentos proibidos")
    d.paragrafo(
        "Os nutrientes são energia, proteína, carboidrato, gordura, fibra, cálcio, ferro, sódio e "
        "vitamina C. No modelo linear as porções podem ser fracionadas; no modelo inteiro, não. Cada "
        "perfil muda os limites Lⱼ e Uⱼ e a lista de alimentos proibidos (Quadro 1).")
    linhas = []
    for cfg in PERFIS.values():
        l = cfg["limites"]
        linhas.append([cfg["nome"], lim(l["kcal"]), lim(l["proteina"]), lim(l["ferro"]),
                       EXCLUI.get(cfg["exclui"][0], "–") if cfg["exclui"] else "–"])
    d.tabela("Perfis nutricionais (limites diários)",
             ["Perfil", "Energia (kcal)", "Proteína (g)", "Ferro (mg)", "Exclui"],
             linhas, [3, 1.4, 1.2, 1, 1.8], tipo="Quadro",
             fonte="Fonte: elaboração do grupo com base nas DRIs (IOM, 2006), na OMS (WHO, 2012) e em "
                   "Thomas, Erdman e Burke (2016). Os demais limites estão em nutriliza/perfis.py.")
    d.paragrafo("As funções objetivo disponíveis são:")
    d.lista([", ".join(rot for rot, _, _ in OBJETIVOS.values()) + ".",
             "Combinação de dois critérios por soma ponderada ou pelo método ε-restrito, que gera a "
             "fronteira de Pareto (por exemplo, custo × proteína)."])

    # 4 ---------------------------------------------------------------
    d.secao("4. Métodos de solução")
    d.paragrafo(
        "Os três métodos foram implementados pelo grupo em Python, sem bibliotecas de otimização; o "
        "resolvedor CBC foi usado só para conferir as respostas. Todos recebem o mesmo modelo e devolvem "
        "uma dieta, mas resolvem versões diferentes dele: o Simplex resolve o modelo linear (porções "
        "fracionadas), e o Branch and Bound e o Genético resolvem o modelo inteiro (porções inteiras). "
        "A Figura 1 mostra como as peças se ligam.")
    d.figura(FIG / "diagrama_metodologia.png", "Visão geral: dados e perfil formam o modelo, que é "
             "resolvido pelos três métodos", largura_cm=15)
    d.tabela("Resumo dos métodos",
             ["", "Simplex", "Branch and Bound", "Algoritmo Genético"],
             [["Modelo resolvido", "Linear (porções fracionadas)", "Inteiro (porções inteiras)",
               "Inteiro (porções inteiras)"],
              ["Tipo", "Exato", "Exato", "Heurístico (metaheurística)"],
              ["Garante o ótimo?", "Sim", "Sim", "Não"],
              ["O que devolve além da dieta", "Preços-sombra (duais)", "Nós explorados e limite",
               "Curva de convergência"],
              ["Arquivo", "nutriliza/simplex.py", "nutriliza/branch_and_bound.py", "nutriliza/genetico.py"]],
             [2.2, 2.4, 2.4, 2.4], fonte="Fonte: elaboração do grupo.")

    d.subsecao("4.1 Simplex de duas fases")
    d.paragrafo(
        "**Ideia.** Em um modelo linear, o conjunto de dietas factíveis é um poliedro, e a melhor dieta "
        "está sempre em um vértice. O Simplex anda de vértice em vértice, sempre para um vizinho que "
        "melhora o objetivo, até que nenhum vizinho seja melhor. Cada vértice corresponde a uma base: um "
        "conjunto de variáveis que podem ser diferentes de zero. Trocar de vértice é um pivô: uma "
        "variável entra na base e outra sai.")
    d.paragrafo("**Passo a passo.**")
    d.lista([
        "**Padronização:** toda restrição vira igualdade. Restrições de mínimo (≥) ganham uma variável "
        "de excesso, as de máximo (≤) uma de folga, e os limites de porção xᵢ ≤ Mᵢ viram restrições.",
        "**Fase 1 (achar uma dieta factível):** como não se sabe de início nenhuma dieta que atenda a "
        "tudo, entram variáveis artificiais que fazem as restrições valerem \"à força\". A fase 1 "
        "minimiza a soma dessas artificiais. Se a soma chega a zero, achou-se uma dieta factível; se "
        "não, o perfil é inviável (não existe dieta que cumpra todas as exigências).",
        "**Fase 2 (melhorar até o ótimo):** a partir da dieta factível, cada pivô escolhe a variável "
        "que mais reduz o custo por unidade acrescentada (custo reduzido mais negativo, regra de "
        "Dantzig) e a que sai pelo teste da razão mínima, que garante que nenhuma restrição seja "
        "violada. Quando nenhum custo reduzido é negativo, a dieta é ótima.",
        "**Proteção contra ciclos:** problemas de dieta têm muitos pivôs degenerados (que não mudam o "
        "custo). Depois de 50 seguidos, o método passa a usar a regra de Bland (menor índice), que "
        "garante que o algoritmo termina.",
        "**Preços-sombra:** na base ótima B, o sistema Bᵀy = c_B dá a variável dual yₖ de cada "
        "restrição. Ela diz quanto o custo mínimo sobe se a exigência k aumentar uma unidade; por "
        "exemplo, quanto custa 1 g a mais de proteína.",
    ])
    d.figura(FIG / "diagrama_simplex.png", "Fluxo do Simplex de duas fases", largura_cm=15)
    d.paragrafo(
        "**Exemplo pequeno.** Com dois alimentos, A (R$ 2 por porção) e B (R$ 3), e duas exigências, "
        "A + B ≥ 4 unidades de um nutriente e A + 3B ≥ 6 unidades de outro, o Simplex chega à dieta "
        "3 porções de A e 1 de B, que custa R$ 9. Os preços-sombra são 1,5 e 0,5: exigir uma unidade a "
        "mais do primeiro nutriente encarece a dieta em R$ 1,50, e do segundo, em R$ 0,50. Esse caso "
        "faz parte dos testes automáticos do projeto (tests/test_solvers.py).")
    d.paragrafo(
        "**Quando usar.** É o método mais rápido (milissegundos) e o único que dá os preços-sombra, mas "
        "só resolve o modelo linear: a dieta pode sair com 2,53 copos de leite.")

    d.subsecao("4.2 Branch and Bound")
    d.paragrafo(
        "**Ideia.** Para obter porções inteiras, não basta arredondar a solução do Simplex: o "
        "arredondamento pode violar alguma restrição ou deixar de ser o melhor. O Branch and Bound "
        "divide o problema em subproblemas menores (branch) e descarta os que não podem conter a melhor "
        "dieta (bound), usando o Simplex para avaliar cada um.")
    d.paragrafo("**Passo a passo.**")
    d.lista([
        "**Raiz:** resolve o modelo com porções fracionadas pelo Simplex. Esse valor é um limite: "
        "nenhuma dieta inteira pode ser mais barata que ele.",
        "**Ramificação:** se alguma porção xⱼ sai fracionária (por exemplo, 2,5), cria dois ramos: "
        "um com xⱼ ≤ 2 e outro com xⱼ ≥ 3. A solução fracionária deixa de ser possível nos dois, mas "
        "nenhuma solução inteira é perdida. A variável escolhida é a mais fracionária (mais próxima de "
        "0,5).",
        "**Avaliação de cada ramo:** o Simplex resolve o ramo. Se a solução for inteira, ela vira a "
        "melhor dieta conhecida (incumbente). Uma heurística de arredondamento também tenta achar "
        "dietas inteiras em cada ramo, para ter uma incumbente cedo.",
        "**Poda:** um ramo é descartado se for inviável, se seu valor não for melhor que a incumbente "
        "(poda por limite) ou se já for inteiro. É a poda que evita testar todas as combinações.",
        "**Ordem de busca:** primeiro desce em profundidade até achar uma dieta inteira; depois "
        "explora sempre o ramo aberto de menor custo (best-bound). Quando não sobra ramo aberto, a "
        "incumbente é comprovadamente ótima.",
    ])
    d.paragrafo(
        "**Exemplo.** Na dieta de custo mínimo do atleta, o Simplex sugere 2,53 copos de leite e 0,85 "
        "bife de fígado, entre outras porções fracionadas. O Branch and Bound cria os ramos \"leite ≤ "
        "2\" e \"leite ≥ 3\", resolve cada um com o Simplex e continua ramificando as porções que "
        "ainda saem fracionadas. A dieta inteira ótima custa R$ 14,45, contra R$ 13,99 da versão "
        "fracionada.")
    d.figura(FIG / "diagrama_branch_and_bound.png", "Esquema da árvore do Branch and Bound; os nós "
             "sombreados são podados", largura_cm=15)
    nos_medio = br(e5.bb_nos.mean(), 0)
    d.paragrafo(
        f"**Quando usar.** É a escolha para o modelo inteiro: garante o ótimo. Neste problema explorou "
        f"em média {nos_medio} nós e levou poucos segundos, mas o número de nós pode crescer muito em "
        f"modelos maiores.")

    d.subsecao("4.3 Algoritmo Genético")
    d.paragrafo(
        "**Ideia.** Inspirado na evolução natural, o Algoritmo Genético mantém uma população de dietas "
        "que se combinam e sofrem pequenas mudanças. As melhores têm mais chance de passar adiante, e a "
        "população melhora geração após geração. Não usa o Simplex nem precisa que o modelo seja "
        "linear, mas não garante o ótimo.")
    d.figura(FIG / "diagrama_cromossomo.png", "Cromossomo: um gene por alimento, com o número de "
             "porções; o gene sombreado é de um alimento excluído pelo perfil", largura_cm=13)
    d.paragrafo("**Passo a passo.**")
    d.lista([
        "**Cromossomo:** cada dieta é um vetor de 37 inteiros, um por alimento, com o número de porções "
        "entre 0 e Mᵢ. Alimentos proibidos pelo perfil têm Mᵢ = 0 e ficam sempre zerados.",
        "**População inicial:** 200 dietas sorteadas ao acaso. Quase nenhuma atende às restrições no "
        "início.",
        "**Avaliação:** cada dieta recebe o valor do objetivo (por exemplo, o custo) e a violação total, "
        "a soma de quanto cada restrição foi desrespeitada, dividida pelo seu limite para pôr kcal, "
        "gramas e miligramas na mesma escala.",
        "**Seleção (torneio binário com regras de Deb):** sorteiam-se duas dietas e fica a melhor: uma factível "
        "sempre vence uma infactível; entre factíveis vence a de menor custo; entre infactíveis vence a "
        "de menor violação. Assim não é preciso calibrar um peso de penalidade.",
        "**Cruzamento uniforme (90%):** o filho herda cada alimento de um dos dois pais, sorteado.",
        "**Mutação:** cada gene tem chance de 1,5/37 (cerca de 4%) de ganhar ou perder uma porção, o "
        "que muda em média 1,5 alimento por filho, e chance quatro vezes menor de ser sorteado de novo.",
        "**Elitismo e busca local:** as 6 melhores dietas passam direto para a próxima geração e são "
        "refinadas testando +1/−1 porção de cada alimento e trocas de uma porção entre dois alimentos, "
        "aceitando a melhor mudança, por até 37 passos. Sem essa busca local, o algoritmo raramente "
        "saía das dietas infactíveis.",
        "**Parada:** após 500 gerações. Como é aleatório, cada caso foi rodado com 10 sementes.",
    ])
    d.figura(FIG / "diagrama_genetico.png", "Fluxo do Algoritmo Genético", largura_cm=15)
    d.paragrafo(
        "**Quando usar.** Neste problema linear perde para o Branch and Bound em qualidade e tempo. "
        "Passa a valer a pena quando o modelo deixa de ser linear, por exemplo com preferências de "
        "sabor ou regras de combinação entre alimentos, casos em que o Simplex e o Branch and Bound não "
        "se aplicam diretamente.")

    # 5 ---------------------------------------------------------------
    d.secao("5. Resultados")
    d.paragrafo(
        f"O Simplex e o Branch and Bound chegaram ao mesmo ótimo do CBC em todos os {len(e1) + len(e5)} "
        f"casos testados (9 perfis com 7 funções objetivo no modelo linear e 3 no inteiro).")

    d.subsecao("5.1 Custo mínimo por perfil")
    d.figura(FIG / "custo_por_perfil.png", "Custo mínimo diário por perfil (modelo linear)", largura_cm=13)
    ref, at, atv = custo.loc["referencia", "custo"], custo.loc["atleta", "custo"], custo.loc["atleta_vegetariano", "custo"]
    d.lista([
        f"A dieta mais barata é a do adulto de referência ({rs(ref)} por dia). Ela já não tem glúten, "
        f"por isso o perfil celíaco custa o mesmo.",
        f"O atleta custa {rs(at)}, {br((at / ref - 1) * 100, 0)}% a mais, pela energia e proteína "
        f"maiores. Sem carnes, sobe para {rs(atv)}.",
    ])

    d.subsecao("5.2 Funções objetivo e análise dual")
    d.paragrafo(
        f"Os critérios conflitam. Para o atleta, maximizar proteína custa {rs(e2.loc['proteina', 'custo'])} "
        f"por dia, contra {rs(e2.loc['custo', 'custo'])} da dieta mais barata. Os preços-sombra mostram "
        f"o que encarece cada dieta:")
    pa, pav = piv.loc["proteina_min", "atleta"], piv.loc["proteina_min", "atleta_vegetariano"]
    d.lista([
        f"Cada grama a mais de proteína custa {rs(pa)} ao atleta e {rs(pav)} ao atleta vegetariano.",
        f"Cada mg a mais de ferro custa {rs(piv.loc['ferro_min', 'referencia'])} ao adulto de "
        f"referência e {rs(piv.loc['ferro_min', 'vegetariano'])} ao vegetariano.",
        f"Energia é barata por kcal, mas como a exigência é grande, ela responde por "
        f"{rs(imp.loc['kcal_min', 'referencia'])} dos {rs(ref)} do adulto de referência.",
        f"No vegano, o cálcio pesa mais que o ferro: {rs(imp.loc['calcio_min', 'vegano'])} contra "
        f"{rs(imp.loc['ferro_min', 'vegano'])} do custo diário.",
    ])
    d.figura(FIG / "pareto.png", "Fronteiras de Pareto: (a) custo × proteína; (b) custo × sódio")

    d.subsecao("5.3 Branch and Bound × Algoritmo Genético")
    resumo = []
    for obj in ["custo", "sodio", "massa"]:
        x = e5[e5.objetivo == obj]
        resumo.append([OBJETIVOS[obj][0], br(x.bb_tempo_s.mean(), 1) + " s",
                       br(x.ga_gap_medio_pct.mean(), 1) + "%", br(x.ga_otimo_pct.mean(), 0) + "%",
                       br(x.ga_tempo_s.mean(), 1) + " s"])
    d.tabela("Modelo inteiro: médias dos 9 perfis por função objetivo",
             ["Função objetivo", "Tempo B&B", "AG acima do ótimo", "AG no ótimo", "Tempo AG"],
             resumo, [3, 1.2, 1.5, 1.2, 1.1], alinhar_direita={1, 2, 3, 4},
             fonte="Fonte: elaboração do grupo. O Branch and Bound achou o ótimo em todos os casos; "
                   "o Genético rodou 10 vezes por caso.")
    d.paragrafo(
        f"O Branch and Bound é a melhor escolha neste problema: garante o ótimo e roda em poucos "
        f"segundos. O Genético sempre achou dietas válidas, mas ficou em média "
        f"{br(e5.ga_gap_medio_pct.mean(), 1)}% acima do ótimo. Exigir porções inteiras encarece a dieta "
        f"de custo mínimo em média "
        f"{br(e5[e5.objetivo == 'custo'].gap_integralidade_pct.mean(), 1)}% em relação ao modelo "
        f"linear.")

    d.subsecao("5.4 Exemplo de cardápio")
    c = e7[e7.perfil == "atleta"]
    d.tabela("Cardápio de custo mínimo do atleta (porções inteiras)",
             ["Alimento", "Porções", "Medida caseira", "Custo"],
             [[r.nome, br(r.porcoes, 0), r.medida, rs(r.custo)] for r in c.itertuples()]
             + [["Total", "", "", rs(c.custo.sum())]],
             [3.2, 1, 2.8, 1.2], alinhar_direita={1, 3},
             fonte="Fonte: elaboração do grupo. Os cardápios dos nove perfis estão em "
                   "resultados/cardapios.md.")

    # 6 ---------------------------------------------------------------
    d.secao("6. Como executar")
    d.lista([
        "**Instalar:** pip install -r requirements.txt",
        "**Experimentos:** python experimentos/rodar_experimentos.py (gera resultados/ e figuras/).",
        "**Interface web:** python web/app.py e abrir http://localhost:8000. A página permite escolher "
        "perfil, função objetivo e método, editar os limites e comparar os três métodos.",
    ])
    d.figura(FIG / "web_simplex.png", "Interface web: atleta, custo mínimo, Simplex", largura_cm=12)

    # 7 ---------------------------------------------------------------
    d.secao("7. Conclusão")
    d.paragrafo(
        "O problema da dieta foi modelado para nove perfis e resolvido por três métodos. O Simplex "
        "resolve o modelo linear em milissegundos e, pela análise dual, mostra o que encarece cada dieta. "
        "O Branch and Bound gera porções inteiras com otimalidade garantida. O Genético funciona, mas "
        "fica alguns por cento acima do ótimo; ele passa a valer a pena se o modelo deixar de ser linear, "
        "por exemplo com preferências de sabor. Os limites e preços são premissas didáticas, e o modelo "
        "não substitui um nutricionista.")

    # Referências ------------------------------------------------------
    d.secao("Referências")
    for ref in [
        "BLAND, R. G. New finite pivoting rules for the simplex method. *Mathematics of Operations Research*, v. 2, n. 2, p. 103–107, 1977.",
        "DANTZIG, G. B. The diet problem. *Interfaces*, v. 20, n. 4, p. 43–47, 1990.",
        "DEB, K. An efficient constraint handling method for genetic algorithms. *Computer Methods in Applied Mechanics and Engineering*, v. 186, n. 2–4, p. 311–338, 2000.",
        "HOLLAND, J. H. *Adaptation in natural and artificial systems*. Ann Arbor: University of Michigan Press, 1975.",
        "INSTITUTE OF MEDICINE. *Dietary reference intakes: the essential guide to nutrient requirements*. Washington, DC: The National Academies Press, 2006.",
        "LAND, A. H.; DOIG, A. G. An automatic method of solving discrete programming problems. *Econometrica*, v. 28, n. 3, p. 497–520, 1960.",
        "NEPA-UNICAMP. *Tabela brasileira de composição de alimentos – TACO*. 4. ed. Campinas: NEPA-UNICAMP, 2011.",
        "STIGLER, G. J. The cost of subsistence. *Journal of Farm Economics*, v. 27, n. 2, p. 303–314, 1945.",
        "THOMAS, D. T.; ERDMAN, K. A.; BURKE, L. M. American College of Sports Medicine joint position statement: nutrition and athletic performance. *Medicine & Science in Sports & Exercise*, v. 48, n. 3, p. 543–568, 2016.",
        "WORLD HEALTH ORGANIZATION. *Guideline: sodium intake for adults and children*. Geneva: WHO, 2012.",
    ]:
        d.referencia(ref)

    saida = RAIZ / "docs" / "Nutriliza_Documentacao.docx"
    d.salvar(saida)
    print(f"gerado: {saida}")


if __name__ == "__main__":
    main()
