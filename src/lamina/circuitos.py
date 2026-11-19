"""Circuits with schemdraw: ladder networks from a short text, and digital filter block diagrams."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402
import schemdraw  # noqa: E402
import schemdraw.dsp as dsp  # noqa: E402
import schemdraw.elements as elm  # noqa: E402

from .estilo import Tema, matplotlib_rc  # noqa: E402
from .graficos import coeficientes  # noqa: E402
from .lienzo import Pieza, figura_svg  # noqa: E402

schemdraw.use("matplotlib")

U = 3.0      # element length
H = 3.0      # ladder height
PASO = 1.2   # minimum wire between two shunt branches
TANQUE = 0.9  # half width of a shunt LC tank


@dataclass
class Item:
    tipo: str            # L, C, R, tanque, serie, fuente, carga
    etiqueta: str        # mathtext label (may be empty)
    pos: str = ""        # "s" series, "p" shunt, "" = alternate
    partes: tuple = ()   # for tanque/serie: two (tipo, etiqueta)
    carga: bool = False  # the load resistor that closes the ladder


def _etiqueta(nombre: str, valor: str | None) -> str:
    m = re.fullmatch(r"([A-Za-z]+)(\w*)", nombre)
    base, sub = (m.group(1), m.group(2)) if m else (nombre, "")
    if len(base) > 1:  # Rg, RL -> R_g, R_L
        base, sub = base[0], base[1:] + sub
    tex = base + (f"_{{{sub}}}" if sub else "")
    if valor:
        tex += "=" + valor.replace("*", r"\cdot ")
    return f"${tex}$"


def _simple(token: str) -> tuple[str, str]:
    nombre, _, valor = token.partition("=")
    nombre = nombre.strip()
    tipo = nombre[0].upper()
    if tipo not in "LCR":
        raise ValueError(f"no entiendo el elemento {token!r}: empieza con L, C o R")
    return tipo, _etiqueta(nombre, valor.strip() or None)


def leer_escalera(texto: str) -> list[Item]:
    """'Rg=1 | L1=1 | C2=2 | tanque(L3=1,C3=1/2) | RL=1' -> items. Prefix s: or p: forces position."""
    items: list[Item] = []
    for tok in [t.strip() for t in re.split(r"\|(?![^(]*\))", texto) if t.strip()]:
        pos = ""
        if re.match(r"^[sp]:", tok):
            pos, tok = tok[0], tok[2:].strip()
        compuesto = re.fullmatch(r"(tanque|serie)\((.*)\)", tok)
        nombre = tok.partition("=")[0].strip()
        if compuesto:
            a, b = (x.strip() for x in compuesto.group(2).split(","))
            items.append(Item(compuesto.group(1), "", pos, (_simple(a), _simple(b))))
        elif nombre in ("Rg", "Vg") or (nombre.lower().startswith("rg")):
            items.append(Item("fuente", _etiqueta(nombre, tok.partition("=")[2] or None)
                              if nombre != "Vg" else ""))
        elif nombre in ("RL", "Rl", "Rc"):
            items.append(Item("R", _etiqueta(nombre, tok.partition("=")[2] or None), "p", carga=True))
        else:
            tipo, et = _simple(tok)
            items.append(Item(tipo, et, pos))
    return items


def _elemento(tipo: str):
    return {"L": elm.Inductor2, "C": elm.Capacitor, "R": elm.Resistor}[tipo]


def _rama(d: schemdraw.Drawing, x: float, y: float, tipo: str, partes: tuple, etiqueta: str,
          vertical: bool) -> None:
    """One element or a two-element composite between (x, y) and one U away (right or down)."""
    if tipo in "LCR":
        e = _elemento(tipo)().at((x, y))
        if vertical:
            d.add(e.down().length(H).label(etiqueta, loc="bottom", ofst=0.25))
        else:
            d.add(e.right().length(U).label(etiqueta, loc="top"))
        return
    (t1, e1), (t2, e2) = partes
    if tipo == "serie":
        if vertical:
            d.add(_elemento(t1)().at((x, y)).down().length(H / 2).label(e1, loc="bottom", ofst=0.25))
            d.add(_elemento(t2)().down().length(H / 2).label(e2, loc="bottom", ofst=0.25))
        else:
            d.add(_elemento(t1)().at((x, y)).right().length(U / 2 + .5).label(e1, loc="top"))
            d.add(_elemento(t2)().right().length(U / 2 + .5).label(e2, loc="top"))
        return
    # tanque: two branches in parallel
    a = TANQUE
    if vertical:
        d.add(elm.Line().at((x, y)).down().length(0.5))
        d.add(elm.Line().at((x - a, y - 0.5)).right().length(2 * a))
        d.add(_elemento(t1)().at((x - a, y - 0.5)).down().length(H - 1).label(e1, loc="top", ofst=0.25))
        d.add(_elemento(t2)().at((x + a, y - 0.5)).down().length(H - 1).label(e2, loc="bottom", ofst=0.25))
        d.add(elm.Line().at((x - a, y - H + 0.5)).right().length(2 * a))
        d.add(elm.Line().at((x, y - H + 0.5)).down().length(0.5))
    else:
        ancho = U + 1
        d.add(elm.Line().at((x, y)).right().length(0.5))
        d.add(elm.Line().at((x + 0.5, y - a)).up().length(2 * a))
        d.add(_elemento(t1)().at((x + 0.5, y + a)).right().length(ancho - 1).label(e1, loc="top"))
        d.add(_elemento(t2)().at((x + 0.5, y - a)).right().length(ancho - 1).label(e2, loc="bottom"))
        d.add(elm.Line().at((x + ancho - 0.5, y - a)).up().length(2 * a))
        d.add(elm.Line().at((x + ancho - 0.5, y)).right().length(0.5))


def _ancho(it: Item) -> float:
    return U + 1 if it.tipo in ("tanque", "serie") else U


def _ancho_etiqueta(et: str) -> float:
    """Rough width of a mathtext label in drawing units (fontsize 15)."""
    visible = re.sub(r"\\\w+|[${}_^]", "", et)
    return 0.36 * len(visible) + 0.2


def _extension(it: Item) -> tuple[float, float]:
    """How far a shunt branch (and its labels) reaches left and right of its node."""
    if it.tipo == "tanque":
        a = TANQUE
        return a + _ancho_etiqueta(it.partes[0][1]) + 0.6, a + _ancho_etiqueta(it.partes[1][1]) + 0.6
    if it.tipo == "serie":
        return 0.5, 0.7 + max(_ancho_etiqueta(e) for _, e in it.partes)
    return 0.5, 0.7 + _ancho_etiqueta(it.etiqueta)


def escalera(args: argparse.Namespace, tema: Tema) -> Pieza:
    items = leer_escalera(args.red)
    plt.rcParams.update(matplotlib_rc(tema))
    schemdraw.config(color=tema.tinta, lw=1.8, fontsize=15, font="serif", bgcolor="none")
    d = schemdraw.Drawing(show=False)
    x = 0.0
    fuente = items and items[0].tipo == "fuente"
    if fuente:
        f = items.pop(0)
        d.add(elm.SourceSin().at((0, -H)).up().length(H).label(r"$V_g$", loc="bottom", ofst=0.3))
        if f.etiqueta:
            d.add(elm.Resistor().at((0, 0)).right().length(U).label(f.etiqueta, loc="top"))
            x = U
    else:
        d.add(elm.Dot(open=True).at((0, 0)))
        d.add(elm.Dot(open=True).at((0, -H)))
        if args.entrada:
            d.add(elm.Arrow().at((-0.2, -H / 2)).right().length(1.4)
                  .label(f"${args.entrada}$", loc="top", ofst=0.15))
        d.add(elm.Line().at((0, 0)).right().length(0.6))
        x = 0.6
    siguiente = args.empieza
    ultimo_p = False
    alcance = x  # rightmost x reached by the previous shunt branch and its label
    posiciones = []
    for it in items:
        pos = it.pos or siguiente
        posiciones.append(pos)
        siguiente = "p" if pos == "s" else "s"
    for i, (it, pos) in enumerate(zip(items, posiciones)):
        if pos == "s":
            # stretch with wire so the next shunt's left labels clear the previous shunt's right ones
            if i + 1 < len(items) and posiciones[i + 1] == "p" and ultimo_p:
                falta = alcance + _extension(items[i + 1])[0] + 0.3 - (x + _ancho(it))
                if falta > 0:
                    d.add(elm.Line().at((x, 0)).right().length(falta / 2))
                    x += falta / 2
                    _rama(d, x, 0, it.tipo, it.partes, it.etiqueta, vertical=False)
                    x += _ancho(it)
                    d.add(elm.Line().at((x, 0)).right().length(falta / 2))
                    x += falta / 2
                else:
                    _rama(d, x, 0, it.tipo, it.partes, it.etiqueta, vertical=False)
                    x += _ancho(it)
            else:
                _rama(d, x, 0, it.tipo, it.partes, it.etiqueta, vertical=False)
                x += _ancho(it)
            ultimo_p = False
        else:
            izq, der = _extension(it)
            if ultimo_p:
                minimo = max(alcance + izq, x + PASO)
            else:
                minimo = max(x, alcance + izq) if i else max(x, izq + 0.3, 2.0 if args.entrada else 0)
            if minimo > x:
                d.add(elm.Line().at((x, 0)).right().length(minimo - x))
                x = minimo
            alcance = x + der
            d.add(elm.Dot().at((x, 0)))
            _rama(d, x, 0, it.tipo, it.partes, it.etiqueta, vertical=True)
            d.add(elm.Dot().at((x, -H)))
            ultimo_p = True
    terminado = bool(items) and items[-1].carga
    if not terminado:
        cola = max(0.8, alcance - x + 0.3) if ultimo_p else 0.8
        d.add(elm.Line().at((x, 0)).right().length(cola))
        x += cola
        d.add(elm.Dot(open=True).at((x, 0)))
        d.add(elm.Dot(open=True).at((x, -H)))
    d.add(elm.Line().at((0, -H)).right().length(x))
    fig = d.draw(show=False).fig
    return figura_svg(fig)


# ---------- block diagrams ----------

def _num(v: float) -> str:
    return f"{v:.4g}".replace(".", "{,}")


def bloques(args: argparse.Namespace, tema: Tema) -> Pieza:
    """Direct form II (canonical): one delay column, feedback gains on the left, feedforward on the
    right, each side a chain of adders. Without --a it is the FIR tapped delay line."""
    b = coeficientes(args.b)
    a = coeficientes(args.a) if args.a else coeficientes("1")
    b, a = b / a[0], a / a[0]
    n = max(len(b), len(a)) - 1
    fir = len(a) == 1
    plt.rcParams.update(matplotlib_rc(tema))
    schemdraw.config(color=tema.tinta, lw=1.6, fontsize=15, font="serif", bgcolor="none")
    d = schemdraw.Drawing(show=False)
    fila, sal = 2.2, 0.9                       # row step; wire from the column to a gain
    xl = 1.8
    xc = 1.6 if fir else xl + 3.8
    xr = xc + 3.8

    def ganancia(y: float, valor: float, hacia: str):
        signo = 1 if hacia == "right" else -1
        d.add(elm.Line().at((xc, y)).to((xc + signo * sal, y)))
        amp = dsp.Amp().at((xc + signo * sal, y)).anchor("input")
        amp = amp.right() if hacia == "right" else amp.left()
        amp.label(f"${_num(valor)}$", loc="top" if hacia == "right" else "bottom", ofst=0.1)
        return d.add(amp)

    def cadena(x: float, filas: list[int], hacia: str, valores: dict[int, float]) -> dict:
        """Adders at every row but the last; the last gain climbs into the adder above it."""
        sumas = {r: d.add(dsp.Sum().right().at((x, -r * fila)).anchor("center")) for r in filas[:-1] or filas}
        for r in filas:
            if r == 0 and not fir and hacia == "left":
                continue
            amp = ganancia(-r * fila, valores[r], hacia)
            if r in sumas:
                d.add(elm.Arrow().at(amp.out).to(sumas[r].W if hacia == "right" else sumas[r].E))
            else:
                d.add(elm.Line().at(amp.out).to((x, -r * fila)))
                arriba = max(q for q in sumas if q < r)
                d.add(elm.Arrow().at((x, -r * fila)).to(sumas[arriba].S))
        orden = sorted(sumas)
        for r1, r2 in zip(orden, orden[1:]):
            d.add(elm.Arrow().at(sumas[r2].N).to(sumas[r1].S))
        return sumas

    # input side
    if fir:
        d.add(elm.Line().at((0, 0)).to((xc, 0)).label(r"$x[n]$", loc="left"))
    else:
        fb = [k for k in range(1, len(a)) if a[k] != 0]
        izq = cadena(xl, [0] + fb, "left", {k: -a[k] for k in fb})
        d.add(elm.Arrow().at((0, 0)).to(izq[0].W).label(r"$x[n]$", loc="left"))
        d.add(elm.Line().at(izq[0].E).to((xc, 0)))
        d.add(elm.Label().at((xc - 0.7, 0.35)).label(r"$w[n]$", loc="center"))
    # delay column
    for k in range(1, n + 1):
        y0 = -(k - 1) * fila
        d.add(dsp.Dot().at((xc, y0)))
        caja = d.add(dsp.Box(w=1.2, h=0.9).right().at((xc, y0 - 0.55)).anchor("N").label(r"$z^{-1}$"))
        d.add(elm.Arrow().at((xc, y0)).to(caja.N))
        d.add(elm.Line().at(caja.S).to((xc, -k * fila)))
    if n:
        d.add(dsp.Dot().at((xc, -n * fila)))
    # output side
    taps = [k for k in range(len(b)) if b[k] != 0]
    der = cadena(xr, taps, "right", {k: b[k] for k in taps})
    d.add(elm.Arrow().at(der[min(der)].E).to((xr + 1.6, -min(der) * fila)).label(r"$y[n]$", loc="right"))
    fig = d.draw(show=False).fig
    return figura_svg(fig)
