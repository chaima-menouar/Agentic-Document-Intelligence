"""Compact charcoal/yellow workspace; trusted layout bypasses Markdown parsing."""
from __future__ import annotations
import html
import streamlit as st

_BASE_CSS = """
<style>
:root { --adi-bg:#18191c; --adi-surface:#222327; --adi-text:#f5f5f2; --adi-muted:#acadb5; --adi-border:#37383f; --adi-gold:#ffd43b; --adi-soft:rgba(255,212,59,.08); }
[data-testid="stAppViewContainer"] { background:radial-gradient(ellipse at 85% 0%,rgba(255,212,59,.045),transparent 45%),var(--adi-bg); color:var(--adi-text); }
[data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"] { max-width:1280px; padding:2.2rem 2.5rem 4rem; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { background:#202125; border-right:1px solid var(--adi-border); }
h1,h2,h3 { color:var(--adi-text); letter-spacing:-.035em; }
[data-testid="stCaptionContainer"] p { color:var(--adi-muted); }
[data-testid="stMarkdownContainer"] a { color:var(--adi-gold); }
[data-testid="stTabs"] [role="tablist"] { gap:1.6rem; border-bottom:1px solid var(--adi-border); background:transparent; }
[data-testid="stTabs"] [role="tab"] { padding:.8rem .1rem; color:var(--adi-muted); }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color:var(--adi-gold); }
[data-testid="stTabs"] [role="tabpanel"] { padding-top:1.6rem; }
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button { border-radius:10px; min-height:42px; transition:background .18s,border-color .18s; }
[data-testid="stButton"] button[kind="primary"] { background:var(--adi-gold); color:#191a1d; border-color:var(--adi-gold); }
[data-testid="stButton"] button[kind="secondary"], [data-testid="stDownloadButton"] button { background:var(--adi-surface); color:var(--adi-text); border-color:var(--adi-border); }
[data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover { border-color:var(--adi-gold); }
button:focus-visible,a:focus-visible { outline:2px solid var(--adi-gold); outline-offset:4px; }
[data-testid="stTextArea"] textarea, [data-baseweb="input"], [data-baseweb="select"] > div { background:var(--adi-surface); color:var(--adi-text); border-radius:10px; }
[data-testid="stFileUploader"] section { min-height:165px; padding:1.5rem; border:1px dashed #585849; border-radius:16px; background:var(--adi-surface); }
[data-testid="stFileUploader"] section:hover { border-color:var(--adi-gold); }
[data-testid="stExpander"], [data-testid="stMetric"] { border-radius:12px; }
[data-testid="stMetric"] { padding:1rem 1.2rem; background:var(--adi-surface); border:1px solid var(--adi-border); }
[data-testid="stMetricValue"] { font-size:1.65rem; color:var(--adi-text); }
.adi-brandbar { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:.3rem 0 2rem; }
.adi-brand { display:flex; align-items:center; gap:.75rem; color:var(--adi-text); font-weight:650; font-size:.92rem; }
.adi-brandmark { width:34px; height:34px; display:grid; place-items:center; background:var(--adi-gold); color:#191a1d; border-radius:10px; font-weight:850; font-size:.7rem; }
.adi-brandmeta { font-size:.75rem; color:var(--adi-muted); }
.adi-hero { display:grid; grid-template-columns:1.35fr 1fr; align-items:center; gap:3rem; padding:1.4rem 0 2.6rem; animation:adiEnter .45s ease both; }
.adi-kicker { color:var(--adi-gold); text-transform:uppercase; letter-spacing:.14em; font-size:.68rem; font-weight:700; }
.adi-hero h1 { margin:.9rem 0 1rem; padding:0; font-size:clamp(2.3rem,4.1vw,3.7rem); line-height:1.08; font-weight:650; letter-spacing:-.055em; }
.adi-hero h1 span { color:var(--adi-gold); }
.adi-subtitle { color:var(--adi-muted); max-width:470px; font-size:.96rem; line-height:1.7; margin:0; }
.adi-art { height:245px; position:relative; display:grid; place-items:center; }
.adi-art::before { content:''; position:absolute; width:245px; height:245px; border-radius:50%; border:1px solid #454438; background:radial-gradient(circle,rgba(255,212,59,.07),transparent 70%); }
.adi-paper { position:absolute; width:158px; height:199px; border:1px solid #51514a; border-radius:14px; background:#2b2c2e; padding:24px 22px; box-shadow:0 14px 40px #0003; }
.adi-paper.back { transform:translate(28px,-6px) rotate(12deg); background:#232427; }
.adi-paper.front { transform:rotate(-7deg); animation:adiFloat 7s ease-in-out infinite; }
.adi-paper-symbol { width:25px; height:31px; border:1.5px solid var(--adi-gold); border-radius:4px; margin-bottom:23px; }
.adi-paper-line { height:5px; border-radius:4px; background:#5a5b5d; margin:11px 0; }
.adi-paper-line.short { width:64%; } .adi-paper-line.highlight { background:#ffd43b88; }
.adi-paper-seal { position:absolute; right:-17px; bottom:25px; width:40px; height:40px; border-radius:50%; background:var(--adi-gold); color:#191a1d; display:grid; place-items:center; font-size:1.15rem; box-shadow:0 0 0 7px #18191c; }
.adi-section { font-size:1.2rem; font-weight:650; color:var(--adi-text); margin:.4rem 0; letter-spacing:-.025em; }
.adi-card,.adi-zone { padding:1.2rem; border:1px solid var(--adi-border); border-radius:12px; background:var(--adi-surface); }
.adi-card-title { color:var(--adi-text); font-weight:650; margin:.5rem 0; }
.adi-card-copy,.adi-zone-copy { color:var(--adi-muted); font-size:.85rem; line-height:1.6; }
.adi-icon,.adi-zone-label { color:var(--adi-gold); font-size:.75rem; font-weight:650; margin-bottom:.5rem; }
.adi-zone { margin-bottom:.8rem; }
.adi-status { display:inline-block; color:var(--adi-muted); font-size:.72rem; padding:.3rem .6rem; border:1px solid var(--adi-border); border-radius:6px; margin:0 .3rem .4rem 0; }
.adi-status.info,.adi-status.gold { color:var(--adi-gold); background:var(--adi-soft); }
.adi-gauge-wrap { display:flex; align-items:center; gap:1rem; margin:1rem 0; }
.adi-gauge { width:60px; height:60px; flex-shrink:0; border-radius:50%; display:grid; place-items:center; background:radial-gradient(circle closest-side,#222327 76%,transparent 78%),conic-gradient(var(--adi-gold) calc(var(--value) * 1%),#37383f 0); }
.adi-gauge strong { font-size:.8rem; color:var(--adi-text); }
.adi-gauge-title { color:var(--adi-text); font-size:.85rem; font-weight:650; }
.adi-gauge-copy { color:var(--adi-muted); font-size:.75rem; }
.adi-benchmark { border-left:2px solid var(--adi-gold); padding:.8rem 1rem; color:var(--adi-muted); background:var(--adi-surface); margin:.4rem 0; border-radius:0 10px 10px 0; }
.adi-config-line { display:flex; justify-content:space-between; gap:1rem; padding:.65rem 0; border-bottom:1px solid var(--adi-border); font-size:.85rem; }
.adi-config-line:last-child { border-bottom:0; } .adi-config-key { color:var(--adi-muted); } .adi-config-value { color:var(--adi-text); text-align:right; }
@keyframes adiEnter { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
@keyframes adiFloat { 0%,100% { transform:translateY(0) rotate(-7deg); } 50% { transform:translateY(-7px) rotate(-5deg); } }
@media(max-width:760px) {
  [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"] { padding:1.6rem 1rem 3rem; }
  .adi-brandmeta { display:none; } .adi-brandbar { margin-bottom:1rem; }
  .adi-hero { grid-template-columns:1fr; gap:0; padding:1rem 0 2rem; }
  .adi-art { display:none; } .adi-hero h1 { font-size:2.5rem; }
  [data-testid="stTabs"] [role="tablist"] { gap:1rem; }
}
@media(prefers-reduced-motion:reduce) { .adi-hero,.adi-paper.front { animation:none; } [data-testid="stButton"] button,[data-testid="stDownloadButton"] button { transition:none; } }
</style>
"""


