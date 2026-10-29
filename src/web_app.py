"""Local web interface for the plate combiner.

Run with ``run_pipeline.py --web``. NiceGUI serves a single-user app on
127.0.0.1; no data leaves the machine. The command line stays available.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import sys
import tempfile
import time
from pathlib import Path

from nicegui import app, context, ui

import app_config
import extract_plates_from_excel as extract_plates
import pcr_tools
import plate_layout
import report_xlsx
import run_pipeline
import seq_structure
import tool_reports
import tools as genetics
from i18n import TEXT

TOOLS = (
    ('tm', 'tool_tm'),
    ('pair', 'tool_pair'),
    ('dna', 'tool_dna'),
    ('units', 'tool_units'),
    ('structure', 'tool_structure'),
    ('pcr', 'tool_pcr'),
    ('gradient', 'tool_gradient'),
    ('layout', 'tool_layout'),
    ('xlsx', 'tool_xlsx'),
)

# Bundled sample next to the pipeline sources (four sheets, range B3:M10).
SAMPLE_WORKBOOK = 'планшеты соя пробелы.xlsx'

# Plate-fold GIF (docs/media in source tree; optional media/ next to exe).
PLATE_FOLD_GIF = 'four-to-384.gif'
PLATE_FOLD_STATIC_URL = '/app-media'

# Four nations plate accents (order matches branding reference quadrants).
PLATE_COLORS = {
    1: '#4f9a28',  # Earth — grassy green
    2: '#1e6fb3',  # Water — deep blue
    3: '#16a487',  # Air — teal/cyan
    4: '#ab1610',  # Fire — dark red
}

# Stylized original parody of four united nation emblems (sidebar glyph).
TOOLS_NATIONS_ICON = """
<svg class="tools-nations-icon" viewBox="0 0 32 32" width="18" height="18" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
  <rect x="1.25" y="1.25" width="14.25" height="14.25" rx="2.5" fill="var(--plate-1)"/>
  <rect x="16.5" y="1.25" width="14.25" height="14.25" rx="2.5" fill="var(--plate-2)"/>
  <rect x="1.25" y="16.5" width="14.25" height="14.25" rx="2.5" fill="var(--plate-3)"/>
  <rect x="16.5" y="16.5" width="14.25" height="14.25" rx="2.5" fill="var(--plate-4)"/>
  <!-- earth: mountain gate -->
  <path d="M5.2 12.2 L8.4 6.2 L11.6 12.2 Z" fill="none" stroke="#f3f7ea" stroke-width="1.35" stroke-linejoin="round"/>
  <path d="M6.4 12.2 h4" stroke="#f3f7ea" stroke-width="1.35" stroke-linecap="round"/>
  <!-- water: moon + waves -->
  <path d="M21.2 6.4a3.1 3.1 0 0 0 4.2 3.1" fill="none" stroke="#eaf4fc" stroke-width="1.3" stroke-linecap="round"/>
  <path d="M19.4 11.1c1.4-1.7 3.4-1.7 4.8 0M19.4 13.2c1.4-1.7 3.4-1.7 4.8 0" fill="none" stroke="#eaf4fc" stroke-width="1.25" stroke-linecap="round"/>
  <!-- air: triple swirl hints -->
  <circle cx="6.4" cy="21.2" r="2.05" fill="none" stroke="#e7fffa" stroke-width="1.25"/>
  <circle cx="10.6" cy="21.2" r="2.05" fill="none" stroke="#e7fffa" stroke-width="1.25"/>
  <circle cx="8.5" cy="25.1" r="2.05" fill="none" stroke="#e7fffa" stroke-width="1.25"/>
  <!-- fire: flame tongue -->
  <path d="M23.7 28.2c-.1-3.1 1.7-4.4 2.1-7.1 1.6 2.1 3.3 3.6 3.3 6.2 0 2.1-1.4 3.2-2.9 3.2-1.4 0-2.4-.9-2.5-2.3z" fill="#f6e7a4"/>
  <rect x="1" y="1" width="30" height="30" rx="7" fill="none" stroke="rgba(42,33,26,.22)" stroke-width="1"/>
