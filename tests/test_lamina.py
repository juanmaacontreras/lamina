"""Every drawing type renders, outputs are self-contained, numbers are right, the note format holds."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import numpy as np
import pytest

from lamina import cli, hoja
from lamina.circuitos import leer_escalera
from lamina.graficos import puntos
from lamina.lienzo import _partir

RAIZ = Path(__file__).resolve().parents[1]
PNG = b"\x89PNG\r\n\x1a\n"

CASOS = {
    "formula": ["formula", r"k_0=\lim_{s\to0}s\,F(s)", r"2k_1=-\frac{15}{2}", "--bien", "1", "--mal", "2",
                "--error", "Revisá $s^2$ en el denominador.", "--pista", "Qué vale $s^2$ en el polo"],
    "polos-s": ["polos", "--polos", "0 ±2j", "--ceros", "±j ±3j", "--valores"],
    "polos-z": ["polos", "--z", "--polos", "0.5±0.5j", "--ceros", "-1^2", "--estable"],
    "bode": ["bode", "--num", "1", "--den", "1 2 2 1", "--marcar", "-3", "--fase",
             "--plantilla", "wp=1 Ap=3 ws=3 As=25"],
    "bode-z": ["bode", "--z", "--num", "0.25 0.5 0.25", "--den", "1", "--atenuacion"],
    "curva": ["curva", "T_3=cos(3*arccos(x))", "T_4=cos(4*arccos(x))", "--x", "-1:1"],
    "escalera": ["escalera", "Rg=1 | L1=1 | C2=2 | tanque(L3=1,C3=1/2) | serie(L4,C4) | RL=1"],
    "escalera-p": ["escalera", "C=2 | p:L=2/9 | p:tanque(L1=2/15,C1=15/8)", "--empieza", "p",
                   "--entrada", "Y(s)"],
    "bloques": ["bloques", "--b", "1 0 -1", "--a", "1 -0.5 0.25"],
    "fir": ["bloques", "--b", "0.25 0.5 0.25"],
}


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("LAMINA_CACHE", str(tmp_path / "cache"))
    return tmp_path


def correr(argv, capsys) -> tuple[Path, Path]:
    assert cli.main(argv) == 0
    png, svg = capsys.readouterr().out.split()
    return Path(png), Path(svg)


@pytest.mark.parametrize("nombre", CASOS)
@pytest.mark.parametrize("claro", [False, True])
def test_cada_tipo_dibuja(nombre, claro, capsys):
    png, svg = correr(CASOS[nombre] + (["--claro"] if claro else []), capsys)
    assert png.read_bytes().startswith(PNG)
    texto = svg.read_text(encoding="utf-8")
    # self-contained: no fonts, no images, no links to files or the web
    assert "<image" not in texto and "@font-face" not in texto and "<text" not in texto
    assert not re.search(r'href="(?!#)', texto)
    fondo = "#FAFBFC" if claro else "#2E3440"
    assert fondo in texto


def test_cache_devuelve_lo_mismo_sin_redibujar(capsys):
    png, _ = correr(CASOS["polos-s"], capsys)
    antes = png.stat().st_mtime_ns
    png2, _ = correr(CASOS["polos-s"], capsys)
    assert png2 == png and png.stat().st_mtime_ns == antes


def test_puntos():
    assert puntos("0 ±2j -1±j 0^2 ±3") == [(0, 1), (2j, 1), (-2j, 1), (-1 + 1j, 1), (-1 - 1j, 1),
                                          (0, 2), (3, 1), (-3, 1)]
    assert puntos("j, -j") == [(1j, 1), (-1j, 1)]


def test_butterworth_cae_3_db_en_1():
    # the same evaluation bode() uses
    b, a = np.array([1.0]), np.array([1.0, 2, 2, 1])
    h = np.polyval(b, 1j) / np.polyval(a, 1j)
    assert 20 * np.log10(abs(h)) == pytest.approx(-3.0103, abs=1e-3)
    assert sorted(np.round(np.roots(a), 6), key=lambda z: (z.real, z.imag)) == \
        sorted(np.round([-1, -0.5 + np.sqrt(3) / 2 * 1j, -0.5 - np.sqrt(3) / 2 * 1j], 6),
               key=lambda z: (z.real, z.imag))


def test_escalera_se_lee():
    items = leer_escalera("Rg=1 | L1=1/2 | p:tanque(L3=1,C3=2) | RL=1")
    assert [i.tipo for i in items] == ["fuente", "L", "tanque", "R"]
    assert items[1].etiqueta == "$L_{1}=1/2$"
    assert items[2].pos == "p" and items[3].carga


def test_rangos_negativos():
    assert cli._rangos_negativos(["curva", "y=x", "--x", "-1:1"]) == ["curva", "y=x", "--x=-1:1"]


def test_texto_no_corta_formulas():
    lineas = _partir(r"Ceros en $\omega=1$ y $\omega=3$, polos en $0$, $2$ e $\infty$: se intercalan.", 40)
    assert all(ln.count("$") % 2 == 0 for ln in lineas)
    assert "$\\omega=3$," in " ".join(lineas)


def test_contrato_pizarron():
    """The sheet example turns into exactly the note the contract shows (cerebro-app tests the
    other side with the same file)."""
    fuente = (RAIZ / "contrato" / "hoja-ejemplo.md").read_text(encoding="utf-8")
    comandos = [hoja.separar_dibujo(ln)[0] for ln in fuente.split("\n") if ln.startswith("@")]
    md = hoja.a_markdown(fuente, [["ejemplo-1.svg"], ["ejemplo-2.svg"]], [shlex.join(c) for c in comandos])
    esperado = (RAIZ / "contrato" / "pizarron-ejemplo.md").read_text(encoding="utf-8")
    assert md == esperado


def test_hoja_al_pizarron(tmp_path, capsys):
    nota = tmp_path / "pz" / "Pizarrón — prueba.md"
    fuente = tmp_path / "h.md"
    fuente.write_text("## Paso\n$$ a=b $$ ✘\n@polos --polos '±j' & @polos --z --ceros '1'\n", encoding="utf-8")
    correr(["hoja", str(fuente), "--pizarron", str(nota)], capsys)
    texto = nota.read_text(encoding="utf-8")
    assert texto.startswith("---\ntipo: pizarrón\n")
    embeds = re.findall(r"!\[\[(lamina-\w+\.svg)\]\]", texto)
    assert len(embeds) == 2 and all((nota.parent / e).exists() for e in embeds)
    assert "$\\displaystyle a=b$ ✘" in texto
    assert "<!-- lamina polos --polos '±j' & polos --z --ceros 1 -->" in texto
    # a second drawing is appended, never overwrites
    correr(["formula", "x=1", "--bien", "1", "--pizarron", str(nota)], capsys)
    assert nota.read_text(encoding="utf-8").startswith(texto)


def test_dos_recuadros_seguidos_no_se_mezclan():
    fuente = "> [!warning] Dónde se rompió\n> a\n> [!tip] Pista\n> b"
    cajas = [b for b in hoja.leer(fuente) if b.tipo == "caja"]
    assert [(c.extra, c.lineas) for c in cajas] == [("warning", ["a"]), ("tip", ["b"])]
    assert "> a\n\n> [!tip]" in hoja.a_markdown(fuente, [], [])
