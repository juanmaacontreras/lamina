"""The ecosystem's shared look: Nord tokens and the bundled fonts.

Tokens copied once from ebook-reader/client/src/styles/tokens.css (Atril; same family as
Bitácora and cerebro-app). Dark = Polar Night, light = Snow Storm. If the shared tokens change,
change them there first and copy them here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FUENTES = Path(__file__).parent / "fuentes"
MATE = str(FUENTES / "latinmodern-math.otf")
TEXTO = str(FUENTES / "lmroman10-regular.otf")
NEGRITA = str(FUENTES / "lmroman10-bold.otf")


@dataclass(frozen=True)
class Tema:
    fondo: str   # the image background (paper in dark, card in light: prints white-ish)
    caja: str    # boxes inside the image (hint, correction)
    linea: str   # grid and thin rules
    tinta: str   # main ink
    suave: str   # secondary ink
    tenue: str   # titles, axis ticks
    acento: str  # poles, highlights
    vivo: str    # zeros, second series
    mal: str     # wrong step
    bien: str    # right step
    aviso: str   # warnings, marks on plots


TEMAS = {
    "oscuro": Tema(fondo="#2E3440", caja="#3B4252", linea="#434C5E", tinta="#ECEFF4",
                   suave="#D8DEE9", tenue="#9AA4B6", acento="#81A1C1", vivo="#88C0D0",
                   mal="#BF616A", bien="#A3BE8C", aviso="#EBCB8B"),
    "claro": Tema(fondo="#FAFBFC", caja="#E5E9F0", linea="#D8DEE9", tinta="#2E3440",
                  suave="#4C566A", tenue="#7A869B", acento="#5E81AC", vivo="#3F86B0",
                  mal="#BF616A", bien="#5F8A4E", aviso="#C2784F"),
}

# Sizes in px at zoom 1 (the PNG is rendered at zoom 2).
TAM_FORMULA = 26
TAM_TEXTO = 19
TAM_TITULO = 17
MARGEN = 26
SEPARACION = 18
RADIO = 14
ZOOM = 2
ANCHO_TEXTO = 64  # characters per line in boxes


def colores_latex(tema: Tema) -> dict[str, str]:
    """Names usable as \\color{name}{...} inside formulas."""
    return {k: getattr(tema, k) for k in ("tinta", "suave", "tenue", "acento", "vivo", "mal", "bien", "aviso")}


def matplotlib_rc(tema: Tema) -> dict:
    """rcParams for every matplotlib-based drawing: text as paths, Latin Modern text, CM math."""
    from matplotlib import font_manager
    if "Latin Modern Roman" not in {f.name for f in font_manager.fontManager.ttflist}:
        font_manager.fontManager.addfont(TEXTO)
    return {
        "svg.fonttype": "path",
        "mathtext.fontset": "cm",
        "font.family": "serif",
        "font.serif": ["Latin Modern Roman", "DejaVu Serif"],
        "axes.unicode_minus": True,
        "font.size": 13,
        "text.color": tema.tinta,
        "axes.edgecolor": tema.tenue,
        "axes.labelcolor": tema.suave,
        "axes.facecolor": "none",
        "figure.facecolor": "none",
        "xtick.color": tema.tenue,
        "ytick.color": tema.tenue,
        "grid.color": tema.linea,
        "grid.linewidth": 0.7,
        "lines.linewidth": 2.0,
        "legend.frameon": False,
        "savefig.transparent": True,
        "svg.hashsalt": "lamina",  # stable ids: the same command gives the same file
    }
