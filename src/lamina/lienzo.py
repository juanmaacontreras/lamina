"""The canvas: every drawing is a column of pieces (SVG fragments) on one rounded card.

A piece is an SVG string with its size in px. Formulas and text come from ziamath (text as
paths, Latin Modern), plots and circuits from matplotlib/schemdraw (text as paths too), so the
final SVG has no fonts or files outside itself and renders the same on any machine.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
from dataclasses import dataclass
from pathlib import Path

import resvg_py
import ziamath as zm

from . import __version__
from .estilo import (ANCHO_TEXTO, MARGEN, MATE, NEGRITA, RADIO, SEPARACION, TAM_FORMULA,
                     TAM_TEXTO, TAM_TITULO, ZOOM, Tema, colores_latex)

zm.config.svg2 = False  # inline glyph paths: no shared <defs> ids between pieces

_UNIDADES = {"px": 1.0, "pt": 4 / 3, "in": 96.0, "mm": 96 / 25.4, "cm": 96 / 2.54, "": 1.0}
_RAIZ = re.compile(r"<svg\b[^>]*>", re.S)


@dataclass
class Pieza:
    svg: str
    ancho: float
    alto: float
    sangria: float = 0.0  # left indent inside the card


def _medida(valor: str) -> float:
    m = re.fullmatch(r"\s*([-\d.eE+]+)\s*([a-z]*)\s*", valor)
    if not m:
        raise ValueError(f"medida SVG que no entiendo: {valor!r}")
    return float(m.group(1)) * _UNIDADES.get(m.group(2), 1.0)


def desde_svg(svg: str, escala: float = 1.0) -> Pieza:
    """Wraps any standalone SVG as a piece, reading its size from the root element."""
    svg = re.sub(r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>", "", svg, flags=re.S).strip()
    raiz = _RAIZ.search(svg)
    if not raiz:
        raise ValueError("no es un SVG")
    tag = raiz.group(0)
    ancho = re.search(r'\swidth="([^"]+)"', tag)
    alto = re.search(r'\sheight="([^"]+)"', tag)
    vb = re.search(r'\sviewBox="([^"]+)"', tag)
    if vb:
        _, _, vw, vh = (float(v) for v in vb.group(1).replace(",", " ").split())
    if ancho and alto:
        w, h = _medida(ancho.group(1)), _medida(alto.group(1))
    elif vb:
        w, h = vw, vh
    else:
        raise ValueError("SVG sin tamaño")
    if not vb:
        tag2 = tag[:-1] + f' viewBox="0 0 {float(re.match(r"[-\d.]+", ancho.group(1)).group(0))} ' \
                          f'{float(re.match(r"[-\d.]+", alto.group(1)).group(0))}">'
        svg = svg.replace(tag, tag2, 1)
    return Pieza(svg=svg, ancho=w * escala, alto=h * escala)


def _ubicar(p: Pieza, x: float, y: float) -> str:
    """The piece's SVG as a nested <svg> placed at (x, y) with its px size."""
    tag = _RAIZ.search(p.svg).group(0)
    limpio = re.sub(r'\s(x|y|width|height)="[^"]*"', "", tag)
    nuevo = limpio[:-1] + f' x="{x:.2f}" y="{y:.2f}" width="{p.ancho:.2f}" height="{p.alto:.2f}">'
    return p.svg.replace(tag, nuevo, 1)


def _colores(tex: str, tema: Tema) -> str:
    for nombre, hexa in colores_latex(tema).items():
        tex = tex.replace("{" + nombre + "}", "{" + hexa + "}")
    return tex


def formula(tex: str, tema: Tema, tam: float = TAM_FORMULA, color: str | None = None) -> Pieza:
    m = zm.Latex(_colores(tex, tema), size=tam, font=MATE, color=color or tema.tinta)
    return desde_svg(m.svg())


def _visible(palabra: str) -> int:
    """Rough printed length: a LaTeX command counts as one glyph, markup counts as nothing."""
    return len(re.sub(r"[${}_^]", "", re.sub(r"\\[A-Za-z]+", "x", palabra)))


def _partir(s: str, ancho: int) -> list[str]:
    """Greedy wrap at `ancho` printed characters, never breaking a $math$ chunk."""
    protegido = re.sub(r"\$[^$]*\$", lambda m: m.group(0).replace(" ", "\x00"), s)
    lineas: list[str] = []
    actual, largo = [], 0
    for p in protegido.split():
        n = _visible(p)
        if actual and largo + 1 + n > ancho:
            lineas.append(" ".join(actual))
            actual, largo = [], 0
        largo += n + (1 if actual else 0)
        actual.append(p)
    if actual:
        lineas.append(" ".join(actual))
    return [ln.replace("\x00", " ") for ln in lineas] or [""]


def texto(s: str, tema: Tema, tam: float = TAM_TEXTO, color: str | None = None,
          negrita: bool = False, ancho: int = ANCHO_TEXTO) -> Pieza:
    """Text with inline $math$, wrapped; **bold** at the start of the text is supported."""
    lineas: list[str] = []
    for parrafo in s.split("\n"):
        lineas.extend(_partir(parrafo, ancho))
    cuerpo = "\n".join(lineas)
    # ziamath misplaces inline math when a separate text font is set: the plain text then uses the
    # math font's own upright letters (same Latin Modern look). Bold only for text without math.
    fuente = NEGRITA if negrita and "$" not in cuerpo else None
    t = zm.Text(_colores(cuerpo, tema), textfont=fuente,
                mathfont=MATE, size=tam, color=color or tema.tinta, linespacing=1.25)
    return desde_svg(t.svg())


