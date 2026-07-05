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

def render_research_directions(pages, total_pages):
    st.markdown("""
    <style>
      .block-container { padding-top: 1.05rem !important; }

      /* Compact Research Compass header: keeps the first screen focused on the actual tool. */
      .directions-title-row {
        margin: 1.72rem 0 .55rem 0;
        padding: 10px 14px 11px 14px;
        border-radius: 20px;
        border: 1px solid rgba(170,215,255,.18);
        background:
          radial-gradient(circle at 18% 18%, rgba(78,163,241,.18), transparent 30%),
          radial-gradient(circle at 76% 58%, rgba(149,117,205,.14), transparent 32%),
          linear-gradient(135deg, rgba(3,7,18,.68), rgba(7,17,31,.44));
        box-shadow: inset 0 0 28px rgba(78,163,241,.045);
        display: flex;
        align-items: baseline;
        gap: 18px;
        flex-wrap: wrap;
      }
      .directions-title-row h1 {
        margin: 0;
        font-size: 2.18rem;
        line-height: 1.12;
        letter-spacing: 0;
        color: #f8fbff;
        white-space: nowrap;
      }
      .directions-title-row p {
        margin: 0;
        color: rgba(221,240,252,.74);
        font-size: .88rem;
        line-height: 1.28;
        max-width: 1120px;
      }
      .direction-card {
        padding: 14px 15px;
        border-radius: 18px;
        border: 1px solid rgba(170,215,255,.18);
        background: linear-gradient(180deg, rgba(8,18,34,.74), rgba(7,15,29,.48));
        box-shadow: inset 0 0 24px rgba(78,163,241,.05);
        min-height: 132px;
      }
      .direction-card .k {
        font-size: 11px;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #8ccfff;
        font-weight: 850;
        margin-bottom: 7px;
      }
      .direction-card h3 {
        margin: 0 0 8px 0;
        color: #f8fbff;
        font-size: 1.05rem;
        line-height: 1.25;
      }
      .direction-card p {
        margin: 0;
        color: rgba(235,248,255,.78);
        line-height: 1.43;
        font-size: .86rem;
      }
      .direction-chip-row { display:flex; flex-wrap:wrap; gap:7px; margin-top:10px; }
      .direction-chip {
        padding: 5px 9px;
        border-radius: 999px;
        border: 1px solid rgba(142,207,255,.22);
        background: rgba(78,163,241,.10);
        color: #c8edff;
        font-size: 12px;
        font-weight: 700;
      }
      .direction-metric-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin-bottom: 16px;
      }
      .direction-metric {
        position: relative;
        overflow: hidden;
        min-height: 96px;
        padding: 13px 14px;
        border-radius: 18px;
        border: 1px solid rgba(190,226,255,.18);
        background:
          radial-gradient(circle at 18% 0%, rgba(255,255,255,.10), transparent 34%),
          linear-gradient(180deg, rgba(17,35,62,.72), rgba(7,15,29,.50));
        box-shadow: inset 0 1px 0 rgba(255,255,255,.10), 0 16px 42px rgba(0,0,0,.18);
        backdrop-filter: blur(18px) saturate(1.28);
      }
      .direction-metric::before {
        content: "";
        position: absolute;
        inset: -80% -35%;
        background: linear-gradient(120deg, transparent 0%, rgba(255,255,255,.10) 38%, rgba(126,220,255,.16) 48%, transparent 66%);
        transform: translateX(-34%) rotate(10deg);
        opacity: .36;
        pointer-events: none;
      }
      .direction-metric .k {
        position: relative;
        color: rgba(235,248,255,.82);
        font-size: 12px;
        font-weight: 760;
      }
      .direction-metric .v {
        position: relative;
        margin-top: 8px;
        color: #fff;
        font-size: 1.75rem;
        line-height: 1;
        font-weight: 850;
      }
      .direction-metric .sub {
        position: relative;
        margin-top: 5px;
        color: rgba(220,236,248,.62);
        font-size: 12px;
        font-weight: 700;
      }
      .direction-metric .v.time {
        font-size: 1.05rem;
        line-height: 1.25;
        white-space: normal;
      }
      .direction-mini-note {
        padding: 11px 13px;
        border-radius: 16px;
        border: 1px solid rgba(74,222,128,.22);
        background: rgba(34,197,94,.09);
        color: rgba(234,255,241,.88);
        font-size: .86rem;
        line-height: 1.43;
      }
      .direction-output-box {
        padding: 14px 15px;
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,.12);
        background: rgba(255,255,255,.045);
        color: rgba(239,248,255,.88);
        line-height: 1.48;
        font-size: .90rem;
      }
      div[data-testid="stMetric"] {
        background: rgba(255,255,255,.035);
        border: 1px solid rgba(170,215,255,.11);
        padding: 10px 12px;
        border-radius: 16px;
      }
      /* Make controls tighter so compass content appears in the first screen. */
      div[data-testid="stSelectbox"], div[data-testid="stRadio"], div[data-testid="stSlider"] {
        margin-top: 0 !important;
        margin-bottom: .15rem !important;
      }
    </style>
    <div class="directions-title-row">
      <h1>&#129517; Research Compass</h1>
      <p>Explore frontier questions from the review paper: choose a theme, inspect uncertainty, connect regions and methods, then generate a starter research idea.</p>
    </div>
    """, unsafe_allow_html=True)

    research_directions = {
        "Ocean heat pathways": {
            "emoji": "*",
            "system": "Ocean-ice shelf interaction",
            "uncertainty": 92,
            "impact": 94,
            "observability": 58,
            "time_scale": "days ->decades",
            "regions": ["Amundsen Sea", "Bellingshausen Sea", "Totten Glacier", "Filchner-Ronne"],
            "methods": ["Ocean moorings", "AUV", "CTD", "High-resolution ocean models"],
            "core_question": "How does warm Circumpolar Deep Water cross the continental shelf and reach ice-shelf cavities?",
            "why_now": "The paper repeatedly points to warm ocean access as a central control on basal melting, but the exact pathways depend on winds, eddies, tides, bathymetry, and freshwater feedbacks.",
            "gap": "Cross-shelf heat transport is still hard to observe directly and difficult to represent in models at the right spatial scale.",
            "student_angle": "Build a conceptual or data-driven map linking bathymetric troughs, wind forcing, and glacier thinning hotspots.",
            "starter_questions": [
                "Which Antarctic margins are most exposed to warm-water access under changing winds?",
                "Can satellite-observed thinning be connected to likely ocean heat pathways?",
                "How does meltwater-driven stratification change the persistence of warm water beneath ice shelves?"
            ]
        },
        "Grounding-line instability": {
            "emoji": "*",
            "system": "Ice dynamics",
            "uncertainty": 88,
            "impact": 96,
            "observability": 64,
            "time_scale": "years ->centuries",
            "regions": ["Thwaites", "Pine Island", "Wilkes Basin", "Aurora Basin"],
            "methods": ["InSAR", "Satellite altimetry", "Radar sounding", "Ice-sheet models"],
            "core_question": "When does grounding-line retreat become self-sustaining on retrograde bed topography?",
            "why_now": "MISI links bed geometry, ice-shelf buttressing, and ocean forcing; it is one of the highest-impact mechanisms for future sea-level projections.",
            "gap": "The timing and reversibility of retreat depend on subglacial topography, basal friction, ocean melt parameterization, and solid-Earth feedbacks.",
            "student_angle": "Use a case-study comparison between Thwaites, Pine Island, and an East Antarctic basin to explain how bed geometry changes risk.",
            "starter_questions": [
                "Which bed geometries make retreat most sensitive to small melt-rate changes?",
                "How do pinning points delay or reorganize grounding-line retreat?",
                "Can InSAR-derived velocity changes be used as early signs of buttressing loss?"
            ]
        },
        "Ice-shelf fracture and calving": {
            "emoji": "*",
            "system": "Atmosphere-ice shelf coupling",
            "uncertainty": 85,
            "impact": 90,
            "observability": 70,
            "time_scale": "days ->years",
            "regions": ["Antarctic Peninsula", "Larsen B", "Wilkins", "Roi Baudouin"],
            "methods": ["Optical imagery", "SAR", "Surface melt mapping", "Fracture models"],
            "core_question": "How do surface melt, hydrofracturing, and calving change ice-shelf buttressing?",
            "why_now": "Surface hydrology and hydrofracture are crucial for understanding rapid shelf collapse and high-end sea-level risk, but MICI remains debated.",
            "gap": "Models still struggle to predict when fractures connect, when shelves collapse, and how quickly inland glaciers respond.",
            "student_angle": "Create a visual diagnostic framework that classifies ice shelves by meltwater ponding, crevasse density, and buttressing importance.",
            "starter_questions": [
                "Which surface-hydrology patterns indicate increasing hydrofracture vulnerability?",
                "How much passive shelf area can be lost before grounded ice accelerates?",
                "Can Larsen B-like collapse logic be generalized to other Antarctic shelves?"
            ]
        },
        "Subglacial water and basal sliding": {
            "emoji": "*",
            "system": "Subglacial hydrology",
            "uncertainty": 91,
            "impact": 82,
            "observability": 42,
            "time_scale": "hours ->millennia",
            "regions": ["Siple Coast", "Thwaites", "Byrd Glacier", "Subglacial lakes"],
            "methods": ["Radar", "Altimetry lake detection", "Boreholes", "Hydrology models"],
            "core_question": "How does water beneath the ice sheet control basal friction and ice velocity?",
            "why_now": "Basal water can lubricate the bed, drain through lakes and channels, and feed freshwater into ice-shelf cavities.",
            "gap": "The subglacial system is difficult to observe directly, so models often rely on simplified sliding laws and uncertain hydrological parameters.",
            "student_angle": "Compare distributed versus channelized drainage and explain how each could stabilize or destabilize ice flow.",
            "starter_questions": [
                "How do active subglacial lake drainage events change downstream velocity?",
                "What remote-sensing signatures indicate a switch from distributed to channelized flow?",
                "How should basal hydrology be represented in beginner-friendly ice-flow simulations?"
            ]
        },
        "Solid-Earth feedbacks": {
            "emoji": "*",
            "system": "Solid Earth-ice interaction",
            "uncertainty": 87,
            "impact": 84,
            "observability": 50,
            "time_scale": "decades ->millennia",
            "regions": ["West Antarctica", "Amundsen Sea", "Antarctic Peninsula", "East Antarctica"],
            "methods": ["GPS/GNSS", "GRACE correction", "Seismology", "GIA models"],
            "core_question": "Can bedrock uplift and sea-level fingerprints slow or reshape ice-sheet retreat?",
            "why_now": "GIA affects both observed mass-balance estimates and physical retreat feedbacks near grounding lines.",
            "gap": "Antarctic mantle viscosity varies in 3D, but many models still simplify Earth structure or lack enough geodetic constraints.",
            "student_angle": "Explain why the solid Earth is not just a correction term but an active feedback in ice-sheet stability.",
            "starter_questions": [
                "Where is rapid bedrock uplift most likely to slow grounding-line retreat?",
                "How sensitive are GRACE-derived mass trends to different GIA assumptions?",
                "Can regional GPS/GNSS constraints improve ice-sheet projection confidence?"
            ]
        },
        "Paleo constraints for future projections": {
            "emoji": "*",
            "system": "Past-future bridge",
            "uncertainty": 80,
            "impact": 88,
            "observability": 56,
            "time_scale": "centuries ->millions of years",
            "regions": ["Pliocene", "Last Interglacial", "Marine margins", "Ice-core sites"],
            "methods": ["Marine sediment cores", "Ice cores", "Sea-level records", "Model-data comparison"],
            "core_question": "How can past warm periods constrain future Antarctic sea-level contribution?",
            "why_now": "The satellite era is too short to reveal the full AIS response, so paleo records are essential for testing long-term sensitivity.",
            "gap": "Paleo sea-level and ice-extent reconstructions have large uncertainties, making it hard to validate specific model physics.",
            "student_angle": "Build a Past-Present-Future evidence chain showing what each archive can and cannot prove.",
            "starter_questions": [
                "Which past warm intervals are most useful analogs for future Antarctic change?",
                "How can paleo records test whether high-end collapse mechanisms are realistic?",
                "What uncertainty remains when using sea-level records to constrain AIS retreat?"
            ]
        },
        "AI-assisted Antarctic research": {
            "emoji": "*",
            "system": "AI + Earth observation",
            "uncertainty": 74,
            "impact": 78,
            "observability": 86,
            "time_scale": "now ->next decade",
            "regions": ["Remote sensing", "Literature synthesis", "Education", "Model workflows"],
            "methods": ["Knowledge graphs", "RAG", "Computer vision", "Interactive visualization"],
            "core_question": "How can AI help organize observations, literature, and model uncertainty without replacing scientific reasoning?",
            "why_now": "Your Atlas itself is a prototype: it turns a dense review paper into explorable knowledge maps, simulations, and paper-grounded Q&A.",
            "gap": "AI tools must remain source-grounded, uncertainty-aware, and connected to real observation and modeling workflows.",
            "student_angle": "Turn this project into a portfolio piece: an AI research assistant for Antarctic ice-sheet literature and remote-sensing reasoning.",
            "starter_questions": [
                "Can a knowledge graph help students navigate AIS mechanisms more effectively than a linear PDF?",
                "How can RAG systems cite paper passages while generating slide-ready scientific explanations?",
                "Can AI detect conceptual links between satellite observations and physical ice-sheet processes?"
            ]
        }
    }

    direction_names = list(research_directions.keys())
    if "directions_selected" not in st.session_state or st.session_state["directions_selected"] not in direction_names:
        st.session_state["directions_selected"] = direction_names[0]

    top_col, option_col = st.columns([0.72, 0.28], gap="large")
    with option_col:
        selected_direction = st.selectbox(
            "Choose a frontier direction",
            direction_names,
            key="directions_selected"
        )
        view_mode = st.radio(
            "View mode",
            ["Compass", "Timeline", "Region map", "Proposal builder"],
            horizontal=False,
            key="directions_view_mode"
        )
        emphasis = st.slider("Ambition level", 1, 5, 3, help="Higher ambition makes the generated research idea broader and more frontier-oriented.")

    selected_info = research_directions[selected_direction]

    with top_col:
        safe_time_scale = html.escape(selected_info["time_scale"]).replace("-&gt;", "&rarr; ")
        st.markdown(f"""
        <div class="direction-metric-grid">
          <div class="direction-metric"><div class="k">Impact</div><div class="v">{selected_info['impact']}</div><div class="sub">/ 100</div></div>
          <div class="direction-metric"><div class="k">Uncertainty</div><div class="v">{selected_info['uncertainty']}</div><div class="sub">/ 100</div></div>
          <div class="direction-metric"><div class="k">Observability</div><div class="v">{selected_info['observability']}</div><div class="sub">/ 100</div></div>
          <div class="direction-metric"><div class="k">Time scale</div><div class="v time">{safe_time_scale}</div></div>
        </div>
        """, unsafe_allow_html=True)

        card_a, card_b, card_c = st.columns([0.34, 0.33, 0.33], gap="small")
        with card_a:
            st.markdown(f"""
            <div class="direction-card">
              <div class="k">Selected frontier</div>
              <h3>{selected_info['emoji']} {selected_direction}</h3>
              <p><b>Core question:</b><br>{selected_info['core_question']}</p>
            </div>
            """, unsafe_allow_html=True)
        with card_b:
            st.markdown(f"""
            <div class="direction-card">
              <div class="k">Why it matters now</div>
              <h3>{selected_info['system']}</h3>
              <p>{selected_info['why_now']}</p>
            </div>
            """, unsafe_allow_html=True)
        with card_c:
            chip_html = "".join([f"<span class='direction-chip'>{m}</span>" for m in selected_info["methods"]])
            st.markdown(f"""
            <div class="direction-card">
              <div class="k">Useful methods</div>
              <h3>Observation + modeling toolkit</h3>
              <div class="direction-chip-row">{chip_html}</div>
            </div>
            """, unsafe_allow_html=True)

    # Plotly compass bubble map
    compass_df = pd.DataFrame([
        {
            "Direction": name,
            "Impact": meta["impact"],
            "Uncertainty": meta["uncertainty"],
            "Observability": meta["observability"],
            "System": meta["system"],
            "emoji": "*",
            "Selected": name == selected_direction,
            "Size": 20 + meta["impact"] * 0.55,
            "Label": f"{meta['emoji']} {name}"
        }
        for name, meta in research_directions.items()
    ])

    if view_mode == "Compass":
        fig = go.Figure()
        fig.add_shape(type="rect", x0=50, x1=100, y0=50, y1=100, fillcolor="rgba(255,180,90,0.08)", line=dict(width=0), layer="below")
        fig.add_shape(type="rect", x0=0, x1=50, y0=50, y1=100, fillcolor="rgba(100,180,255,0.06)", line=dict(width=0), layer="below")
        fig.add_shape(type="rect", x0=50, x1=100, y0=0, y1=50, fillcolor="rgba(120,255,180,0.055)", line=dict(width=0), layer="below")
        fig.add_trace(go.Scatter(
            x=compass_df["Uncertainty"],
            y=compass_df["Impact"],
            mode="markers+text",
            text=compass_df["Label"],
            textposition="top center",
            marker=dict(
                size=compass_df["Size"],
                color=compass_df["Observability"],
                colorscale="Blues",
                showscale=True,
                colorbar=dict(title="Observability"),
                line=dict(width=np.where(compass_df["Selected"], 4, 1), color=np.where(compass_df["Selected"], "white", "rgba(255,255,255,.45)")),
                opacity=np.where(compass_df["Selected"], 1.0, 0.72)
            ),
            customdata=np.stack([compass_df["System"], compass_df["Observability"]], axis=-1),
            hovertemplate="<b>%{text}</b><br>System: %{customdata[0]}<br>Uncertainty: %{x}/100<br>Impact: %{y}/100<br>Observability: %{customdata[1]}/100<extra></extra>"
        ))
        fig.add_annotation(x=78, y=96, text="High impact + high uncertainty = frontier zone", showarrow=False, font=dict(size=14))
        fig.update_layout(
            height=520,
            margin=dict(l=10, r=10, t=25, b=10),
            xaxis=dict(title="Scientific uncertainty", range=[35, 100], gridcolor="rgba(150,180,200,.16)"),
            yaxis=dict(title="Sea-level / Earth-system impact", range=[65, 100], gridcolor="rgba(150,180,200,.16)"),
            plot_bgcolor="rgba(3,7,18,0.15)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(240,248,255,.88)")
        )
        st.plotly_chart(fig, use_container_width=True, key="directions_compass_plot")
        st.markdown(f"""
        <div class="direction-mini-note">
          <b>How to read it:</b> directions in the upper-right are scientifically important but still uncertain. The selected item is highlighted; color indicates how directly observable the process is with current tools.
        </div>
        """, unsafe_allow_html=True)

    elif view_mode == "Timeline":
        timeline = pd.DataFrame([
            {"Stage": "Past evidence", "Position": 0, "Description": "Use paleo records to test whether the mechanism happened before.", "Direction": selected_direction},
            {"Stage": "Present observation", "Position": 1, "Description": "Use satellites, field data, and ocean/solid-Earth observations to identify active signals.", "Direction": selected_direction},
            {"Stage": "Process model", "Position": 2, "Description": "Represent the mechanism in physical or statistical models.", "Direction": selected_direction},
            {"Stage": "Coupled projection", "Position": 3, "Description": "Connect the mechanism to sea-level projections and uncertainty.", "Direction": selected_direction},
            {"Stage": "Research product", "Position": 4, "Description": "Turn the result into a map, figure, interactive tool, or proposal.", "Direction": selected_direction},
        ])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timeline["Position"], y=[1]*len(timeline), mode="lines+markers+text",
            text=timeline["Stage"], textposition="top center",
            marker=dict(size=[28, 32, 32, 32, 30], line=dict(width=2, color="white")),
            line=dict(width=5),
            hovertext=timeline["Description"], hovertemplate="<b>%{text}</b><br>%{hovertext}<extra></extra>"
        ))
        fig.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=45, b=20),
            xaxis=dict(visible=False, range=[-.35, 4.35]),
            yaxis=dict(visible=False, range=[0.6, 1.35]),
            plot_bgcolor="rgba(3,7,18,0.15)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(240,248,255,.88)")
        )
        st.plotly_chart(fig, use_container_width=True, key="directions_timeline_plot")
        st.markdown(f"""
        <div class="direction-output-box">
          <b>{selected_info['emoji']} {selected_direction} as a research pathway</b><br><br>
          1. Start from the paper's review of known mechanisms.<br>
          2. Identify the current observation gap: {selected_info['gap']}<br>
          3. Use methods such as {', '.join(selected_info['methods'][:3])}.<br>
          4. Convert the result into a figure, map, model comparison, or AI-assisted explainer.
        </div>
        """, unsafe_allow_html=True)

    elif view_mode == "Region map":
        region_coords = {
            "Amundsen Sea": (-74.5, -110), "Bellingshausen Sea": (-72, -85), "Totten Glacier": (-67, 116),
            "Filchner-Ronne": (-78, -55), "Thwaites": (-75.5, -106), "Pine Island": (-75, -100),
            "Wilkes Basin": (-70, 140), "Aurora Basin": (-72, 120), "Antarctic Peninsula": (-65, -62),
            "Larsen B": (-65.5, -61), "Wilkins": (-70, -73), "Roi Baudouin": (-70, 24),
            "Siple Coast": (-82, -150), "Byrd Glacier": (-80, 160), "Subglacial lakes": (-77, 105),
            "West Antarctica": (-78, -115), "East Antarctica": (-78, 80), "Marine margins": (-70, 30),
            "Ice-core sites": (-76, 20), "Remote sensing": (-75, 0), "Literature synthesis": (-74, 40),
            "Education": (-73, 80), "Model workflows": (-73, 120), "GRACE correction": (-76, -30)
        }
        rows = []
        for r in selected_info["regions"]:
            lat, lon = region_coords.get(r, (-75, 0))
            rows.append({"Region": r, "lat": lat, "lon": lon, "Direction": selected_direction})
        region_df = pd.DataFrame(rows)
        fig = go.Figure(go.Scattergeo(
            lat=region_df["lat"], lon=region_df["lon"], text=region_df["Region"],
            mode="markers+text", textposition="top center",
            marker=dict(size=18, color="deepskyblue", line=dict(width=2, color="white")),
            hovertemplate="<b>%{text}</b><br>Linked to: " + selected_direction + "<extra></extra>"
        ))
        fig.update_geos(
            projection_type="azimuthal equal area",
            projection_rotation=dict(lat=-90),
            lataxis_range=[-90, -55],
            showland=True, landcolor="rgb(235,245,250)",
            showocean=True, oceancolor="rgb(8,35,60)",
            showcountries=False, showcoastlines=True, coastlinecolor="rgba(80,120,140,.7)",
            bgcolor="rgba(0,0,0,0)"
        )
        fig.update_layout(
            height=520,
            margin=dict(l=0, r=0, t=18, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(240,248,255,.88)")
        )
        st.plotly_chart(fig, use_container_width=True, key="directions_region_map")
        st.caption("This is a conceptual region locator for research planning, not a precise GIS layer.")

    elif view_mode == "Proposal builder":
        q_options = selected_info["starter_questions"]
        chosen_q = st.selectbox("Choose a starter question", q_options, key="directions_starter_question")
        method_focus = st.multiselect("Methods to include", selected_info["methods"], default=selected_info["methods"][:2], key="directions_methods")
        region_focus = st.multiselect("Regions / evidence contexts", selected_info["regions"], default=selected_info["regions"][:2], key="directions_regions")
        ambition_text = {
            1: "a small class-project style literature synthesis",
            2: "a focused exploratory analysis",
            3: "a feasible undergraduate research proposal",
            4: "an ambitious portfolio project with visualization or modeling",
            5: "a high-end PhD-style frontier proposal"
        }[emphasis]
        proposal = f"""Title: {selected_info['emoji']} {selected_direction}: {chosen_q}

Research style: {ambition_text}

Motivation:
{selected_info['why_now']}

Knowledge gap:
{selected_info['gap']}

Possible approach:
Use {', '.join(method_focus) if method_focus else 'selected observations and models'} focused on {', '.join(region_focus) if region_focus else 'a suitable Antarctic case region'}. The goal is to connect mechanism, observation, and uncertainty rather than only summarize the paper.

Expected output:
1. A concept map of the mechanism.
2. A small evidence table linking observations to physical interpretation.
3. A visual figure or interactive module that explains the research direction.
4. A short uncertainty paragraph explaining what remains unknown.

Why this fits your Atlas:
{selected_info['student_angle']}"""
        st.text_area("Generated research proposal seed", proposal, height=430)
        st.download_button(
            "Download proposal seed as .txt",
            proposal,
            file_name=f"research_direction_{selected_direction.lower().replace(' ', '_').replace('-', '_')}.txt",
            mime="text/plain",
            use_container_width=True
        )

    st.divider()
    st.subheader("Research seed cards")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        st.markdown(f"""
        <div class="direction-output-box">
          <b>Key gap</b><br>{selected_info['gap']}<br><br>
          <b>Beginner-researcher angle</b><br>{selected_info['student_angle']}
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("**Starter questions**")
        for sq in selected_info["starter_questions"]:
            st.write(f"- {sq}")
