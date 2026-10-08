"""Mantine-inspired dark/light visual system for the V2 Streamlit interface."""

from __future__ import annotations

import html

import streamlit as st


THEMES = {
    "Dark": {
        "bg": "#1A1B1E",
        "bg2": "#141517",
        "surface": "#25262B",
        "surface2": "#2C2E33",
        "surface3": "#373A40",
        "text": "#F8F9FA",
        "muted": "#909296",
        "border": "#373A40",
        "accent": "#FFD43B",
        "accent_hover": "#FCC419",
        "accent_soft": "rgba(255, 212, 59, 0.11)",
        "shadow": "rgba(0, 0, 0, 0.34)",
        "button_text": "#1A1B1E",
    },
    "Light": {
        "bg": "#F8F9FA",
        "bg2": "#F1F3F5",
        "surface": "#FFFFFF",
        "surface2": "#F8F9FA",
        "surface3": "#E9ECEF",
        "text": "#1A1B1E",
        "muted": "#868E96",
        "border": "#DEE2E6",
        "accent": "#FFD43B",
        "accent_hover": "#FAB005",
        "accent_soft": "rgba(255, 212, 59, 0.16)",
        "shadow": "rgba(33, 37, 41, 0.12)",
        "button_text": "#1A1B1E",
    },
}


