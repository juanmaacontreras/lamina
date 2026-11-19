"""lamina <tipo> ... : one drawing per command. Prints the PNG path (for the chat) and the SVG path.

Every command takes --claro (light theme, for printing), --titulo, -o (output path) and
--pizarron NOTE.md (appends the drawing to the session note, with its SVG next to it).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import shlex
import sys
from pathlib import Path

from . import hoja
from .estilo import TEMAS
from .lienzo import Pieza, clave, en_cache, formula, guardar, tarjeta



def _comunes(p: argparse.ArgumentParser) -> None:
    p.add_argument("--claro", action="store_true", help="tema claro (para imprimir)")
    p.add_argument("--titulo", help="título chico arriba")
    p.add_argument("-o", "--salida", help="ruta del PNG (el SVG va al lado)")
    p.add_argument("--pizarron", metavar="NOTA.md", help="sumar el dibujo a esta nota")


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="lamina", description="Dibujos para el chat de estudio.")
    sub = ap.add_subparsers(dest="tipo", required=True)

    p = sub.add_parser("formula", help="pasos en LaTeX, con ✔/✘ y recuadros")
    p.add_argument("pasos", nargs="+", help="una fórmula LaTeX por paso")
    p.add_argument("--mal", type=int, nargs="*", default=[], help="pasos (desde 1) marcados ✘")
    p.add_argument("--bien", type=int, nargs="*", default=[], help="pasos marcados ✔")
    p.add_argument("--pista", help="recuadro amarillo (puede llevar $math$)")
    p.add_argument("--error", help="recuadro rojo «Dónde se rompió»")
    _comunes(p)

    p = sub.add_parser("polos", help="mapa de polos y ceros en el plano s o z")
    p.add_argument("--plano", choices=("s", "z"), default="s")
    p.add_argument("--z", dest="plano", action="store_const", const="z", help="atajo de --plano z")
    p.add_argument("--polos", help="p. ej. '0 ±2j -1±j 0^2'")
    p.add_argument("--ceros")
    p.add_argument("--valores", action="store_true", help="escribir el valor de cada punto")
    p.add_argument("--estable", action="store_true", help="sombrear el semiplano izquierdo")
    p.add_argument("--ceros-inf", help="texto para ceros en infinito, p. ej. '1'")
    _comunes(p)

    p = sub.add_parser("bode", help="módulo (y fase) de H(s) o H(z)")
    p.add_argument("--num", required=True, help="coeficientes, potencias decrecientes de s "
                                                 "(con --z: b0 b1 ... en z^-k)")
    p.add_argument("--den", required=True)
    p.add_argument("--z", action="store_true", help="H(z): eje Ω de 0 a π")
    p.add_argument("--w", help="rango de ω, p. ej. 0.01:100")
    p.add_argument("--fase", action="store_true")
    p.add_argument("--lineal", action="store_true", help="|H| lineal en vez de dB")
    p.add_argument("--atenuacion", action="store_true", help="graficar A = −20 log|H|")
    p.add_argument("--marcar", type=float, help="nivel a marcar con sus cruces, p. ej. -3")
    p.add_argument("--plantilla", help="'wp=1 Ap=3 ws=2 As=40' (tipo=pa para pasa altos)")
    _comunes(p)

    p = sub.add_parser("curva", help="y = f(x), una o varias")
    p.add_argument("expr", nargs="+", help="'y=1/(1+x^4)' (numpy: sin, exp, sqrt, cosh, ...)")
    p.add_argument("--x", default="0:5", help="rango, p. ej. 0:3")
    p.add_argument("--y", help="rango vertical")
    p.add_argument("--logx", action="store_true")
    p.add_argument("--xlabel", default="x")
    _comunes(p)

    p = sub.add_parser("escalera", help="red en escalera: 'Rg=1 | L1=1 | C2=2 | tanque(L3=1,C3=1) | RL=1'")
    p.add_argument("red")
    p.add_argument("--empieza", choices=("s", "p"), default="s",
                   help="primer elemento en serie (s) o en derivación (p)")
    p.add_argument("--entrada", help="flecha de entrada, p. ej. 'Z(s)'")
    _comunes(p)

    p = sub.add_parser("bloques", help="filtro digital en forma directa II (o FIR)")
    p.add_argument("--b", required=True, help="b0 b1 ... (numerador en z^-k)")
    p.add_argument("--a", help="1 a1 a2 ... (denominador en z^-k); sin --a es FIR")
    _comunes(p)

    p = sub.add_parser("completar", help="dibujar los SVG que le faltan a notas del pizarrón")
    p.add_argument("rutas", nargs="+", help="notas o carpetas")

    p = sub.add_parser("hoja", help="hoja completa en Markdown con @dibujos (de un archivo o de stdin)")
    p.add_argument("archivo", nargs="?", default="-")
    _comunes(p)
    return ap


def _dibujar(args: argparse.Namespace) -> list[Pieza]:
    tema = TEMAS["claro" if args.claro else "oscuro"]
    if args.tipo == "polos":
        from .graficos import polos
        return [polos(args, tema)]
    if args.tipo == "bode":
        from .graficos import bode
        return [bode(args, tema)]
    if args.tipo == "curva":
        from .graficos import curva
        return [curva(args, tema)]
    if args.tipo == "escalera":
        from .circuitos import escalera
        return [escalera(args, tema)]
    if args.tipo == "bloques":
        from .circuitos import bloques
        return [bloques(args, tema)]
    if args.tipo == "formula":
        return hoja.piezas(hoja.leer(_formula_a_hoja(args)), tema, None)[1]
    raise ValueError(args.tipo)


def _formula_a_hoja(args: argparse.Namespace) -> str:
    lineas = []
    for i, f in enumerate(args.pasos, 1):
        m = " ✘" if i in args.mal else " ✔" if i in args.bien else ""
        lineas.append(f"$$ {f} $${m}")
    if args.error:
        lineas += ["> [!warning] Dónde se rompió", f"> {args.error}"]
    if args.pista:
        lineas += ["> [!tip] Pista", f"> {args.pista}"]
    return "\n".join(lineas)


def _subparser_args(argv: list[str], claro: bool) -> argparse.Namespace:
    a = parser().parse_args(argv)
    a.claro = claro
    return a


def dibujar_hoja(fuente: str, claro: bool) -> tuple[str, list[tuple[str, str]]]:
    """Renders a sheet. Returns its SVG and, per @line, (command, SVG of that drawing alone)."""
    tema = TEMAS["claro" if claro else "oscuro"]
    sueltos: list[tuple[str, str]] = []

    def dibujar(linea: str) -> Pieza:
        argv = hoja.separar_dibujo(linea)[0]
        p = _dibujar(_subparser_args(argv, claro))[0]
        sueltos.append((shlex.join(argv + (["--claro"] if claro else [])), tarjeta([p], tema)))
        return p

    titulo, pzs = hoja.piezas(hoja.leer(fuente), tema, dibujar)
    return tarjeta(pzs, tema, titulo), sueltos


def _agregar_al_pizarron(nota: Path, markdown: str) -> None:
    hoy = dt.date.today().isoformat()
    if not nota.exists():
        nota.parent.mkdir(parents=True, exist_ok=True)
        nota.write_text(f"---\ntipo: pizarrón\nfecha: {hoy}\norigen: Claude\n---\n\n"
                        f"# {nota.stem}\n", encoding="utf-8")
    actual = nota.read_text(encoding="utf-8")
    sep = "" if actual.endswith("\n\n") else "\n" if actual.endswith("\n") else "\n\n"
    nota.write_text(actual + sep + markdown, encoding="utf-8")


_CON_NUMEROS = ("--x", "--y", "--w", "--polos", "--ceros", "--num", "--den", "--b", "--a")


def _rangos_negativos(argv: list[str]) -> list[str]:
    """'--x -1:1' -> '--x=-1:1': argparse would take a value starting with '-' for an option."""
    out: list[str] = []
    for a in argv:
        if out and out[-1] in _CON_NUMEROS and re.match(r"-[\d.j±]", a):
            out[-1] = f"{out[-1]}={a}"
        else:
            out.append(a)
    return out


def _sin_salida(argv: list[str]) -> list[str]:
    """The command as it is recorded in the note: without where its files went."""
    out, saltar = [], False
    for a in argv:
        if saltar:
            saltar = False
        elif a in ("--pizarron", "-o", "--salida"):
            saltar = True
        elif not a.startswith(("--pizarron=", "--salida=")):
            out.append(a)
    return out


def completar(rutas: list[str]) -> list[Path]:
    """Draws every ![[lamina-*.svg]] a note names but does not have yet (notes written from a
    cloud session carry only the commands). Returns the files it wrote."""
    hechos: list[Path] = []
    notas = [p for r in rutas for p in (sorted(Path(r).rglob("*.md")) if Path(r).is_dir() else [Path(r)])]
    patron = re.compile(r"<!-- lamina (.+?) -->\n((?:!\[\[lamina-\w+\.svg\]\] ?)+)")
    for nota in notas:
        for m in patron.finditer(nota.read_text(encoding="utf-8")):
            for cmd in m.group(1).split(" & "):
                destino = nota.parent / nombre_en_nota(cmd)
                if destino.exists():
                    continue
                argv = shlex.split(cmd)
                a = parser().parse_args(_rangos_negativos(argv))
                tema = TEMAS["claro" if a.claro else "oscuro"]
                svg = tarjeta(_dibujar(a), tema, getattr(a, "titulo", None))
                destino.write_text(svg, encoding="utf-8")
                hechos.append(destino)
    return hechos


def nombre_en_nota(cmd: str) -> str:
    """The SVG's name in the vault depends only on the command, so `completar` can rebuild it."""
    return f"lamina-{hashlib.sha256(cmd.encode()).hexdigest()[:12]}.svg"


