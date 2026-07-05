import streamlit as st


def apply_global_styles():
    st.markdown("""
    <style>
      .block-container {
        padding-top: 1.65rem !important;
        max-width: 1280px !important;
      }

      :root {
        --ios-bg-0: #030712;
        --ios-bg-1: #07111f;
        --ios-glass: rgba(11, 23, 43, .62);
        --ios-glass-strong: rgba(15, 31, 56, .78);
        --ios-stroke: rgba(190, 226, 255, .18);
        --ios-stroke-hot: rgba(132, 208, 255, .48);
        --ios-text: #f4f9ff;
        --ios-muted: rgba(220, 236, 248, .70);
        --ios-blue: #5aa7ff;
        --ios-cyan: #7edcff;
        --ios-green: #73f0a2;
        --ios-shadow: 0 24px 70px rgba(0, 0, 0, .34);
        --ios-glass-edge: rgba(225, 244, 255, .26);
        --ios-liquid-sheen: linear-gradient(120deg, transparent 0%, rgba(255,255,255,.13) 28%, rgba(126,220,255,.22) 46%, rgba(255,255,255,.10) 58%, transparent 76%);
      }

      @keyframes iosRiseIn {
        from { opacity: 0; transform: translateY(10px) scale(.992); }
        to { opacity: 1; transform: translateY(0) scale(1); }
      }
      @keyframes iosSoftPulse {
        0%, 100% { box-shadow: 0 0 0 rgba(126, 220, 255, 0); }
        50% { box-shadow: 0 0 28px rgba(126, 220, 255, .18); }
      }
      @keyframes iosLiquidDrift {
        0% { background-position: 0% 0%, 100% 18%, 50% 50%; }
        50% { background-position: 8% 7%, 92% 25%, 53% 45%; }
        100% { background-position: 0% 0%, 100% 18%, 50% 50%; }
      }
      @keyframes iosSheenSweep {
        from { transform: translateX(-140%) rotate(10deg); opacity: 0; }
        28% { opacity: 1; }
        to { transform: translateX(140%) rotate(10deg); opacity: 0; }
      }
      @keyframes iosGlassBloom {
        0%, 100% { border-color: rgba(190, 226, 255, .16); box-shadow: inset 0 1px 0 rgba(255,255,255,.055), 0 14px 38px rgba(0,0,0,.18); }
        50% { border-color: rgba(126, 220, 255, .32); box-shadow: inset 0 1px 0 rgba(255,255,255,.11), 0 18px 46px rgba(72, 164, 255, .12); }
      }

      .stApp {
        color: var(--ios-text);
        background:
          radial-gradient(circle at 18% 10%, rgba(90, 167, 255, .16), transparent 28%),
          radial-gradient(circle at 86% 34%, rgba(126, 220, 255, .08), transparent 26%),
          linear-gradient(135deg, var(--ios-bg-0) 0%, var(--ios-bg-1) 48%, #020617 100%) !important;
        background-size: 140% 140%, 160% 160%, 100% 100% !important;
        animation: iosLiquidDrift 24s ease-in-out infinite;
      }
      .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        background:
          linear-gradient(135deg, transparent 0%, rgba(255,255,255,.035) 38%, transparent 60%),
          radial-gradient(circle at 42% 12%, rgba(126,220,255,.08), transparent 28%);
        mix-blend-mode: screen;
      }
      .main .block-container {
        position: relative;
        z-index: 1;
        animation: iosRiseIn .34s cubic-bezier(.2,.8,.2,1) both;
      }

      h1, h2, h3 {
        letter-spacing: 0 !important;
        color: var(--ios-text) !important;
        text-wrap: balance;
      }
      h1 {
        margin-top: .35rem !important;
        line-height: 1.14 !important;
        margin-bottom: .55rem !important;
        animation: iosRiseIn .34s cubic-bezier(.2,.8,.2,1) both;
        text-shadow: 0 0 28px rgba(126, 220, 255, .10);
      }

      .atlas-module-title,
      .visualizer-intro,
      .directions-title-row,
      .system-title-row {
        position: relative !important;
        overflow: hidden !important;
        display: flex !important;
        align-items: center !important;
        gap: 18px !important;
        flex-wrap: wrap !important;
        margin: 1.12rem 0 .68rem 0 !important;
        padding: 18px 20px !important;
        border-radius: 28px !important;
        border: 1px solid rgba(210, 238, 255, .18) !important;
        background:
          radial-gradient(circle at 12% 0%, rgba(255,255,255,.11), transparent 35%),
          radial-gradient(circle at 82% 30%, rgba(126,220,255,.08), transparent 30%),
          linear-gradient(180deg, rgba(17,35,62,.62), rgba(5,13,27,.38)) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.12), 0 18px 52px rgba(0,0,0,.20) !important;
        backdrop-filter: blur(22px) saturate(1.32);
        animation: iosRiseIn .34s cubic-bezier(.2,.8,.2,1) both;
      }
      .atlas-module-title::before,
      .visualizer-intro::before,
      .directions-title-row::before,
      .system-title-row::before {
        content: "";
        position: absolute;
        inset: -80% -35%;
        background: var(--ios-liquid-sheen);
        transform: translateX(-28%) rotate(10deg);
        opacity: .36;
        pointer-events: none;
      }
      .atlas-module-title h1,
      .visualizer-intro h1,
      .directions-title-row h1 {
        position: relative;
        margin: 0 !important;
        font-size: clamp(2rem, 4vw, 2.65rem) !important;
        line-height: 1.1 !important;
        white-space: normal !important;
      }
      .system-title-row .system-title {
        position: relative;
        margin: 0 !important;
        font-size: clamp(2rem, 4vw, 2.65rem) !important;
        line-height: 1.1 !important;
      }
      .atlas-module-title p,
      .visualizer-intro p,
      .directions-title-row p,
      .system-title-row .system-inline-hint {
        position: relative;
        flex: 1 1 420px;
        min-width: 260px;
        margin: 0 !important;
        color: rgba(221, 240, 252, .76) !important;
        font-size: .9rem !important;
        line-height: 1.35 !important;
        max-width: 980px !important;
      }

      div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]),
      div[data-testid="stAlert"],
      div[data-testid="stExpander"],
      div[data-testid="stTextArea"] textarea {
        position: relative;
        overflow: hidden;
        border-radius: 18px !important;
        border: 1px solid var(--ios-glass-edge) !important;
        background:
          radial-gradient(circle at 12% 0%, rgba(255,255,255,.10), transparent 32%),
          linear-gradient(180deg, rgba(20, 38, 66, .78), rgba(7, 15, 29, .54)) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.12), inset 0 -1px 0 rgba(126,220,255,.07), 0 18px 48px rgba(0,0,0,.22) !important;
        backdrop-filter: blur(22px) saturate(1.35);
      }

      div[data-testid="stAlert"] {
        animation: iosRiseIn .28s cubic-bezier(.2,.8,.2,1) both;
      }

      div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
      div[data-testid="stTextInput"] input,
      div[data-testid="stTextArea"] textarea {
        border-radius: 14px !important;
        border-color: rgba(190, 226, 255, .20) !important;
        background: rgba(14, 27, 49, .82) !important;
        color: var(--ios-text) !important;
        transition: border-color .2s ease, box-shadow .2s ease, background .2s ease;
      }
      div[data-testid="stTextInput"] input:focus,
      div[data-testid="stTextArea"] textarea:focus {
        border-color: var(--ios-stroke-hot) !important;
        box-shadow: 0 0 0 3px rgba(90, 167, 255, .16) !important;
      }

      div.stButton > button {
        position: relative;
        overflow: hidden;
        border-radius: 999px !important;
        border: 1px solid rgba(190, 226, 255, .22) !important;
        background: linear-gradient(180deg, rgba(92, 171, 255, .98), rgba(22, 126, 248, .94)) !important;
        box-shadow: 0 10px 26px rgba(36, 135, 255, .24), inset 0 1px 0 rgba(255,255,255,.28) !important;
        transition: transform .16s ease, box-shadow .16s ease, filter .16s ease;
      }
      div.stButton > button::before {
        content: "";
        position: absolute;
        inset: -60% -30%;
        background: var(--ios-liquid-sheen);
        transform: translateX(-140%) rotate(10deg);
        opacity: 0;
        pointer-events: none;
      }
      div.stButton > button:hover {
        transform: translateY(-1px);
        filter: brightness(1.05);
        box-shadow: 0 16px 34px rgba(36, 135, 255, .30), inset 0 1px 0 rgba(255,255,255,.32) !important;
      }
      div.stButton > button:hover::before {
        animation: iosSheenSweep .82s cubic-bezier(.2,.8,.2,1);
      }
      div.stButton > button:active {
        transform: translateY(0) scale(.985);
      }

      div[data-testid="stSidebar"] {
        background: rgba(5, 11, 24, .74) !important;
        border-right: 1px solid rgba(190, 226, 255, .11);
        backdrop-filter: blur(20px) saturate(1.25);
      }
      div[data-testid="stSidebar"] [role="radio"] {
        border-radius: 999px;
        transition: background .18s ease, transform .18s ease;
      }
      div[data-testid="stSidebar"] [role="radio"]:hover {
        background: rgba(90, 167, 255, .08);
        transform: translateX(2px);
      }

      div[data-testid="stMetric"] {
        padding: 14px 16px;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(13, 26, 48, .72), rgba(7, 15, 29, .54));
        border: 1px solid rgba(190, 226, 255, .16);
        box-shadow: 0 16px 42px rgba(0,0,0,.18);
        animation: iosRiseIn .32s cubic-bezier(.2,.8,.2,1) both;
      }

      div[data-testid="stPlotlyChart"],
      div[data-testid="stDataFrame"],
      div[data-testid="stCodeBlock"],
      div[data-testid="stJson"] {
        border-radius: 22px !important;
        overflow: hidden !important;
        border: 1px solid rgba(190, 226, 255, .16) !important;
        background:
          radial-gradient(circle at 18% 0%, rgba(255,255,255,.08), transparent 34%),
          linear-gradient(180deg, rgba(15, 31, 56, .62), rgba(5, 12, 25, .46)) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 20px 52px rgba(0,0,0,.22) !important;
        animation: iosRiseIn .34s cubic-bezier(.2,.8,.2,1) both;
      }
      div[data-testid="stIFrame"] iframe {
        border-radius: 28px !important;
        background:
          radial-gradient(circle at 18% 0%, rgba(255,255,255,.08), transparent 34%),
          rgba(5, 12, 25, .42) !important;
        box-shadow: 0 22px 62px rgba(0,0,0,.25);
      }
      div[data-testid="stIFrame"] {
        scroll-margin-top: 96px !important;
      }
      div[data-testid="stSlider"] {
        padding: 2px 0 8px 0;
      }
      div[data-testid="stSlider"] [data-baseweb="slider"] {
        filter: drop-shadow(0 0 14px rgba(126, 220, 255, .10));
      }
      div[data-testid="stRadio"] [role="radio"],
      div[data-testid="stCheckbox"] label,
      div[data-testid="stToggle"] label {
        transition: transform .16s ease, opacity .16s ease, color .16s ease;
      }
      div[data-testid="stRadio"] [role="radio"]:hover,
      div[data-testid="stCheckbox"] label:hover,
      div[data-testid="stToggle"] label:hover {
        transform: translateY(-1px);
      }

      mark {
        color: #05111f;
        background: linear-gradient(180deg, #bff0ff, #75d8ff);
        border-radius: 6px;
        padding: 0 .18em;
      }

      .ios-result-card {
        position: relative;
        overflow: hidden;
        margin: 10px 0;
        padding: 14px 16px;
        border-radius: 18px;
        border: 1px solid rgba(190, 226, 255, .22);
        background:
          radial-gradient(circle at 14% 0%, rgba(255,255,255,.10), transparent 34%),
          linear-gradient(180deg, rgba(17, 35, 62, .78), rgba(7, 15, 29, .54));
        box-shadow: 0 18px 48px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.10);
        animation: iosRiseIn .28s cubic-bezier(.2,.8,.2,1) both;
      }
      .ios-result-card::before {
        content: "";
        position: absolute;
        inset: -70% -30%;
        background: var(--ios-liquid-sheen);
        transform: translateX(-140%) rotate(10deg);
        opacity: .0;
        pointer-events: none;
      }
      .ios-result-card:hover {
        border-color: rgba(126, 220, 255, .38);
        animation: iosGlassBloom 1.8s ease-in-out infinite;
      }
      .ios-result-card:hover::before {
        animation: iosSheenSweep 1s cubic-bezier(.2,.8,.2,1);
      }
      .ios-kicker {
        color: var(--ios-cyan);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: .08em;
        text-transform: uppercase;
      }
      .ios-muted {
        color: var(--ios-muted);
        line-height: 1.5;
      }

      /* Keep the page from visually dimming while AI requests are running. */
      [data-testid="stStatusWidget"],
      [data-testid="stDecoration"] {
        display: none !important;
        visibility: hidden !important;
      }
      [data-testid="stAppViewContainer"],
      .stApp,
      .main {
        opacity: 1 !important;
        filter: none !important;
      }

      /* Hide Streamlit's small "Press Enter to apply" input instruction. */
      [data-testid="InputInstructions"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
      }

      /* Keep sidebar navigation stable and prevent long radio labels from wrapping. */
      [data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] {
        gap: .46rem !important;
        min-height: auto !important;
        align-items: stretch !important;
      }
      [data-testid="stSidebar"] div[data-testid="stRadio"] [role="radio"] {
        padding-top: .12rem !important;
        padding-bottom: .12rem !important;
        min-height: 1.7rem !important;
      }
      [data-testid="stSidebar"] div[data-testid="stRadio"] label,
      [data-testid="stSidebar"] div[data-testid="stRadio"] p {
        white-space: nowrap !important;
        line-height: 1.25 !important;
      }

      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
          animation-duration: .01ms !important;
          animation-iteration-count: 1 !important;
          scroll-behavior: auto !important;
          transition-duration: .01ms !important;
        }
      }

    </style>
    """, unsafe_allow_html=True)
