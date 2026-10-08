"""Modern visual system for the V2 Streamlit interface."""

from __future__ import annotations

import streamlit as st


V2_THEME_CSS = r"""
<style>
:root {
  --adi-bg: #07111f;
  --adi-bg-2: #0b1628;
  --adi-panel: rgba(15, 29, 50, 0.78);
  --adi-panel-strong: rgba(18, 36, 62, 0.94);
  --adi-line: rgba(111, 211, 255, 0.16);
  --adi-line-strong: rgba(111, 211, 255, 0.35);
  --adi-text: #e9f4ff;
  --adi-muted: #8ea8c3;
  --adi-blue: #4da3ff;
  --adi-cyan: #62e6ff;
  --adi-violet: #8b7cff;
  --adi-green: #64e8b7;
  --adi-gold: #ffd479;
  --adi-red: #ff8c9b;
  --adi-shadow: 0 18px 55px rgba(0, 0, 0, 0.28);
}

html, body, [data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 8% 0%, rgba(77, 163, 255, 0.16), transparent 28rem),
    radial-gradient(circle at 90% 8%, rgba(98, 230, 255, 0.10), transparent 30rem),
    linear-gradient(180deg, var(--adi-bg) 0%, #081525 54%, #07111f 100%);
  color: var(--adi-text);
}

[data-testid="stAppViewBlockContainer"] {
  max-width: 1500px;
  padding-top: 1.5rem;
}

[data-testid="stSidebar"] {
  background:
    linear-gradient(180deg, rgba(9, 21, 37, 0.98), rgba(8, 18, 32, 0.98));
  border-right: 1px solid var(--adi-line);
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
  color: #dbeaff;
}

h1, h2, h3 {
  letter-spacing: -0.02em;
}

h1 {
  color: #f4fbff;
}

p, li {
  color: #c8d9ea;
}

[data-testid="stCaptionContainer"] {
  color: var(--adi-muted);
}

div[data-baseweb="tab-list"] {
  gap: .45rem;
  background: rgba(8, 19, 34, 0.78);
  border: 1px solid var(--adi-line);
  border-radius: 18px;
  padding: .38rem;
  box-shadow: 0 8px 28px rgba(0,0,0,.18);
  position: sticky;
  top: .55rem;
  z-index: 8;
  backdrop-filter: blur(18px);
}

button[data-baseweb="tab"] {
  min-height: 44px;
  border-radius: 13px;
  color: var(--adi-muted);
  font-weight: 650;
  padding-left: 1rem;
  padding-right: 1rem;
}

button[data-baseweb="tab"][aria-selected="true"] {
  color: #f7fcff;
  background: linear-gradient(135deg, rgba(77,163,255,.22), rgba(98,230,255,.10));
  border: 1px solid rgba(98,230,255,.28);
}

div.stButton > button, div.stDownloadButton > button {
  border: 1px solid rgba(98,230,255,.32);
  border-radius: 13px;
  min-height: 42px;
  font-weight: 700;
  background: linear-gradient(135deg, rgba(77,163,255,.22), rgba(98,230,255,.12));
  color: #effaff;
  box-shadow: 0 8px 24px rgba(24, 107, 184, .16);
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}

div.stButton > button:hover, div.stDownloadButton > button:hover {
  transform: translateY(-1px);
  border-color: rgba(98,230,255,.65);
  box-shadow: 0 12px 30px rgba(24, 107, 184, .24);
}

[data-testid="stMetric"] {
  background: linear-gradient(145deg, rgba(16,34,58,.88), rgba(11,25,44,.82));
  border: 1px solid var(--adi-line);
  border-radius: 16px;
  padding: 1rem 1.05rem;
  box-shadow: 0 12px 36px rgba(0,0,0,.18);
  min-height: 108px;
}

[data-testid="stMetricValue"] {
  color: #f7fcff;
}

[data-testid="stFileUploader"] {
  background: rgba(12, 27, 47, .70);
  border: 1px dashed rgba(98,230,255,.30);
  border-radius: 18px;
  padding: .6rem;
}

[data-testid="stExpander"] {
  background: rgba(13, 28, 49, .66);
  border: 1px solid var(--adi-line);
  border-radius: 15px;
  overflow: hidden;
}

[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
  background-color: rgba(11, 25, 44, .88) !important;
  border-color: rgba(111,211,255,.18) !important;
  color: #edf8ff !important;
  border-radius: 12px !important;
}

[data-testid="stAlert"] {
  border-radius: 14px;
  border: 1px solid var(--adi-line);
}

.adi-hero {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(98, 230, 255, .22);
  background:
    linear-gradient(135deg, rgba(15,37,64,.97), rgba(10,24,43,.95)),
    radial-gradient(circle at 90% 20%, rgba(98,230,255,.20), transparent 18rem);
  border-radius: 26px;
  padding: 1.45rem 1.55rem 1.35rem 1.55rem;
  box-shadow: var(--adi-shadow);
  margin-bottom: 1rem;
  animation: adiFadeUp .55s ease both;
}

.adi-hero::after {
  content: "";
  position: absolute;
  top: -40%;
  right: -8%;
  width: 34%;
  height: 180%;
  background: linear-gradient(90deg, transparent, rgba(98,230,255,.10), transparent);
  transform: rotate(12deg);
  animation: adiScan 7s linear infinite;
  pointer-events: none;
}

.adi-kicker {
  display: inline-flex;
  align-items: center;
  gap: .45rem;
  color: var(--adi-cyan);
  font-size: .76rem;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.adi-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--adi-green);
  box-shadow: 0 0 0 0 rgba(100,232,183,.42);
  animation: adiPulse 2.1s infinite;
}

.adi-title {
  margin: .5rem 0 .35rem 0;
  color: #f7fcff;
  font-size: clamp(2rem, 3vw, 3.45rem);
  line-height: 1.02;
  font-weight: 820;
  letter-spacing: -.045em;
}

.adi-subtitle {
  max-width: 850px;
  color: #afc5da;
  font-size: 1.02rem;
  line-height: 1.65;
  margin-bottom: 1rem;
}

.adi-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: .55rem;
}

.adi-chip {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  border: 1px solid rgba(111,211,255,.20);
  border-radius: 999px;
  padding: .42rem .72rem;
  background: rgba(8, 22, 39, .60);
  color: #cfe6f7;
  font-size: .78rem;
  font-weight: 650;
}

.adi-chip strong {
  color: var(--adi-cyan);
}

.adi-section {
  color: #f3fbff;
  font-size: 1.08rem;
  font-weight: 760;
  margin: .4rem 0 .6rem 0;
}

.adi-card {
  height: 100%;
  background: linear-gradient(145deg, rgba(16,34,58,.82), rgba(10,24,42,.78));
  border: 1px solid var(--adi-line);
  border-radius: 18px;
  padding: 1.05rem 1.05rem .95rem 1.05rem;
  box-shadow: 0 12px 32px rgba(0,0,0,.16);
  animation: adiFadeUp .48s ease both;
}

.adi-card:hover {
  border-color: rgba(98,230,255,.34);
  transform: translateY(-1px);
  transition: all .18s ease;
}

.adi-card-title {
  color: #f1f8ff;
  font-weight: 760;
  margin-bottom: .35rem;
}

.adi-card-copy {
  color: #94abc1;
  line-height: 1.52;
  font-size: .90rem;
}

.adi-icon {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: .7rem;
  border-radius: 11px;
  background: linear-gradient(135deg, rgba(77,163,255,.20), rgba(98,230,255,.12));
  border: 1px solid rgba(98,230,255,.20);
  color: var(--adi-cyan);
  font-size: 1rem;
  font-weight: 800;
}

.adi-flow {
  display: grid;
  grid-template-columns: repeat(5, minmax(105px, 1fr));
  gap: .62rem;
  align-items: center;
  margin: .6rem 0 1.1rem 0;
}

.adi-flow-step {
  position: relative;
  min-height: 82px;
  padding: .88rem .8rem;
  border-radius: 16px;
  background: rgba(13, 29, 51, .72);
  border: 1px solid var(--adi-line);
  text-align: center;
  overflow: hidden;
}

.adi-flow-step::before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--adi-cyan), transparent);
  animation: adiFlow 3.5s ease-in-out infinite;
}

.adi-flow-name {
  color: #eaf7ff;
  font-size: .86rem;
  font-weight: 760;
}

.adi-flow-copy {
  color: #7f9ab5;
  font-size: .72rem;
  margin-top: .25rem;
}

.adi-zone {
  border: 1px solid var(--adi-line);
  background: rgba(12, 27, 48, .58);
  border-radius: 18px;
  padding: .9rem;
  min-height: 84px;
  margin-bottom: .75rem;
}

.adi-zone-label {
  color: var(--adi-cyan);
  font-size: .72rem;
  letter-spacing: .09em;
  text-transform: uppercase;
  font-weight: 800;
  margin-bottom: .24rem;
}

.adi-zone-copy {
  color: #91a9c0;
  font-size: .84rem;
}

.adi-status {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: .35rem .62rem;
  margin: 0 .35rem .35rem 0;
  font-size: .75rem;
  font-weight: 760;
  border: 1px solid rgba(100,232,183,.22);
  background: rgba(100,232,183,.08);
  color: #a8f3d5;
}

.adi-status.info {
  border-color: rgba(98,230,255,.22);
  background: rgba(98,230,255,.08);
  color: #aeefff;
}

.adi-status.gold {
  border-color: rgba(255,212,121,.22);
  background: rgba(255,212,121,.08);
  color: #ffe0a0;
}

.adi-benchmark {
  border-left: 3px solid var(--adi-cyan);
  background: rgba(15, 31, 53, .68);
  border-radius: 12px;
  padding: .78rem .9rem;
  color: #9cb2c7;
  margin: .35rem 0;
}

.adi-config-line {
  display: flex;
  justify-content: space-between;
  gap: .7rem;
  padding: .58rem 0;
  border-bottom: 1px solid rgba(111,211,255,.09);
}

.adi-config-line:last-child {
  border-bottom: none;
}

.adi-config-key { color: #829bb5; }
.adi-config-value { color: #e7f4ff; font-weight: 650; text-align: right; }

@keyframes adiFadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes adiPulse {
  0% { box-shadow: 0 0 0 0 rgba(100,232,183,.38); }
  70% { box-shadow: 0 0 0 9px rgba(100,232,183,0); }
  100% { box-shadow: 0 0 0 0 rgba(100,232,183,0); }
}

@keyframes adiScan {
  from { transform: translateX(-240%) rotate(12deg); }
  to { transform: translateX(340%) rotate(12deg); }
}

@keyframes adiFlow {
  0%,100% { opacity: .25; transform: translateX(-20%); }
  50% { opacity: 1; transform: translateX(20%); }
}

@media (max-width: 900px) {
  .adi-flow { grid-template-columns: 1fr; }
  .adi-hero { padding: 1.15rem; border-radius: 20px; }
}
</style>
"""