def marca(ok: bool, tema: Tema, tam: float = 22) -> Pieza:
    """A check mark or a cross, drawn as paths (no font needed)."""
    c = tema.bien if ok else tema.mal
    if ok:
        trazo = f'<path d="M3 {tam*.55} L{tam*.4} {tam*.88} L{tam-2} {tam*.12}" '
    else:
        trazo = f'<path d="M4 4 L{tam-4} {tam-4} M{tam-4} 4 L4 {tam-4}" '
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{tam}" height="{tam}" '
           f'viewBox="0 0 {tam} {tam}">{trazo}fill="none" stroke="{c}" stroke-width="3.2" '
           f'stroke-linecap="round" stroke-linejoin="round"/></svg>')
    return desde_svg(svg)


def fila(piezas: list[Pieza], gap: float = 18) -> Pieza:
    """Pieces side by side, vertically centered."""
    ancho = sum(p.ancho for p in piezas) + gap * (len(piezas) - 1)
    alto = max(p.alto for p in piezas)
    x, partes = 0.0, []
    for p in piezas:
        partes.append(_ubicar(p, x, (alto - p.alto) / 2))
        x += p.ancho + gap
    return _envolver(partes, ancho, alto)


def columna(piezas: list[Pieza], gap: float = SEPARACION) -> Pieza:
    ancho = max(p.sangria + p.ancho for p in piezas)
    alto = sum(p.alto for p in piezas) + gap * (len(piezas) - 1)
    y, partes = 0.0, []
    for p in piezas:
        partes.append(_ubicar(p, p.sangria, y))
        y += p.alto + gap
    return _envolver(partes, ancho, alto)


def caja(contenido: Pieza, tema: Tema, barra: str | None = None, pad: float = 16,
         ancho_min: float = 0) -> Pieza:
    """A rounded box in the box color, with an optional colored bar on the left."""
    bar = 8 if barra else 0
    ancho = max(contenido.ancho + 2 * pad + bar, ancho_min)
    alto = contenido.alto + 2 * pad
    partes = [f'<rect x="0" y="0" width="{ancho:.2f}" height="{alto:.2f}" rx="10" fill="{tema.caja}"/>']
    if barra:  # a rounded bar inset on the left
        partes.append(f'<rect x="9" y="9" width="4" height="{alto - 18:.2f}" rx="2" fill="{barra}"/>')
    partes.append(_ubicar(contenido, bar + pad, pad))
    return _envolver(partes, ancho, alto)


def _envolver(partes: list[str], ancho: float, alto: float) -> Pieza:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{ancho:.2f}" height="{alto:.2f}" viewBox="0 0 {ancho:.2f} {alto:.2f}">'
           + "".join(partes) + "</svg>")
    return Pieza(svg=svg, ancho=ancho, alto=alto)


def tarjeta(piezas: list[Pieza], tema: Tema, titulo: str | None = None) -> str:
    """The final image: title (if any) and the pieces on the card background."""
    todas = ([texto(titulo, tema, tam=TAM_TITULO, color=tema.tenue, ancho=90)] if titulo else []) + piezas
    cuerpo = columna(todas)
    ancho, alto = cuerpo.ancho + 2 * MARGEN, cuerpo.alto + 2 * MARGEN
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{ancho:.2f}" height="{alto:.2f}" viewBox="0 0 {ancho:.2f} {alto:.2f}">'
            f'<rect width="{ancho:.2f}" height="{alto:.2f}" rx="{RADIO}" fill="{tema.fondo}"/>'
            + _ubicar(cuerpo, MARGEN, MARGEN) + "</svg>")


def figura_svg(fig) -> Pieza:
    """A matplotlib figure as a piece (text already as paths through the rc)."""
    import matplotlib.pyplot as plt
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.06,
                metadata={"Date": None, "Creator": None, "Format": None, "Type": None})
    plt.close(fig)
    return desde_svg(buf.getvalue())


# ---------- output and cache ----------

def carpeta_cache() -> Path:
    base = Path(os.environ.get("LAMINA_CACHE", Path.home() / ".cache" / "lamina"))
    base.mkdir(parents=True, exist_ok=True)
    return base


def _huella_codigo() -> str:
    """Changes whenever the package code changes, so the cache never serves an old drawing."""
    h = hashlib.sha256(__version__.encode())
    for f in sorted(Path(__file__).parent.glob("*.py")):
        h.update(f.read_bytes())
    return h.hexdigest()


_HUELLA = _huella_codigo()


def clave(*partes: object) -> str:
    return hashlib.sha256(repr((_HUELLA,) + partes).encode()).hexdigest()[:12]


def png_de(svg: str) -> bytes:
    return bytes(resvg_py.svg_to_bytes(svg_string=svg, zoom=ZOOM))


def guardar(svg: str, nombre: str, salida: str | None = None) -> tuple[Path, Path]:
    """Writes NAME.svg and NAME.png in the cache (or next to `salida`) and returns both paths."""
    if salida:
        png = Path(salida).with_suffix(".png")
        png.parent.mkdir(parents=True, exist_ok=True)
    else:
        png = carpeta_cache() / f"{nombre}.png"
    svgp = png.with_suffix(".svg")
    svgp.write_text(svg, encoding="utf-8")
    png.write_bytes(png_de(svg))
    return png, svgp


def en_cache(nombre: str) -> tuple[Path, Path] | None:
    png = carpeta_cache() / f"{nombre}.png"
    return (png, png.with_suffix(".svg")) if png.exists() and png.with_suffix(".svg").exists() else None
