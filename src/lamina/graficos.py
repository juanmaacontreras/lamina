"""Plots: pole-zero maps (s and z planes), frequency response with templates, and y = f(x)."""

from __future__ import annotations

import argparse
import re

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .estilo import Tema, matplotlib_rc  # noqa: E402
from .lienzo import Pieza, figura_svg  # noqa: E402

ANCHO_FIG = 5.6  # inches; the card adds its margin around


# ---------- parsing ----------

def _num(s: str) -> complex:
    s = s.strip().replace("i", "j").replace(",", ".").replace(" ", "")
    s = re.sub(r"(^|[+\-])j", r"\g<1>1j", s)       # bare j -> 1j
    s = re.sub(r"(\d)\*?j", r"\1j", s)
    return complex(s)


def puntos(texto: str | None) -> list[tuple[complex, int]]:
    """'0, ±j, -1±2j, ±3, 0^2' -> [(value, multiplicity)]. Separator: ';' or whitespace or ','
    between items (decimals use '.')."""
    if not texto:
        return []
    salida: list[tuple[complex, int]] = []
    for item in re.split(r"[;\s]+|,(?=\s)|,(?=[^\d])", texto.strip()):
        if not item:
            continue
        mult = 1
        if "^" in item:
            item, m = item.split("^")
            mult = int(m)
        if "±" in item or "+-" in item:
            item = item.replace("+-", "±")
            a, b = item.split("±")
            base = _num(a) if a else 0
            d = _num(b)
            salida += [(base + d, mult), (base - d, mult)]
        else:
            salida.append((_num(item), mult))
    return salida


def coeficientes(texto: str) -> np.ndarray:
    return np.array([float(c.replace(",", ".")) for c in re.split(r"[\s;]+", texto.strip()) if c])


def _fig(tema: Tema, alto: float = 4.0):
    plt.rcParams.update(matplotlib_rc(tema))
    return plt.figure(figsize=(ANCHO_FIG, alto))


def _etiqueta_valor(z: complex) -> str:
    def f(x: float) -> str:
        r = round(x, 3)
        return f"{r:g}".replace("-", "−").replace(".", ",")
    if abs(z.imag) < 1e-12:
        return f(z.real)
    if abs(z.real) < 1e-12:
        return f"{f(z.imag)}j" if abs(z.imag) != 1 else ("j" if z.imag > 0 else "−j")
    return f"{f(z.real)}{'+' if z.imag > 0 else '−'}{f(abs(z.imag))}j"


# ---------- pole-zero map ----------

def polos(args: argparse.Namespace, tema: Tema) -> Pieza:
    ceros = puntos(args.ceros)
    pols = puntos(args.polos)
    plano_z = args.plano == "z"
    fig = _fig(tema, 4.2)
    ax = fig.add_subplot(111)
    ax.set_aspect("equal")
    todos = [p for p, _ in ceros + pols] or [0j]
    lim = max(1.3 if plano_z else 1.0, max(max(abs(p.real), abs(p.imag)) for p in todos) * 1.3)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.axhline(0, color=tema.tenue, lw=1)
    ax.axvline(0, color=tema.tenue, lw=1.6 if not plano_z else 1)
    if plano_z:
        t = np.linspace(0, 2 * np.pi, 400)
        ax.plot(np.cos(t), np.sin(t), color=tema.suave, lw=1.3, ls="--")
    elif args.estable:
        ax.axvspan(-lim, 0, color=tema.bien, alpha=0.08, lw=0)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.grid(True)
    ax.set_xlabel(r"$\mathrm{Re}$" + (r"$\{z\}$" if plano_z else r"$\{s\}=\sigma$"))
    ax.set_ylabel(r"$\mathrm{Im}$" + (r"$\{z\}$" if plano_z else r"$\{s\}=\omega$"))
    for p, m in pols:
        ax.plot(p.real, p.imag, marker="x", ms=13, mew=2.8, color=tema.acento, ls="none")
        if m > 1:
            ax.annotate(f"({m})", (p.real, p.imag), xytext=(9, 7), textcoords="offset points",
                        color=tema.acento, fontsize=11)
    for c, m in ceros:
        ax.plot(c.real, c.imag, marker="o", ms=12, mew=2.6, mfc="none", color=tema.vivo, ls="none")
        if m > 1:
            ax.annotate(f"({m})", (c.real, c.imag), xytext=(9, 7), textcoords="offset points",
                        color=tema.vivo, fontsize=11)
    if args.valores:
        vistos: set[tuple[float, float]] = set()
        for p, _ in ceros + pols:
            k = (round(p.real, 6), round(p.imag, 6))
            if k in vistos:
                continue
            vistos.add(k)
            ax.annotate(_etiqueta_valor(p), (p.real, p.imag), xytext=(10, -15),
                        textcoords="offset points", color=tema.suave, fontsize=11)
    # legend by shape, not only by color
    ax.plot([], [], marker="x", ms=9, mew=2.4, color=tema.acento, ls="none", label="polo")
    ax.plot([], [], marker="o", ms=8, mew=2.2, mfc="none", color=tema.vivo, ls="none", label="cero")
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=11, labelcolor=tema.suave)
    if args.ceros_inf:
        ax.text(1.02, 0.05, f"cero en ∞: {args.ceros_inf}", transform=ax.transAxes,
                color=tema.vivo, fontsize=11)
    return figura_svg(fig)