def _svg_al_lado(nota: Path, svg: str, cmd: str) -> str:
    nota.parent.mkdir(parents=True, exist_ok=True)
    archivo = nombre_en_nota(cmd)
    (nota.parent / archivo).write_text(svg, encoding="utf-8")
    return archivo


def main(argv: list[str] | None = None) -> int:
    argv = _rangos_negativos(sys.argv[1:] if argv is None else argv)
    args = parser().parse_args(argv)
    if args.tipo == "completar":
        for f in completar(args.rutas):
            print(f)
        return 0
    claro = args.claro
    tema = TEMAS["claro" if claro else "oscuro"]
    nota = Path(args.pizarron) if args.pizarron else None

    if args.tipo == "hoja":
        fuente = sys.stdin.read() if args.archivo == "-" else Path(args.archivo).read_text(encoding="utf-8")
        if args.titulo:
            fuente = f"# {args.titulo}\n" + fuente
        nombre = "hoja-" + clave("hoja", fuente, claro)
        hecho = None if args.salida or nota else en_cache(nombre)
        if hecho:
            png, svg = hecho
        else:
            svg_txt, sueltos = dibujar_hoja(fuente, claro)
            png, svg = guardar(svg_txt, nombre, args.salida)
            if nota:
                archivos = iter([_svg_al_lado(nota, s, cmd) for cmd, s in sueltos])
                comandos = iter([cmd for cmd, _ in sueltos])
                embeds, cmds = [], []
                for ln in fuente.split("\n"):
                    if ln.startswith("@"):  # one @line may hold several drawings joined by &
                        partes = range(len(ln.split(" & ")))
                        embeds.append([next(archivos) for _ in partes])
                        cmds.append(" & ".join(next(comandos) for _ in partes))
                _agregar_al_pizarron(nota, hoja.a_markdown(fuente, embeds, cmds))
    else:
        firma = {k: v for k, v in vars(args).items() if k not in ("salida", "pizarron")}
        nombre = f"{args.tipo}-" + clave(sorted(firma.items()))
        hecho = None if args.salida else en_cache(nombre)
        png, svg = hecho or guardar(tarjeta(_dibujar(args), tema, args.titulo), nombre, args.salida)
        if nota:
            if args.tipo == "formula":
                md = hoja.a_markdown(_formula_a_hoja(args), [], [])
            else:
                cmd = shlex.join(_sin_salida(argv))
                archivo = _svg_al_lado(nota, svg.read_text(encoding="utf-8"), cmd)
                md = f"<!-- lamina {cmd} -->\n![[{archivo}]]\n"
            if args.titulo:
                md = f"## {args.titulo}\n\n" + md
            _agregar_al_pizarron(nota, md)
    print(png)
    print(svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