</svg>
""".strip()

THEME_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root {
  --paper: #f3ebe0;
  --paper-2: #fffaf3;
  --ink: #2a211a;
  --muted: #6f6256;
  --line: #ddcdba;
  --rust: #9a4526;
  --amber: #c9842c;
  --olive: #5a6a42;
  --cocoa: #1f1712;
  --drawer-w: 248px;
  /* Four nations — plate 1…4 order matches reference (Earth, Water, Air, Fire) */
  --plate-1: #4f9a28;
  --plate-2: #1e6fb3;
  --plate-3: #16a487;
  --plate-4: #ab1610;
  --plate-1-soft: rgba(79, 154, 40, .12);
  --plate-2-soft: rgba(30, 111, 179, .12);
  --plate-3-soft: rgba(22, 164, 135, .12);
  --plate-4-soft: rgba(171, 22, 16, .12);
}
html { color-scheme: light; }
body {
  background:
    radial-gradient(980px 520px at 6% -12%, #edd4b4 0%, transparent 58%),
    radial-gradient(820px 460px at 100% 0%, #e6cba8 0%, transparent 54%),
    linear-gradient(180deg, #f7f0e6 0%, var(--paper) 40%, #efe4d5 100%);
  color: var(--ink);
  font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  line-height: 1.45;
}
body::before {
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  opacity: .35;
  background-image: radial-gradient(rgba(42, 33, 26, .04) 1px, transparent 1px);
  background-size: 4px 4px;
}
.q-layout, .q-page-container, .q-page { background: transparent !important; }
.q-page-container { padding-top: 0 !important; }
.q-page {
  max-width: 920px;
  width: 100%;
  margin: 0 auto;
  padding: 28px 28px 64px;
  box-sizing: border-box;
}
.app-header {
  background: rgba(247, 240, 230, .88) !important;
  backdrop-filter: blur(14px) saturate(1.05);
  border-bottom: 1px solid var(--line);
  color: var(--ink) !important;
  box-shadow: none !important;
  min-height: 52px !important;
}
.app-header .q-btn { color: var(--ink) !important; }
.app-header .header-title {
  font-size: 15px; font-weight: 600; letter-spacing: .01em;
}
.app-drawer {
  background: linear-gradient(180deg, #fbf6ed 0%, #f0e4d2 100%) !important;
  border-right: 1px solid var(--line);
  width: var(--drawer-w) !important;
}
.app-drawer .q-drawer__content {
  padding: 18px 14px 20px;
  display: flex; flex-direction: column; gap: 2px;
}
.brand {
  font-size: 11px; font-weight: 700; letter-spacing: .2em;
  color: var(--muted); text-transform: uppercase;
  margin: 0 6px 10px;
}
.nav-section {
  font-size: 10px; font-weight: 650; letter-spacing: .16em;
  text-transform: uppercase; color: var(--muted);
  margin: 12px 8px 6px; opacity: .85;
}
.nav-tools-heading {
  display: flex; align-items: center; gap: 8px;
  margin: 14px 6px 6px; opacity: 1;
}
.nav-tools-heading .nav-section-label {
  font-size: 10px; font-weight: 650; letter-spacing: .16em;
  text-transform: uppercase; color: var(--muted); margin: 0; opacity: .9;
}
.tools-nations-icon {
  flex: 0 0 auto; display: block;
  width: 18px; height: 18px;
  filter: drop-shadow(0 1px 0 rgba(255,255,255,.55));
}
.nav-link {
  display: block; border-radius: 8px; padding: 8px 10px !important;
  color: var(--ink) !important; text-decoration: none !important;
  font-size: 13.5px; font-weight: 500;
  transition: background .15s ease, color .15s ease;
}
.nav-link:hover { background: rgba(154, 69, 38, .08); }
.nav-link.nav-active {
  background: rgba(154, 69, 38, .12);
  font-weight: 650; box-shadow: inset 3px 0 0 var(--rust);
}
.lang-row { margin-top: auto; padding-top: 16px; }
.panel {
  background: var(--paper-2) !important;
  border: 1px solid var(--line) !important;
  border-radius: 14px !important;
  box-shadow: 0 1px 0 rgba(255,255,255,.7) inset, 0 10px 28px -22px rgba(60, 36, 18, .4) !important;
  padding: 20px 22px 18px;
}
.panel + .panel { margin-top: 14px; }
.panel-title {
  font-size: 15px; font-weight: 650; letter-spacing: -.01em;
  margin: 0 0 14px; color: var(--ink);
}
.hero { gap: 6px; padding: 4px 2px 22px; max-width: 40rem; }
.hero-kicker {
  font-size: 11px; letter-spacing: .2em; text-transform: uppercase;
  color: var(--rust); font-weight: 700;
}
.hero-title {
  font-size: clamp(28px, 4.2vw, 42px); line-height: 1.05; letter-spacing: -.03em;
  font-weight: 700; color: var(--ink);
}
.hero-title .hero-accent { color: var(--rust); }
.hero-sub { color: var(--muted); max-width: 52ch; font-size: 14.5px; margin-top: 2px; }
.first-run-row {
  display: flex; flex-wrap: wrap; gap: 14px; align-items: stretch;
  margin: 0 0 16px; width: 100%;
}
.first-run-slot {
  flex: 1 1 280px; min-width: min(100%, 240px); display: flex;
}
.first-run-slot:empty { display: none; }
.first-run {
  background: linear-gradient(120deg, rgba(255,250,243,.96), rgba(237,212,180,.42));
  border: 1px solid var(--line);
  border-left: 3px solid var(--rust);
  border-radius: 12px;
  padding: 14px 16px 12px 18px;
  margin: 0;
  width: 100%;
  box-sizing: border-box;
  box-shadow: 0 8px 22px -20px rgba(60, 36, 18, .45);
}
.first-run-title {
  font-size: 11px; font-weight: 700; letter-spacing: .16em;
  text-transform: uppercase; color: var(--rust); margin: 0 0 6px;
}
.first-run-body {
  color: var(--muted); font-size: 13.5px; max-width: 48ch;
  margin: 0 0 12px; line-height: 1.45;
}
.first-run-actions {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
}
.plate-fold {
  position: relative; overflow: hidden;
  flex: 1 1 240px; max-width: 340px; min-width: min(100%, 200px);
  margin: 0; padding: 12px 12px 10px;
  background: linear-gradient(145deg, rgba(255,250,243,.98), rgba(237,212,180,.38));
  border: 1px solid var(--line); border-radius: 12px;
  box-shadow: 0 8px 22px -20px rgba(60, 36, 18, .45);
  box-sizing: border-box;
}
.plate-fold::before {
  content: ''; position: absolute; left: 0; right: 0; top: 0; height: 3px;
  background: linear-gradient(
    90deg, var(--plate-1), var(--plate-2), var(--plate-3), var(--plate-4)
  );
}
.plate-fold .q-img, .plate-fold img {
  width: 100%; border-radius: 8px; display: block;
  background: rgba(255, 250, 243, .65);
}
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid var(--line); border-radius: 999px;
  padding: 4px 11px; font-size: 11px; color: var(--muted);
  background: rgba(255, 250, 242, .85); font-weight: 500;
}
.q-card { border-radius: 14px; box-shadow: none !important; }
.q-btn { text-transform: none !important; border-radius: 10px !important; letter-spacing: .01em; font-weight: 600; }
.q-btn--flat { border-radius: 8px !important; font-weight: 550; }
.q-btn--unelevated.bg-primary, .q-btn.bg-primary {
  box-shadow: 0 8px 18px -12px rgba(154, 69, 38, .7) !important;
}
.q-field { margin-bottom: 4px; }
.q-field__native, .q-field__input, .q-field__label { font-family: inherit !important; }
.q-field--outlined .q-field__control,
.q-field--filled .q-field__control,
.q-field--standard .q-field__control {
  background: #fff !important;
  border-radius: 10px !important;
  min-height: 44px;
}
.q-field--standard .q-field__control:before {
  border: 1px solid var(--line) !important;
  border-bottom-width: 1px !important;
  border-radius: 10px;
}
.q-field--standard .q-field__control:after {
  height: 0 !important; border: none !important;
}
.q-field--standard.q-field--focused .q-field__control:before {
  border-color: var(--rust) !important;
}
.q-field--outlined .q-field__control:before { border-color: var(--line); }
.q-field--outlined.q-field--focused .q-field__control:after { border-color: var(--rust); }
.q-field__label { color: var(--muted) !important; font-weight: 500; }
.q-field--dense .q-field__control { min-height: 40px; }
.q-uploader {
  width: 100%; max-width: 100%;
  border: 1px dashed var(--line) !important;
  border-radius: 12px !important;
  background: rgba(255,255,255,.55) !important;
  box-shadow: none !important;
  min-height: 0 !important;
}
.q-uploader__header {
  background: transparent !important;
  color: var(--ink) !important;
  padding: 10px 12px !important;
}
.q-uploader__list { min-height: 0 !important; padding: 0 8px 8px !important; }
.q-uploader .q-btn { color: var(--rust) !important; }
.meta-line { color: var(--muted); font-size: 12.5px; margin-top: 8px; }
.status-ok { color: var(--olive) !important; font-weight: 600; font-size: 13px; }
.action-bar {
  display: flex; flex-wrap: wrap; align-items: center; gap: 14px;
  margin: 16px 0 8px;
}
.action-hint { color: var(--muted); font-size: 13px; max-width: 36ch; }
.log-wrap {
  background: var(--cocoa);
  border-radius: 14px;
  border: 1px solid #35261d;
  overflow: hidden;
  margin-top: 8px;
}
.log-wrap .log-label {
  color: #cbb59a; font-size: 11px; font-weight: 650;
  letter-spacing: .14em; text-transform: uppercase;
  padding: 10px 14px 0;
}
.log-panel {
  background: transparent !important; color: #f0e2cc !important;
  border-radius: 0 !important; border: none !important;
  padding: 8px 14px 14px !important; font-size: 12.5px;
  font-family: 'IBM Plex Mono', ui-monospace, monospace !important;
  min-height: 140px !important; max-height: 240px;
}
.status-ok, .meta-line { display: block; margin-top: 10px; }
.empty-state {
  text-align: left; padding: 28px 24px;
  color: var(--muted); font-size: 14.5px;
}
.tool-panel .q-field { max-width: 36rem; }
.tool-panel .q-textarea { max-width: 42rem; }
.tool-actions { margin-top: 12px; }
.sheet-grid { display: flex; flex-wrap: wrap; gap: 12px; width: 100%; }
.sheet-grid > * { flex: 1 1 180px; min-width: 160px; max-width: 220px; }
.plate-legend {
  display: flex; flex-wrap: wrap; gap: 10px 14px;
  margin: 0 0 12px; align-items: center;
}
.plate-chip-legend {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11.5px; font-weight: 600; color: var(--muted);
}
.plate-chip-legend i {
  width: 10px; height: 10px; border-radius: 999px; display: inline-block;
  box-shadow: 0 0 0 1px rgba(42,33,26,.12);
}
.plate-chip-legend.p1 { color: var(--plate-1); }
.plate-chip-legend.p1 i { background: var(--plate-1); }
.plate-chip-legend.p2 { color: var(--plate-2); }
.plate-chip-legend.p2 i { background: var(--plate-2); }
.plate-chip-legend.p3 { color: var(--plate-3); }
.plate-chip-legend.p3 i { background: var(--plate-3); }
.plate-chip-legend.p4 { color: var(--plate-4); }
.plate-chip-legend.p4 i { background: var(--plate-4); }
.plate-chip .q-field__label { font-weight: 650 !important; }
.plate-chip-1 .q-field__label { color: var(--plate-1) !important; }
.plate-chip-2 .q-field__label { color: var(--plate-2) !important; }
.plate-chip-3 .q-field__label { color: var(--plate-3) !important; }
.plate-chip-4 .q-field__label { color: var(--plate-4) !important; }
.plate-chip-1.q-field--outlined .q-field__control:before,
.plate-chip-1.q-field--standard .q-field__control:before {
  border-color: var(--plate-1) !important;
}
.plate-chip-2.q-field--outlined .q-field__control:before,
.plate-chip-2.q-field--standard .q-field__control:before {
  border-color: var(--plate-2) !important;
}
.plate-chip-3.q-field--outlined .q-field__control:before,
.plate-chip-3.q-field--standard .q-field__control:before {
  border-color: var(--plate-3) !important;
}
.plate-chip-4.q-field--outlined .q-field__control:before,
.plate-chip-4.q-field--standard .q-field__control:before {
  border-color: var(--plate-4) !important;
}
.plate-chip-1.q-field--outlined.q-field--focused .q-field__control:after,
.plate-chip-1.q-field--standard.q-field--focused .q-field__control:before {
  border-color: var(--plate-1) !important;
}
.plate-chip-2.q-field--outlined.q-field--focused .q-field__control:after,
.plate-chip-2.q-field--standard.q-field--focused .q-field__control:before {
  border-color: var(--plate-2) !important;
}
.plate-chip-3.q-field--outlined.q-field--focused .q-field__control:after,
.plate-chip-3.q-field--standard.q-field--focused .q-field__control:before {
  border-color: var(--plate-3) !important;
}
.plate-chip-4.q-field--outlined.q-field--focused .q-field__control:after,
.plate-chip-4.q-field--standard.q-field--focused .q-field__control:before {
  border-color: var(--plate-4) !important;
}
.plate-chip-1 .q-field__control { background: linear-gradient(180deg, #fff, var(--plate-1-soft)) !important; }
.plate-chip-2 .q-field__control { background: linear-gradient(180deg, #fff, var(--plate-2-soft)) !important; }
.plate-chip-3 .q-field__control { background: linear-gradient(180deg, #fff, var(--plate-3-soft)) !important; }
.plate-chip-4 .q-field__control { background: linear-gradient(180deg, #fff, var(--plate-4-soft)) !important; }
.range-row { margin-top: 14px; max-width: 220px; }
.extract-row {
  display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end;
  margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line);
}
.extract-row .q-select { min-width: 180px; flex: 1 1 200px; max-width: 280px; }
.results-legend { max-width: 44rem; }
.results-legend .legend-intro { color: var(--muted); font-size: 13.5px; margin: 0 0 10px; }
.results-legend ul {
  margin: 0; padding: 0 0 0 1.1rem; color: var(--ink); font-size: 13.5px;
  line-height: 1.45;
}
.results-legend li { margin: 0 0 6px; }
.results-legend code {
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 12.5px; color: var(--rust);
  background: rgba(154, 69, 38, .06); padding: 1px 5px; border-radius: 4px;
}
.q-tab { text-transform: none !important; letter-spacing: .01em; }
.q-tab--active { color: var(--rust) !important; }
.q-tab__indicator { background: linear-gradient(90deg, var(--rust), var(--amber)) !important; }
.q-notification { border-radius: 10px !important; }
::selection { background: #efc48a; color: var(--cocoa); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: #d2bea2; border-radius: 999px; }
::-webkit-scrollbar-track { background: transparent; }
@media (max-width: 720px) {
  .q-page { padding: 18px 16px 48px; }
  .hero-title { font-size: 26px; }
  .app-drawer { width: min(86vw, 280px) !important; }
  .first-run-row { flex-direction: column; }
  .plate-fold { max-width: 100%; flex: 1 1 auto; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
"""
def current_lang():
    try:
        return app.storage.user.get('lang', 'en')
    except Exception:
        return 'en'


