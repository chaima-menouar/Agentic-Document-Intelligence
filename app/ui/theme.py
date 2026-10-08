"""Cinematic, theme-aware visual system for the V2 Streamlit interface."""

from __future__ import annotations

import html

import streamlit as st


THEMES = {
    "Aurora": {
        "bg": "#050713",
        "bg2": "#0a0f22",
        "panel": "rgba(14, 20, 42, 0.74)",
        "panel_strong": "rgba(18, 25, 52, 0.94)",
        "text": "#f7f8ff",
        "muted": "#9ba8c9",
        "line": "rgba(148, 163, 255, 0.18)",
        "line_strong": "rgba(148, 163, 255, 0.38)",
        "a": "#7c5cff",
        "b": "#20d9ff",
        "c": "#ff5fcf",
        "d": "#a6ff7a",
        "e": "#ffbd59",
        "danger": "#ff6b8a",
        "shadow": "rgba(42, 26, 95, 0.38)",
    },
    "Prism": {
        "bg": "#07100f",
        "bg2": "#0b1817",
        "panel": "rgba(13, 31, 29, 0.76)",
        "panel_strong": "rgba(16, 39, 36, 0.95)",
        "text": "#f4fff9",
        "muted": "#a2bbb2",
        "line": "rgba(102, 255, 209, 0.16)",
        "line_strong": "rgba(102, 255, 209, 0.36)",
        "a": "#00e6a8",
        "b": "#37b8ff",
        "c": "#d8ff52",
        "d": "#b388ff",
        "e": "#ff9d5c",
        "danger": "#ff6f91",
        "shadow": "rgba(0, 77, 57, 0.34)",
    },
    "Ember": {
        "bg": "#12080c",
        "bg2": "#1a0c12",
        "panel": "rgba(39, 18, 28, 0.76)",
        "panel_strong": "rgba(52, 22, 36, 0.95)",
        "text": "#fff8fb",
        "muted": "#c3a7b2",
        "line": "rgba(255, 143, 116, 0.17)",
        "line_strong": "rgba(255, 143, 116, 0.38)",
        "a": "#ff5f6d",
        "b": "#ff9a44",
        "c": "#d96cff",
        "d": "#52e5ff",
        "e": "#ffe66d",
        "danger": "#ff4f7a",
        "shadow": "rgba(119, 27, 56, 0.36)",
    },
    "Pearl": {
        "bg": "#f6f7fb",
        "bg2": "#eef1f8",
        "panel": "rgba(255, 255, 255, 0.74)",
        "panel_strong": "rgba(255, 255, 255, 0.96)",
        "text": "#15182a",
        "muted": "#66708b",
        "line": "rgba(72, 87, 155, 0.16)",
        "line_strong": "rgba(72, 87, 155, 0.30)",
        "a": "#6554ff",
        "b": "#0891d1",
        "c": "#db3ea4",
        "d": "#3aa76d",
        "e": "#e58a17",
        "danger": "#e6496f",
        "shadow": "rgba(66, 73, 115, 0.18)",
    },
}