# ---------- frequency response ----------

def _respuesta(args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, str]:
    b = coeficientes(args.num)
    a = coeficientes(args.den)
    if args.z:  # H(z) = sum b_k z^-k / sum a_k z^-k, axis Omega in [0, pi]
        w = np.linspace(0, np.pi, 2000)
        zinv = np.exp(-1j * w)
        h = np.polyval(b[::-1], zinv) / np.polyval(a[::-1], zinv)
        return w, h, r"$\Omega$"
    lo, hi = (float(x) for x in args.w.split(":")) if args.w else (None, None)
    if lo is None:
        raices = np.abs(np.concatenate([np.roots(a), np.roots(b) if len(b) > 1 else []]))
        raices = raices[raices > 1e-9]
        c = np.exp(np.mean(np.log(raices))) if raices.size else 1.0
        lo, hi = c / 100, c * 100
    w = np.logspace(np.log10(lo), np.log10(hi), 2000)
    h = np.polyval(b, 1j * w) / np.polyval(a, 1j * w)
    return w, h, r"$\omega$"


def bode(args: argparse.Namespace, tema: Tema) -> Pieza:
    w, h, xl = _respuesta(args)
    mod = np.abs(h)
    db = 20 * np.log10(np.maximum(mod, 1e-12))
    filas = 2 if args.fase else 1
    fig = _fig(tema, 3.3 * filas)
    ax = fig.add_subplot(filas, 1, 1)
    y = mod if args.lineal else (-db if args.atenuacion else db)
    ax.plot(w, y, color=tema.acento)
    if not args.z:
        ax.set_xscale("log")
    if args.z:
        ax.set_xlim(0, np.pi)
        ax.set_xticks([0, np.pi / 4, np.pi / 2, 3 * np.pi / 4, np.pi],
                      ["0", r"$\pi/4$", r"$\pi/2$", r"$3\pi/4$", r"$\pi$"])
    ax.set_ylabel(r"$|H|$" if args.lineal else (r"$A$ [dB]" if args.atenuacion else r"$|H|$ [dB]"))
    if not args.lineal:
        piso = np.percentile(y, 2 if not args.atenuacion else 98)
        if args.atenuacion:
            ax.set_ylim(min(-1, y.min() - 3), max(piso, 10))
        else:
            ax.set_ylim(max(piso, y.max() - 80), y.max() + 5)
    ax.grid(True, which="both")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if args.marcar is not None:
        nivel = args.marcar
        ax.axhline(nivel, color=tema.aviso, lw=1.2, ls="--")
        cruces = np.where(np.diff(np.sign(y - nivel)))[0]
        for i in cruces[:3]:
            x0 = w[i] + (w[i + 1] - w[i]) * (nivel - y[i]) / (y[i + 1] - y[i])
            ax.axvline(x0, color=tema.aviso, lw=1, ls=":")
            ax.annotate(f"{x0:.3g}".replace(".", ","), (x0, nivel), xytext=(5, 6), textcoords="offset points",
                        color=tema.aviso, fontsize=11)
    if args.plantilla:
        _plantilla(ax, args.plantilla, tema, atenuacion=args.atenuacion)
    if args.fase:
        ax2 = fig.add_subplot(2, 1, 2, sharex=ax)
        ax2.plot(w, np.degrees(np.unwrap(np.angle(h))), color=tema.vivo)
        ax2.set_ylabel(r"fase [°]")
        ax2.grid(True, which="both")
        for s in ("top", "right"):
            ax2.spines[s].set_visible(False)
        ax2.set_xlabel(xl)
    else:
        ax.set_xlabel(xl)
    fig.tight_layout()
    return figura_svg(fig)