def tr(key):
    return TEXT[current_lang()].get(key, key)


def change_language(code):
    app.storage.user['lang'] = code if code in TEXT else 'en'
    ui.navigate.reload()


def resolve_plate_fold_gif(base_dir: Path) -> Path | None:
    """Locate the plate-fold GIF for web mode or a frozen exe layout.

    Source checkout: ``docs/media/four-to-384.gif`` (sibling of ``src/``).
    Packaged: optional ``media/four-to-384.gif`` next to the exe, or the same
    path under ``sys._MEIPASS`` if bundled with ``--add-data`` on rebuild.
    """
    base = Path(base_dir)
    candidates = [
        base / 'media' / PLATE_FOLD_GIF,
        base.parent / 'docs' / 'media' / PLATE_FOLD_GIF,
        Path(__file__).resolve().parent.parent / 'docs' / 'media' / PLATE_FOLD_GIF,
    ]
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            root = Path(meipass)
            candidates[:0] = [
                root / 'media' / PLATE_FOLD_GIF,
                root / 'docs' / 'media' / PLATE_FOLD_GIF,
            ]
    for path in candidates:
        if path.is_file():
            return path
    return None


class State:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self._default_config, self._default_error, _source = app_config.load_config(
            self.base_dir
        )
        self.running = False
        self.uploads = self.base_dir / '.uploads'
        self.uploads.mkdir(exist_ok=True)
        self._prune_uploads()

    @property
    def config(self):
        try:
            stored = app.storage.user.get('config')
        except Exception:
            stored = None
        return stored if stored is not None else self._default_config

    @config.setter
    def config(self, value):
        app.storage.user['config'] = value

    @property
    def error(self):
        try:
            if 'config_error' in app.storage.user:
                return app.storage.user['config_error']
        except Exception:
            pass
        return self._default_error

    @error.setter
    def error(self, value):
        app.storage.user['config_error'] = value

    def _prune_uploads(self):
        cutoff = time.time() - 7 * 24 * 3600
        for path in self.uploads.glob('*'):
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                pass

    def workbooks(self):
        found = app_config.discover_excel(self.base_dir)
        return found + sorted(self.uploads.glob('*.xlsx'))

    def sheets(self):
        if not self.config:
            return []
        try:
            path = self.config_path()
            return app_config.sheet_names(path)
        except (app_config.ConfigError, OSError, ValueError):
            return []

    def config_path(self):
        path = Path(self.config.get('excel_file', ''))
        return path if path.is_absolute() else self.base_dir / path

    def apply(self, excel_file, sheets, range_text):
        config = app_config.build_config(
            self.base_dir,
            excel_file=excel_file,
            sheets=sheets,
            data_range=app_config.parse_range(range_text),
        )
        app_config.validate_config(config, self.base_dir)
        self.config = config
        self.error = None
        return config

    def sample_workbook(self):
        """Return the bundled sample Excel path when present in the app folder."""
        candidate = self.base_dir / SAMPLE_WORKBOOK
        return candidate if candidate.is_file() else None