_BASE_CSS = r"""
<style>
* {
  box-sizing: border-box;
}

:root {
  --adi-radius-xl: 30px;
  --adi-radius-lg: 22px;
  --adi-radius-md: 16px;
  --adi-fast: 180ms;
  --adi-slow: 700ms;
}

html {
  scroll-behavior: smooth;
}

html, body, [data-testid="stAppViewContainer"] {
  color: var(--adi-text);
  background:
    radial-gradient(circle at 9% 3%, color-mix(in srgb, var(--adi-a) 18%, transparent), transparent 30rem),
    radial-gradient(circle at 88% 9%, color-mix(in srgb, var(--adi-c) 14%, transparent), transparent 34rem),
    radial-gradient(circle at 72% 84%, color-mix(in srgb, var(--adi-b) 10%, transparent), transparent 30rem),
    linear-gradient(150deg, var(--adi-bg) 0%, var(--adi-bg-2) 50%, var(--adi-bg) 100%);
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  opacity: .34;
  background-image:
    linear-gradient(color-mix(in srgb, var(--adi-line) 45%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, var(--adi-line) 45%, transparent) 1px, transparent 1px);
  background-size: 58px 58px;
  mask-image: radial-gradient(circle at 55% 18%, #000 0%, transparent 72%);
}

body::after {
  content: "";
  position: fixed;
  width: 34rem;
  height: 34rem;
  left: -14rem;
  bottom: -15rem;
  pointer-events: none;
  border-radius: 50%;
  filter: blur(72px);
  opacity: .18;
  background: conic-gradient(from 20deg, var(--adi-a), var(--adi-c), var(--adi-b), var(--adi-d), var(--adi-a));
  animation: adiAmbient 18s ease-in-out infinite alternate;
  z-index: 0;
}

[data-testid="stAppViewContainer"] > .main {
  position: relative;
  z-index: 1;
}

[data-testid="stAppViewBlockContainer"] {
  max-width: 1560px;
  padding-top: 1.15rem;
  padding-bottom: 4rem;
}

[data-testid="stHeader"] {
  background: transparent;
}

[data-testid="stSidebar"] {
  background:
    linear-gradient(180deg,
      color-mix(in srgb, var(--adi-panel-strong) 92%, transparent),
      color-mix(in srgb, var(--adi-bg) 97%, transparent));
  border-right: 1px solid var(--adi-line);
  backdrop-filter: blur(26px);
}

[data-testid="stSidebar"]::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  background: linear-gradient(180deg, var(--adi-a), var(--adi-b), var(--adi-c), var(--adi-d));
  opacity: .75;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
  color: var(--adi-text);
}

h1, h2, h3, h4 {
  color: var(--adi-text);
  letter-spacing: -.028em;
}

p, li, label {
  color: color-mix(in srgb, var(--adi-text) 86%, var(--adi-muted));
}

[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
  color: var(--adi-muted) !important;
}

[data-testid="stMarkdownContainer"] a {
  color: var(--adi-b);
}

/* navigation */
div[data-baseweb="tab-list"] {
  gap: .4rem;
  background: color-mix(in srgb, var(--adi-panel-strong) 80%, transparent);
  border: 1px solid var(--adi-line);
  border-radius: 20px;
  padding: .38rem;
  box-shadow: 0 16px 46px var(--adi-shadow);
  position: sticky;
  top: .55rem;
  z-index: 20;
  backdrop-filter: blur(24px) saturate(145%);
}

button[data-baseweb="tab"] {
  min-height: 46px;
  border-radius: 14px;
  color: var(--adi-muted);
  font-weight: 720;
  padding-left: 1rem;
  padding-right: 1rem;
  transition:
    color var(--adi-fast) ease,
    background var(--adi-fast) ease,
    transform var(--adi-fast) ease;
}

button[data-baseweb="tab"]:hover {
  color: var(--adi-text);
  transform: translateY(-1px);
}

button[data-baseweb="tab"][aria-selected="true"] {
  color: #fff;
  background:
    linear-gradient(135deg,
      color-mix(in srgb, var(--adi-a) 75%, transparent),
      color-mix(in srgb, var(--adi-c) 46%, transparent),
      color-mix(in srgb, var(--adi-b) 44%, transparent));
  box-shadow:
    0 9px 24px color-mix(in srgb, var(--adi-a) 20%, transparent),
    inset 0 1px 0 rgba(255,255,255,.16);
  border: 1px solid color-mix(in srgb, var(--adi-b) 42%, transparent);
}

/* buttons */
div.stButton > button,
div.stDownloadButton > button {
  position: relative;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--adi-b) 36%, var(--adi-line));
  border-radius: 15px;
  min-height: 44px;
  font-weight: 760;
  color: #fff;
  background:
    linear-gradient(110deg,
      color-mix(in srgb, var(--adi-a) 72%, #171b37),
      color-mix(in srgb, var(--adi-c) 52%, #171b37) 48%,
      color-mix(in srgb, var(--adi-b) 65%, #171b37));
  background-size: 180% 100%;
  box-shadow:
    0 12px 30px color-mix(in srgb, var(--adi-a) 20%, transparent),
    inset 0 1px 0 rgba(255,255,255,.18);
  transition:
    transform var(--adi-fast) ease,
    box-shadow var(--adi-fast) ease,
    background-position .4s ease;
}

div.stButton > button:hover,
div.stDownloadButton > button:hover {
  transform: translateY(-2px);
  background-position: 100% 0;
  box-shadow:
    0 18px 40px color-mix(in srgb, var(--adi-c) 22%, transparent),
    inset 0 1px 0 rgba(255,255,255,.22);
}

div.stButton > button:active,
div.stDownloadButton > button:active {
  transform: translateY(0) scale(.99);
}

/* metrics / containers */
[data-testid="stMetric"] {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(145deg,
      color-mix(in srgb, var(--adi-panel-strong) 92%, transparent),
      color-mix(in srgb, var(--adi-panel) 86%, transparent));
  border: 1px solid var(--adi-line);
  border-radius: 18px;
  padding: 1rem 1.05rem;
  box-shadow: 0 12px 36px color-mix(in srgb, var(--adi-shadow) 60%, transparent);
  min-height: 108px;
  backdrop-filter: blur(18px);
}

[data-testid="stMetric"]::after {
  content: "";
  position: absolute;
  width: 80px;
  height: 80px;
  right: -30px;
  bottom: -38px;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--adi-b) 24%, transparent), transparent 70%);
}

[data-testid="stMetricValue"] {
  color: var(--adi-text);
  font-weight: 820;
  letter-spacing: -.04em;
}

[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--adi-line) !important;
  background: color-mix(in srgb, var(--adi-panel) 72%, transparent);
  border-radius: 20px !important;
  box-shadow: 0 14px 38px color-mix(in srgb, var(--adi-shadow) 40%, transparent);
  backdrop-filter: blur(18px);
}

/* inputs */
[data-testid="stFileUploader"] {
  background:
    linear-gradient(145deg,
      color-mix(in srgb, var(--adi-panel) 82%, transparent),
      color-mix(in srgb, var(--adi-bg) 78%, transparent));
  border: 1px dashed color-mix(in srgb, var(--adi-b) 42%, var(--adi-line));
  border-radius: 22px;
  padding: .75rem;
  transition: border-color var(--adi-fast) ease, box-shadow var(--adi-fast) ease;
}

[data-testid="stFileUploader"]:hover {
  border-color: color-mix(in srgb, var(--adi-c) 68%, var(--adi-line));
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--adi-c) 8%, transparent);
}

[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
  background:
    linear-gradient(145deg,
      color-mix(in srgb, var(--adi-panel-strong) 88%, transparent),
      color-mix(in srgb, var(--adi-bg) 76%, transparent)) !important;
  border-color: var(--adi-line) !important;
  color: var(--adi-text) !important;
  border-radius: 14px !important;
  box-shadow: inset 0 1px 0 color-mix(in srgb, #fff 6%, transparent);
}

[data-testid="stTextArea"] textarea:focus,
[data-baseweb="select"] > div:focus-within,
[data-baseweb="input"] > div:focus-within {
  border-color: color-mix(in srgb, var(--adi-b) 55%, var(--adi-line)) !important;
  box-shadow:
    0 0 0 4px color-mix(in srgb, var(--adi-b) 9%, transparent),
    0 10px 24px color-mix(in srgb, var(--adi-a) 10%, transparent) !important;
}

[data-testid="stExpander"] {
  background: color-mix(in srgb, var(--adi-panel) 72%, transparent);
  border: 1px solid var(--adi-line);
  border-radius: 16px;
  overflow: hidden;
  backdrop-filter: blur(16px);
}

[data-testid="stAlert"] {
  border-radius: 15px;
  border: 1px solid var(--adi-line);
  background: color-mix(in srgb, var(--adi-panel-strong) 82%, transparent);
}

/* hero */
.adi-hero {
  position: relative;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(340px, .75fr);
  align-items: center;
  gap: 1.25rem;
  min-height: 360px;
  border: 1px solid color-mix(in srgb, var(--adi-a) 30%, var(--adi-line));
  background:
    radial-gradient(circle at 12% 18%, color-mix(in srgb, var(--adi-a) 22%, transparent), transparent 30rem),
    radial-gradient(circle at 90% 18%, color-mix(in srgb, var(--adi-c) 20%, transparent), transparent 25rem),
    linear-gradient(135deg,
      color-mix(in srgb, var(--adi-panel-strong) 95%, transparent),
      color-mix(in srgb, var(--adi-bg) 90%, transparent));
  border-radius: 32px;
  padding: 2rem 2.15rem;
  box-shadow:
    0 28px 90px var(--adi-shadow),
    inset 0 1px 0 rgba(255,255,255,.07);
  margin-bottom: 1rem;
  isolation: isolate;
  animation: adiFadeUp .65s cubic-bezier(.22,.9,.28,1) both;
}

.adi-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    repeating-linear-gradient(
      90deg,
      transparent 0 74px,
      color-mix(in srgb, var(--adi-line) 42%, transparent) 75px
    ),
    repeating-linear-gradient(
      0deg,
      transparent 0 74px,
      color-mix(in srgb, var(--adi-line) 32%, transparent) 75px
    );
  opacity: .19;
  mask-image: linear-gradient(90deg, transparent, #000 38%, #000 100%);
  z-index: -1;
}

.adi-hero::after {
  content: "";
  position: absolute;
  top: -65%;
  left: -28%;
  width: 46%;
  height: 230%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.13), transparent);
  transform: rotate(16deg);
  animation: adiScan 8s linear infinite;
  z-index: -1;
}

.adi-kicker {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  color: var(--adi-b);
  font-size: .74rem;
  font-weight: 850;
  letter-spacing: .13em;
  text-transform: uppercase;
}

.adi-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--adi-d);
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--adi-d) 52%, transparent);
  animation: adiPulse 2.1s infinite;
}

.adi-title {
  margin: .7rem 0 .55rem 0;
  color: var(--adi-text);
  font-size: clamp(2.25rem, 4.3vw, 5rem);
  line-height: .96;
  font-weight: 900;
  letter-spacing: -.062em;
}

.adi-title .gradient {
  color: transparent;
  background: linear-gradient(100deg, var(--adi-b), var(--adi-a) 38%, var(--adi-c) 68%, var(--adi-e));
  background-size: 180% 100%;
  background-clip: text;
  -webkit-background-clip: text;
  animation: adiGradient 8s ease-in-out infinite alternate;
}

.adi-subtitle {
  max-width: 830px;
  color: var(--adi-muted);
  font-size: 1.02rem;
  line-height: 1.72;
  margin-bottom: 1.15rem;
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
  border: 1px solid var(--adi-line);
  border-radius: 999px;
  padding: .43rem .72rem;
  background: color-mix(in srgb, var(--adi-panel-strong) 66%, transparent);
  color: color-mix(in srgb, var(--adi-text) 88%, var(--adi-muted));
  font-size: .76rem;
  font-weight: 720;
  backdrop-filter: blur(14px);
  transition: transform var(--adi-fast) ease, border-color var(--adi-fast) ease;
}

.adi-chip:nth-child(1) strong { color: var(--adi-b); }
.adi-chip:nth-child(2) strong { color: var(--adi-a); }
.adi-chip:nth-child(3) strong { color: var(--adi-c); }
.adi-chip:nth-child(4) strong { color: var(--adi-d); }
.adi-chip:nth-child(5) strong { color: var(--adi-e); }

.adi-chip:hover {
  transform: translateY(-2px);
  border-color: var(--adi-line-strong);
}

/* animated hero system map */
.adi-system-map {
  position: relative;
  height: 300px;
  min-width: 320px;
  display: grid;
  place-items: center;
}

.adi-orbit {
  position: absolute;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--adi-line-strong) 82%, transparent);
  animation: adiRotate 18s linear infinite;
}

.adi-orbit.o1 { width: 264px; height: 264px; }
.adi-orbit.o2 { width: 196px; height: 196px; animation-direction: reverse; animation-duration: 13s; }
.adi-orbit.o3 {
  width: 118px;
  height: 118px;
  border-style: dashed;
  border-color: color-mix(in srgb, var(--adi-c) 34%, transparent);
  animation-duration: 9s;
}

.adi-orbit::after {
  content: "";
  position: absolute;
  width: 10px;
  height: 10px;
  top: -5px;
  left: calc(50% - 5px);
  border-radius: 50%;
  background: var(--adi-b);
  box-shadow: 0 0 24px var(--adi-b);
}

.adi-orbit.o2::after { background: var(--adi-c); box-shadow: 0 0 24px var(--adi-c); }
.adi-orbit.o3::after { background: var(--adi-d); box-shadow: 0 0 20px var(--adi-d); }

.adi-core {
  position: relative;
  z-index: 2;
  width: 108px;
  height: 138px;
  border-radius: 20px;
  display: grid;
  place-items: center;
  background:
    linear-gradient(145deg,
      color-mix(in srgb, var(--adi-a) 36%, var(--adi-panel-strong)),
      color-mix(in srgb, var(--adi-b) 22%, var(--adi-panel-strong)));
  border: 1px solid color-mix(in srgb, var(--adi-b) 44%, var(--adi-line));
  box-shadow:
    0 20px 55px color-mix(in srgb, var(--adi-a) 30%, transparent),
    inset 0 1px 0 rgba(255,255,255,.18);
  animation: adiFloat 4.5s ease-in-out infinite;
}

.adi-core::before {
  content: "";
  position: absolute;
  left: 18px;
  right: 18px;
  top: 30px;
  height: 2px;
  border-radius: 3px;
  background: var(--adi-b);
  box-shadow:
    0 17px 0 color-mix(in srgb, var(--adi-c) 78%, transparent),
    0 34px 0 color-mix(in srgb, var(--adi-d) 72%, transparent),
    0 51px 0 color-mix(in srgb, var(--adi-e) 68%, transparent);
}

.adi-core-label {
  position: absolute;
  bottom: 12px;
  font-size: .65rem;
  font-weight: 850;
  letter-spacing: .12em;
  color: var(--adi-text);
}

.adi-node {
  position: absolute;
  z-index: 4;
  min-width: 66px;
  padding: .4rem .55rem;
  text-align: center;
  border-radius: 12px;
  font-size: .65rem;
  font-weight: 820;
  letter-spacing: .06em;
  color: var(--adi-text);
  background: color-mix(in srgb, var(--adi-panel-strong) 84%, transparent);
  border: 1px solid var(--adi-line);
  box-shadow: 0 10px 28px color-mix(in srgb, var(--adi-shadow) 56%, transparent);
  backdrop-filter: blur(14px);
  animation: adiNodeFloat 4s ease-in-out infinite;
}

.adi-node.n1 { top: 26px; left: 32px; border-color: color-mix(in srgb, var(--adi-b) 48%, var(--adi-line)); color: var(--adi-b); }
.adi-node.n2 { top: 38px; right: 18px; border-color: color-mix(in srgb, var(--adi-c) 48%, var(--adi-line)); color: var(--adi-c); animation-delay: -.8s; }
.adi-node.n3 { bottom: 38px; left: 18px; border-color: color-mix(in srgb, var(--adi-d) 48%, var(--adi-line)); color: var(--adi-d); animation-delay: -1.7s; }
.adi-node.n4 { bottom: 24px; right: 35px; border-color: color-mix(in srgb, var(--adi-e) 48%, var(--adi-line)); color: var(--adi-e); animation-delay: -2.4s; }

/* sections and bento cards */
.adi-section {
  display: flex;
  align-items: center;
  gap: .55rem;
  color: var(--adi-text);
  font-size: 1.08rem;
  font-weight: 820;
  margin: .55rem 0 .7rem 0;
  letter-spacing: -.02em;
}

.adi-section::before {
  content: "";
  width: 28px;
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--adi-a), var(--adi-c), var(--adi-b));
  box-shadow: 0 0 16px color-mix(in srgb, var(--adi-c) 30%, transparent);
}

.adi-card {
  --card-accent: var(--adi-b);
  position: relative;
  overflow: hidden;
  height: 100%;
  background:
    linear-gradient(145deg,
      color-mix(in srgb, var(--adi-panel-strong) 86%, transparent),
      color-mix(in srgb, var(--adi-panel) 82%, transparent));
  border: 1px solid var(--adi-line);
  border-radius: 21px;
  padding: 1.05rem 1.05rem 1rem 1.05rem;
  box-shadow: 0 16px 42px color-mix(in srgb, var(--adi-shadow) 48%, transparent);
  backdrop-filter: blur(18px);
  animation: adiFadeUp .5s cubic-bezier(.22,.9,.28,1) both;
  transition:
    transform var(--adi-fast) ease,
    border-color var(--adi-fast) ease,
    box-shadow var(--adi-fast) ease;
}

.adi-card::before {
  content: "";
  position: absolute;
  width: 120px;
  height: 120px;
  top: -70px;
  right: -50px;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--card-accent) 25%, transparent), transparent 70%);
  transition: transform .3s ease;
}

.adi-card::after {
  content: "";
  position: absolute;
  inset: 0;
  border-top: 1px solid color-mix(in srgb, var(--card-accent) 40%, transparent);
  border-radius: inherit;
  pointer-events: none;
}

.adi-card:hover {
  transform: translateY(-5px);
  border-color: color-mix(in srgb, var(--card-accent) 44%, var(--adi-line));
  box-shadow:
    0 24px 54px color-mix(in srgb, var(--adi-shadow) 62%, transparent),
    0 0 0 1px color-mix(in srgb, var(--card-accent) 10%, transparent);
}

.adi-card:hover::before {
  transform: scale(1.35);
}

.adi-card.accent-a { --card-accent: var(--adi-a); }
.adi-card.accent-b { --card-accent: var(--adi-b); }
.adi-card.accent-c { --card-accent: var(--adi-c); }
.adi-card.accent-d { --card-accent: var(--adi-d); }
.adi-card.accent-e { --card-accent: var(--adi-e); }

.adi-card-title {
  color: var(--adi-text);
  font-weight: 820;
  margin-bottom: .35rem;
  letter-spacing: -.018em;
}

.adi-card-copy {
  color: var(--adi-muted);
  line-height: 1.58;
  font-size: .89rem;
}

.adi-icon {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: .75rem;
  border-radius: 12px;
  background:
    linear-gradient(145deg,
      color-mix(in srgb, var(--card-accent) 25%, transparent),
      color-mix(in srgb, var(--adi-panel-strong) 74%, transparent));
  border: 1px solid color-mix(in srgb, var(--card-accent) 34%, var(--adi-line));
  color: var(--card-accent);
  font-size: .83rem;
  font-weight: 900;
  box-shadow: 0 8px 22px color-mix(in srgb, var(--card-accent) 14%, transparent);
}

/* animated pipeline */
.adi-flow {
  position: relative;
  display: grid;
  grid-template-columns: repeat(5, minmax(105px, 1fr));
  gap: .7rem;
  align-items: center;
  margin: .75rem 0 1.15rem 0;
}

.adi-flow::before {
  content: "";
  position: absolute;
  height: 2px;
  left: 6%;
  right: 6%;
  top: 35px;
  background: linear-gradient(90deg, var(--adi-b), var(--adi-a), var(--adi-c), var(--adi-d), var(--adi-e));
  opacity: .42;
  box-shadow: 0 0 18px color-mix(in srgb, var(--adi-b) 28%, transparent);
}

.adi-flow-step {
  --step-accent: var(--adi-b);
  position: relative;
  min-height: 92px;
  padding: .9rem .82rem;
  border-radius: 18px;
  background: color-mix(in srgb, var(--adi-panel-strong) 78%, transparent);
  border: 1px solid var(--adi-line);
  text-align: center;
  overflow: hidden;
  box-shadow: 0 12px 34px color-mix(in srgb, var(--adi-shadow) 38%, transparent);
  backdrop-filter: blur(16px);
}

.adi-flow-step:nth-child(1) { --step-accent: var(--adi-b); }
.adi-flow-step:nth-child(2) { --step-accent: var(--adi-a); }
.adi-flow-step:nth-child(3) { --step-accent: var(--adi-c); }
.adi-flow-step:nth-child(4) { --step-accent: var(--adi-d); }
.adi-flow-step:nth-child(5) { --step-accent: var(--adi-e); }

.adi-flow-step::before {
  content: "";
  position: absolute;
  left: 8%;
  right: 8%;
  top: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--step-accent), transparent);
  animation: adiFlow 3.5s ease-in-out infinite;
}

.adi-flow-step::after {
  content: "";
  position: absolute;
  width: 8px;
  height: 8px;
  top: 31px;
  left: calc(50% - 4px);
  border-radius: 50%;
  background: var(--step-accent);
  box-shadow: 0 0 18px var(--step-accent);
}

.adi-flow-name {
  color: var(--adi-text);
  font-size: .83rem;
  font-weight: 800;
  margin-top: .72rem;
}

.adi-flow-copy {
  color: var(--adi-muted);
  font-size: .70rem;
  margin-top: .25rem;
}

/* assistant zones */
.adi-zone {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--adi-line);
  background:
    linear-gradient(145deg,
      color-mix(in srgb, var(--adi-panel-strong) 78%, transparent),
      color-mix(in srgb, var(--adi-panel) 68%, transparent));
  border-radius: 18px;
  padding: .92rem;
  min-height: 90px;
  margin-bottom: .75rem;
  backdrop-filter: blur(16px);
}

.adi-zone::after {
  content: "";
  position: absolute;
  height: 1px;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, var(--adi-a), var(--adi-c), var(--adi-b));
  opacity: .45;
}

.adi-zone-label {
  color: var(--adi-b);
  font-size: .69rem;
  letter-spacing: .10em;
  text-transform: uppercase;
  font-weight: 900;
  margin-bottom: .26rem;
}

.adi-zone-copy {
  color: var(--adi-muted);
  font-size: .82rem;
  line-height: 1.48;
}

.adi-status {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: .36rem .64rem;
  margin: 0 .34rem .34rem 0;
  font-size: .72rem;
  font-weight: 800;
  border: 1px solid color-mix(in srgb, var(--adi-d) 28%, var(--adi-line));
  background: color-mix(in srgb, var(--adi-d) 9%, transparent);
  color: color-mix(in srgb, var(--adi-d) 82%, var(--adi-text));
  backdrop-filter: blur(12px);
}

.adi-status.info {
  border-color: color-mix(in srgb, var(--adi-b) 32%, var(--adi-line));
  background: color-mix(in srgb, var(--adi-b) 9%, transparent);
  color: color-mix(in srgb, var(--adi-b) 82%, var(--adi-text));
}

.adi-status.gold {
  border-color: color-mix(in srgb, var(--adi-e) 32%, var(--adi-line));
  background: color-mix(in srgb, var(--adi-e) 9%, transparent);
  color: color-mix(in srgb, var(--adi-e) 82%, var(--adi-text));
}

.adi-status.magenta {
  border-color: color-mix(in srgb, var(--adi-c) 32%, var(--adi-line));
  background: color-mix(in srgb, var(--adi-c) 9%, transparent);
  color: color-mix(in srgb, var(--adi-c) 82%, var(--adi-text));
}

/* verification gauge */
.adi-gauge-wrap {
  display: flex;
  align-items: center;
  gap: .85rem;
  margin: .55rem 0 .75rem 0;
  padding: .72rem;
  border-radius: 16px;
  background: color-mix(in srgb, var(--adi-panel) 70%, transparent);
  border: 1px solid var(--adi-line);
}

.adi-gauge {
  --value: 0;
  --gauge-accent: var(--adi-d);
  width: 64px;
  height: 64px;
  flex: 0 0 64px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle closest-side, var(--adi-panel-strong) 72%, transparent 73% 99%),
    conic-gradient(var(--gauge-accent) calc(var(--value) * 1%), color-mix(in srgb, var(--adi-line) 76%, transparent) 0);
  box-shadow: 0 0 24px color-mix(in srgb, var(--gauge-accent) 18%, transparent);
}

.adi-gauge strong {
  color: var(--adi-text);
  font-size: .78rem;
}

.adi-gauge-title {
  color: var(--adi-text);
  font-weight: 800;
  font-size: .84rem;
}

.adi-gauge-copy {
  color: var(--adi-muted);
  font-size: .74rem;
  line-height: 1.4;
}

/* benchmark/config */
.adi-benchmark {
  position: relative;
  overflow: hidden;
  border-left: 3px solid var(--adi-b);
  background: color-mix(in srgb, var(--adi-panel) 72%, transparent);
  border-radius: 14px;
  padding: .85rem .95rem;
  color: var(--adi-muted);
  margin: .4rem 0;
  box-shadow: 0 10px 28px color-mix(in srgb, var(--adi-shadow) 34%, transparent);
}

.adi-benchmark::after {
  content: "";
  position: absolute;
  width: 90px;
  height: 90px;
  right: -38px;
  top: -38px;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--adi-c) 18%, transparent), transparent 70%);
}

.adi-config-line {
  display: flex;
  justify-content: space-between;
  gap: .7rem;
  padding: .62rem 0;
  border-bottom: 1px solid color-mix(in srgb, var(--adi-line) 72%, transparent);
}

.adi-config-line:last-child { border-bottom: none; }
.adi-config-key { color: var(--adi-muted); }
.adi-config-value { color: var(--adi-text); font-weight: 720; text-align: right; }

/* animations */
@keyframes adiFadeUp {
  from { opacity: 0; transform: translateY(12px) scale(.992); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes adiPulse {
  0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--adi-d) 42%, transparent); }
  70% { box-shadow: 0 0 0 10px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}

@keyframes adiScan {
  from { transform: translateX(-50%) rotate(16deg); }
  to { transform: translateX(420%) rotate(16deg); }
}

@keyframes adiFlow {
  0%,100% { opacity: .24; transform: translateX(-25%); }
  50% { opacity: 1; transform: translateX(25%); }
}

@keyframes adiGradient {
  0% { background-position: 0% 50%; }
  100% { background-position: 100% 50%; }
}

@keyframes adiRotate {
  to { transform: rotate(360deg); }
}

@keyframes adiFloat {
  0%,100% { transform: translateY(-3px) rotate(-1deg); }
  50% { transform: translateY(7px) rotate(1deg); }
}

@keyframes adiNodeFloat {
  0%,100% { transform: translateY(0); }
  50% { transform: translateY(-7px); }
}

@keyframes adiAmbient {
  0% { transform: scale(.9) rotate(0deg); }
  100% { transform: scale(1.12) rotate(30deg); }
}

@media (max-width: 980px) {
  .adi-hero {
    grid-template-columns: 1fr;
    min-height: auto;
  }
  .adi-system-map {
    height: 260px;
  }
  .adi-flow {
    grid-template-columns: 1fr;
  }
  .adi-flow::before {
    display: none;
  }
  .adi-flow-step::after {
    top: 14px;
    left: 14px;
  }
  .adi-flow-name {
    margin-top: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .001ms !important;
  }
}
</style>
"""


