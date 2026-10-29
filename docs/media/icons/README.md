# Avatar Combiner application icons

Original **four-nations parody** mark (Earth / Water / Air / Fire) for OS app icons and lab shortcuts — larger and clearer than the tiny Tools sidebar glyph in `web_app.py`.

## Files

| File | Use |
|------|-----|
| `../../src/assets/app-icon.svg` | Vector source |
| `../../src/assets/app-icon.ico` | Windows multi-size ICO (16 / 32 / 48 / 256) |
| `../../src/assets/app-icon-256.png` / `app-icon-512.png` | Linux / generic PNG |
| `app-icon-*.png` (this folder) | Size ladder exports |
| `../../src/assets/avatar-combiner.desktop` | Linux `.desktop` template (`Icon=avatar-combiner`) |

## Regenerate

```text
python src/assets/generate_app_icons.py
```

Requires Pillow. Writes PNG/ICO under `src/assets/` and this folder.

## Windows exe (PyInstaller)

`src/build_binary.py` passes `--icon src/assets/app-icon.ico` when the file exists. Rebuild:

```text
cd src
uv run python build_binary.py
```

The packaged exe under `src/dist/` picks up the icon on the next full build. Dist also gets a copy of `app-icon.ico` plus `create-shortcuts.*`.

## Windows bat → shortcut icons

`.bat` files cannot embed icons. From the repo root or `src/dist`:

```text
create-shortcuts.bat
```

Creates `Avatar Combiner Web.lnk` and `Stop Avatar Combiner Web.lnk` with `IconLocation` set to `app-icon.ico`. Pin those `.lnk` files.

## Linux desktop entry

1. Copy `app-icon-256.png` to `~/.local/share/icons/hicolor/256x256/apps/avatar-combiner.png` (and optionally 512).
2. Copy `src/assets/avatar-combiner.desktop` to `~/.local/share/applications/`, edit `Exec=` / `Path=` / `Icon=` for your install.
3. `update-desktop-database ~/.local/share/applications` (optional).

Palette: Earth `#4f9a28`, Water `#1e6fb3`, Air `#16a487`, Fire `#ab1610`.
