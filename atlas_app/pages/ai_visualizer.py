import html
import json
import re
import textwrap

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components

from atlas_app.ai import *
from atlas_app.config import *
from atlas_app.paper import *

def render_ai_visualizer(pages, total_pages):
    st.markdown('''
    <style>
      .block-container { padding-top: 1.42rem !important; }

      /* Compact one-line title row */
      .visualizer-intro {
        margin: .32rem 0 .35rem 0;
        display: flex;
        align-items: center;
        gap: 18px;
        flex-wrap: nowrap;
      }
      .visualizer-intro h1 {
        margin: 0;
        color: #f8fbff;
        font-size: 2.25rem;
        line-height: 1.18;
        font-weight: 850;
        letter-spacing: 0;
        white-space: nowrap;
      }
      .visualizer-intro p {
        margin: 0;
        color: rgba(188, 221, 239, .75);
        font-size: .88rem;
        line-height: 1.15;
        max-width: 980px;
      }

      /* Compress the control row: selectbox + radio */
      div[data-testid="stSelectbox"], div[data-testid="stRadio"] {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
      }
      div[data-testid="stSelectbox"] label,
      div[data-testid="stRadio"] label {
        font-size: .78rem !important;
        font-weight: 760 !important;
        margin-bottom: .05rem !important;
        padding-bottom: 0 !important;
      }
      div[data-testid="stSelectbox"] > div,
      div[data-testid="stRadio"] > div {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
      }
      div[data-baseweb="select"] > div {
        min-height: 34px !important;
        height: 34px !important;
      }
      div[data-baseweb="select"] div {
        line-height: 1.05 !important;
      }
      div[data-testid="stRadio"] [role="radiogroup"] {
        gap: .75rem !important;
        min-height: 34px !important;
        align-items: center !important;
      }
      div[data-testid="stRadio"] [role="radio"] {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
      }

      /* Keep the Scientific Story Engine close to controls without hiding it under Streamlit's top bar. */
      div[data-testid="stIFrame"] {
        margin-top: .35rem !important;
        scroll-margin-top: 96px !important;
      }

      /* Do not let the AI Visualizer radio compression affect the sidebar navigation. */
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
    </style>
    <div class="visualizer-intro">
      <h1>&#127912; AI Visualizer</h1>
      <p>Transform the review paper into an interactive scientific story: mechanisms grow step by step, evidence nodes light up, and each pathway becomes slide-ready.</p>
    </div>
    ''', unsafe_allow_html=True)

    story_bank = {
        "Ice Sheet Stability": {
            "subtitle": "From ocean heat to ice-sheet retreat",
            "opening": "Antarctic stability is not controlled by one factor. It emerges from ocean forcing, ice-shelf buttressing, grounding-line geometry, and feedbacks across the Earth system.",
            "modes": {
                "Past": [
                    {"id": "Past Warm Periods", "type": "Paleo evidence", "x": 18, "y": 28, "note": "Pliocene and Last Interglacial evidence shows that the AIS can respond strongly to warmer climates.", "evidence": "Ice cores - marine sediments - sea-level constraints"},
                    {"id": "Marine-based Ice", "type": "Boundary condition", "x": 39, "y": 42, "note": "Ice grounded below sea level is especially sensitive to ocean and grounding-line feedbacks.", "evidence": "Subglacial basins - continental shelf records"},
                    {"id": "Retreat Episodes", "type": "Ice response", "x": 62, "y": 35, "note": "Past retreat helps test whether models can reproduce rapid ice-sheet change.", "evidence": "Grounding-zone wedges - iceberg plow marks"},
                    {"id": "Model Constraints", "type": "Research use", "x": 80, "y": 55, "note": "Paleo records constrain future projections by showing what the ice sheet has done before.", "evidence": "Paleo-data model comparison"}
                ],
                "Present": [
                    {"id": "Warm Ocean Access", "type": "Ocean", "x": 16, "y": 46, "note": "Warm Circumpolar Deep Water can reach vulnerable ice-shelf cavities.", "evidence": "Ocean observations - shelf-break bathymetry"},
                    {"id": "Basal Melting", "type": "Ice shelf", "x": 34, "y": 32, "note": "Ocean heat melts the underside of floating ice shelves.", "evidence": "Altimetry - ocean moorings - melt-rate estimates"},
                    {"id": "Reduced Buttressing", "type": "Ice dynamics", "x": 52, "y": 42, "note": "Thinner or damaged shelves provide less back stress to grounded ice.", "evidence": "Ice velocity - shelf-thickness change"},
                    {"id": "Grounding Line Retreat", "type": "Ice dynamics", "x": 69, "y": 31, "note": "The grounding line controls how much grounded ice can discharge into the ocean.", "evidence": "InSAR - altimetry - tidal flexure"},
                    {"id": "Faster Ice Flow", "type": "Observation", "x": 84, "y": 48, "note": "Velocity observations reveal acceleration of outlet glaciers in key sectors.", "evidence": "InSAR velocity fields"}
                ],
                "Future": [
                    {"id": "Continued Warming", "type": "Forcing", "x": 15, "y": 32, "note": "Future atmosphere and ocean forcing determine the pressure placed on the AIS.", "evidence": "Climate scenarios"},
                    {"id": "Instability Thresholds", "type": "Uncertainty", "x": 35, "y": 48, "note": "MISI and possible MICI-like behavior could amplify retreat once thresholds are crossed.", "evidence": "Ice-sheet models - process studies"},
                    {"id": "Coupled Feedbacks", "type": "Earth system", "x": 57, "y": 34, "note": "Ocean, ice, atmosphere, and solid Earth feedbacks interact across time scales.", "evidence": "Coupled ice-ocean-solid Earth models"},
                    {"id": "Sea-level Risk", "type": "Impact", "x": 78, "y": 50, "note": "Antarctica remains a major uncertainty in future sea-level projections.", "evidence": "Projection ensembles - uncertainty quantification"}
                ]
            }
        },
        "Ocean-driven Ice Loss": {
            "subtitle": "How ocean heat becomes ice discharge",
            "opening": "Warm water reaches the ice shelf cavity, melts ice from below, weakens buttressing, and allows grounded ice to accelerate.",
            "modes": {
                "Past": [
                    {"id": "Shelf Troughs", "type": "Landscape memory", "x": 18, "y": 50, "note": "Repeated glacial erosion carved troughs that can route warm water toward the margin.", "evidence": "Bathymetry - marine geomorphology"},
                    {"id": "Past Ocean States", "type": "Paleo ocean", "x": 39, "y": 35, "note": "Marine records reconstruct past ocean warmth and ice-margin retreat.", "evidence": "Marine sediment cores"},
                    {"id": "Retreat History", "type": "Paleo ice", "x": 63, "y": 43, "note": "Past retreat episodes provide analogs for modern ocean-forced change.", "evidence": "Continental shelf archives"},
                    {"id": "Sensitivity Test", "type": "Model constraint", "x": 81, "y": 31, "note": "Models are tested against past retreat and sea-level evidence.", "evidence": "Paleo-calibrated simulations"}
                ],
                "Present": [
                    {"id": "CDW Intrusion", "type": "Ocean", "x": 14, "y": 45, "note": "Circumpolar Deep Water brings heat onto the continental shelf.", "evidence": "Ocean profiles - shelf-break circulation"},
                    {"id": "Ice-shelf Cavity", "type": "Hidden interface", "x": 33, "y": 31, "note": "The most important melting often occurs beneath floating ice shelves, out of direct view.", "evidence": "Radar - ocean access drilling - models"},
                    {"id": "Basal Melt", "type": "Process", "x": 50, "y": 45, "note": "Heat and salt exchange at the ice-ocean boundary melts ice from below.", "evidence": "Melt-rate estimates - ocean modeling"},
                    {"id": "Shelf Thinning", "type": "Observation", "x": 67, "y": 31, "note": "Altimetry detects surface lowering that indicates thinning.", "evidence": "Satellite altimetry"},
                    {"id": "Ice Discharge", "type": "Impact", "x": 84, "y": 48, "note": "Once buttressing weakens, grounded ice can flow faster into the ocean.", "evidence": "InSAR velocity - mass balance"}
                ],
                "Future": [
                    {"id": "Stronger Heat Flux", "type": "Forcing", "x": 15, "y": 36, "note": "Changes in winds, eddies, tides, and circulation may alter heat delivery to shelves.", "evidence": "High-resolution ocean models"},
                    {"id": "Freshwater Feedback", "type": "Feedback", "x": 36, "y": 52, "note": "Meltwater can increase stratification and trap subsurface heat.", "evidence": "Freshwater-ocean coupling"},
                    {"id": "More Basal Melt", "type": "Amplification", "x": 58, "y": 34, "note": "A warmer, more stratified shelf ocean can sustain higher basal melt rates.", "evidence": "Ice-ocean model experiments"},
                    {"id": "Projection Spread", "type": "Uncertainty", "x": 80, "y": 48, "note": "Ocean forcing remains one of the central uncertainties in future AIS mass loss.", "evidence": "Model intercomparison"}
                ]
            }
        },
        "Hydrofracture & Ice Cliff Risk": {
            "subtitle": "Atmospheric melt, shelf collapse, and high-end risk",
            "opening": "Surface meltwater can pond on ice shelves, deepen crevasses through hydrofracture, and reduce shelf integrity.",
            "modes": {
                "Past": [
                    {"id": "Warm Intervals", "type": "Climate context", "x": 18, "y": 34, "note": "Past warm periods help test whether surface-melt processes can explain high sea levels.", "evidence": "Last Interglacial - Pliocene"},
                    {"id": "Ice-shelf Absence", "type": "Paleo state", "x": 42, "y": 50, "note": "Some records imply reduced ice-shelf cover during warmer conditions.", "evidence": "Marine sediment evidence"},
                    {"id": "Rapid Retreat Clues", "type": "Paleo evidence", "x": 65, "y": 36, "note": "Geomorphic evidence can suggest rapid retreat or calving behavior.", "evidence": "Iceberg-keel plow marks"},
                    {"id": "Model Debate", "type": "Uncertainty", "x": 82, "y": 53, "note": "MICI is influential but still debated and requires more validation.", "evidence": "Ice-sheet model comparisons"}
                ],
                "Present": [
                    {"id": "Surface Melt", "type": "Atmosphere", "x": 16, "y": 35, "note": "Surface melt is most prominent around the Antarctic Peninsula and shelf margins.", "evidence": "Satellite melt detection"},
                    {"id": "Melt Ponds", "type": "Hydrology", "x": 35, "y": 50, "note": "Ponded water adds weight and can fill crevasses.", "evidence": "Optical imagery - surface hydrology mapping"},
                    {"id": "Hydrofracturing", "type": "Fracture", "x": 54, "y": 34, "note": "Water pressure can drive cracks deeper into the shelf.", "evidence": "Larsen-style collapse interpretation"},
                    {"id": "Shelf Collapse", "type": "Instability", "x": 72, "y": 48, "note": "Shelf breakup reduces buttressing and can accelerate tributary glaciers.", "evidence": "Larsen B observations"},
                    {"id": "Flow Acceleration", "type": "Observation", "x": 86, "y": 32, "note": "Post-collapse velocity change shows the mechanical importance of ice shelves.", "evidence": "InSAR velocity"}
                ],
                "Future": [
                    {"id": "More Surface Melt", "type": "Forcing", "x": 16, "y": 45, "note": "Atmospheric warming may expand meltwater systems on ice shelves.", "evidence": "Climate projections"},
                    {"id": "Shelf Vulnerability", "type": "Risk", "x": 37, "y": 31, "note": "Vulnerability depends on firn capacity, fracture fields, shelf geometry, and stress state.", "evidence": "Surface hydrology + fracture models"},
                    {"id": "Possible MICI", "type": "Debated mechanism", "x": 60, "y": 49, "note": "Marine Ice Cliff Instability could raise high-end sea-level outcomes, but evidence remains limited.", "evidence": "Model parameterization - field analogs"},
                    {"id": "High-end Sea Level", "type": "Impact", "x": 82, "y": 34, "note": "This pathway matters most for low-probability, high-impact projection tails.", "evidence": "Scenario ensembles"}
                ]
            }
        },
        "Solid Earth Feedbacks": {
            "subtitle": "The bed below the ice is part of the story",
            "opening": "Bed topography, geothermal heat, basal water, and glacial isostatic adjustment shape how the ice sheet responds.",
            "modes": {
                "Past": [
                    {"id": "Tectonic Template", "type": "Deep control", "x": 16, "y": 42, "note": "Rifting, basins, and mountains created the bed geometry on which ice evolves.", "evidence": "Geophysics - bed maps"},
                    {"id": "Dynamic Topography", "type": "Long-term change", "x": 38, "y": 30, "note": "Mantle-driven uplift or subsidence can alter vulnerability over million-year scales.", "evidence": "Mantle circulation models"},
                    {"id": "Past Loading", "type": "GIA memory", "x": 61, "y": 47, "note": "The solid Earth continues to respond to past ice loading changes.", "evidence": "Relative sea level - GPS"},
                    {"id": "Paleo Boundary", "type": "Model input", "x": 81, "y": 35, "note": "Past topography and sea level affect reconstructions of AIS history.", "evidence": "Ice-sheet + GIA models"}
                ],
                "Present": [
                    {"id": "Bed Topography", "type": "Boundary", "x": 16, "y": 34, "note": "Retrograde beds and subglacial basins affect grounding-line stability.", "evidence": "Radar - BEDMAP-style products"},
                    {"id": "Geothermal Heat", "type": "Basal energy", "x": 36, "y": 51, "note": "Heat from below can produce basal meltwater and influence sliding.", "evidence": "Magnetic/seismic heat-flux estimates"},
                    {"id": "Subglacial Hydrology", "type": "Basal water", "x": 58, "y": 34, "note": "Water beneath the ice can lubricate the bed and connect interior ice to shelf cavities.", "evidence": "Radar - altimetry lake drainage"},
                    {"id": "GIA Correction", "type": "Observation need", "x": 80, "y": 49, "note": "Gravity-based mass estimates require correction for solid-Earth motion.", "evidence": "GRACE - GPS/GNSS"}
                ],
                "Future": [
                    {"id": "Bedrock Uplift", "type": "Feedback", "x": 17, "y": 46, "note": "Ice loss can trigger bedrock uplift and local sea-level fall near grounding lines.", "evidence": "GIA theory - GPS"},
                    {"id": "Relative Sea Level", "type": "Stabilizer", "x": 39, "y": 31, "note": "Local sea-level fall can slow retreat in some settings.", "evidence": "Coupled sea-level models"},
                    {"id": "3D Earth Structure", "type": "Uncertainty", "x": 61, "y": 49, "note": "Viscosity varies strongly across Antarctica, affecting feedback timing.", "evidence": "Seismology - geodesy"},
                    {"id": "Coupled Projection", "type": "Model frontier", "x": 82, "y": 35, "note": "Future projections need ice, ocean, atmosphere, and solid Earth coupling.", "evidence": "Coupled model development"}
                ]
            }
        }
    }

    story_col, lens_col = st.columns([0.58, 0.42], gap="small")
    with story_col:
        story_topic = st.selectbox("Choose story", list(story_bank.keys()), key="visualizer_story_topic")
    with lens_col:
        time_mode = st.radio("Lens", ["Past", "Present", "Future"], horizontal=True, key="visualizer_time_lens")

    current_story = story_bank[story_topic]
    story_payload = {
        "topic": story_topic,
        "subtitle": current_story["subtitle"],
        "opening": current_story["opening"],
        "mode": time_mode,
        "nodes": current_story["modes"][time_mode]
    }

    story_html = r'''
    <div id="ai-story-root">
      <style>
        #ai-story-root { width: 100%; height: 690px; position: relative; overflow: hidden; border-radius: 32px; isolation:isolate; color: #eef8ff; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: radial-gradient(circle at 18% 18%, rgba(78,163,241,.26), transparent 28%), radial-gradient(circle at 78% 72%, rgba(149,117,205,.22), transparent 30%), radial-gradient(circle at 50% 52%, rgba(185,242,255,.10), transparent 25%), linear-gradient(135deg, #030712 0%, #07111f 47%, #020617 100%); background-size:135% 135%, 150% 150%, 120% 120%, 100% 100%; box-shadow: inset 0 0 105px rgba(78,163,241,.14), 0 26px 82px rgba(0,0,0,.34); animation:aiNebulaDrift 24s ease-in-out infinite; }
        #ai-story-root * { box-sizing: border-box; }
        #ai-story-root::before,
        #ai-story-root::after { content:""; position:absolute; inset:-18%; pointer-events:none; z-index:1; }
        #ai-story-root::before { background:linear-gradient(115deg, transparent 8%, rgba(255,255,255,.055) 37%, rgba(126,220,255,.10) 48%, transparent 62%); mix-blend-mode:screen; opacity:.70; animation:aiGlassDrift 12s ease-in-out infinite; }
        #ai-story-root::after { background:radial-gradient(ellipse at 52% 52%, transparent 34%, rgba(2,6,23,.34) 84%); z-index:1; }
        .ai-v-star { position:absolute; width:2px; height:2px; border-radius:50%; background:rgba(255,255,255,.72); box-shadow:0 0 10px rgba(255,255,255,.65); animation:aiTwinkle 3.8s infinite ease-in-out alternate; }
        @keyframes aiTwinkle { from { opacity:.22; transform:scale(.7); } to { opacity:.95; transform:scale(1.35); } }
        @keyframes aiNebulaDrift { 0%,100% { background-position:0% 0%, 100% 92%, 50% 50%, 0 0; } 50% { background-position:8% 6%, 91% 80%, 44% 56%, 0 0; } }
        @keyframes aiGlassDrift { 0%,100% { transform:translateX(-8%) rotate(-3deg); opacity:.52; } 50% { transform:translateX(8%) rotate(3deg); opacity:.86; } }
        @keyframes aiPanelIn { from { opacity:0; transform:translateY(12px) scale(.985); } to { opacity:1; transform:translateY(0) scale(1); } }
        @keyframes aiStageFloat { 0%,100% { transform:translate3d(0,0,0); } 50% { transform:translate3d(0,-5px,0); } }
        .ai-story-title { position:absolute; left:24px; top:62px; width: 430px; z-index:10; overflow:hidden; padding:18px 20px; border-radius:24px; border:1px solid rgba(210,238,255,.22); background:radial-gradient(circle at 14% 0%, rgba(255,255,255,.12), transparent 34%), linear-gradient(180deg, rgba(14,27,49,.66), rgba(4,12,25,.42)); backdrop-filter: blur(22px) saturate(1.32); box-shadow:inset 0 1px 0 rgba(255,255,255,.13), 0 18px 48px rgba(0,0,0,.18); animation:aiPanelIn .38s cubic-bezier(.2,.8,.2,1) both; }
        .ai-story-title::before { content:""; position:absolute; inset:-80% -35%; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.11) 38%, rgba(126,220,255,.18) 48%, transparent 66%); transform:translateX(-28%) rotate(10deg); opacity:.62; pointer-events:none; }
        .ai-story-title .kicker { color:#8dd8ff; font-size:12px; letter-spacing:1.2px; text-transform:uppercase; font-weight:850; }
        .ai-story-title h2 { margin:7px 0 5px 0; font-size:28px; letter-spacing:0; color:#fff; }
        .ai-story-title p { margin:0; color:rgba(231,245,255,.75); font-size:13px; line-height:1.42; }
        .ai-story-stage { position:absolute; left:24px; top:225px; width: calc(100% - 372px); height: 438px; z-index:5; border-radius:28px; border:1px solid rgba(210,238,255,.20); overflow:hidden; background: radial-gradient(ellipse at 46% 50%, rgba(223,249,255,.12), transparent 55%), linear-gradient(180deg, rgba(8,19,36,.52), rgba(2,6,23,.26)); box-shadow:inset 0 1px 0 rgba(255,255,255,.10), 0 20px 56px rgba(0,0,0,.22); animation:aiPanelIn .44s cubic-bezier(.2,.8,.2,1) both; }
        .ai-story-stage::before { content:""; position:absolute; inset:-60% -30%; z-index:3; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.08) 38%, rgba(126,220,255,.12) 48%, transparent 66%); opacity:.54; transform:translateX(-24%) rotate(10deg); pointer-events:none; }
        .ai-stage-bg { position:absolute; inset:0; background: radial-gradient(ellipse at 30% 66%, rgba(248,252,255,.78), rgba(180,220,235,.34) 25%, transparent 52%), radial-gradient(ellipse at 75% 70%, rgba(55,160,190,.20), transparent 42%), linear-gradient(180deg, rgba(45,125,170,.06), rgba(0,0,0,.05)); opacity:.78; animation:aiStageFloat 7s ease-in-out infinite; }
        .ai-stage-bg::before { content:""; position:absolute; left:-8%; right:-8%; bottom:58px; height:128px; background:linear-gradient(180deg, rgba(255,255,255,.72), rgba(185,230,242,.44)); clip-path: polygon(0% 62%, 10% 47%, 21% 54%, 32% 30%, 45% 48%, 57% 28%, 70% 46%, 83% 25%, 100% 52%, 100% 100%, 0% 100%); filter: drop-shadow(0 0 20px rgba(170,240,255,.20)); }
        .ai-stage-bg::after { content:""; position:absolute; left:0; right:0; bottom:0; height:104px; background:linear-gradient(180deg, rgba(46,160,205,.35), rgba(4,30,55,.80)); }
        #ai-story-svg { position:absolute; inset:0; width:100%; height:100%; z-index:4; }
        .ai-controls { position:absolute; left:22px; top:18px; z-index:12; display:flex; gap:10px; align-items:center; }
        .ai-controls button { position:relative; overflow:hidden; border:1px solid rgba(180,230,255,.34); border-radius:999px; padding:9px 14px; background:linear-gradient(180deg, rgba(17,35,62,.72), rgba(2,6,23,.54)); color:#eaf8ff; font-weight:850; cursor:pointer; box-shadow:0 10px 24px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.12); backdrop-filter:blur(14px); transition:transform .16s ease, border-color .16s ease, background .16s ease; }
        .ai-controls button::before { content:""; position:absolute; inset:-70% -35%; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.14) 38%, rgba(126,220,255,.22) 48%, transparent 66%); transform:translateX(-130%) rotate(10deg); opacity:0; pointer-events:none; }
        .ai-controls button:hover { transform:translateY(-1px); background:rgba(56,189,248,.20); border-color:rgba(186,230,253,.72); }
        .ai-controls button:hover::before { animation:aiButtonSheen .75s cubic-bezier(.2,.8,.2,1); }
        @keyframes aiButtonSheen { from { transform:translateX(-130%) rotate(10deg); opacity:0; } 28% { opacity:1; } to { transform:translateX(130%) rotate(10deg); opacity:0; } }
        .ai-progress { width:160px; height:7px; border-radius:999px; background:rgba(255,255,255,.12); overflow:hidden; border:1px solid rgba(255,255,255,.12); }
        .ai-progress span { display:block; height:100%; width:0%; background:linear-gradient(90deg, #6edcff, #d8f7ff); border-radius:999px; transition:width .3s ease; }
        .ai-side-panel { position:absolute; right:24px; top:62px; width:320px; height:601px; z-index:10; overflow:hidden; padding:20px; border-radius:28px; border:1px solid rgba(210,238,255,.30); background:radial-gradient(circle at 12% 0%, rgba(255,255,255,.12), transparent 34%), linear-gradient(180deg, rgba(12,25,46,.90), rgba(5,13,27,.70)); backdrop-filter: blur(24px) saturate(1.38); box-shadow:0 24px 74px rgba(0,0,0,.40), inset 0 1px 0 rgba(255,255,255,.14), inset 0 -1px 0 rgba(126,220,255,.08); animation:aiPanelIn .46s cubic-bezier(.2,.8,.2,1) both; }
        .ai-side-panel::before { content:""; position:absolute; inset:-70% -35%; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.11) 38%, rgba(126,220,255,.18) 48%, transparent 66%); transform:translateX(-30%) rotate(10deg); opacity:.40; pointer-events:none; }
        .ai-panel-badge { display:inline-flex; padding:7px 11px; border-radius:999px; color:#bfe6ff; background:rgba(78,163,241,.14); border:1px solid rgba(142,207,255,.25); font-size:12px; font-weight:850; }
        .ai-side-panel h3 { margin:15px 0 9px 0; font-size:24px; line-height:1.15; color:#fff; }
        .ai-side-panel .muted { color:rgba(235,248,255,.72); font-size:13px; line-height:1.45; }
        .ai-label { margin-top:16px; color:#8ccfff; font-size:11px; text-transform:uppercase; letter-spacing:1px; font-weight:850; }
        .ai-value { margin-top:6px; color:rgba(239,248,255,.88); line-height:1.45; font-size:13px; }
        .ai-mini-grid { display:grid; grid-template-columns:1fr 1fr; gap:9px; margin-top:16px; }
        .ai-mini-card { padding:10px; min-height:70px; border-radius:15px; border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.055); box-shadow:inset 0 1px 0 rgba(255,255,255,.06); }
        .ai-mini-card b { color:#fff; font-size:13px; }
        .ai-mini-card div { margin-top:5px; color:rgba(230,245,255,.70); font-size:12px; line-height:1.3; }
        .ai-slide-box { margin-top:16px; padding:13px; border-radius:17px; background:rgba(34,197,94,.09); border:1px solid rgba(74,222,128,.22); color:rgba(235,255,242,.88); font-size:13px; line-height:1.45; }
        .ai-node { cursor:pointer; opacity:0; transition:opacity .45s ease; }
        .ai-node .halo, .ai-node .core { transform-box:fill-box; transform-origin:center; }
        .ai-node .halo { fill:rgba(150,225,255,.12); stroke:rgba(160,230,255,.35); stroke-width:1.2; animation:aiBreath 2.8s ease-in-out infinite; }
        .ai-node .core { stroke:rgba(255,255,255,.82); stroke-width:1.6; filter:drop-shadow(0 0 18px rgba(126,220,255,.58)); }
        .ai-node text { pointer-events:none; text-anchor:middle; font-weight:850; fill:#f8fdff; paint-order:stroke; stroke:rgba(2,6,23,.92); stroke-width:4px; stroke-linejoin:round; }
        .ai-node.visible { opacity:1; }
        .ai-node.visible .core { animation:aiCorePop .38s cubic-bezier(.2,.8,.2,1) both; }
        .ai-node.active .halo { fill:rgba(255,255,255,.18); stroke:rgba(255,255,255,.82); stroke-width:2.4; }
        .ai-node.active .core { filter:drop-shadow(0 0 32px rgba(255,255,255,.95)); }
        .ai-link { opacity:0; stroke:rgba(160,225,255,.65); stroke-width:2.6; stroke-linecap:round; stroke-dasharray:8 9; filter:drop-shadow(0 0 8px rgba(120,220,255,.35)); transition:opacity .45s ease; }
        .ai-link.visible { opacity:.95; animation:dashMove 1.4s linear infinite; }
        @keyframes dashMove { to { stroke-dashoffset:-34; } }
        @keyframes aiBreath { 0%,100% { transform:scale(1); opacity:.70; } 50% { transform:scale(1.18); opacity:1; } }
        @keyframes aiCorePop { from { transform:scale(.72); opacity:.55; } to { transform:scale(1); opacity:1; } }
        .ai-caption { position:absolute; left:50%; transform:translateX(-50%); bottom:88px; z-index:8; width:min(640px, 72%); padding:12px 15px; border-radius:18px; border:1px solid rgba(255,255,255,.16); background:rgba(2,6,23,.52); box-shadow:0 14px 34px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.08); color:rgba(239,248,255,.84); font-size:13px; line-height:1.45; text-align:center; backdrop-filter:blur(14px) saturate(1.25); }
      </style>
      <div class="ai-story-title"><div class="kicker">Scientific Story Engine - __MODE__ lens</div><h2>__TOPIC__</h2><p><b>__SUBTITLE__</b><br>__OPENING__</p></div>
      <div class="ai-story-stage"><div class="ai-stage-bg"></div><svg id="ai-story-svg" viewBox="0 0 900 470" preserveAspectRatio="xMidYMid meet"></svg><div class="ai-caption" id="ai-caption">Click Begin Story to reveal the mechanism step by step, or click any glowing node to inspect its evidence card.</div><div class="ai-controls"><button id="ai-play">Begin Story</button><button id="ai-reset">Reset</button><div class="ai-progress"><span id="ai-progress-bar"></span></div></div></div>
      <div class="ai-side-panel" id="ai-side-panel"></div>
    </div>
    <script>
    (function(){
      const payload = __PAYLOAD__; const root = document.getElementById('ai-story-root'); const svg = document.getElementById('ai-story-svg'); const panel = document.getElementById('ai-side-panel'); const caption = document.getElementById('ai-caption'); const bar = document.getElementById('ai-progress-bar'); const NS = 'http://www.w3.org/2000/svg'; let step = -1; let timer = null;
      const typeColors = {'Ocean':'#4EA3F1','Ice shelf':'#B8F2FF','Ice Dynamics':'#7BDFF2','Ice dynamics':'#7BDFF2','Observation':'#9575CD','Atmosphere':'#A7C7E7','Hydrology':'#58D5FF','Fracture':'#FF8A65','Instability':'#FFB067','Debated mechanism':'#FFB067','Impact':'#CDB4DB','Forcing':'#F6C85F','Uncertainty':'#FFD166','Earth system':'#9CCC65','Boundary':'#C19A6B','Solid Earth':'#C19A6B','Basal water':'#79E0EE','Basal energy':'#F6C85F','Observation need':'#9575CD','Feedback':'#9CCC65','Stabilizer':'#9CCC65','Model frontier':'#CDB4DB','Paleo evidence':'#F6C85F','Paleo ice':'#F6C85F','Paleo ocean':'#4EA3F1','Research use':'#CDB4DB','Model constraint':'#CDB4DB','Landscape memory':'#C19A6B','Boundary condition':'#C19A6B','Ice response':'#7BDFF2','Deep control':'#C19A6B','Long-term change':'#9CCC65','GIA memory':'#9CCC65','Model input':'#CDB4DB','Amplification':'#FFB067','Risk':'#FFB067','Climate context':'#A7C7E7','Paleo state':'#F6C85F'};
      for (let i=0; i<90; i++) { const s = document.createElement('div'); s.className='ai-v-star'; s.style.left = Math.random()*100 + '%'; s.style.top = Math.random()*100 + '%'; s.style.animationDelay = Math.random()*4 + 's'; root.appendChild(s); }
      function el(name, attrs={}) { const e=document.createElementNS(NS,name); Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v)); return e; }
      function esc(t){ return String(t ?? '').replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[m])); }
      function wrapText(g, text, x, y, width, fs) { const words = String(text).split(/\s+/); let line='', lines=[]; words.forEach(w => { const test = line ? line + ' ' + w : w; if (test.length > width && line) { lines.push(line); line=w; } else line=test; }); if (line) lines.push(line); const t = el('text', {x:x, y:y, 'font-size':fs}); lines.slice(0,2).forEach((ln,i)=>{ const sp=el('tspan', {x:x, dy:i? '1.15em':'0'}); sp.textContent=ln; t.appendChild(sp); }); g.appendChild(t); }
      function nodeXY(n){ return {x:n.x*9, y:n.y*4.7}; }
      const defs = el('defs'); defs.innerHTML = `<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="rgba(190,240,255,.85)" /></marker>`; svg.appendChild(defs);
      const linkLayer = el('g'); const nodeLayer = el('g'); svg.appendChild(linkLayer); svg.appendChild(nodeLayer); const links = [];
      for(let i=0; i<payload.nodes.length-1; i++) { const a=nodeXY(payload.nodes[i]), b=nodeXY(payload.nodes[i+1]); const path = el('path', {class:'ai-link', d:`M ${a.x} ${a.y} C ${(a.x+b.x)/2} ${a.y-70}, ${(a.x+b.x)/2} ${b.y+70}, ${b.x} ${b.y}`, markerEnd:'url(#arrow)'}); path.dataset.index=i; linkLayer.appendChild(path); links.push(path); }
      const nodeEls = payload.nodes.map((n,i)=>{ const p=nodeXY(n), color=typeColors[n.type] || '#9EDBFF'; const g=el('g', {class:'ai-node', transform:`translate(${p.x},${p.y})`}); g.dataset.index=i; g.appendChild(el('circle', {class:'halo', r:50})); g.appendChild(el('circle', {class:'core', r:28, fill:color, 'fill-opacity':.88})); wrapText(g, n.id, 0, 5, 18, 13); g.addEventListener('click', ()=>revealTo(i)); nodeLayer.appendChild(g); return g; });
      function panelHtml(n, idx){ const chain = payload.nodes.map(x=>x.id).join(' \u2192 '); return `<span class="ai-panel-badge">${esc(payload.mode)} - ${esc(n.type)}</span><h3>${esc(n.id)}</h3><div class="muted">Node ${idx+1} of ${payload.nodes.length} in <b>${esc(payload.topic)}</b>.</div><div class="ai-label">Scientific meaning</div><div class="ai-value">${esc(n.note)}</div><div class="ai-label">Evidence layer</div><div class="ai-value">${esc(n.evidence)}</div><div class="ai-mini-grid"><div class="ai-mini-card"><b>Use in slides</b><div>Turn this node into one visual beat in a talk.</div></div><div class="ai-mini-card"><b>Reading logic</b><div>Connect mechanism, observation, and uncertainty.</div></div></div><div class="ai-slide-box"><b>Slide-ready chain</b><br>${esc(chain)}</div>`; }
      function revealTo(idx){ const safeIdx = Math.max(0, Math.min(idx, payload.nodes.length - 1)); step = safeIdx; nodeEls.forEach((g,i)=>{ g.classList.toggle('visible', i<=safeIdx); g.classList.toggle('active', i===safeIdx); }); links.forEach((l,i)=>l.classList.toggle('visible', i<safeIdx)); const n=payload.nodes[safeIdx]; panel.innerHTML = panelHtml(n, safeIdx); caption.innerHTML = `<b>${esc(n.id)}</b>  - ${esc(n.note)}`; bar.style.width = `${((safeIdx+1)/payload.nodes.length)*100}%`; }
      function reset(){ step=-1; if(timer) clearInterval(timer); timer=null; document.getElementById('ai-play').textContent='Begin Story'; nodeEls.forEach(g=>{g.classList.remove('visible','active');}); links.forEach(l=>l.classList.remove('visible')); bar.style.width='0%'; caption.innerHTML='Click Begin Story to reveal the mechanism step by step, or click any glowing node to inspect its evidence card.'; panel.innerHTML = `<span class="ai-panel-badge">Scientific Story Engine</span><h3>${esc(payload.topic)}</h3><div class="muted">${esc(payload.opening)}</div><div class="ai-label">Current lens</div><div class="ai-value">${esc(payload.mode)} - ${payload.nodes.length} story beats</div><div class="ai-slide-box"><b>How to use this module</b><br>Press Begin Story, then use each glowing node as one step of a scientific explanation. The right card gives the short interpretation and evidence layer.</div>`; }
      document.getElementById('ai-play').onclick = function(){ if(timer) clearInterval(timer); this.textContent='Playing'; revealTo(0); timer=setInterval(()=>{ if(step >= payload.nodes.length-1){ clearInterval(timer); timer=null; revealTo(payload.nodes.length-1); document.getElementById('ai-play').textContent='Replay Story'; return; } revealTo(step+1); }, 1150); };
      document.getElementById('ai-reset').onclick = reset; reset();
    })();
    </script>
    '''
    story_html = story_html.replace("__PAYLOAD__", json.dumps(story_payload, ensure_ascii=False))
    story_html = story_html.replace("__TOPIC__", str(story_payload["topic"]))
    story_html = story_html.replace("__SUBTITLE__", str(story_payload["subtitle"]))
    story_html = story_html.replace("__OPENING__", str(story_payload["opening"]))
    story_html = story_html.replace("__MODE__", str(story_payload["mode"]))

    components.html(story_html, height=700, scrolling=False)

    st.caption("This is a curated scientific-story visualization based on the review-paper mechanisms. It is designed for explanation and presentation, not as a raw-data simulation.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Story", story_topic)
    c2.metric("Lens", time_mode)
    c3.metric("Story beats", len(story_payload["nodes"]))
    c4.metric("Output mode", "Interactive")

    st.divider()
    st.subheader("Slide-ready export text")
    chain_text = " → ".join([n["id"] for n in story_payload["nodes"]])
    slide_note = f"""Slide title: {story_topic}  - {time_mode}

Main message: {current_story['opening']}

Visual chain: {chain_text}

Speaker note: Use the animation as a step-by-step explanation. Each node represents one scientific beat; the right card links the beat to evidence such as satellite observations, ocean data, paleo records, or coupled models."""
    st.code(slide_note)

    with st.expander("Storyboard table", expanded=False):
        storyboard_df = pd.DataFrame([
            {"Stage": i + 1, "Node": n["id"], "System / Type": n["type"], "Meaning": n["note"], "Evidence": n["evidence"]}
            for i, n in enumerate(story_payload["nodes"])
        ])
        st.dataframe(storyboard_df, use_container_width=True, hide_index=True)