def _plantilla(ax, texto: str, tema: Tema, atenuacion: bool) -> None:
    """'wp=1 Ap=3 ws=2 As=40' (low-pass; add tipo=pa for high-pass): shades the forbidden zones."""
    p = {k.strip(): float(v.replace(",", ".")) for k, v in
         (x.split("=") for x in re.split(r"[\s;]+", texto.strip()) if "=" in x and not x.startswith("tipo"))}
    pasa_altos = "tipo=pa" in texto
    wp, ws, ap, as_ = p["wp"], p["ws"], p.get("Ap", 3), p.get("As", 40)
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    kw = dict(color=tema.mal, alpha=0.18, lw=0)
    banda_paso = (x0, wp) if not pasa_altos else (wp, x1)
    banda_rech = (ws, x1) if not pasa_altos else (x0, ws)
    if atenuacion:
        ax.fill_between(banda_paso, ap, y1, **kw)
        ax.fill_between(banda_rech, y0, as_, **kw)
    else:
        ax.fill_between(banda_paso, y0, -ap, **kw)
        ax.fill_between(banda_rech, -as_, y1, **kw)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)


# ---------- y = f(x) ----------

_SEGURO = {k: getattr(np, k) for k in ("sin", "cos", "tan", "exp", "log", "log10", "sqrt", "abs",
                                          "arctan", "arcsin", "arccos", "sinh", "cosh", "tanh",
                                          "arccosh", "arcsinh", "pi", "e", "where", "sign")}
_SEGURO.update(ln=np.log, atan=np.arctan, acosh=np.arccosh, cosh=np.cosh)


def _evaluar(expr: str, x: np.ndarray) -> np.ndarray:
    expr = expr.replace("^", "**")
    with np.errstate(all="ignore"):
        y = eval(expr, {"__builtins__": {}}, {**_SEGURO, "x": x})  # noqa: S307 - local tool, own input
    return np.broadcast_to(np.asarray(y, dtype=float), x.shape)


def curva(args: argparse.Namespace, tema: Tema) -> Pieza:
    lo, hi = (float(v) for v in args.x.split(":"))
    x = np.linspace(lo, hi, 1500)
    fig = _fig(tema, 3.6)
    ax = fig.add_subplot(111)
    colores = [tema.acento, tema.vivo, tema.aviso, tema.bien]
    estilos = ["-", "--", "-.", ":"]
    for i, e in enumerate(args.expr):
        nombre, _, cuerpo = e.partition("=") if "=" in e else ("", "", e)
        y = _evaluar(cuerpo or nombre, x)
        ax.plot(x, y, color=colores[i % 4], ls=estilos[i % 4],
                label=f"${nombre.strip()}$" if cuerpo and len(args.expr) > 1 else None)
    if args.y:
        ax.set_ylim(*(float(v) for v in args.y.split(":")))
    if args.logx:
        ax.set_xscale("log")
    ax.axhline(0, color=tema.tenue, lw=0.8)
    ax.grid(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlabel(f"${args.xlabel}$")
    if len(args.expr) > 1:
        ax.legend(labelcolor=tema.suave)
    fig.tight_layout()
    return figura_svg(fig)