def apply_v2_theme(theme: str = "Dark") -> None:
    st.html(_BASE_CSS)


def render_hero(theme: str = "Dark") -> None:
    st.html("""
        <header class="adi-brandbar">
          <div class="adi-brand"><span class="adi-brandmark">AI</span>Agentic Document Intelligence</div>
          <div class="adi-brandmeta">Your document workspace</div>
        </header>
        <section class="adi-hero">
          <div>
            <div class="adi-kicker">Clarity, backed by evidence</div>
            <h1>Your documents.<br><span>Answers you can check.</span></h1>
            <p class="adi-subtitle">Bring your PDFs, ask a question, and explore the sources behind each answer. Everything starts with your documents.</p>
          </div>
          <div class="adi-art" aria-hidden="true">
            <div class="adi-paper back"></div>
            <div class="adi-paper front"><div class="adi-paper-symbol"></div>
              <div class="adi-paper-line"></div><div class="adi-paper-line short"></div>
              <div class="adi-paper-line highlight"></div><div class="adi-paper-line short"></div>
              <div class="adi-paper-seal">✓</div>
            </div>
          </div>
        </section>
    """)


def feature_card(icon: str, title: str, copy: str, accent: str = "b") -> None:
    st.html(f'<div class="adi-card"><div class="adi-icon">{html.escape(icon)}</div>'
            f'<div class="adi-card-title">{html.escape(title)}</div>'
            f'<div class="adi-card-copy">{html.escape(copy)}</div></div>')


def zone_intro(label: str, copy: str) -> None:
    st.html(f'<div class="adi-zone"><div class="adi-zone-label">{html.escape(label)}</div>'
            f'<div class="adi-zone-copy">{html.escape(copy)}</div></div>')


def status_pills(items: list[tuple[str, str]]) -> None:
    rendered = []
    for label, variant in items:
        safe_variant = variant if variant in {"", "info", "gold", "magenta"} else ""
        rendered.append(f'<span class="adi-status {safe_variant}">{html.escape(label)}</span>')
    st.html("".join(rendered))


def verification_gauge(value: float, title: str, detail: str, *, accent: str = "d") -> None:
    percent = max(0.0, min(1.0, value)) * 100
    st.html(f'<div class="adi-gauge-wrap"><div class="adi-gauge" style="--value:{percent:.1f}">'
            f'<strong>{percent:.0f}%</strong></div><div><div class="adi-gauge-title">{html.escape(title)}</div>'
            f'<div class="adi-gauge-copy">{html.escape(detail)}</div></div></div>')


def config_line(key: str, value: str) -> str:
    return ('<div class="adi-config-line">'
            f'<span class="adi-config-key">{html.escape(key)}</span>'
            f'<span class="adi-config-value">{html.escape(value)}</span></div>')
