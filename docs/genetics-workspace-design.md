# Genetics workspace — design

**Status:** proposed, 2026-10-20  
**Scope:** the `T` screen of `avatar-combiner`  
**Related:** `docs/genetics-suite-2026.md` (idea catalog), implementation plan
`docs/superpowers/plans/2026-10-20-genetics-workspace.md`

## Intent

Turn the flat four-item Tools screen into a small genetics workspace that can
grow without becoming a list of 100 buttons. Version 1 adds two capabilities
and reorganises the existing four. Everything else stays out until it earns a
slot.

## Principles

1. **Three keystrokes to anywhere.** Home `T`, then one digit.
2. **One screen, one job.** Inspect, analyse, import are separate screens.
3. **State is visible.** Empty, waiting, result, error and unavailable each
   look different without colour.
4. **Colour is never the only signal.** Pair every colour with a glyph or word.
5. **Offline first.** V1 imports local files and computes locally. No network.
6. **Tokens only.** Use the existing primitive → semantic → component model in
   `src/ui.py`. No new hex values.
7. **60 columns is the floor.** Must render at 60×20, look best at 100×30.
8. **No new TUI framework.** Standard library only, same as today.

## Information architecture

```
Home
└── [T] Genetics
    ├── [1] Primer Tm            inspect
    ├── [2] Primer pair          inspect
    ├── [3] DNA transforms       inspect
    ├── [4] Units                inspect
    ├── [5] Oligo structure      analyse  (new)
    └── [6] Import sequence      files    (new)
```

Future modules get a numbered slot only when implemented. Until then they are
not drawn; a grey “soon” row is allowed only in the design mockup, never in the
shipped screen.

## Screen anatomy

```
┌ Avatar ────────────────────────────────────────────────────────────────┐
│ 4 × 96-well plates  →  1 × 384-well plate                              │
└────────────────────────────────────────────────────────────────────────┘

┌ GENETICS ──────────────────────────────────────────────────────────────┐
│ INSPECT                                                                │
│ [1] Primer Tm              [2] Primer pair                             │
│ [3] DNA transforms         [4] Units                                   │
│                                                                        │
│ STRUCTURE & FILES                                                      │
│ [5] Oligo structure        [6] Import sequence file                    │
│                                                                        │
│ [B] Back                                                               │
└────────────────────────────────────────────────────────────────────────┘

┌ RESULT ────────────────────────────────────────────────────────────────┐
│ SEQUENCE      ACGTACGTACGT                                             │
│ LENGTH        12 nt                                                    │
│ ΔG            -1.70 kcal/mol                                           │
│ Tm            43.4 °C                                                  │
│ FOLD          ((((....))))                                             │
└────────────────────────────────────────────────────────────────────────┘

1–4 inspect  ·  5 structure  ·  6 import  ·  B back
```

Rules:

- The header is unchanged from every other screen.
- Group labels are uppercase, `dim`, and never selectable.
- Keys are `accent`; the two new tools use `accent2` to mark the new group.
- `[B]` sits last, `muted`.
- The result box appears only after a result or an error.
- Long sequences wrap at 60 characters, matching `tool_sequence_lines`.

## Interaction model

| Key | Home | Genetics hub | Prompt |
|---|---|---|---|
| `1`–`4` | run / results / open / config | inspect tools | literal |
| `5` | help | oligo structure | literal |
| `6` | language | import sequence | literal |
| `7` | genetics | — | literal |
| `↑` `↓` | — | reserved for future list | — |
| `Enter` | run | confirm | confirm |
| `Esc` / `B` | — | back to home | cancel |
| `Ctrl+U` / `Ctrl+W` | — | — | clear / delete word |
| `L` | switch language | switch language | switch language |
| `Q` / `Ctrl+C` | quit | quit | cancel then quit |

The prompt keeps the existing `prompt_text` contract: returns `str` on Enter,
`None` on Esc. New tools must not read keys themselves.

## States