def available_themes() -> list[str]:
    return list(THEMES)


def apply_v2_theme(theme: str = "Aurora") -> None:
    palette = THEMES.get(theme, THEMES["Aurora"])
    variables = f"""
    <style>
    :root {{
      --adi-bg: {palette["bg"]};
      --adi-bg-2: {palette["bg2"]};
      --adi-panel: {palette["panel"]};
      --adi-panel-strong: {palette["panel_strong"]};
      --adi-text: {palette["text"]};
      --adi-muted: {palette["muted"]};
      --adi-line: {palette["line"]};
      --adi-line-strong: {palette["line_strong"]};
      --adi-a: {palette["a"]};
      --adi-b: {palette["b"]};
      --adi-c: {palette["c"]};
      --adi-d: {palette["d"]};
      --adi-e: {palette["e"]};
      --adi-danger: {palette["danger"]};
      --adi-shadow: {palette["shadow"]};
    }}
    </style>
    """
    st.markdown(variables + _BASE_CSS, unsafe_allow_html=True)


def render_hero(theme: str = "Aurora") -> None:
    safe_theme = html.escape(theme)
    st.markdown(
        f"""
        <section class="adi-hero">
          <div>
            <div class="adi-kicker"><span class="adi-dot"></span> V2 · {safe_theme} intelligence surface</div>
            <div class="adi-title">Agentic <span class="gradient">Document Intelligence</span></div>
            <div class="adi-subtitle">
              A local-first evidence system that reads documents, retrieves the strongest
              passages, verifies claims semantically, and launches bounded agentic recovery
              only when the evidence is not strong enough.
            </div>
            <div class="adi-chip-row">
              <span class="adi-chip"><strong>OCR</strong> scanned pages</span>
              <span class="adi-chip"><strong>RAG</strong> dense + hybrid</span>
              <span class="adi-chip"><strong>NLI</strong> semantic verification</span>
              <span class="adi-chip"><strong>AGENT</strong> adaptive recovery</span>
              <span class="adi-chip"><strong>LOCAL</strong> private-first</span>
            </div>
          </div>
          <div class="adi-system-map" aria-hidden="true">
            <div class="adi-orbit o1"></div>
            <div class="adi-orbit o2"></div>
            <div class="adi-orbit o3"></div>
            <div class="adi-core"><span class="adi-core-label">EVIDENCE</span></div>
            <div class="adi-node n1">OCR</div>
            <div class="adi-node n2">RAG</div>
            <div class="adi-node n3">VERIFY</div>
            <div class="adi-node n4">AGENT</div>
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
          <div class="adi-flow-step"><div class="adi-flow-name">04 · Verify</div><div class="adi-flow-copy">Semantic entailment</div></div>
          <div class="adi-flow-step"><div class="adi-flow-name">05 · Recover</div><div class="adi-flow-copy">Adaptive re-retrieval</div></div>
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
    accent = accent if accent in {"a", "b", "c", "d", "e"} else "b"
    st.markdown(
        f"""
        <div class="adi-card accent-{accent}">
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
    allowed = {"", "info", "gold", "magenta"}
    rendered = []
    for label, variant in items:
        safe_variant = variant if variant in allowed else ""
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
    percent = max(0.0, min(1.0, value)) * 100
    accent_var = {
        "a": "var(--adi-a)",
        "b": "var(--adi-b)",
        "c": "var(--adi-c)",
        "d": "var(--adi-d)",
        "e": "var(--adi-e)",
    }.get(accent, "var(--adi-d)")
    st.markdown(
        f"""
        <div class="adi-gauge-wrap">
          <div class="adi-gauge" style="--value:{percent:.1f};--gauge-accent:{accent_var}">
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