def build_app(base_dir):
    state = State(base_dir)
    plate_fold_gif = resolve_plate_fold_gif(base_dir)
    if plate_fold_gif is not None:
        # Serve the GIF directory once; URL stays stable for ui.image.
        app.add_static_files(PLATE_FOLD_STATIC_URL, str(plate_fold_gif.parent))

    def shell(title, active):
        ui.colors(
            primary='#9a4526',
            secondary='#5a6a42',
            accent='#c9842c',
            positive='#5a6a42',
            negative='#9a4526',
            warning='#c9842c',
            info='#6d7f8a',
        )
        ui.add_head_html(f'<style>{THEME_CSS}</style>', shared=True)

        with ui.left_drawer(value=True, bordered=False).classes('app-drawer') as drawer:
            ui.label(tr('brand')).classes('brand')
            ui.link(tr('pipeline'), '/').classes(
                'nav-link' + (' nav-active' if active == 'pipeline' else '')
            )
            ui.link(tr('results'), '/results').classes(
                'nav-link' + (' nav-active' if active == 'results' else '')
            )
            with ui.element('div').classes('nav-tools-heading').props(
                f'role=group aria-label="{tr("tools_section")}"'
            ):
                ui.html(TOOLS_NATIONS_ICON, sanitize=False)
                ui.label(tr('tools_section')).classes('nav-section-label')
            for key, label_key in TOOLS:
                classes = 'nav-link'
                if active == key:
                    classes += ' nav-active'
                ui.link(tr(label_key), f'/tools?tool={key}').classes(classes)
            with ui.row().classes('items-center gap-1 lang-row'):
                ui.label(tr('language')).classes('text-xs opacity-60')
                ui.button(
                    'EN',
                    on_click=lambda: change_language('en'),
                ).props('flat dense')
                ui.button(
                    'RU',
                    on_click=lambda: change_language('ru'),
                ).props('flat dense')

        with ui.header().classes('app-header items-center'):
            ui.button(icon='menu', on_click=lambda: drawer.toggle()).props(
                'flat dense round'
            )
            ui.label(title).classes('header-title')
            ui.space()
            ui.label(tr('badge_local')).classes('badge')

    def drain_logs(element, lines):
        while lines:
            element.push(lines.pop(0))

    def download_file(path):
        path = Path(path)
        ui.download(str(path), filename=path.name)

    def result_files(folder):
        return sorted(path for path in Path(folder).iterdir() if path.is_file())

    def render_result(folder, container):
        container.clear()
        with container:
            ui.label(f"{tr('result')}: {Path(folder).name}").classes('text-lg font-bold')
            manifest = Path(folder) / 'manifest.json'
            if manifest.is_file():
                data = json.loads(manifest.read_text(encoding='utf-8'))
                tree = ui.tree(
                    [_json_node(data, 'manifest', 'manifest.json')],
                    label_key='label',
                    node_key='id',
                    children_key='children',
                ).classes('w-full font-mono text-sm')
                tree.expand()
                ui.button(
                    icon='content_copy',
                    on_click=lambda: ui.clipboard.write(
                        json.dumps(data, ensure_ascii=False, indent=2)
                    ),
                ).props('flat dense round size=sm').tooltip(tr('copy_json'))
            with ui.row().classes('flex-wrap'):
                for path in result_files(folder):
                    ui.button(
                        path.name,
                        on_click=lambda path=path: download_file(path),
                    ).props('flat dense')

    @ui.page('/')
    def index():
        ui.page_title(tr('app_title'))
        shell(tr('pipeline'), 'pipeline')
        with ui.column().classes('hero'):
            ui.label(tr('hero_kicker')).classes('hero-kicker')
            with ui.element('div').classes('hero-title'):
                ui.html(
                    '4 × 96 <span class="hero-accent">→</span> 1 × 384',
                    sanitize=False,
                )
            ui.label(tr('hero_sub')).classes('hero-sub')

        try:
            show_first_run = not app.storage.user.get('first_run_dismissed')
        except Exception:
            show_first_run = True
        with ui.element('div').classes('first-run-row').mark('first_run_row'):
            first_run_slot = ui.element('div').classes('first-run-slot')
            if plate_fold_gif is not None:
                with ui.element('figure').classes('plate-fold').mark('plate_fold'):
                    ui.image(
                        f'{PLATE_FOLD_STATIC_URL}/{PLATE_FOLD_GIF}'
                    ).props(f'alt="{tr("plate_fold_alt")}"').mark('plate_fold_gif')

        if state.error:
            ui.label(
                app_config.localize_error(state.error, current_lang())
            ).classes('text-red-600')

        workbooks = state.workbooks()
        options = {str(path): path.name for path in workbooks}
        current = str(state.config_path()) if state.config else None
        if current not in options:
            current = None
        selected = {'path': current}

        with ui.card().classes('w-full panel'):
            ui.label(tr('source')).classes('panel-title')
            workbook_select = ui.select(
                options,
                value=current,
                label=tr('excel_file'),
            ).classes('w-full').props('outlined dense').mark('workbook')
            upload = ui.upload(
                label=tr('upload_xlsx'),
                auto_upload=True,
                max_file_size=50_000_000,
                on_rejected=lambda: on_rejected(),
            ).props('accept=".xlsx,.xlsm" flat bordered hide-upload-btn')
            workbook_info = ui.label('').classes('meta-line').mark('workbook_info')

        with ui.card().classes('w-full panel'):
            ui.label(tr('sheets')).classes('panel-title')
            with ui.element('div').classes('plate-legend'):
                for index in range(1, 5):
                    with ui.element('span').classes(f'plate-chip-legend p{index}'):
                        ui.html('<i></i>', sanitize=False)
                        ui.label(f"{tr('plate')} {index}")
            sheet_row = ui.element('div').classes('sheet-grid')
            sheet_status = ui.label('').classes('status-ok').mark('selection_status')
            sheet_hint = ui.label('').classes('meta-line').mark('selection_hint')
            range_input = ui.input(
                tr('data_range'),
                value='B3:M10',
            ).classes('range-row').props('outlined dense').mark('range')
            with ui.element('div').classes('extract-row').mark('plate_extract'):
                ui.label(tr('extract_title')).classes('panel-title').style(
                    'margin: 0; flex: 1 1 100%'
                )
                ui.label(tr('extract_hint')).classes('meta-line').style(
                    'margin: 0; flex: 1 1 100%'
                )
                extract_select = ui.select(
                    {},
                    label=tr('extract_plate'),
                ).props('outlined dense').mark('extract_plate')
                extract_button = ui.button(
                    tr('extract_copy'),
                    on_click=lambda: copy_plate_column(),
                ).props('color=primary unelevated dense').mark('extract_copy')

        action_slot = ui.element('div').classes('action-bar')
        with ui.element('div').classes('log-wrap w-full'):
            ui.label(tr('live_log')).classes('log-label')
            log = ui.log(max_lines=1000).classes('w-full log-panel')
        log_lines = []
        result_box = ui.column().classes('w-full mt-4')
        ui.timer(0.3, lambda: drain_logs(log, log_lines))

        def current_sheets():
            values = []
            for index in range(4):
                select = sheet_selects[index]
                values.append(select.value)
            return values

        sheet_selects = []
        with sheet_row:
            for index in range(4):
                plate_n = index + 1
                sheet_selects.append(
                    ui.select([], label=f"{tr('plate')} {plate_n}")
                    .classes(f'w-full plate-chip plate-chip-{plate_n}')
                    .props('outlined dense clearable')
                    .mark(f'sheet_{plate_n}')
                )

        def load_sheets():
            names = state.sheets()
            defaults = [None] * 4
            if state.config:
                for index, key in enumerate(app_config.PLATE_KEYS):
                    item = state.config['sheets'].get(key)
                    if item and item.get('sheet_name') in names:
                        defaults[index] = item['sheet_name']
            if not any(defaults):
                for index, name in enumerate(names[:4]):
                    defaults[index] = name
            for index, select in enumerate(sheet_selects):
                select.options = names
                select.value = defaults[index]
                select.update()
            refresh_extract_options()

        def refresh_extract_options():
            sheets = [value for value in current_sheets() if value]
            options = {'all': tr('extract_all')}
            for index, name in enumerate(sheets):
                options[str(index)] = f"{tr('plate')} {index + 1} · {name}"
            current = extract_select.value
            extract_select.set_options(
                options,
                value=current if current in options else (
                    '0' if sheets else 'all'
                ),
            )

        def copy_plate_column():
            path = selected.get('path')
            sheets = [value for value in current_sheets() if value]
            if not path or not sheets:
                ui.notify(tr('extract_empty'), type='warning')
                return
            try:
                config = state.apply(path, sheets, range_input.value)
                from openpyxl import load_workbook

                workbook = load_workbook(path, data_only=True)
                try:
                    blocks = []
                    keys = app_config.selected_plate_keys(config)
                    choice = extract_select.value
                    if choice == 'all' or choice is None:
                        targets = list(enumerate(keys))
                    else:
                        index = int(choice)
                        targets = [(index, keys[index])]
                    for index, key in targets:
                        sheet_name = config['sheets'][key]['sheet_name']
                        plate_data, _metadata = extract_plates.extract_plate_data(
                            workbook, sheet_name, config
                        )
                        values = extract_plates.observations_column(plate_data)
                        blocks.append((sheet_name, values))
                finally:
                    workbook.close()
                text = extract_plates.format_observations(
                    blocks, include_headers=len(blocks) > 1
                )
            except (app_config.ConfigError, OSError, ValueError, KeyError) as exc:
                ui.notify(
                    app_config.localize_error(exc, current_lang()),
                    type='negative',
                )
                return
            ui.clipboard.write(text)
            lines = text.count('\n') + (1 if text else 0)
            ui.notify(tr('extract_copied_n').format(n=lines), type='positive')

        def refresh_validation():
            path = selected.get('path')
            if not path:
                sheet_status.text = ''
                sheet_hint.text = ''
                workbook_info.text = ''
                button.enabled = False
                refresh_extract_options()
                return
            try:
                sheets = [value for value in current_sheets() if value]
                state.apply(path, sheets, range_input.value)
            except (app_config.ConfigError, OSError, ValueError) as exc:
                sheet_status.text = app_config.localize_error(exc, current_lang())
                sheet_status.classes(replace='meta-line')
                sheet_status.style('color: #b91c1c')
                sheet_hint.text = ''
                workbook_info.text = ''
                button.enabled = False
                refresh_extract_options()
                return
            count = len(app_config.selected_plate_keys(state.config))
            sheet_status.text = tr('selection_ready').format(n=count)
            sheet_status.classes(replace='status-ok')
            sheet_status.style('color: #5a6a42')
            sheet_hint.text = tr('selection_partial_hint') if count < 4 else ''
            try:
                workbook_info.text = app_config.workbook_summary(path, state.config)
            except Exception:
                workbook_info.text = ''
            button.enabled = True
            refresh_extract_options()

        def on_workbook(event):
            if not event.value:
                return
            selected['path'] = event.value
            try:
                state.apply(event.value, None, range_input.value)
            except (app_config.ConfigError, OSError, ValueError) as exc:
                ui.notify(
                    app_config.localize_error(exc, current_lang()),
                    type='negative',
                )
                return
            load_sheets()
            refresh_validation()

        def dismiss_first_run():
            try:
                app.storage.user['first_run_dismissed'] = True
            except Exception:
                pass
            first_run_slot.clear()

        def use_sample_workbook():
            sample = state.sample_workbook()
            if sample is None:
                ui.notify(tr('first_run_sample_missing'), type='warning')
                return
            path = str(sample)
            selected['path'] = path
            workbook_select.set_options(
                {str(item): item.name for item in state.workbooks()},
                value=path,
            )
            try:
                state.apply(path, None, range_input.value)
            except (app_config.ConfigError, OSError, ValueError) as exc:
                ui.notify(
                    app_config.localize_error(exc, current_lang()),
                    type='negative',
                )
                return
            load_sheets()
            refresh_validation()

        if show_first_run:
            with first_run_slot:
                with ui.element('div').classes('first-run').mark('first_run'):
                    ui.label(tr('first_run_title')).classes('first-run-title')
                    ui.label(tr('first_run_body')).classes('first-run-body')
                    with ui.element('div').classes('first-run-actions'):
                        if state.sample_workbook() is not None:
                            ui.button(
                                tr('first_run_use_sample'),
                                on_click=use_sample_workbook,
                            ).props(
                                'color=primary unelevated dense'
                            ).mark('first_run_sample')
                        ui.button(
                            tr('first_run_dismiss'),
                            on_click=dismiss_first_run,
                        ).props('flat dense').mark('first_run_dismiss')

        workbook_select.on_value_change(on_workbook)

        async def on_upload(event):
            name = Path(event.file.name).name
            if Path(name).suffix.lower() not in ('.xlsx', '.xlsm'):
                ui.notify(tr('upload_ext_error'), type='negative')
                return
            target = state.uploads / name
            if (state.base_dir / name).exists():
                target = state.uploads / f'{Path(name).stem}-uploaded{Path(name).suffix}'
            target.write_bytes(await event.file.read())
            try:
                config = app_config.build_config(
                    state.base_dir, excel_file=target
                )
                app_config.validate_config(config, state.base_dir)
            except (app_config.ConfigError, OSError, ValueError) as exc:
                ui.notify(
                    f"{tr('file_rejected')}: "
                    f"{app_config.localize_error(exc, current_lang())}",
                    type='negative',
                )
                target.unlink(missing_ok=True)
                upload.reset()
                return
            state.config = config
            state.error = None
            selected['path'] = str(target)
            workbook_select.options = {
                str(path): path.name for path in state.workbooks()
            }
            workbook_select.value = str(target)
            workbook_select.update()
            load_sheets()
            refresh_validation()
            ui.notify(
                f"{tr('uploaded')}: {name} · "
                f"{app_config.workbook_summary(target, state.config)}",
                type='positive',
            )
            upload.reset()

        upload.on_upload(on_upload)

        def on_rejected():
            upload.reset()
            ui.notify(tr('upload_type_error'), type='negative')

        async def run_now():
            if state.running:
                ui.notify(tr('run_in_progress'), type='warning')
                return
            try:
                excel = selected.get('path')
                if not excel:
                    raise app_config.ConfigError('select a workbook first')
                sheets = [value for value in current_sheets() if value]
                config = state.apply(excel, sheets, range_input.value)
            except (app_config.ConfigError, OSError, ValueError) as exc:
                ui.notify(
                    app_config.localize_error(exc, current_lang()),
                    type='negative',
                )
                return

            state.running = True
            result_box.clear()
            log.clear()
            button.props('loading')
            try:
                result = await asyncio.to_thread(
                    run_pipeline.run,
                    base_dir=state.base_dir,
                    log=lambda message: log_lines.append(str(message)),
                    config=config,
                )
            except (run_pipeline.PipelineError, OSError) as exc:
                ui.notify(
                    f"{tr('failed')}: "
                    f"{app_config.localize_error(exc, current_lang())}",
                    type='negative',
                )
            else:
                render_result(result, result_box)
                ui.notify(f"{tr('done')}: {result.name}", type='positive')
            finally:
                state.running = False
                button.props(remove='loading')

        with action_slot:
            button = ui.button(tr('run'), on_click=run_now).props(
                'color=primary unelevated size=md'
            ).mark('run_pipeline')
            ui.label(tr('run_hint')).classes('action-hint')
        for select in sheet_selects:
            select.on_value_change(lambda event: refresh_validation())
        range_input.on_value_change(lambda event: refresh_validation())
        load_sheets()
        refresh_validation()

    def render_results_legend():
        with ui.card().classes('w-full panel results-legend').mark('results_legend'):
            ui.label(tr('results_legend_title')).classes('panel-title')
            ui.label(tr('results_legend_intro')).classes('legend-intro')
            items = (
                'legend_plate_csv',
                'legend_column_txt',
                'legend_metadata',
                'legend_combined',
                'legend_pivot',
                'legend_ids',
                'legend_manifest',
            )
            lines = []
            for key in items:
                text = tr(key)
                if ' — ' in text:
                    name, desc = text.split(' — ', 1)
                    lines.append(f'<li><code>{name}</code> — {desc}</li>')
                else:
                    lines.append(f'<li>{text}</li>')
            ui.html(
                '<ul>' + ''.join(lines) + '</ul>',
                sanitize=False,
            )

    @ui.page('/results')
    def results_page():
        ui.page_title(tr('results'))
        shell(tr('results'), 'results')
        render_results_legend()

        folders = sorted(
            (
                path
                for path in state.base_dir.iterdir()
                if path.is_dir() and run_pipeline.RESULT_DIR_PATTERN.match(path.name)
            ),
            key=lambda path: path.name,
            reverse=True,
        )
        if not folders:
            with ui.card().classes('w-full panel'):
                ui.label(tr('results')).classes('panel-title')
                ui.label(tr('no_results_web')).classes('empty-state')
            return

        for folder in folders:
            with ui.card().classes('w-full panel'):
                render_result(folder, ui.column().classes('w-full'))

    @ui.page('/tools')
    def tools_page():
        ui.page_title(tr('tools'))
        tool_key = context.client.request.query_params.get('tool', 'tm')
        shell(tr('tools'), tool_key)

        def show(container, text):
            container.clear()
            with container:
                ui.code(str(text)).classes('w-full')

        def safe_show(container, function):
            try:
                show(container, function())
            except (genetics.ToolError, app_config.ConfigError, OSError, ValueError, ImportError) as exc:
                show(container, f"{tr('error')}: {exc}")

        with ui.tabs().classes('w-full') as tabs:
            tm_tab = ui.tab(tr('tool_tm'))
            pair_tab = ui.tab(tr('tool_pair'))
            dna_tab = ui.tab(tr('tool_dna'))
            units_tab = ui.tab(tr('tool_units'))
            structure_tab = ui.tab(tr('tool_structure'))
            pcr_tab = ui.tab(tr('tool_pcr'))
            gradient_tab = ui.tab(tr('tool_gradient'))
            layout_tab = ui.tab(tr('tool_layout'))
            xlsx_tab = ui.tab(tr('tool_xlsx'))
        tabs.style('display: none')

        tab_map = {
            'tm': tm_tab,
            'pair': pair_tab,
            'dna': dna_tab,
            'units': units_tab,
            'structure': structure_tab,
            'pcr': pcr_tab,
            'gradient': gradient_tab,
            'layout': layout_tab,
            'xlsx': xlsx_tab,
        }

        with ui.tab_panels(tabs, value=tab_map.get(tool_key, tm_tab)).classes(
            'w-full'
        ):
            with ui.tab_panel(tm_tab):
                with ui.card().classes('w-full panel tool-panel'):
                    ui.label(tr('tool_tm')).classes('panel-title')
                    tm_sequence = (
                        ui.input(tr('sequence'))
                        .classes('w-full')
                        .props('outlined dense')
                        .mark('tm_sequence')
                    )
                    tm_out = ui.column().classes('w-full mt-2')
                    ui.button(
                        tr('analyse'),
                        on_click=lambda: safe_show(
                            tm_out,
                            lambda: _primer_report(
                                genetics.analyze_primer(tm_sequence.value)
                            ),
                        ),
                    ).props('color=primary unelevated').classes(
                        'tool-actions'
                    ).mark('tm_button')

            with ui.tab_panel(pair_tab):
                with ui.card().classes('w-full panel tool-panel'):
                    ui.label(tr('tool_pair')).classes('panel-title')
                    pair_forward = (
                        ui.input(tr('forward'))
                        .classes('w-full')
                        .props('outlined dense')
                    )
                    pair_reverse = (
                        ui.input(tr('reverse_primer'))
                        .classes('w-full')
                        .props('outlined dense')
                    )
                    pair_out = ui.column().classes('w-full mt-2')
                    ui.button(
                        tr('analyse_pair'),
                        on_click=lambda: safe_show(
                            pair_out,
                            lambda: _pair_report(
                                genetics.analyze_pair(
                                    pair_forward.value, pair_reverse.value
                                )
                            ),
                        ),
                    ).props('color=primary unelevated').classes('tool-actions')

            with ui.tab_panel(dna_tab):
                with ui.card().classes('w-full panel tool-panel'):
                    ui.label(tr('tool_dna')).classes('panel-title')
                    dna_sequence = (
                        ui.input(tr('sequence'))
                        .classes('w-full')
                        .props('outlined dense')
                        .mark('dna_sequence')
                    )
                    dna_out = ui.column().classes('w-full mt-2')

                    def run_dna():
                        try:
                            rows = tool_reports.dna_rows(dna_sequence.value)
                        except (
                            genetics.ToolError,
                            OSError,
                            ValueError,
                        ) as exc:
                            show(dna_out, f"{tr('error')}: {exc}")
                            return
                        dna_out.clear()
                        with dna_out:
                            for key, value in rows:
                                with ui.row().classes('items-center gap-2 w-full'):
                                    ui.label(tr(key)).classes(
                                        'text-xs opacity-60 w-32'
                                    )
                                    ui.label(value).classes('font-mono break-all')
                                    ui.button(
                                        icon='content_copy',
                                        on_click=lambda value=value: ui.clipboard.write(
                                            value
                                        ),
                                    ).props('flat dense round size=sm')

                    ui.button(tr('transform'), on_click=run_dna).props(
                        'color=primary unelevated'
                    ).classes('tool-actions').mark('dna_button')

            with ui.tab_panel(units_tab):
                with ui.card().classes('w-full panel tool-panel'):
                    ui.label(tr('tool_units')).classes('panel-title')
                    unit_dimension = ui.select(
                        {
                            name: tr(f'dim_{name}')
                            for name in genetics.dimensions()
                        },
                        value='concentration',
                        label=tr('dimension'),
                    ).classes('w-full').props('outlined dense').mark(
                        'unit_dimension'
                    )
                    unit_from = ui.select(
                        genetics.units_for('concentration'),
                        value='uM',
                        label=tr('from_unit'),
                    ).classes('w-full').props('outlined dense').mark('unit_from')
                    unit_to = ui.select(
                        genetics.units_for('concentration'),
                        value='nM',
                        label=tr('to_unit'),
                    ).classes('w-full').props('outlined dense').mark('unit_to')
                    unit_value = (
                        ui.input(tr('value'), value='25')
                        .classes('w-full')
                        .props('outlined dense')
                        .mark('unit_value')
                    )
                    unit_out = ui.column().classes('w-full mt-2')

                    def change_dimension(event):
                        units = genetics.units_for(event.value)
                        unit_from.options = units
                        unit_to.options = units
                        unit_from.value = units[0]
                        unit_to.value = units[-1] if len(units) > 1 else units[0]
                        unit_from.update()
                        unit_to.update()

                    unit_dimension.on_value_change(change_dimension)

                    def convert_units():
                        raw = str(unit_value.value).strip().replace(',', '.')
                        try:
                            number = float(raw)
                        except ValueError as exc:
                            raise genetics.ToolError(tr('value_not_number')) from exc
                        result = genetics.convert(
                            number, unit_from.value, unit_to.value
                        )
                        return f'{genetics.format_number(result)} {unit_to.value}'

                    ui.button(
                        tr('convert'),
                        on_click=lambda: safe_show(unit_out, convert_units),
                    ).props('color=primary unelevated').classes(
                        'tool-actions'
                    ).mark('unit_button')

            with ui.tab_panel(structure_tab):
                with ui.card().classes('w-full panel tool-panel'):
                    ui.label(tr('tool_structure')).classes('panel-title')
                    structure_sequence = (
                        ui.input(tr('sequence'))
                        .classes('w-full')
                        .props('outlined dense')
                    )
                    structure_out = ui.column().classes('w-full mt-2')
                    ui.button(
                        tr('fold'),
                        on_click=lambda: safe_show(
                            structure_out,
                            lambda: _structure_report(
                                seq_structure.analyze_structure(
                                    structure_sequence.value
                                )
                            ),
                        ),
                    ).props('color=primary unelevated').classes('tool-actions')

            with ui.tab_panel(pcr_tab):
                with ui.card().classes('w-full panel tool-panel'):
                    ui.label(tr('tool_pcr')).classes('panel-title')
                    pcr_template = (
                        ui.textarea(tr('template'))
                        .classes('w-full')
                        .props('outlined')
                    )
                    pcr_forward = (
                        ui.input(tr('forward'))
                        .classes('w-full')
                        .props('outlined dense')
                    )
                    pcr_reverse = (
                        ui.input(tr('reverse_primer'))
                        .classes('w-full')
                        .props('outlined dense')
                    )
                    pcr_out = ui.column().classes('w-full mt-2')
                    ui.button(
                        tr('simulate'),
                        on_click=lambda: safe_show(
                            pcr_out,
                            lambda: _pcr_report(
                                pcr_tools.simulate_pcr(
                                    pcr_template.value,
                                    pcr_forward.value,
                                    pcr_reverse.value,
                                )
                            ),
                        ),
                    ).props('color=primary unelevated').classes('tool-actions')

            with ui.tab_panel(gradient_tab):
                with ui.card().classes('w-full panel tool-panel'):
                    ui.label(tr('tool_gradient')).classes('panel-title')
                    ui.label(tr('gradient_hint')).classes('meta-line')
                    gradient_back = (
                        ui.input(tr('gradient_back'), value='64')
                        .classes('w-full')
                        .props('outlined dense')
                        .mark('gradient_back')
                    )
                    gradient_front = (
                        ui.input(tr('gradient_front'), value='52')
                        .classes('w-full')
                        .props('outlined dense')
                        .mark('gradient_front')
                    )
                    gradient_out = ui.column().classes('w-full mt-2')
                    ui.button(
                        tr('analyse'),
                        on_click=lambda: safe_show(
                            gradient_out,
                            lambda: _gradient_report(
                                genetics.block_gradient(
                                    gradient_back.value, gradient_front.value
                                )
                            ),
                        ),
                    ).props('color=primary unelevated').classes(
                        'tool-actions'
                    ).mark('gradient_button')

            with ui.tab_panel(layout_tab):
                with ui.card().classes('w-full panel tool-panel'):
                    ui.label(tr('tool_layout')).classes('panel-title')
                    layout_out = ui.column().classes('w-full mt-2')

                    async def on_layout(event):
                        target = Path(tempfile.mkdtemp()) / 'plate.toml'
                        target.write_bytes(await event.file.read())
                        safe_show(
                            layout_out,
                            lambda: _layout_report(
                                plate_layout.load_layout(target)
                            ),
                        )

                    ui.label(tr('upload_layout')).classes('meta-line')
                    ui.upload(on_upload=on_layout, auto_upload=True).props(
                        'flat bordered hide-upload-btn'
                    )

            with ui.tab_panel(xlsx_tab):
                with ui.card().classes('w-full panel tool-panel'):
                    ui.label(tr('tool_xlsx')).classes('panel-title')
                    xlsx_out = ui.column().classes('w-full mt-2')
                    result_dirs = sorted(
                        path.name
                        for path in state.base_dir.iterdir()
                        if path.is_dir()
                        and run_pipeline.RESULT_DIR_PATTERN.match(path.name)
                    )
                    folder = (
                        ui.select(result_dirs, label=tr('result_folder'))
                        .classes('w-full')
                        .props('outlined dense')
                    )
                    ui.button(
                        tr('export_xlsx'),
                        on_click=lambda: safe_show(
                            xlsx_out,
                            lambda: str(
                                report_xlsx.export_workbook(
                                    state.base_dir / folder.value
                                )
                            ),
                        ),
                    ).props('color=primary unelevated').classes(
                        'tool-actions'
                    ).mark('xlsx_button')

    return state