| State | Rendering |
|---|---|
| Empty | Hub with no result box |
| Waiting for input | Existing prompt screen, title = tool name, hint = format |
| Success | Result box, values in `text`, labels in `dim` |
| Error | Result box with `✗ <message>` in `error`, one line, no traceback |
| Unavailable | Grey label plus `(needs <dep>)`, key does nothing |
| Long result | Wrap at 60; no scrolling in v1 |

An error never leaves the user on a blank screen: the result box keeps the last
successful output until the next run succeeds, matching current behaviour.

## Tokens

Reuse the existing semantic roles. No new primitives.

| Meaning | Role | Fallback colour |
|---|---|---|
| Offline / local | `success` | 42 |
| Network / cloud | `warning` | 214 |
| Human-only data | `dim` | 240 |
| Future module | `dim` | 240 |
| Selected / new group | `accent2` | 141 |
| Primary action | `accent` | 45 |

Rationale: `success` already means “ready” on Home, and local analysis is the
ready path. Network work is a warning because it leaks identifiers.

## Typography and layout

- Monospace only; the terminal supplies the font.
- Labels: uppercase, left-padded to 12 columns (`tool_line`).
- Values: sentence case, never truncated without `…`.
- Sequences: 60 characters per chunk; continuation lines indent 13 columns.
- Numbers: one decimal for Tm and ΔG, two for ΔG in kcal/mol.
- No emoji. Glyphs limited to `●`, `✓`, `✗`, `▌`, `│`.

## Copy deck

New keys for `TEXT['en']` and `TEXT['ru']`.

| Key | EN | RU |
|---|---|---|
| `tools` | Genetics | Генетика |
| `group_inspect` | INSPECT | ПРОВЕРКА |
| `group_files` | STRUCTURE & FILES | СТРУКТУРА И ФАЙЛЫ |
| `tool_structure` | Oligo structure | Структура олиго |
| `tool_import` | Import sequence file | Импорт файла |
| `structure_hint` | ACGT only. Hairpins and self-dimers. | Только ACGT. Шпильки и самодимеры. |
| `structure_dg` | ΔG | ΔG |
| `structure_fold` | Fold | Складка |
| `structure_none` | no stable structure | нет устойчивой структуры |
| `import_path` | File path | Путь к файлу |
| `import_format` | Format | Формат |
| `import_topology` | Topology | Топология |
| `import_records` | Records | Записей |
| `import_features` | Features | Признаки |
| `import_hint` | .gb .gbk .dna .fa .fasta | .gb .gbk .dna .fa .fasta |
| `tool_footer` | 1–4 inspect · 5 structure · 6 import · B back | 1–4 проверка · 5 структура · 6 импорт · B назад |

Rules: no new wording for existing actions; RU uses «Генетика», not
«Инструменты генетика», because the screen is now a workspace.

## Responsive behaviour

| Width | Behaviour |
|---|---|
| 60–79 | one action per row; hint wraps |
| 80–99 | two columns, as in the wireframe |
| ≥100 | same, with wider result box; never more than two columns |

Height below 20 is not supported; the existing `paint_lines` clips.

## Accessibility

- `NO_COLOR` and non-TTY paths already disable ANSI; new screens must use
  `Theme` only.
- Every state has a non-colour marker: `●` ready, `✗` error, `…` truncated.
- Language switch applies immediately to new strings.
- No timed states, no animations.

## Rejected

| Option | Why rejected |
|---|---|
| Show all 100 catalog ideas as menu items | Unusable; hides the three tools people need |
| Third-party TUI (Textual/Rich) | Breaks the stdlib-only, small-exe constraint |
| Web UI | Out of scope for a lab desktop tool |
| Mouse support | Terminal-only product; keyboard is faster |
| Cloud annotation in v1 | Privacy and offline-first conflict; needs caching design |
| Plate maps via `wellmap`/`Plateo` | Both pull pandas/numpy, which the bundle excludes |
| Logo/brand work | This is an internal tool, not a brand exercise |

## Handoff

V1 implements ideas 13 (`seqfold`) and 29 (`snapgene_reader`) from the catalog,
plus local GenBank/FASTA import through the existing Biopython dependency. The
implementation plan is `docs/superpowers/plans/2026-10-20-genetics-workspace.md`.
