# Contract: the pizarrón note

Lámina writes it; cerebro-app (and Obsidian) render it. Both sides test against
`contrato/pizarron-ejemplo.md`: Lámina generates it from `contrato/hoja-ejemplo.md`
(`tests/test_lamina.py::test_contrato_pizarron`), cerebro-app renders it without errors
(`tests/pizarron.test.ts`, a copy of the same file).

## Where

`UTN/<Materia>/pizarrón/Pizarrón — <YYYY-MM-DD>.md` in the vault, one note per study day.
The SVGs go next to it as `lamina-<hash>.svg` (the hash is unique, so names never collide in
the vault). Lámina never overwrites: it only appends.

## Format

A new note starts with:

```markdown
---
tipo: pizarrón
fecha: 2026-11-20
origen: Claude
---

# Pizarrón — 2026-11-20
```

Then each drawing or sheet appends blocks separated by one blank line:

| Block | Markdown |
|---|---|
| Section | `## Paso 2 · Residuos` (a sheet's `# título` becomes `##`) |
| Formula without a mark | `$$` / TeX / `$$` on three lines |
| Formula with a mark | `$\displaystyle TeX$ ✔` or `✘` (inline, so the mark can follow) |
| Text, bullets, tables | as written, `$x$` inline math |
| Box | Obsidian callout: `> [!warning] Título` then `> text` lines |
| Drawing | `<!-- lamina <command> -->` then `![[lamina-<hash>.svg]]` (several on one line when side by side) |

The hidden comment keeps the exact command, so a drawing can be redone or changed later.
cerebro-app strips HTML comments and renders `![[x.svg]]` as an image.

## Rules

- The SVGs are self-contained: no fonts, no images, no links (text is drawn as paths).
- Marks are ✔ (U+2714) and ✘ (U+2718); color is never the only signal.
- `## Apuntes` belongs to Juanma: Lámina never writes in a note that is not a pizarrón.