def render_rows(rows):
    return '\n'.join(
        f"{tr(key)}  {tr('no_structure') if value is None else value}"
        for key, value in rows
    )


def _json_node(value, path, label):
    if isinstance(value, dict):
        return {
            'id': path,
            'label': label,
            'expand': True,
            'children': [
                _json_node(item, f'{path}.{key}', str(key))
                for key, item in value.items()
            ],
        }
    if isinstance(value, list):
        return {
            'id': path,
            'label': label,
            'expand': True,
            'children': [
                _json_node(item, f'{path}.{index}', f'[{index}]')
                for index, item in enumerate(value)
            ],
        }
    return {'id': path, 'label': f'{label}: {value}'}


def _primer_report(report):
    return render_rows(tool_reports.primer_rows(report))


def _pair_report(report):
    return render_rows(tool_reports.pair_rows(report))


def _dna_report(sequence):
    return render_rows(tool_reports.dna_rows(sequence))


def _structure_report(report):
    return render_rows(tool_reports.structure_rows(report))


def _pcr_report(report):
    return render_rows(tool_reports.pcr_rows(report))


def _gradient_report(report):
    return '\n'.join(
        f'{letter}: {value}' for letter, value in tool_reports.gradient_rows(report)
    )


def _layout_report(report):
    return render_rows(tool_reports.layout_rows(report))


def main(base_dir=None, port=8080, show=True):
    build_app(base_dir or run_pipeline.application_dir())
    ui.run(
        host='127.0.0.1',
        port=port,
        title=TEXT['en']['app_title'],
        favicon='◈',
        reload=False,
        show=show,
        dark=False,
        storage_secret=secrets.token_hex(16),
    )