def apply_v2_theme() -> None:
    st.markdown(V2_THEME_CSS, unsafe_allow_html=True)


def render_hero() -> None:
    st.markdown(
        """
        <div class="adi-hero">
          <div class="adi-kicker"><span class="adi-dot"></span> V2 Release Candidate · Local-first AI</div>
          <div class="adi-title">Agentic Document Intelligence</div>
          <div class="adi-subtitle">
            Evidence-grounded document QA that can ingest scanned PDFs, retrieve
            inspectable sources, verify claims semantically, and adaptively recover
            missing evidence without hiding the reasoning trail.
          </div>
          <div class="adi-chip-row">
            <span class="adi-chip"><strong>OCR</strong> scanned PDFs</span>
            <span class="adi-chip"><strong>RAG</strong> BGE + FAISS</span>
            <span class="adi-chip"><strong>VERIFY</strong> local NLI</span>
            <span class="adi-chip"><strong>AGENT</strong> budgeted recovery</span>
            <span class="adi-chip"><strong>LOCAL</strong> zero paid API required</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_pipeline() -> None:
    st.markdown(
        """
        <div class="adi-flow">
          <div class="adi-flow-step"><div class="adi-flow-name">01 · Ingest</div><div class="adi-flow-copy">PDF + OCR provenance</div></div>
          <div class="adi-flow-step"><div class="adi-flow-name">02 · Retrieve</div><div class="adi-flow-copy">Dense / hybrid evidence</div></div>
          <div class="adi-flow-step"><div class="adi-flow-name">03 · Answer</div><div class="adi-flow-copy">Grounded generation</div></div>
          <div class="adi-flow-step"><div class="adi-flow-name">04 · Verify</div><div class="adi-flow-copy">Claim-level support</div></div>
          <div class="adi-flow-step"><div class="adi-flow-name">05 · Recover</div><div class="adi-flow-copy">Adaptive re-retrieval</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_card(icon: str, title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="adi-card">
          <div class="adi-icon">{icon}</div>
          <div class="adi-card-title">{title}</div>
          <div class="adi-card-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def zone_intro(label: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="adi-zone">
          <div class="adi-zone-label">{label}</div>
          <div class="adi-zone-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pills(items: list[tuple[str, str]]) -> None:
    html = "".join(
        f'<span class="adi-status {variant}">{label}</span>'
        for label, variant in items
    )
    st.markdown(html, unsafe_allow_html=True)


def config_line(key: str, value: str) -> str:
    return (
        '<div class="adi-config-line">'
        f'<span class="adi-config-key">{key}</span>'
        f'<span class="adi-config-value">{value}</span>'
        '</div>'
    )
