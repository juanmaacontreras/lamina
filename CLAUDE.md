# Lámina

Turns a short description into a study drawing (PNG for the chat, SVG for the vault) in the
ecosystem's Nord look. Part of the ecosystem: https://claude.ai/artifact/PHQmVerxfbkkCipzxGaF2d

**Does:** formulas with ✔/✘ and boxes, pole-zero maps, Bode with templates, ladders, block
diagrams, y = f(x), whole sheets (`hoja`), and appends them to a pizarrón note.
**Does not:** solve or check math (sympy does), decide what to show (`/clase` does), show
anything by itself (Claude sends the PNG), touch notes other than the one given with
`--pizarron`, or use any paid API or TeX.

- Usage reference: `README.md`. Note format: `docs/contrato.md`; change it there and in
  `contrato/` first, then the cerebro-app test that reads the same file.
- Pure Python on purpose (runs in cloud sessions). Never add a dependency on TeX or system libs.
- Colors only from `src/lamina/estilo.py` (copied from Atril's `tokens.css`); never inline a hex.
- Color never carries information alone: poles ✕ vs zeros ○, marks ✔ vs ✘, dashed vs solid.
- Look at every visual change as a PNG, dark and light, before committing. `uv run pytest`
  before every commit.
- Code, comments and commits in English; CLI help and drawn text in Rioplatense Spanish.
