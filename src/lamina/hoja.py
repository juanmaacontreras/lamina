"""A sheet: a small Markdown subset (the pizarrón note format) plus @drawing lines.

The same text gives two outputs: one image for the chat, and the Markdown appended to the
session's pizarrón note, where each @drawing becomes an ![[x.svg]] embed. docs/contrato.md
describes the format.

    # Título                       small title on top of the image
    ## Paso 2 · Residuos           section heading
    $$ 2k_1 = ... $$ ✘             display formula (one line), optional ✔ / ✘
    Texto con $x$ en línea ✔       paragraph
    - ítem                         bullet
    > [!warning] Dónde se rompió   box: warning/error (red), tip (yellow), note (blue), success (green)
    > texto del recuadro
    | a | b |                      table (the |---| row is skipped)
    @polos --ceros '±j' & @escalera 'L=1 | C=2'    drawings, side by side with &
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field

from .estilo import Tema
from .lienzo import Pieza, caja, columna, fila, formula, marca, texto

MARCAS = {"✔": True, "✓": True, "✘": False, "✗": False}
CAJAS = {"warning": "mal", "error": "mal", "danger": "mal", "bug": "mal", "tip": "aviso",
         "hint": "aviso", "pista": "aviso", "note": "acento", "info": "acento", "abstract": "acento",
         "success": "bien", "check": "bien", "ok": "bien", "question": "vivo"}


@dataclass
class Bloque:
    tipo: str                    # titulo, seccion, formula, parrafo, item, caja, tabla, dibujo
    texto: str = ""
    marca: bool | None = None
    extra: str = ""              # box kind / its title
    lineas: list[str] = field(default_factory=list)


def _sin_marca(s: str) -> tuple[str, bool | None]:
    s = s.rstrip()
    for m, ok in MARCAS.items():
        if s.endswith(m):
            return s[: -len(m)].rstrip(), ok
    return s, None


def _limpiar(s: str) -> str:
    """Markdown emphasis is not drawn: **x** and `x` become plain x."""
    return re.sub(r"\*\*(.+?)\*\*|`([^`]+)`", lambda m: m.group(1) or m.group(2), s)


def leer(fuente: str) -> list[Bloque]:
    bloques: list[Bloque] = []
    lineas = fuente.strip("\n").split("\n")
    i = 0
    while i < len(lineas):
        ln = lineas[i].rstrip()
        if not ln.strip() or ln.strip().startswith("<!--"):
            i += 1
            continue
        if ln.startswith("# "):
            bloques.append(Bloque("titulo", ln[2:].strip()))
        elif ln.startswith("## ") or ln.startswith("### "):
            t, m = _sin_marca(ln.lstrip("#").strip())
            bloques.append(Bloque("seccion", t, m))
        elif ln.strip().startswith("$$"):
            t, m = _sin_marca(ln.strip())
            bloques.append(Bloque("formula", t.strip("$").strip(), m))
        elif ln.startswith(">"):
            cab = re.match(r">\s*\[!(\w+)\]\s*(.*)", ln)
            tipo, titulo = (cab.group(1).lower(), cab.group(2)) if cab else ("note", "")
            cuerpo = [] if cab else [ln.lstrip("> ").rstrip()]
            i += 1
            while i < len(lineas) and lineas[i].startswith(">") and not re.match(r">\s*\[!", lineas[i]):
                cuerpo.append(lineas[i][1:].strip())
                i += 1
            bloques.append(Bloque("caja", titulo, None, tipo, cuerpo))
            continue
        elif ln.startswith("|"):
            filas = []
            while i < len(lineas) and lineas[i].startswith("|"):
                celdas = [c.strip() for c in lineas[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in celdas):
                    filas.append(celdas)
                i += 1
            bloques.append(Bloque("tabla", lineas=["\x1f".join(f) for f in filas]))
            continue
        elif ln.startswith("@"):
            bloques.append(Bloque("dibujo", ln))
        elif re.match(r"\s*[-*] ", ln):
            t, m = _sin_marca(re.sub(r"^\s*[-*] ", "", ln))
            bloques.append(Bloque("item", t, m))
        else:
            t, m = _sin_marca(ln)
            bloques.append(Bloque("parrafo", t, m))
        i += 1
    return bloques


def _con_marca(p: Pieza, m: bool | None, tema: Tema) -> Pieza:
    return p if m is None else fila([p, marca(m, tema)], gap=14)


def _texto_mixto(s: str, tema: Tema, **kw) -> Pieza:
    """Text where $$..$$ inside a line is drawn as inline math."""
    return texto(_limpiar(s).replace("$$", "$"), tema, **kw)


def _tabla(filas: list[list[str]], tema: Tema) -> Pieza:
    celdas = [[_texto_mixto(c, tema, ancho=40, negrita=(r == 0)) for c in f] for r, f in enumerate(filas)]
    ncol = max(len(f) for f in celdas)
    anchos = [max((f[c].ancho for f in celdas if c < len(f)), default=0) for c in range(ncol)]
    filas_p = []
    for f in celdas:
        pzs = []
        for c in range(ncol):
            p = f[c] if c < len(f) else texto(" ", tema)
            relleno = Pieza(p.svg, p.ancho, p.alto)
            pzs.append(_ancho_fijo(relleno, anchos[c]))
        filas_p.append(fila(pzs, gap=28))
    return caja(columna(filas_p, gap=10), tema, pad=14)


def _ancho_fijo(p: Pieza, ancho: float) -> Pieza:
    from .lienzo import _envolver, _ubicar
    return _envolver([_ubicar(p, 0, 0)], ancho, p.alto)


def piezas(bloques: list[Bloque], tema: Tema, dibujar) -> tuple[str | None, list[Pieza]]:
    """Turns blocks into pieces. `dibujar(linea)` renders one @drawing line into a piece."""
    titulo = None
    out: list[Pieza] = []
    for b in bloques:
        if b.tipo == "titulo":
            titulo = b.texto
        elif b.tipo == "seccion":
            out.append(_con_marca(_texto_mixto(b.texto, tema, negrita=True, color=tema.acento, tam=21),
                                  b.marca, tema))
        elif b.tipo == "formula":
            out.append(_con_marca(formula(b.texto, tema), b.marca, tema))
        elif b.tipo == "parrafo":
            out.append(_con_marca(_texto_mixto(b.texto, tema), b.marca, tema))
        elif b.tipo == "item":
            p = _con_marca(fila([texto("•", tema, color=tema.tenue), _texto_mixto(b.texto, tema)], gap=10),
                           b.marca, tema)
            p.sangria = 6
            out.append(p)
        elif b.tipo == "caja":
            color = getattr(tema, CAJAS.get(b.extra, "acento"))
            partes = []
            if b.texto:
                partes.append(_texto_mixto(b.texto, tema, negrita=True, color=color))
            partes += [_linea_caja(ln, tema) for ln in b.lineas if ln]
            out.append(caja(columna(partes, gap=8), tema, barra=color))
        elif b.tipo == "tabla":
            out.append(_tabla([ln.split("\x1f") for ln in b.lineas], tema))
        elif b.tipo == "dibujo":
            grupo = [d.strip() for d in b.texto.split(" & ")]
            dibujos = [dibujar(d) for d in grupo]
            out.append(dibujos[0] if len(dibujos) == 1 else fila(dibujos, gap=24))
    return titulo, out


def _linea_caja(ln: str, tema: Tema) -> Pieza:
    t, m = _sin_marca(ln)
    if t.strip().startswith("$$"):
        return _con_marca(formula(t.strip().strip("$"), tema), m, tema)
    return _con_marca(_texto_mixto(t, tema), m, tema)


def a_markdown(fuente: str, embeds: list[list[str]], comandos: list[str]) -> str:
    """The sheet as note Markdown. Each @line becomes its embeds plus a hidden comment with the
    command (so the drawing can be redone); `embeds[i]` holds the file names of the i-th @line.
    Blocks are separated by blank lines; a formula carrying a mark stays inline so the mark
    can follow it."""
    bloques: list[list[str]] = []
    k = 0
    for ln in fuente.strip("\n").split("\n"):
        if not ln.strip():
            continue
        if ln.startswith("@"):
            nuevo = [f"<!-- lamina {comandos[k]} -->", " ".join(f"![[{e}]]" for e in embeds[k])]
            k += 1
        elif ln.startswith("# "):
            nuevo = ["#" + ln]
        elif ln.strip().startswith("$$"):
            tex, m = _sin_marca(ln.strip())
            tex = tex.strip("$").strip()
            nuevo = [f"$$\n{tex}\n$$" if m is None else f"$\\displaystyle {tex}$ {'✔' if m else '✘'}"]
        else:
            nuevo = [ln]
        nueva_caja = re.match(r">\s*\[!", ln)
        pegado = bloques and ((ln.startswith(">") and not nueva_caja and bloques[-1][-1].startswith(">"))
                              or (ln.startswith("|") and bloques[-1][-1].startswith("|"))
                              or (re.match(r"\s*[-*] ", ln) and re.match(r"\s*[-*] ", bloques[-1][-1])))
        if pegado:
            bloques[-1].extend(nuevo)
        else:
            bloques.append(nuevo)
    return "\n\n".join("\n".join(b) for b in bloques) + "\n"


def separar_dibujo(linea: str) -> list[list[str]]:
    """'@polos --s & @bode ...' -> [['polos', '--s'], ['bode', ...]] as argv lists."""
    return [shlex.split(d.strip()[1:]) for d in linea.split(" & ")]
