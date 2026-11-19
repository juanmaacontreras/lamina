# Lámina

Drawings for the study chat. One command, one image: formulas with ✔/✘ and correction boxes,
pole-zero maps (s and z planes), frequency response with templates, ladder networks, digital
filter block diagrams, and y = f(x). Each command writes a PNG (to send into the chat) and an
SVG (for the vault), in the ecosystem's Nord look, dark by default.

Pure Python (ziamath, matplotlib, schemdraw, resvg): no TeX and nothing from the PC, so it runs
the same in a cloud session as on the PC. Repeated drawings come from the cache
(`~/.cache/lamina`, or `$LAMINA_CACHE`).

## Install

```bash
uv tool install --editable ~/projects/lamina                              # PC
uv tool install git+https://github.com/juanmaacontreras/lamina            # cloud session
```

## Use

Every command prints two lines: the PNG path, then the SVG path. Common options: `--claro` (light,
for printing), `--titulo`, `-o PATH`, `--pizarron NOTE.md` (append to the session note, SVGs
next to it). Decimals take a dot; labels come out with a comma.

| Type | Example |
|---|---|
| `formula` | `lamina formula 'k_0=\lim_{s\to0}sF' '2k_1=-\tfrac{15}{2}' --bien 1 --mal 2 --error 'Revisá $s^2$…' --pista '…'` |
| `polos` | `lamina polos --polos '0 ±2j' --ceros '±j ±3j' --valores` · `--z` (unit circle) · `--estable` · `0^2` = double |
| `bode` | `lamina bode --num 1 --den '1 2 2 1' --marcar -3 --plantilla 'wp=1 Ap=3 ws=3 As=25' --fase` · `--z` (coefficients in z⁻ᵏ, axis Ω) · `--atenuacion` · `--lineal` · `--w 0.1:10` |
| `curva` | `lamina curva 'T_3=cos(3*arccos(x))' 'T_4=cos(4*arccos(x))' --x -1:1` (numpy names) |
| `escalera` | `lamina escalera 'Rg=1 \| L1=1 \| C2=2 \| tanque(L3=1,C3=1/2) \| RL=1'` |
| `bloques` | `lamina bloques --b '1 0 -1' --a '1 -0.5 0.25'` (direct form II; without `--a`, FIR) |
| `hoja` | a whole sheet from a file or stdin, below |

**Ladder text.** Elements separated by `|`, alternating series/shunt from `--empieza s|p`
(default series). `s:` or `p:` in front forces the position (all-parallel Foster:
`'C=2 | p:L=2/9 | p:tanque(L1=2/15,C1=15/8)' --empieza p`). `L C R` with an optional
`=value`; `tanque(a,b)` is a parallel pair, `serie(a,b)` a series pair; `Rg=` at the start
draws the generator, `RL=` at the end the load. `--entrada 'Z(s)'` adds the input arrow.

**Sheet.** The pizarrón note's Markdown plus `@` lines, so one text gives the chat image and the
note. Blocks: `# título`, `## sección`, `$$ … $$ ✔` (one line), paragraphs with `$x$`,
`- ítem`, `> [!warning|tip|note|success] título` boxes, tables, and `@tipo args` drawings
(`@a … & @b …` side by side).

```bash
lamina hoja --pizarron "$VAULT/UTN/<Materia>/pizarrón/Pizarrón — 2026-11-20.md" <<'EOF'
## Paso 2 · Residuos
$$ 2k_1=\lim_{s^2\to-4}\frac{(s^2+4)F(s)}{s}=-\frac{15}{2} $$ ✘
> [!warning] Dónde se rompió
> Un residuo negativo en una LC es imposible.
@polos --polos '0 ±2j' --ceros '±j ±3j'
EOF
```

Colors inside formulas by name: `\color{mal}{…}`, `bien`, `aviso`, `acento`, `vivo`.

## Tests

`uv run pytest`: every type in both themes, self-contained SVGs, cache, parsing, numbers
(Butterworth −3 dB at ω = 1), and the note contract (`docs/contrato.md`).

## Fonts

`src/lamina/fuentes/` bundles Latin Modern (GUST Font License, free to redistribute), so the
drawings look like the LaTeX summaries on any machine.