_BASE_CSS = r"""
<style>
* { box-sizing: border-box; }

:root {
  --adi-radius-xl: 28px;
  --adi-radius-lg: 18px;
  --adi-radius-md: 13px;
  --adi-fast: 180ms;
  --adi-medium: 360ms;
}

html { scroll-behavior: smooth; }

html, body, [data-testid="stAppViewContainer"] {
  color: var(--adi-text);
  background:
    radial-gradient(circle at 85% -8%, var(--adi-accent-soft), transparent 26rem),
    linear-gradient(180deg, var(--adi-bg) 0%, var(--adi-bg2) 100%);
}

[data-testid="stAppViewContainer"] {
  position: relative;
  isolation: isolate;
  overflow-x: hidden;
}

.adi-ambient {
  position: fixed;
  inset: 0;
  z-index: -2;
  pointer-events: none;
  overflow: hidden;
  background:
    linear-gradient(
      115deg,
      transparent 0%,
      color-mix(in srgb, var(--adi-accent) 5%, transparent) 38%,
      transparent 62%
    );
}

.adi-ambient::before {
  content: "";
  position: absolute;
  inset: -30%;
  background:
    radial-gradient(circle at 18% 24%, color-mix(in srgb, var(--adi-accent) 16%, transparent) 0, transparent 23%),
    radial-gradient(circle at 82% 18%, color-mix(in srgb, var(--adi-text) 6%, transparent) 0, transparent 22%),
    radial-gradient(circle at 72% 76%, color-mix(in srgb, var(--adi-accent) 10%, transparent) 0, transparent 24%),
    radial-gradient(circle at 25% 82%, color-mix(in srgb, var(--adi-text) 4%, transparent) 0, transparent 20%);
  filter: blur(24px);
  animation: adiAuroraDrift 22s ease-in-out infinite alternate;
}

.adi-ambient::after {
  content: "";
  position: absolute;
  inset: 0;
  opacity: .18;
  background-image:
    linear-gradient(color-mix(in srgb, var(--adi-border) 50%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, var(--adi-border) 50%, transparent) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: linear-gradient(to bottom, black 0%, transparent 78%);
}

.adi-orb {
  position: fixed;
  z-index: -1;
  width: 260px;
  height: 260px;
  border-radius: 999px;
  pointer-events: none;
  filter: blur(8px);
  opacity: .22;
  background: radial-gradient(circle, var(--adi-accent) 0%, transparent 68%);
}

.adi-orb.one {
  top: 12%;
  left: -90px;
  animation: adiOrbOne 16s ease-in-out infinite alternate;
}

.adi-orb.two {
  right: -110px;
  top: 46%;
  width: 340px;
  height: 340px;
  opacity: .16;
  animation: adiOrbTwo 20s ease-in-out infinite alternate;
}

[data-testid="stAppViewBlockContainer"] {
  max-width: 1500px;
  padding-top: 1rem;
  padding-bottom: 4rem;
}

[data-testid="stHeader"] { background: transparent; }

[data-testid="stSidebar"] {
  background: var(--adi-surface);
  border-right: 1px solid var(--adi-border);
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

p, li, label {
  color: color-mix(in srgb, var(--adi-text) 84%, var(--adi-muted));
}

[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
  color: var(--adi-muted) !important;
}

[data-testid="stMarkdownContainer"] a { color: var(--adi-text); }

/* Top tabs */
div[data-baseweb="tab-list"] {
  gap: .2rem;
  background: color-mix(in srgb, var(--adi-surface) 88%, transparent);
  border: 1px solid color-mix(in srgb, var(--adi-border) 84%, transparent);
  border-radius: 14px;
  padding: .28rem;
  position: sticky;
  top: .55rem;
  z-index: 20;
  box-shadow: 0 10px 28px var(--adi-shadow);
}

button[data-baseweb="tab"] {
  min-height: 42px;
  border-radius: 10px;
  color: var(--adi-muted);
  font-weight: 700;
  padding: 0 .9rem;
  transition: background var(--adi-fast) ease, color var(--adi-fast) ease, transform var(--adi-fast) ease;
}

button[data-baseweb="tab"]:hover {
  color: var(--adi-text);
  background: var(--adi-surface2);
  transform: translateY(-1px);
}

button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--adi-button-text);
  background: var(--adi-accent);
  border: 1px solid var(--adi-accent);
  box-shadow: 0 6px 18px color-mix(in srgb, var(--adi-accent) 20%, transparent);
}

/* Native controls */
div.stButton > button,
div.stDownloadButton > button {
  border: 1px solid var(--adi-accent);
  border-radius: 10px;
  min-height: 42px;
  font-weight: 750;
  background: var(--adi-accent);
  color: var(--adi-button-text);
  box-shadow: 0 8px 18px color-mix(in srgb, var(--adi-accent) 14%, transparent);
  transition: transform var(--adi-fast) ease, background var(--adi-fast) ease, box-shadow var(--adi-fast) ease;
}

div.stButton > button:hover,
div.stDownloadButton > button:hover {
  transform: translateY(-2px);
  background: var(--adi-accent-hover);
  border-color: var(--adi-accent-hover);
  box-shadow: 0 12px 28px color-mix(in srgb, var(--adi-accent) 22%, transparent);
}

div.stButton > button:active,
div.stDownloadButton > button:active {
  transform: translateY(0) scale(.99);
}

[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
  background: var(--adi-surface) !important;
  border: 1px solid var(--adi-border) !important;
  color: var(--adi-text) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
}

[data-testid="stTextArea"] textarea:focus,
[data-baseweb="select"] > div:focus-within,
[data-baseweb="input"] > div:focus-within {
  border-color: var(--adi-accent) !important;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--adi-accent) 18%, transparent) !important;
}

[data-baseweb="popover"] > div,
[data-baseweb="menu"] {
  background: var(--adi-surface) !important;
  border: 1px solid var(--adi-border) !important;
  border-radius: 10px !important;
  box-shadow: 0 18px 40px var(--adi-shadow) !important;
}

[role="option"] { color: var(--adi-text) !important; }
[role="option"]:hover,
[aria-selected="true"][role="option"] {
  background: var(--adi-accent-soft) !important;
}

[data-testid="stFileUploader"] {
  background: var(--adi-surface);
  border: 1px dashed color-mix(in srgb, var(--adi-accent) 48%, var(--adi-border));
  border-radius: 14px;
  padding: .65rem;
  transition: border-color var(--adi-fast) ease, box-shadow var(--adi-fast) ease;
}

[data-testid="stFileUploader"]:hover {
  border-color: var(--adi-accent);
  box-shadow: 0 0 0 3px var(--adi-accent-soft);
}

[data-testid="stMetric"] {
  position: relative;
  overflow: hidden;
  background: var(--adi-surface);
  border: 1px solid var(--adi-border);
  border-radius: 14px;
  padding: 1rem;
  min-height: 102px;
  box-shadow: 0 8px 24px var(--adi-shadow);
}

[data-testid="stMetric"]::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--adi-accent);
}

[data-testid="stMetricValue"] {
  color: var(--adi-text);
  font-weight: 820;
  letter-spacing: -.04em;
}

[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--adi-border) !important;
  background: var(--adi-surface);
  border-radius: 16px !important;
  box-shadow: 0 8px 24px var(--adi-shadow);
}

[data-testid="stExpander"] {
  background: var(--adi-surface);
  border: 1px solid var(--adi-border);
  border-radius: 12px;
  overflow: hidden;
}

[data-testid="stAlert"],
[data-testid="stStatusWidget"] {
  border-radius: 12px;
  border: 1px solid var(--adi-border);
  background: var(--adi-surface);
}

[data-testid="stSlider"] [role="slider"] {
  background: var(--adi-accent) !important;
  border-color: var(--adi-accent) !important;
  box-shadow: 0 0 0 4px var(--adi-accent-soft);
}

[data-testid="stCheckbox"] span[data-baseweb="checkbox"][aria-checked="true"] > div {
  background: var(--adi-accent) !important;
  border-color: var(--adi-accent) !important;
}

[data-testid="stProgress"] > div > div {
  background: var(--adi-accent) !important;
}

[data-testid="stCodeBlock"],
[data-testid="stDataFrame"] {
  border: 1px solid var(--adi-border);
  border-radius: 12px;
  overflow: hidden;
}

* {
  scrollbar-width: thin;
  scrollbar-color: var(--adi-surface3) transparent;
}

/* Brand bar */
.adi-brandbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 60px;
  padding: .7rem .95rem;
  margin-bottom: .75rem;
  background: var(--adi-surface);
  border: 1px solid var(--adi-border);
  border-radius: 16px;
  box-shadow: 0 8px 24px var(--adi-shadow);
  animation: adiFadeIn .45s ease both;
}

.adi-brand {
  display: flex;
  align-items: center;
  gap: .72rem;
  color: var(--adi-text);
  font-size: 1rem;
  font-weight: 820;
  letter-spacing: -.025em;
}

.adi-brandmark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #1A1B1E;
  background: var(--adi-accent);
  font-size: .72rem;
  font-weight: 900;
  box-shadow: 0 0 0 5px var(--adi-accent-soft);
}

.adi-brandmeta {
  display: flex;
  align-items: center;
  gap: .45rem;
  color: var(--adi-muted);
  font-size: .74rem;
}

.adi-live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--adi-accent);
  animation: adiPulse 2s ease-out infinite;
}

/* Hero inspired by the supplied reference */
.adi-hero {
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(20px) saturate(130%);
  -webkit-backdrop-filter: blur(20px) saturate(130%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(420px, .95fr);
  min-height: 430px;
  align-items: center;
  gap: 2rem;
  padding: 3.3rem 3.2rem;
  margin-bottom: 1rem;
  background: var(--adi-surface);
  border: 1px solid var(--adi-border);
  border-radius: 24px;
  box-shadow: 0 16px 42px var(--adi-shadow);
  animation: adiFadeUp .55s cubic-bezier(.22,.9,.28,1) both;
}

.adi-hero::before {
  content: "";
  position: absolute;
  inset: -2px;
  pointer-events: none;
  background: linear-gradient(
    112deg,
    transparent 15%,
    color-mix(in srgb, var(--adi-accent) 10%, transparent) 40%,
    transparent 62%
  );
  transform: translateX(-75%);
  animation: adiHeroShimmer 8s ease-in-out infinite;
}

.adi-hero::after {
  content: "";
  position: absolute;
  width: 360px;
  height: 360px;
  right: -120px;
  top: -150px;
  border-radius: 50%;
  background: var(--adi-accent-soft);
  filter: blur(4px);
  pointer-events: none;
}

.adi-kicker {
  color: var(--adi-muted);
  font-size: .72rem;
  font-weight: 800;
  letter-spacing: .09em;
  text-transform: uppercase;
}

.adi-title {
  max-width: 760px;
  margin: .65rem 0 .7rem 0;
  color: var(--adi-text);
  font-size: clamp(2.5rem, 4.2vw, 4.9rem);
  line-height: .98;
  font-weight: 900;
  letter-spacing: -.064em;
}

.adi-title .accent {
  color: var(--adi-accent);
}

.adi-subtitle {
  max-width: 720px;
  color: var(--adi-muted);
  font-size: 1.02rem;
  line-height: 1.7;
  margin-bottom: 1.2rem;
}

.adi-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: .5rem;
}

.adi-chip {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--adi-border);
  border-radius: 9px;
  padding: .43rem .65rem;
  background: var(--adi-surface2);
  color: var(--adi-text);
  font-size: .74rem;
  font-weight: 700;
  transition: transform var(--adi-fast) ease, border-color var(--adi-fast) ease;
}

.adi-chip strong {
  color: var(--adi-accent);
  margin-right: .28rem;
}

.adi-chip:hover {
  transform: translateY(-2px);
  border-color: var(--adi-accent);
}

/* Stacked document/evidence preview */
.adi-visual-stage {
  position: relative;
  height: 330px;
  perspective: 1100px;
  transform: rotate(-2deg);
}

.adi-preview {
  position: absolute;
  right: 0;
  width: min(100%, 430px);
  border: 1px solid var(--adi-border);
  border-radius: 14px;
  background: var(--adi-bg2);
  box-shadow: 0 18px 42px var(--adi-shadow);
  overflow: hidden;
  transition: transform .3s ease, box-shadow .3s ease;
}

.adi-preview:hover {
  z-index: 8;
  box-shadow: 0 26px 56px var(--adi-shadow);
}

.adi-preview.p1 {
  top: 0;
  right: -22px;
  transform: rotate(4deg) translateZ(0);
  animation: adiCardFloat 6s ease-in-out infinite;
}

.adi-preview.p2 {
  top: 104px;
  right: 36px;
  transform: rotate(-2deg);
  animation: adiCardFloat 6.8s ease-in-out -1.3s infinite;
}

.adi-preview.p3 {
  top: 218px;
  right: -2px;
  transform: rotate(3deg);
  animation: adiCardFloat 7.4s ease-in-out -2.4s infinite;
}

.adi-preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .6rem;
  padding: .58rem .72rem;
  border-bottom: 1px solid var(--adi-border);
  color: var(--adi-muted);
  font-size: .63rem;
  font-weight: 700;
}

.adi-preview-body {
  padding: .8rem .86rem .9rem;
}

.adi-preview-title {
  color: var(--adi-text);
  font-size: .86rem;
  font-weight: 820;
  margin-bottom: .32rem;
}

.adi-preview-copy {
  color: var(--adi-muted);
  font-size: .67rem;
  line-height: 1.48;
}

.adi-preview-line {
  height: 6px;
  margin-top: .5rem;
  border-radius: 99px;
  background: var(--adi-surface3);
}

.adi-preview-line.short { width: 62%; }
.adi-preview-line.mid { width: 82%; }

.adi-preview-accent {
  display: inline-flex;
  align-items: center;
  gap: .28rem;
  color: #1A1B1E;
  background: var(--adi-accent);
  padding: .22rem .42rem;
  border-radius: 6px;
  font-size: .58rem;
  font-weight: 850;
}

/* Sections/cards */
.adi-section {
  display: flex;
  align-items: center;
  gap: .55rem;
  color: var(--adi-text);
  font-size: 1.05rem;
  font-weight: 820;
  margin: .55rem 0 .7rem;
}

.adi-section::before {
  content: "";
  width: 20px;
  height: 4px;
  border-radius: 99px;
  background: var(--adi-accent);
}

.adi-card {
  height: 100%;
  position: relative;
  overflow: hidden;
  background: color-mix(in srgb, var(--adi-surface) 90%, transparent);
  backdrop-filter: blur(16px) saturate(125%);
  -webkit-backdrop-filter: blur(16px) saturate(125%);
  border: 1px solid var(--adi-border);
  border-radius: 15px;
  padding: 1.05rem;
  box-shadow: 0 8px 24px var(--adi-shadow);
  animation: adiFadeUp .45s ease both;
  transition: transform var(--adi-fast) ease, border-color var(--adi-fast) ease, box-shadow var(--adi-fast) ease;
}

.adi-card::after {
  content: "";
  position: absolute;
  width: 120px;
  height: 120px;
  right: -55px;
  bottom: -60px;
  border-radius: 999px;
  background: var(--adi-accent-soft);
  filter: blur(4px);
  opacity: 0;
  transition: opacity var(--adi-medium) ease, transform var(--adi-medium) ease;
}

.adi-card:hover::after {
  opacity: 1;
  transform: scale(1.18);
}

.adi-card:hover {
  transform: translateY(-6px) scale(1.008);
  border-color: color-mix(in srgb, var(--adi-accent) 52%, var(--adi-border));
  box-shadow: 0 14px 34px var(--adi-shadow);
}

.adi-card-title {
  color: var(--adi-text);
  font-weight: 800;
  margin-bottom: .35rem;
}

.adi-card-copy {
  color: var(--adi-muted);
  line-height: 1.52;
  font-size: .88rem;
}

.adi-icon {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: .7rem;
  border-radius: 9px;
  background: var(--adi-accent-soft);
  border: 1px solid color-mix(in srgb, var(--adi-accent) 38%, var(--adi-border));
  color: var(--adi-accent);
  font-size: .76rem;
  font-weight: 900;
}

/* Pipeline */
.adi-flow {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: .65rem;
  margin: .7rem 0 1.1rem;
}

.adi-flow-step {
  position: relative;
  min-height: 88px;
  padding: .85rem;
  background: var(--adi-surface);
  border: 1px solid var(--adi-border);
  border-radius: 13px;
  box-shadow: 0 7px 20px var(--adi-shadow);
  overflow: hidden;
}

.adi-flow-step::before {
  content: "";
  position: absolute;
  left: -30%;
  top: 0;
  width: 30%;
  height: 3px;
  background: var(--adi-accent);
  animation: adiScanLine 3.6s ease-in-out infinite;
}

.adi-flow-name {
  color: var(--adi-text);
  font-size: .82rem;
  font-weight: 800;
}

.adi-flow-copy {
  color: var(--adi-muted);
  font-size: .7rem;
  margin-top: .28rem;
}

/* Zones/status/gauge */
.adi-zone {
  border: 1px solid var(--adi-border);
  background: var(--adi-surface);
  border-radius: 14px;
  padding: .9rem;
  min-height: 88px;
  margin-bottom: .7rem;
}

.adi-zone-label {
  color: var(--adi-accent);
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
  padding: .34rem .6rem;
  margin: 0 .32rem .32rem 0;
  font-size: .71rem;
  font-weight: 780;
  border: 1px solid var(--adi-border);
  background: var(--adi-surface2);
  color: var(--adi-text);
}

.adi-status.info,
.adi-status.gold,
.adi-status.magenta {
  border-color: color-mix(in srgb, var(--adi-accent) 45%, var(--adi-border));
  background: var(--adi-accent-soft);
  color: var(--adi-text);
}

.adi-gauge-wrap {
  display: flex;
  align-items: center;
  gap: .8rem;
  margin: .55rem 0 .7rem;
  padding: .72rem;
  border-radius: 13px;
  background: var(--adi-surface);
  border: 1px solid var(--adi-border);
}

.adi-gauge {
  --value: 0;
  width: 62px;
  height: 62px;
  flex: 0 0 62px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle closest-side, var(--adi-surface) 72%, transparent 73% 99%),
    conic-gradient(var(--adi-accent) calc(var(--value) * 1%), var(--adi-surface3) 0);
}

.adi-gauge strong {
  color: var(--adi-text);
  font-size: .76rem;
}

.adi-gauge-title {
  color: var(--adi-text);
  font-weight: 800;
  font-size: .82rem;
}

.adi-gauge-copy {
  color: var(--adi-muted);
  font-size: .72rem;
  line-height: 1.4;
}

.adi-benchmark {
  border-left: 3px solid var(--adi-accent);
  background: var(--adi-surface);
  border-radius: 11px;
  padding: .8rem .9rem;
  color: var(--adi-muted);
  margin: .35rem 0;
  box-shadow: 0 6px 18px var(--adi-shadow);
}

.adi-config-line {
  display: flex;
  justify-content: space-between;
  gap: .7rem;
  padding: .58rem 0;
  border-bottom: 1px solid var(--adi-border);
}

.adi-config-line:last-child { border-bottom: none; }
.adi-config-key { color: var(--adi-muted); }
.adi-config-value { color: var(--adi-text); font-weight: 700; text-align: right; }

@keyframes adiFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes adiFadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes adiPulse {
  0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--adi-accent) 38%, transparent); }
  70% { box-shadow: 0 0 0 9px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}

@keyframes adiCardFloat {
  0%, 100% { margin-top: 0; }
  50% { margin-top: -8px; }
}

@keyframes adiScanLine {
  0% { left: -30%; opacity: 0; }
  25% { opacity: 1; }
  75% { opacity: 1; }
  100% { left: 105%; opacity: 0; }
}

@keyframes adiAuroraDrift {
  0% { transform: translate3d(-2%, -1%, 0) rotate(0deg) scale(1); }
  50% { transform: translate3d(3%, 2%, 0) rotate(5deg) scale(1.04); }
  100% { transform: translate3d(-1%, 4%, 0) rotate(-4deg) scale(1.08); }
}

@keyframes adiOrbOne {
  from { transform: translate3d(0, 0, 0) scale(.95); }
  to { transform: translate3d(90px, 70px, 0) scale(1.18); }
}

@keyframes adiOrbTwo {
  from { transform: translate3d(0, 0, 0) scale(1); }
  to { transform: translate3d(-120px, -55px, 0) scale(1.12); }
}

@keyframes adiHeroShimmer {
  0%, 64%, 100% { transform: translateX(-85%); opacity: 0; }
  72% { opacity: 1; }
  88% { transform: translateX(85%); opacity: .8; }
}

@media (max-width: 980px) {
  .adi-brandmeta { display: none; }
  .adi-hero {
    grid-template-columns: 1fr;
    padding: 2rem 1.4rem;
  }
  .adi-visual-stage {
    height: 300px;
    max-width: 520px;
    margin: 0 auto;
    width: 100%;
  }
  .adi-flow { grid-template-columns: 1fr; }
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
    return ["Dark", "Light"]


def apply_v2_theme(theme: str = "Dark") -> None:
    palette = THEMES.get(theme, THEMES["Dark"])
    variables = f"""
    <style>
    :root {{
      --adi-bg: {palette["bg"]};
      --adi-bg2: {palette["bg2"]};
      --adi-surface: {palette["surface"]};
      --adi-surface2: {palette["surface2"]};
      --adi-surface3: {palette["surface3"]};
      --adi-text: {palette["text"]};
      --adi-muted: {palette["muted"]};
      --adi-border: {palette["border"]};
      --adi-accent: {palette["accent"]};
      --adi-accent-hover: {palette["accent_hover"]};
      --adi-accent-soft: {palette["accent_soft"]};
      --adi-shadow: {palette["shadow"]};
      --adi-button-text: {palette["button_text"]};
    }}
    </style>
    """
    st.markdown(variables + _BASE_CSS, unsafe_allow_html=True)


def render_ambient_background() -> None:
    """Render the lightweight animated V2 background layer."""
    st.markdown(
        """
        <div class="adi-ambient" aria-hidden="true"></div>
        <div class="adi-orb one" aria-hidden="true"></div>
        <div class="adi-orb two" aria-hidden="true"></div>
        """,
        unsafe_allow_html=True,
    )


def render_hero(theme: str = "Dark") -> None:
    safe_theme = html.escape(theme)
    st.markdown(
        f"""
        <div class="adi-brandbar">
          <div class="adi-brand">
            <span class="adi-brandmark">AI</span>
            Agentic Document Intelligence
          </div>
          <div class="adi-brandmeta">
            <span class="adi-live-dot"></span>
            V2 · {safe_theme} mode · local-first
          </div>
        </div>

        <section class="adi-hero">
          <div>
            <div class="adi-kicker">Evidence-grounded AI for documents</div>
            <div class="adi-title">
              Ask your documents.<br>
              <span class="accent">Verify every answer.</span>
            </div>
            <div class="adi-subtitle">
              Ingest text or scanned PDFs, retrieve inspectable evidence, verify
              generated claims, and let a bounded agent recover missing support —
              all with a local-first architecture.
            </div>
            <div class="adi-chip-row">
              <span class="adi-chip"><strong>01</strong> OCR ingestion</span>
              <span class="adi-chip"><strong>02</strong> Evidence RAG</span>
              <span class="adi-chip"><strong>03</strong> Semantic verification</span>
              <span class="adi-chip"><strong>04</strong> Agentic recovery</span>
            </div>
          </div>

          <div class="adi-visual-stage" aria-hidden="true">
            <div class="adi-preview p1">
              <div class="adi-preview-head">
                <span>DOCUMENT INGESTION</span>
                <span class="adi-preview-accent">OCR READY</span>
              </div>
              <div class="adi-preview-body">
                <div class="adi-preview-title">Research_Report.pdf</div>
                <div class="adi-preview-copy">Page provenance preserved · 18 pages · local extraction</div>
                <div class="adi-preview-line"></div>
                <div class="adi-preview-line mid"></div>
                <div class="adi-preview-line short"></div>
              </div>
            </div>

            <div class="adi-preview p2">
              <div class="adi-preview-head">
                <span>ANSWER VERIFICATION</span>
                <span class="adi-preview-accent">SUPPORTED</span>
              </div>
              <div class="adi-preview-body">
                <div class="adi-preview-title">Claim grounded in cited evidence [S2]</div>
                <div class="adi-preview-copy">Semantic entailment confirms the retrieved source supports the answer.</div>
                <div class="adi-preview-line mid"></div>
                <div class="adi-preview-line"></div>
              </div>
            </div>

            <div class="adi-preview p3">
              <div class="adi-preview-head">
                <span>AGENT TRACE</span>
                <span class="adi-preview-accent">ROUND 01</span>
              </div>
              <div class="adi-preview-body">
                <div class="adi-preview-title">Missing evidence detected → targeted retrieval</div>
                <div class="adi-preview-copy">Recovery stays inside the configured evidence budget.</div>
              </div>
            </div>
          </div>
        </section>
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
          <div class="adi-flow-step"><div class="adi-flow-name">04 · Verify</div><div class="adi-flow-copy">Semantic support</div></div>
          <div class="adi-flow-step"><div class="adi-flow-name">05 · Recover</div><div class="adi-flow-copy">Bounded re-retrieval</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_card(
    icon: str,
    title: str,
    copy: str,
    accent: str = "b",
) -> None:
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
