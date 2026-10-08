"""Final dark/gold visual system for Agentic Document Intelligence."""

from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st


_BG_PATH = Path(__file__).resolve().parent / "assets" / "adi_background.svg"


def _background_data_uri() -> str:
    if not _BG_PATH.exists():
        return ""
    encoded = base64.b64encode(_BG_PATH.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


_BASE_CSS = r"""
<style>
* { box-sizing: border-box; }

:root {
  --adi-bg: #101113;
  --adi-bg2: #17181b;
  --adi-surface: rgba(31, 33, 37, .78);
  --adi-surface-strong: rgba(34, 36, 41, .92);
  --adi-surface2: rgba(44, 46, 51, .82);
  --adi-text: #F8F9FA;
  --adi-muted: #A5A7AB;
  --adi-border: rgba(255,255,255,.095);
  --adi-gold: #FFD43B;
  --adi-gold2: #FCC419;
  --adi-gold-soft: rgba(255, 212, 59, .11);
  --adi-shadow: rgba(0,0,0,.34);
  --adi-fast: 180ms;
  --adi-medium: 360ms;
}

html { scroll-behavior: smooth; }

html, body, [data-testid="stAppViewContainer"] {
  color: var(--adi-text);
}

[data-testid="stAppViewContainer"] {
  min-height: 100vh;
  background:
    linear-gradient(180deg, rgba(10,11,13,.73), rgba(10,11,13,.87)),
    var(--adi-background-image),
    linear-gradient(135deg, var(--adi-bg), var(--adi-bg2));
  background-size: cover;
  background-position: center top;
  background-repeat: no-repeat;
  background-attachment: fixed;
  animation: adiBgDrift 22s ease-in-out infinite alternate;
}

[data-testid="stAppViewContainer"]::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background:
    radial-gradient(circle at 12% 15%, rgba(255,212,59,.08), transparent 26%),
    radial-gradient(circle at 88% 22%, rgba(252,196,25,.06), transparent 24%);
  animation: adiGlowShift 14s ease-in-out infinite alternate;
}

[data-testid="stAppViewBlockContainer"] {
  position: relative;
  z-index: 1;
  max-width: 1480px;
  padding-top: 1.15rem;
  padding-bottom: 4rem;
}

[data-testid="stHeader"] { background: transparent; }

[data-testid="stSidebar"] {
  background: rgba(28, 30, 34, .90);
  border-right: 1px solid var(--adi-border);
  backdrop-filter: blur(18px) saturate(120%);
  -webkit-backdrop-filter: blur(18px) saturate(120%);
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
  color: var(--adi-text);
}

h1, h2, h3, h4 {
  color: var(--adi-text);
  letter-spacing: -.035em;
}

p, li, label { color: color-mix(in srgb, var(--adi-text) 86%, var(--adi-muted)); }

[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
  color: var(--adi-muted) !important;
}

[data-testid="stMarkdownContainer"] a { color: var(--adi-gold); }

/* Navigation */
div[data-baseweb="tab-list"] {
  gap: .28rem;
  padding: .3rem;
  position: sticky;
  top: .55rem;
  z-index: 20;
  background: rgba(28,30,34,.82);
  border: 1px solid var(--adi-border);
  border-radius: 15px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 12px 30px var(--adi-shadow);
}

button[data-baseweb="tab"] {
  min-height: 42px;
  border-radius: 10px;
  color: var(--adi-muted);
  font-weight: 720;
  padding: 0 1rem;
  transition: transform var(--adi-fast) ease, color var(--adi-fast) ease, background var(--adi-fast) ease;
}

button[data-baseweb="tab"]:hover {
  color: var(--adi-text);
  background: rgba(255,255,255,.045);
  transform: translateY(-1px);
}

button[data-baseweb="tab"][aria-selected="true"] {
  color: #17181b;
  background: var(--adi-gold);
  border: 1px solid var(--adi-gold);
}

/* Controls */
div.stButton > button,
div.stDownloadButton > button {
  min-height: 43px;
  border-radius: 11px;
  border: 1px solid var(--adi-gold);
  background: var(--adi-gold);
  color: #17181b;
  font-weight: 800;
  box-shadow: 0 9px 22px rgba(255,212,59,.13);
  transition: transform var(--adi-fast) ease, background var(--adi-fast) ease, box-shadow var(--adi-fast) ease;
}

div.stButton > button:hover,
div.stDownloadButton > button:hover {
  transform: translateY(-2px);
  background: var(--adi-gold2);
  border-color: var(--adi-gold2);
  box-shadow: 0 13px 30px rgba(255,212,59,.20);
}

div.stButton > button:active,
div.stDownloadButton > button:active {
  transform: translateY(0) scale(.99);
}

[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
  color: var(--adi-text) !important;
  background: rgba(28,30,34,.86) !important;
  border: 1px solid var(--adi-border) !important;
  border-radius: 11px !important;
  box-shadow: none !important;
}

[data-testid="stTextArea"] textarea:focus,
[data-baseweb="select"] > div:focus-within,
[data-baseweb="input"] > div:focus-within {
  border-color: rgba(255,212,59,.75) !important;
  box-shadow: 0 0 0 3px rgba(255,212,59,.10) !important;
}

[data-baseweb="popover"] > div,
[data-baseweb="menu"] {
  background: #24262b !important;
  border: 1px solid var(--adi-border) !important;
  border-radius: 11px !important;
  box-shadow: 0 18px 42px rgba(0,0,0,.45) !important;
}

[role="option"] { color: var(--adi-text) !important; }
[role="option"]:hover,
[aria-selected="true"][role="option"] {
  background: var(--adi-gold-soft) !important;
}

[data-testid="stFileUploader"] {
  background: rgba(28,30,34,.72);
  border: 1px dashed rgba(255,212,59,.40);
  border-radius: 16px;
  padding: .72rem;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  transition: border-color var(--adi-fast) ease, box-shadow var(--adi-fast) ease, transform var(--adi-fast) ease;
}

[data-testid="stFileUploader"]:hover {
  border-color: var(--adi-gold);
  box-shadow: 0 0 0 3px rgba(255,212,59,.08);
  transform: translateY(-1px);
}

[data-testid="stMetric"] {
  position: relative;
  overflow: hidden;
  min-height: 102px;
  padding: 1rem;
  background: rgba(31,33,37,.74);
  border: 1px solid var(--adi-border);
  border-radius: 15px;
  box-shadow: 0 10px 26px var(--adi-shadow);
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
}

[data-testid="stMetric"]::before {
  content: "";
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--adi-gold);
}

[data-testid="stMetricValue"] {
  color: var(--adi-text);
  font-weight: 850;
  letter-spacing: -.04em;
}

[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stExpander"],
[data-testid="stAlert"],
[data-testid="stStatusWidget"] {
  background: rgba(31,33,37,.76) !important;
  border: 1px solid var(--adi-border) !important;
  border-radius: 15px !important;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

[data-testid="stSlider"] [role="slider"] {
  background: var(--adi-gold) !important;
  border-color: var(--adi-gold) !important;
  box-shadow: 0 0 0 4px var(--adi-gold-soft);
}

[data-testid="stCheckbox"] span[data-baseweb="checkbox"][aria-checked="true"] > div {
  background: var(--adi-gold) !important;
  border-color: var(--adi-gold) !important;
}

[data-testid="stProgress"] > div > div { background: var(--adi-gold) !important; }

[data-testid="stCodeBlock"],
[data-testid="stDataFrame"] {
  border: 1px solid var(--adi-border);
  border-radius: 12px;
  overflow: hidden;
}

/* Brand */
.adi-brandbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 58px;
  padding: .72rem 1rem;
  margin-bottom: .8rem;
  background: rgba(31,33,37,.72);
  border: 1px solid var(--adi-border);
  border-radius: 16px;
  box-shadow: 0 10px 28px var(--adi-shadow);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  animation: adiFade .45s ease both;
}

.adi-brand {
  display: flex;
  align-items: center;
  gap: .72rem;
  color: var(--adi-text);
  font-size: 1rem;
  font-weight: 850;
  letter-spacing: -.025em;
}

.adi-brandmark {
  width: 35px;
  height: 35px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #17181b;
  background: var(--adi-gold);
  font-size: .7rem;
  font-weight: 950;
  box-shadow: 0 0 0 5px rgba(255,212,59,.09);
}

.adi-brandmeta {
  display: flex;
  align-items: center;
  gap: .45rem;
  color: var(--adi-muted);
  font-size: .74rem;
}

.adi-live-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--adi-gold);
  box-shadow: 0 0 15px rgba(255,212,59,.5);
  animation: adiPulse 2s ease-out infinite;
}

/* Hero: deliberately clean; artwork is the background */
.adi-hero {
  position: relative;
  overflow: hidden;
  min-height: 390px;
  display: flex;
  align-items: center;
  padding: 3.5rem 3.4rem;
  margin-bottom: 1rem;
  border-radius: 28px;
  background:
    linear-gradient(90deg, rgba(26,27,30,.91) 0%, rgba(26,27,30,.75) 52%, rgba(26,27,30,.36) 100%);
  border: 1px solid var(--adi-border);
  box-shadow: 0 18px 46px rgba(0,0,0,.36);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  animation: adiFadeUp .55s cubic-bezier(.22,.9,.28,1) both;
}

.adi-hero::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(112deg, transparent 28%, rgba(255,212,59,.06) 48%, transparent 68%);
  transform: translateX(-100%);
  animation: adiHeroSweep 9s ease-in-out infinite;
}

.adi-hero-copy {
  position: relative;
  z-index: 2;
  width: min(760px, 75%);
}

.adi-kicker {
  color: #C8B873;
  font-size: .72rem;
  font-weight: 850;
  letter-spacing: .11em;
  text-transform: uppercase;
}

.adi-title {
  margin: .7rem 0 .8rem;
  color: var(--adi-text);
  font-size: clamp(2.6rem, 4.6vw, 5.15rem);
  line-height: .98;
  font-weight: 950;
  letter-spacing: -.065em;
}

.adi-title .accent { color: var(--adi-gold); }

.adi-subtitle {
  max-width: 690px;
  color: #B8BABE;
  font-size: 1rem;
  line-height: 1.7;
  margin-bottom: 1.25rem;
}

.adi-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: .5rem;
}

.adi-chip {
  display: inline-flex;
  align-items: center;
  padding: .45rem .68rem;
  border-radius: 10px;
  background: rgba(37,39,44,.72);
  border: 1px solid rgba(255,255,255,.08);
  color: var(--adi-text);
  font-size: .73rem;
  font-weight: 760;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.adi-chip strong {
  color: var(--adi-gold);
  margin-right: .3rem;
}

/* Reusable content */
.adi-section {
  display: flex;
  align-items: center;
  gap: .55rem;
  color: var(--adi-text);
  font-size: 1.05rem;
  font-weight: 850;
  margin: .65rem 0 .75rem;
}

.adi-section::before {
  content: "";
  width: 21px; height: 4px;
  border-radius: 99px;
  background: var(--adi-gold);
}

.adi-card {
  height: 100%;
  position: relative;
  overflow: hidden;
  padding: 1.1rem;
  border-radius: 16px;
  background: rgba(31,33,37,.73);
  border: 1px solid var(--adi-border);
  box-shadow: 0 10px 28px var(--adi-shadow);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  transition: transform var(--adi-fast) ease, border-color var(--adi-fast) ease, box-shadow var(--adi-fast) ease;
}

.adi-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255,212,59,.30);
  box-shadow: 0 15px 36px rgba(0,0,0,.38);
}

.adi-card-title {
  color: var(--adi-text);
  font-weight: 820;
  margin-bottom: .36rem;
}

.adi-card-copy {
  color: var(--adi-muted);
  line-height: 1.55;
  font-size: .87rem;
}

.adi-icon {
  width: 37px; height: 37px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: .72rem;
  border-radius: 10px;
  background: var(--adi-gold-soft);
  border: 1px solid rgba(255,212,59,.22);
  color: var(--adi-gold);
  font-size: .76rem;
  font-weight: 900;
}

.adi-zone {
  min-height: 88px;
  margin-bottom: .7rem;
  padding: .92rem;
  border-radius: 15px;
  background: rgba(31,33,37,.70);
  border: 1px solid var(--adi-border);
  backdrop-filter: blur(13px);
  -webkit-backdrop-filter: blur(13px);
}

.adi-zone-label {
  color: var(--adi-gold);
  font-size: .68rem;
  letter-spacing: .09em;
  text-transform: uppercase;
  font-weight: 900;
  margin-bottom: .24rem;
}

.adi-zone-copy {
  color: var(--adi-muted);
  font-size: .81rem;
  line-height: 1.48;
}

.adi-status {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: .36rem .62rem;
  margin: 0 .34rem .34rem 0;
  font-size: .71rem;
  font-weight: 780;
  border: 1px solid var(--adi-border);
  background: rgba(37,39,44,.76);
  color: var(--adi-text);
}

.adi-status.info,
.adi-status.gold,
.adi-status.magenta {
  border-color: rgba(255,212,59,.28);
  background: var(--adi-gold-soft);
}

.adi-gauge-wrap {
  display: flex;
  align-items: center;
  gap: .8rem;
  margin: .55rem 0 .7rem;
  padding: .75rem;
  border-radius: 14px;
  background: rgba(31,33,37,.72);
  border: 1px solid var(--adi-border);
}

.adi-gauge {
  --value: 0;
  width: 62px; height: 62px; flex: 0 0 62px;
  display: grid; place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle closest-side, #24262b 72%, transparent 73% 99%),
    conic-gradient(var(--adi-gold) calc(var(--value) * 1%), #3a3c42 0);
}

.adi-gauge strong { color: var(--adi-text); font-size: .76rem; }
.adi-gauge-title { color: var(--adi-text); font-weight: 820; font-size: .82rem; }
.adi-gauge-copy { color: var(--adi-muted); font-size: .72rem; line-height: 1.4; }

.adi-benchmark {
  border-left: 3px solid var(--adi-gold);
  background: rgba(31,33,37,.70);
  border-radius: 11px;
  padding: .82rem .92rem;
  color: var(--adi-muted);
  margin: .35rem 0;
}

.adi-config-line {
  display: flex;
  justify-content: space-between;
  gap: .7rem;
  padding: .6rem 0;
  border-bottom: 1px solid var(--adi-border);
}

.adi-config-line:last-child { border-bottom: none; }
.adi-config-key { color: var(--adi-muted); }
.adi-config-value { color: var(--adi-text); font-weight: 720; text-align: right; }

* {
  scrollbar-width: thin;
  scrollbar-color: #3a3c42 transparent;
}

@keyframes adiBgDrift {
  0% { background-position: center top; }
  100% { background-position: 51% 2%; }
}

@keyframes adiGlowShift {
  from { opacity: .72; transform: scale(1); }
  to { opacity: 1; transform: scale(1.035); }
}

@keyframes adiFade {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes adiFadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes adiPulse {
  0% { box-shadow: 0 0 0 0 rgba(255,212,59,.38); }
  70% { box-shadow: 0 0 0 9px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}

@keyframes adiHeroSweep {
  0%, 68%, 100% { transform: translateX(-100%); opacity: 0; }
  76% { opacity: 1; }
  90% { transform: translateX(100%); opacity: .8; }
}

@media (max-width: 980px) {
  .adi-brandmeta { display: none; }
  .adi-hero {
    min-height: 360px;
    padding: 2.2rem 1.5rem;
    background: rgba(26,27,30,.82);
  }
  .adi-hero-copy { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .001ms !important;
  }
}
</style>
"""


def available_themes() -> list[str]:
    """Kept for compatibility; the final product uses one polished theme."""
    return ["Dark"]


def apply_v2_theme(theme: str = "Dark") -> None:
    del theme
    background = _background_data_uri()
    background_css = (
        f'url("{background}")'
        if background
        else "linear-gradient(135deg, #101113, #17181b)"
    )
    st.markdown(
        f"<style>:root {{ --adi-background-image: {background_css}; }}</style>"
        + _BASE_CSS,
        unsafe_allow_html=True,
    )


def render_ambient_background() -> None:
    """Compatibility no-op: the generated artwork is now the app background."""


def render_hero(theme: str = "Dark") -> None:
    del theme
    st.markdown(
        """
        <div class="adi-brandbar">
          <div class="adi-brand">
            <span class="adi-brandmark">AI</span>
            Agentic Document Intelligence
          </div>
          <div class="adi-brandmeta">
            <span class="adi-live-dot"></span>
            Local-first · evidence-grounded
          </div>
        </div>

        <section class="adi-hero">
          <div class="adi-hero-copy">
            <div class="adi-kicker">Evidence-grounded AI for documents</div>
            <div class="adi-title">
              Ask your documents.<br>
              <span class="accent">Verify every answer.</span>
            </div>
            <div class="adi-subtitle">
              Read text or scanned PDFs, retrieve inspectable evidence, verify
              generated claims, and recover missing support with a bounded
              evidence-aware agent.
            </div>
            <div class="adi-chip-row">
              <span class="adi-chip"><strong>01</strong> OCR ingestion</span>
              <span class="adi-chip"><strong>02</strong> Evidence retrieval</span>
              <span class="adi-chip"><strong>03</strong> Semantic verification</span>
              <span class="adi-chip"><strong>04</strong> Agentic recovery</span>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_pipeline() -> None:
    """Deprecated visual retained only for import compatibility."""


def feature_card(icon: str, title: str, copy: str, accent: str = "b") -> None:
    del accent
    st.markdown(
        f"""
        <div class="adi-card">
          <div class="adi-icon">{html.escape(icon)}</div>
          <div class="adi-card-title">{html.escape(title)}</div>
          <div class="adi-card-copy">{html.escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def zone_intro(label: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="adi-zone">
          <div class="adi-zone-label">{html.escape(label)}</div>
          <div class="adi-zone-copy">{html.escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pills(items: list[tuple[str, str]]) -> None:
    rendered = []
    for label, variant in items:
        safe_variant = variant if variant in {"", "info", "gold", "magenta"} else ""
        rendered.append(
            f'<span class="adi-status {safe_variant}">{html.escape(label)}</span>'
        )
    st.markdown("".join(rendered), unsafe_allow_html=True)


def verification_gauge(
    value: float,
    title: str,
    detail: str,
    *,
    accent: str = "d",
) -> None:
    del accent
    percent = max(0.0, min(1.0, value)) * 100
    st.markdown(
        f"""
        <div class="adi-gauge-wrap">
          <div class="adi-gauge" style="--value:{percent:.1f}">
            <strong>{percent:.0f}%</strong>
          </div>
          <div>
            <div class="adi-gauge-title">{html.escape(title)}</div>
            <div class="adi-gauge-copy">{html.escape(detail)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def config_line(key: str, value: str) -> str:
    return (
        '<div class="adi-config-line">'
        f'<span class="adi-config-key">{html.escape(key)}</span>'
        f'<span class="adi-config-value">{html.escape(value)}</span>'
        '</div>'
    )
