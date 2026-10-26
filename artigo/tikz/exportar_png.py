"""Converte artigo/figuras_png.pdf (uma página por diagrama) em PNGs em figuras/."""
from pathlib import Path

import pymupdf

ARTIGO = Path(__file__).resolve().parent.parent
FIG = ARTIGO.parent / "figuras"
NOMES = ["diagrama_metodologia", "diagrama_simplex", "diagrama_branch_and_bound",
         "diagrama_genetico", "diagrama_cromossomo"]

pdf = pymupdf.open(ARTIGO / "figuras_png.pdf")
assert len(pdf) == len(NOMES), f"{len(pdf)} páginas, esperado {len(NOMES)}"
for pagina, nome in zip(pdf, NOMES):
    pagina.get_pixmap(dpi=250).save(FIG / f"{nome}.png")
    print(f"figuras/{nome}.png")
