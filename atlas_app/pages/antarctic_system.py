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

def render_antarctic_system(pages, total_pages):
    st.markdown("""
    <style>
      /* Antarctic System Explorer: online-safe responsive controls. */
      .block-container {
        padding-top: 2.35rem !important;
      }
      h1, h2, h3 {
        margin-top: .38rem !important;
        margin-bottom: .38rem !important;
      }

      /* Keep controls compact without forcing columns into a single crowded strip. */
      div[data-testid="stVerticalBlock"] { gap: .20rem !important; }
      div[data-testid="stHorizontalBlock"] { gap: .55rem !important; }
      div[data-testid="stSelectbox"] { margin-top: 0 !important; }
      div[data-testid="stToggle"] {
        margin-top: 0 !important;
        padding-top: 0 !important;
        min-height: 1.9rem !important;
      }
      div[data-testid="stSelectbox"] > label {
        padding-bottom: .18rem !important;
      }
      div[data-testid="stSelectbox"] label,
      div[data-testid="stToggle"] label {
        margin-bottom: .34rem !important;
        font-size: .82rem !important;
        font-weight: 760 !important;
      }

      .system-title-row {
        display: flex;
        align-items: baseline;
        gap: 18px;
        margin: .95rem 0 .58rem 0;
        flex-wrap: wrap;
      }
      .system-title-row .system-title {
        margin: 0;
        color: #f8fbff;
        font-size: clamp(2.05rem, 4vw, 2.72rem);
        line-height: 1.18;
        font-weight: 800;
        letter-spacing: 0;
      }
      .system-title-row .system-inline-hint {
        color: rgba(188, 221, 239, .72);
        font-size: .84rem;
        line-height: 1.25;
        font-weight: 500;
        max-width: 980px;
      }
      .system-control-strip {
        margin-top: .10rem;
        padding: 0;
        border-radius: 0;
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
      }
      .system-control-title {
        margin: .42rem 0 .34rem 0 !important;
        padding-bottom: .02rem !important;
        font-size: .84rem;
        font-weight: 850;
        letter-spacing: .01em;
        color: rgba(158, 216, 245, .82);
      }
      .system-layer-row {
        margin-top: .12rem !important;
        margin-left: 0 !important;
      }

      /* Observation layer buttons: compact translucent pills, equal width, deployment-safe. */
      div.stButton > button {
        min-height: 44px !important;
        height: 44px !important;
        border-radius: 999px !important;
        padding: .48rem .78rem !important;
        font-size: .84rem !important;
        line-height: 1.05 !important;
        font-weight: 780 !important;
        white-space: nowrap !important;
        background: rgba(56, 189, 248, 0.34) !important;
        border: 1px solid rgba(125, 211, 252, 0.58) !important;
        color: rgba(232, 250, 255, 0.98) !important;
        text-shadow: 0 0 6px rgba(255,255,255,0.15);
        box-shadow:
          0 0 4px rgba(56, 189, 248, 0.26),
          0 0 14px rgba(56, 189, 248, 0.18),
          inset 0 0 2px rgba(224,252,255,0.16);
        backdrop-filter: blur(8px);
        transition: all 0.16s ease !important;
      }
      div.stButton > button[kind="primary"] {
        background: rgba(56, 189, 248, 0.52) !important;
        border-color: rgba(186, 230, 253, 0.90) !important;
        box-shadow:
          0 0 8px rgba(56, 189, 248, 0.44),
          0 0 24px rgba(56, 189, 248, 0.30),
          inset 0 0 4px rgba(224,252,255,0.22) !important;
      }
      div.stButton > button:hover {
        background: rgba(14, 165, 233, 0.56) !important;
        border-color: rgba(186, 230, 253, 0.92) !important;
        transform: translateY(-1px);
      }

      /* Let the visualization start close to the controls without overlap. */
      iframe[title="streamlit_component.streamlit.components.v1.html"] {
        margin-top: .05rem !important;
      }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="system-title-row">
      <div class="system-title">&#128752; Antarctic System Explorer</div>
      <div class="system-inline-hint">
        Explore how different observation tools see the same Antarctic case study. Choose a glacier or ice-shelf case, then switch the sensor layer to see what that tool would reveal.
      </div>
    </div>
    """, unsafe_allow_html=True)

    cases = {
        "Thwaites Glacier": {
            "region": "West Antarctica / Amundsen Sea Sector",
            "type": "Fast outlet glacier",
            "main_theme": "Ocean-driven thinning, grounding-line retreat, and MISI-like vulnerability",
            "location_label": "Amundsen Sea Sector",
            "coords": "~75°S, 106°W",
            "base_note": "Thwaites is often discussed as one of the most vulnerable WAIS glaciers because warm ocean water can thin its ice shelf and reduce buttressing.",
            "visual_seed": "thwaites",
            "tools": {
                "Satellite Altimetry": {
                    "icon": "*",
                    "measures": "Surface elevation change",
                    "observed": "Surface lowering and dynamic thinning near the glacier trunk and grounding zone.",
                    "result": "The satellite-era record indicates strong thinning in the Amundsen Sea sector.",
                    "interpretation": "Lower surface elevation is consistent with ice-shelf thinning and faster discharge of grounded ice.",
                    "visual": "Laser/radar tracks scan across the glacier while a blue-to-red thinning layer appears over the trunk.",
                    "process": "Elevation loss ->thinner ice shelf ->weaker buttressing ->faster flow"
                },
                "InSAR Velocity": {
                    "icon": "*",
                    "measures": "Ice velocity and deformation",
                    "observed": "Fast flow and acceleration toward the floating ice shelf.",
                    "result": "Velocity patterns reveal where ice discharge is concentrated and where flow responds to buttressing loss.",
                    "interpretation": "Faster flow suggests reduced resistance near the grounding line and shelf front.",
                    "visual": "Orange velocity vectors appear over the glacier trunk and lengthen downstream.",
                    "process": "Phase difference ->displacement ->velocity field ->ice discharge"
                },
                "GRACE / GRACE-FO": {
                    "icon": "*",
                    "measures": "Regional mass change from gravity",
                    "observed": "Large-scale negative mass balance in West Antarctica.",
                    "result": "GRACE-like observations connect glacier change to regional mass loss.",
                    "interpretation": "Mass loss contributes to global mean sea-level rise, but requires GIA correction.",
                    "visual": "A broad red gravity-anomaly style field covers the regional basin.",
                    "process": "Gravity change ->mass balance ->sea-level contribution"
                },
                "GPS / GNSS": {
                    "icon": "*",
                    "measures": "Point motion and bedrock response",
                    "observed": "Sparse station-style points track crustal motion and local displacement.",
                    "result": "GNSS helps separate ice-mass change from solid-Earth motion.",
                    "interpretation": "This is important for constraining GIA and interpreting gravity-based mass estimates.",
                    "visual": "Station markers pulse, with small vectors showing motion/uplift.",
                    "process": "Station position ->crustal motion ->GIA correction"
                },
                "Ice-penetrating Radar": {
                    "icon": "*",
                    "measures": "Ice thickness, bed topography, internal layers",
                    "observed": "Bed geometry and possible retrograde slopes beneath the glacier system.",
                    "result": "Radar-style profiles reveal the hidden boundary conditions controlling retreat.",
                    "interpretation": "Bed topography determines whether retreat can become self-sustaining.",
                    "visual": "Radar flight lines and a glowing subglacial cross-section appear beneath the ice.",
                    "process": "Radar echo ->bed map ->instability assessment"
                },
                "Ice / Marine Sediment Cores": {
                    "icon": "*",
                    "measures": "Past climate and retreat history",
                    "observed": "Marine records help reconstruct previous grounding-line positions and retreat episodes.",
                    "result": "Paleo evidence extends interpretation beyond the short satellite era.",
                    "interpretation": "Past retreat provides context for how the system may respond to future forcing.",
                    "visual": "Core sites appear offshore, connected to a time-depth archive strip.",
                    "process": "Core record ->past retreat ->future sensitivity constraint"
                }
            }
        },
        "Pine Island Glacier": {
            "region": "West Antarctica / Amundsen Sea Sector",
            "type": "Fast outlet glacier",
            "main_theme": "CDW intrusion, ice-shelf thinning, grounding-line retreat",
            "location_label": "Pine Island Bay",
            "coords": "~75°S, 100°W",
            "base_note": "Pine Island Glacier is a classic example of rapid retreat linked to warm Circumpolar Deep Water reaching the ice-shelf cavity.",
            "visual_seed": "pine",
            "tools": {
                "Satellite Altimetry": {
                    "icon": "*",
                    "measures": "Surface elevation change",
                    "observed": "Strong thinning along the glacier and ice shelf.",
                    "result": "Altimetry-style evidence shows where surface lowering is concentrated.",
                    "interpretation": "Surface lowering reflects dynamic thinning and enhanced basal melting.",
                    "visual": "Repeated satellite tracks reveal a thinning corridor near the grounding zone.",
                    "process": "Repeated elevation profiles ->thinning map ->dynamic response"
                },
                "InSAR Velocity": {
                    "icon": "*",
                    "measures": "Ice velocity and grounding-zone motion",
                    "observed": "Fast outlet flow toward Pine Island Bay.",
                    "result": "Velocity vectors show the main discharge pathway.",
                    "interpretation": "Acceleration is consistent with reduced ice-shelf buttressing.",
                    "visual": "Dense downstream arrows highlight the fast-flowing trunk.",
                    "process": "SAR phase ->velocity ->ice discharge"
                },
                "GRACE / GRACE-FO": {
                    "icon": "*",
                    "measures": "Regional mass balance",
                    "observed": "Part of the broader Amundsen Sea mass-loss signal.",
                    "result": "Gravity change captures integrated regional loss rather than local glacier detail.",
                    "interpretation": "Useful for linking local dynamic change to total mass loss.",
                    "visual": "A basin-scale mass-loss halo overlays the map.",
                    "process": "Gravity anomaly ->regional mass trend ->sea-level signal"
                },
                "GPS / GNSS": {
                    "icon": "*",
                    "measures": "Bedrock and surface motion at stations",
                    "observed": "Point observations can help constrain solid-Earth response.",
                    "result": "GNSS is precise but spatially sparse.",
                    "interpretation": "Important for separating ice signals from bedrock uplift.",
                    "visual": "Station points blink at the margin with uplift arrows.",
                    "process": "Position time series ->uplift rate ->correction"
                },
                "Ice-penetrating Radar": {
                    "icon": "*",
                    "measures": "Bed and cavity geometry",
                    "observed": "Troughs and bed features that route ocean heat toward the grounding line.",
                    "result": "Radar and bathymetry reveal pathways for warm water access.",
                    "interpretation": "Geometry helps explain why Pine Island is sensitive to ocean forcing.",
                    "visual": "Subglacial troughs glow beneath the ice image.",
                    "process": "Bed sounding ->trough geometry ->ocean access pathway"
                },
                "Ice / Marine Sediment Cores": {
                    "icon": "*",
                    "measures": "Past retreat and ocean conditions",
                    "observed": "Marine archives record earlier ice-margin behavior in Pine Island Trough.",
                    "result": "Sediment evidence helps test whether retreat was rapid or episodic.",
                    "interpretation": "Past retreat constrains model scenarios for future instability.",
                    "visual": "Offshore core dots and a layered sediment strip appear.",
                    "process": "Sediment layers ->retreat history ->model constraint"
                }
            }
        },
        "Totten Glacier": {
            "region": "East Antarctica / Sabrina Coast",
            "type": "East Antarctic outlet glacier",
            "main_theme": "Warm water access to a marine-based EAIS sector",
            "location_label": "Sabrina Coast",
            "coords": "~67°S, 116°E",
            "base_note": "Totten Glacier shows that parts of East Antarctica can also be sensitive to ocean heat and marine-based bed geometry.",
            "visual_seed": "totten",
            "tools": {
                "Satellite Altimetry": {
                    "icon": "*",
                    "measures": "Surface height change",
                    "observed": "Surface lowering in a vulnerable East Antarctic outlet system.",
                    "result": "Altimetry helps detect whether EAIS outlet glaciers are thinning or thickening.",
                    "interpretation": "Thinning suggests ocean forcing can affect parts of East Antarctica too.",
                    "visual": "Satellite tracks cross an East Antarctic outlet with localized thinning colors.",
                    "process": "Elevation change ->outlet thinning ->EAIS vulnerability"
                },
                "InSAR Velocity": {
                    "icon": "*",
                    "measures": "Ice velocity",
                    "observed": "Fast flow through the Totten outlet toward the coast.",
                    "result": "InSAR-style velocity mapping identifies dynamic outlet behavior.",
                    "interpretation": "Flow pattern links inland catchment ice to coastal forcing.",
                    "visual": "Flow arrows converge toward the outlet glacier trunk.",
                    "process": "Velocity field ->discharge pathway ->dynamic thinning"
                },
                "GRACE / GRACE-FO": {
                    "icon": "*",
                    "measures": "Large-scale mass balance",
                    "observed": "EAIS mass change is harder to isolate because signals are broad and uncertain.",
                    "result": "GRACE provides continent-scale mass context but local attribution is limited.",
                    "interpretation": "Needs careful regional interpretation and GIA correction.",
                    "visual": "A broad, softer mass-balance field overlays the East Antarctic sector.",
                    "process": "Gravity trend ->regional mass estimate ->uncertainty"
                },
                "GPS / GNSS": {
                    "icon": "*",
                    "measures": "Crustal motion and vertical uplift",
                    "observed": "Sparse geodetic constraints for East Antarctic solid-Earth response.",
                    "result": "GNSS helps improve corrections to mass-balance estimates.",
                    "interpretation": "Especially important where mass-change signals are subtle.",
                    "visual": "Few station markers emphasize sparse but precise measurements.",
                    "process": "GNSS station ->uplift correction ->better mass estimate"
                },
                "Ice-penetrating Radar": {
                    "icon": "*",
                    "measures": "Ice thickness, bed, subglacial basin structure",
                    "observed": "Marine-based geometry and bed pathways beneath the outlet system.",
                    "result": "Radar is central for identifying hidden EAIS vulnerabilities.",
                    "interpretation": "Bed shape controls whether ocean-driven retreat can propagate inland.",
                    "visual": "A deep basin cross-section appears below the satellite-style surface.",
                    "process": "Radar profile ->marine basin ->retreat sensitivity"
                },
                "Ice / Marine Sediment Cores": {
                    "icon": "*",
                    "measures": "Past EAIS and ocean conditions",
                    "observed": "Marine sediment records can indicate past margin retreat and ocean warmth.",
                    "result": "Paleo data helps evaluate long-term East Antarctic sensitivity.",
                    "interpretation": "Useful because satellite records are too short for millennial-scale behavior.",
                    "visual": "Core archive marks appear along the continental shelf.",
                    "process": "Paleo archive ->warm-period behavior ->future analog"
                }
            }
        },
        "Larsen B Ice Shelf": {
            "region": "Antarctic Peninsula",
            "type": "Collapsed ice shelf",
            "main_theme": "Surface meltwater, hydrofracturing, and buttressing loss",
            "location_label": "Antarctic Peninsula",
            "coords": "~65°S, 61°W",
            "base_note": "Larsen B is a famous example of ice-shelf collapse followed by acceleration of tributary glaciers after buttressing was lost.",
            "visual_seed": "larsen",
            "tools": {
                "Satellite Altimetry": {
                    "icon": "*",
                    "measures": "Surface elevation before/after collapse",
                    "observed": "Elevation and surface morphology changed dramatically after shelf breakup.",
                    "result": "Altimetry-like monitoring helps quantify post-collapse glacier thinning.",
                    "interpretation": "After shelf loss, tributary glaciers can accelerate and thin.",
                    "visual": "Before/after scan lines reveal lowered tributary glacier surfaces.",
                    "process": "Ice-shelf loss ->tributary thinning ->reduced stability"
                },
                "InSAR Velocity": {
                    "icon": "*",
                    "measures": "Tributary glacier acceleration",
                    "observed": "Glaciers feeding the former shelf accelerated after collapse.",
                    "result": "Velocity mapping directly shows the dynamic impact of buttressing loss.",
                    "interpretation": "This is a clear example of why floating shelves matter for grounded ice.",
                    "visual": "Arrows behind the former shelf become longer and brighter.",
                    "process": "Shelf collapse ->lower back stress ->faster tributary flow"
                },
                "GRACE / GRACE-FO": {
                    "icon": "*",
                    "measures": "Regional mass change",
                    "observed": "Regional signal is smaller and harder to isolate than WAIS basin-scale loss.",
                    "result": "GRACE gives context but is not the primary local diagnostic here.",
                    "interpretation": "Better used with altimetry and velocity for this case.",
                    "visual": "A faint regional mass-change layer appears over the Peninsula.",
                    "process": "Regional gravity ->mass context ->multi-sensor interpretation"
                },
                "GPS / GNSS": {
                    "icon": "*",
                    "measures": "Local motion and crustal response",
                    "observed": "Point measurements can support local deformation and uplift context.",
                    "result": "GNSS is useful but sparse relative to satellite imagery.",
                    "interpretation": "Best interpreted together with optical/SAR records.",
                    "visual": "A few station vectors appear along the Peninsula.",
                    "process": "Station motion ->local deformation ->context"
                },
                "Ice-penetrating Radar": {
                    "icon": "*",
                    "measures": "Shelf and tributary geometry",
                    "observed": "Internal structure and thickness help explain shelf weakness and tributary response.",
                    "result": "Radar can support understanding of mechanical vulnerability.",
                    "interpretation": "Geometry and crevasse structure affect collapse potential.",
                    "visual": "Crack-like internal layers and radar profiles appear across the shelf.",
                    "process": "Internal structure ->fracture vulnerability ->collapse risk"
                },
                "Ice / Marine Sediment Cores": {
                    "icon": "*",
                    "measures": "Longer-term shelf and climate history",
                    "observed": "Records can help determine whether collapse was unusual in recent millennia.",
                    "result": "Paleo context tells whether modern breakup exceeds natural variability.",
                    "interpretation": "Important for connecting recent atmospheric warming to shelf stability.",
                    "visual": "Core archive appears near the shelf front and former embayment.",
                    "process": "Archive record ->shelf history ->modern anomaly"
                }
            }
        },
        "Wilkes Subglacial Basin": {
            "region": "East Antarctica",
            "type": "Marine-based subglacial basin",
            "main_theme": "Bed topography, marine-based ice, long-term sensitivity",
            "location_label": "Wilkes Land",
            "coords": "~70°S, 140°E",
            "base_note": "Wilkes Subglacial Basin is important because marine-based East Antarctic ice could be vulnerable if warming and bed geometry allow retreat to propagate inland.",
            "visual_seed": "wilkes",
            "tools": {
                "Satellite Altimetry": {
                    "icon": "*",
                    "measures": "Broad surface elevation trends",
                    "observed": "Surface elevation provides a first view of present-day change over a large basin.",
                    "result": "Altimetry helps detect whether the basin is stable, thinning, or thickening.",
                    "interpretation": "Present changes must be interpreted against snowfall and firn processes.",
                    "visual": "Wide satellite tracks sweep across the basin surface.",
                    "process": "Elevation trend ->basin-scale change ->mass-balance clue"
                },
                "InSAR Velocity": {
                    "icon": "*",
                    "measures": "Outlet velocity patterns",
                    "observed": "Velocity fields show where ice can drain from the basin toward the coast.",
                    "result": "InSAR identifies fast-flow corridors and outlet controls.",
                    "interpretation": "Flow pathways connect interior basin geometry to coastal vulnerability.",
                    "visual": "Flow arrows trace drainage from the basin toward the margin.",
                    "process": "Velocity map ->drainage structure ->discharge risk"
                },
                "GRACE / GRACE-FO": {
                    "icon": "*",
                    "measures": "Large-scale mass change",
                    "observed": "Broad gravity signals help monitor basin-scale mass balance.",
                    "result": "Spatial resolution is coarse, so interpretation is regional.",
                    "interpretation": "GIA correction is essential in East Antarctica.",
                    "visual": "A broad mass-balance wash appears across Wilkes Land.",
                    "process": "Gravity field ->basin mass trend ->GIA-sensitive estimate"
                },
                "GPS / GNSS": {
                    "icon": "*",
                    "measures": "Crustal uplift and solid-Earth correction",
                    "observed": "Sparse but valuable constraints on vertical bedrock motion.",
                    "result": "GNSS improves the correction needed for gravity-derived ice mass.",
                    "interpretation": "Important for reducing uncertainty in East Antarctic mass balance.",
                    "visual": "Uplift vectors appear as fixed station points over the basin margin.",
                    "process": "Uplift rate ->GIA model ->corrected ice mass"
                },
                "Ice-penetrating Radar": {
                    "icon": "*",
                    "measures": "Hidden basin geometry and bed slope",
                    "observed": "Deep subglacial basin and retrograde-bed style geometry.",
                    "result": "Radar is the most visually important tool for this case because the key feature is hidden beneath ice.",
                    "interpretation": "Bed topography controls long-term marine ice-sheet sensitivity.",
                    "visual": "A large glowing subglacial basin appears beneath the ice surface.",
                    "process": "Bed echo ->basin geometry ->marine instability potential"
                },
                "Ice / Marine Sediment Cores": {
                    "icon": "*",
                    "measures": "Past warm-period ice extent",
                    "observed": "Paleo records test whether marine-based EAIS sectors retreated in past warm climates.",
                    "result": "Core evidence helps constrain long-term sensitivity that satellites cannot capture.",
                    "interpretation": "Useful for Pliocene and interglacial analogs.",
                    "visual": "Archive markers connect the basin to past warm-period evidence.",
                    "process": "Past margin record ->warm-climate response ->future constraint"
                }
            }
        }
    }

    tool_order = ["Satellite Altimetry", "InSAR Velocity", "GRACE / GRACE-FO", "GPS / GNSS", "Ice-penetrating Radar", "Ice / Marine Sediment Cores"]

    layer_label_map = {
        "Satellite Altimetry": "Altimetry",
        "InSAR Velocity": "InSAR",
        "GRACE / GRACE-FO": "GRACE",
        "GPS / GNSS": "GNSS",
        "Ice-penetrating Radar": "Radar",
        "Ice / Marine Sediment Cores": "Cores"
    }

    if "system_tool_select" not in st.session_state or st.session_state["system_tool_select"] not in tool_order:
        st.session_state["system_tool_select"] = tool_order[0]
    if "system_visual_layers" not in st.session_state or not isinstance(st.session_state["system_visual_layers"], list):
        st.session_state["system_visual_layers"] = [st.session_state["system_tool_select"]]

    st.markdown("<div class='system-control-strip'>", unsafe_allow_html=True)
    st.caption("Conceptual visualization: the base scene and sensor layers illustrate observation logic, not downloaded raw remote-sensing data.")

    # Deployment-safe layout: keep Case Study and Multi-layer mode on the first row,
    # then give Observation layers a full row. This prevents Streamlit Cloud / browser
    # width differences from squeezing the toggle to the far right or overlapping pills.
    case_col, mode_col = st.columns([0.58, 0.42], gap="large")
    with case_col:
        selected_case = st.selectbox("Case Study", list(cases.keys()), key="system_case_select")
    with mode_col:
        layer_mode = st.toggle(
            "Multi-layer mode",
            value=False,
            key="system_multilayer_mode",
            help="Off: buttons choose the primary observation layer. On: buttons become multi-select visible layers."
        )

    st.markdown("<div class='system-control-title'>Observation layers</div>", unsafe_allow_html=True)
    st.markdown("<div class='system-layer-row'>", unsafe_allow_html=True)
    layer_cols = st.columns([1, 1, 1, 1, 1, 1], gap="small")
    for i, layer_name in enumerate(tool_order):
        with layer_cols[i]:
            if layer_mode:
                active = layer_name in st.session_state["system_visual_layers"]
                if st.button(
                    layer_label_map[layer_name],
                    key=f"system_layer_btn_multi_{i}",
                    type="primary" if active else "secondary",
                    use_container_width=True
                ):
                    current_layers = list(st.session_state.get("system_visual_layers", []))
                    if layer_name in current_layers:
                        current_layers = [x for x in current_layers if x != layer_name]
                    else:
                        current_layers.append(layer_name)
                    if not current_layers:
                        current_layers = [st.session_state["system_tool_select"]]
                    st.session_state["system_visual_layers"] = current_layers
                    st.rerun()
            else:
                active = layer_name == st.session_state["system_tool_select"]
                if st.button(
                    layer_label_map[layer_name],
                    key=f"system_layer_btn_single_{i}",
                    type="primary" if active else "secondary",
                    use_container_width=True
                ):
                    st.session_state["system_tool_select"] = layer_name
                    st.session_state["system_visual_layers"] = [layer_name]
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    selected_tool = st.session_state["system_tool_select"]
    if layer_mode:
        visual_layers = [layer for layer in st.session_state.get("system_visual_layers", []) if layer in tool_order]
        if not visual_layers:
            visual_layers = [selected_tool]
        if selected_tool not in visual_layers:
            selected_tool = visual_layers[0]
            st.session_state["system_tool_select"] = selected_tool
    else:
        visual_layers = [selected_tool]
        st.session_state["system_visual_layers"] = visual_layers

    case = cases[selected_case]
    tool = case["tools"][selected_tool]

    explorer_payload = {
        "case_name": selected_case,
        "case": case,
        "tool_name": selected_tool,
        "tool": tool,
        "tool_order": tool_order
    }

    explorer_html = """
    <div id="sensor-explorer-root">
      <style>
        #sensor-explorer-root {
          width: 100%; height: 655px; overflow: hidden; position: relative; border-radius: 32px; isolation:isolate;
          color: #edf8ff; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background:
            radial-gradient(circle at 20% 18%, rgba(78,163,241,.24), transparent 30%),
            radial-gradient(circle at 86% 20%, rgba(149,117,205,.18), transparent 26%),
            linear-gradient(135deg, #030712 0%, #07111f 48%, #020617 100%);
          background-size: 135% 135%, 150% 150%, 100% 100%;
          box-shadow: inset 0 0 100px rgba(78,163,241,.14), 0 26px 82px rgba(0,0,0,.34);
          animation: sensorNebulaDrift 24s ease-in-out infinite;
        }
        #sensor-explorer-root * { box-sizing: border-box; }
        #sensor-explorer-root::before,
        #sensor-explorer-root::after { content:""; position:absolute; inset:-18%; pointer-events:none; z-index:1; }
        #sensor-explorer-root::before {
          background:linear-gradient(115deg, transparent 8%, rgba(255,255,255,.055) 38%, rgba(126,220,255,.10) 49%, transparent 63%);
          mix-blend-mode:screen; opacity:.70; animation:sensorGlassDrift 13s ease-in-out infinite;
        }
        #sensor-explorer-root::after {
          background:radial-gradient(ellipse at 52% 52%, transparent 35%, rgba(2,6,23,.36) 84%);
          z-index:1;
        }
        @keyframes sensorNebulaDrift { 0%,100% { background-position:0% 0%, 100% 18%, 0 0; } 50% { background-position:8% 7%, 91% 26%, 0 0; } }
        @keyframes sensorGlassDrift { 0%,100% { transform:translateX(-7%) rotate(-3deg); opacity:.52; } 50% { transform:translateX(7%) rotate(3deg); opacity:.86; } }
        @keyframes sensorPanelIn { from { opacity:0; transform:translateY(12px) scale(.985); } to { opacity:1; transform:translateY(0) scale(1); } }
        .sensor-title {
          position:absolute; top:10px; left:22px; z-index:9;
          max-width: calc(100% - 44px); width: auto;
          display:flex; align-items:center; gap:16px;
          padding:9px 13px; border-radius:18px; overflow:hidden; background:radial-gradient(circle at 14% 0%, rgba(255,255,255,.10), transparent 34%), linear-gradient(180deg, rgba(14,27,49,.60), rgba(4,12,25,.40));
          border:1px solid rgba(210,238,255,.20); backdrop-filter: blur(18px) saturate(1.28);
          box-shadow:inset 0 1px 0 rgba(255,255,255,.12), 0 16px 44px rgba(0,0,0,.18);
          animation:sensorPanelIn .36s cubic-bezier(.2,.8,.2,1) both;
          white-space: nowrap;
        }
        .sensor-title h2 {
          margin:0;
          font-size:20px;
          letter-spacing:.2px;
          flex:0 0 auto;
          white-space:nowrap;
        }
        .sensor-title p {
          margin:0;
          color:rgba(230,245,255,.72);
          font-size:12px;
          line-height:1.1;
          white-space:nowrap;
          overflow:hidden;
          text-overflow:ellipsis;
        }
        .sat-frame {
          position:absolute; left:22px; top:62px; width:66%; height:570px; border-radius:26px; overflow:hidden;
          z-index:4; border:1px solid rgba(210,238,255,.22); background:#06111e;
          box-shadow: 0 24px 74px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.10), inset 0 0 62px rgba(110,210,255,.10);
          animation:sensorPanelIn .42s cubic-bezier(.2,.8,.2,1) both;
        }
        .sat-frame::before { content:""; position:absolute; inset:-60% -30%; z-index:2; pointer-events:none; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.08) 38%, rgba(126,220,255,.12) 48%, transparent 66%); opacity:.50; transform:translateX(-26%) rotate(10deg); }
        .sat-image {
          position:absolute; inset:0;
          background:
            radial-gradient(ellipse at 22% 36%, rgba(245,252,255,.92) 0%, rgba(205,232,244,.82) 20%, rgba(94,138,162,.20) 38%, transparent 55%),
            radial-gradient(ellipse at 58% 52%, rgba(255,255,255,.84) 0%, rgba(205,230,238,.55) 18%, rgba(45,88,118,.12) 45%, transparent 62%),
            radial-gradient(ellipse at 76% 64%, rgba(145,220,238,.24), transparent 34%),
            linear-gradient(135deg, #0b2940 0%, #163b52 35%, #081624 100%);
          filter: saturate(1.04) contrast(1.06);
        }
        .sat-image::before {
          content:""; position:absolute; inset:-20%; opacity:.26;
          background-image:
            repeating-linear-gradient(18deg, rgba(255,255,255,.20) 0 1px, transparent 1px 18px),
            repeating-linear-gradient(105deg, rgba(255,255,255,.10) 0 1px, transparent 1px 26px);
          transform: rotate(-2deg);
        }
        .sat-image::after {
          content:""; position:absolute; inset:0; opacity:.30; mix-blend-mode: screen;
          background: radial-gradient(circle at 50% 50%, transparent 0 38%, rgba(0,0,0,.55) 86%);
        }
        .case-thwaites .sat-image { background:
          radial-gradient(ellipse at 25% 40%, rgba(250,252,255,.95), rgba(209,232,242,.82) 22%, rgba(64,98,130,.14) 45%, transparent 64%),
          radial-gradient(ellipse at 72% 70%, rgba(0,110,155,.45), rgba(3,22,45,.88) 58%),
          linear-gradient(135deg, #092034, #13324b 46%, #03111f); }
        .case-pine .sat-image { background:
          radial-gradient(ellipse at 32% 42%, rgba(248,252,255,.96), rgba(215,236,246,.80) 24%, rgba(58,90,122,.20) 48%, transparent 64%),
          radial-gradient(ellipse at 78% 55%, rgba(52,160,194,.42), rgba(3,20,39,.88) 60%),
          linear-gradient(145deg, #082132, #153d55 48%, #061522); }
        .case-totten .sat-image { background:
          radial-gradient(ellipse at 68% 38%, rgba(250,252,255,.96), rgba(220,239,247,.78) 26%, rgba(65,100,128,.16) 50%, transparent 66%),
          radial-gradient(ellipse at 18% 70%, rgba(35,145,190,.42), rgba(4,23,44,.88) 60%),
          linear-gradient(135deg, #0d273b, #174058 48%, #061421); }
        .case-larsen .sat-image { background:
          radial-gradient(ellipse at 50% 48%, rgba(247,252,255,.94), rgba(200,228,238,.80) 18%, rgba(88,128,148,.24) 38%, transparent 54%),
          linear-gradient(100deg, #0b3148 0%, #194962 48%, #061421 100%); }
        .case-wilkes .sat-image { background:
          radial-gradient(ellipse at 52% 42%, rgba(250,252,255,.97), rgba(224,240,248,.82) 32%, rgba(73,105,128,.22) 58%, transparent 72%),
          radial-gradient(ellipse at 80% 74%, rgba(42,150,185,.34), transparent 45%),
          linear-gradient(135deg, #09233a, #13364d 52%, #04111d); }
        .glacier-outline {
          position:absolute; left:9%; top:12%; width:62%; height:76%; border-radius:60% 44% 46% 62%;
          border:2px solid rgba(255,255,255,.34); background:rgba(255,255,255,.045);
          box-shadow: inset 0 0 40px rgba(255,255,255,.10), 0 0 25px rgba(160,230,255,.10);
          transform: rotate(-10deg);
        }
        .case-larsen .glacier-outline { left:25%; width:36%; border-radius:28% 70% 55% 42%; transform:rotate(4deg); }
        .case-wilkes .glacier-outline { left:21%; top:15%; width:58%; height:72%; border-radius:50%; transform:rotate(0deg); }
        .ocean-label, .ice-label, .case-label {
          position:absolute; z-index:3; padding:7px 10px; border-radius:999px; font-size:12px;
          background:rgba(2,6,23,.50); border:1px solid rgba(210,238,255,.20); backdrop-filter: blur(12px) saturate(1.24);
          box-shadow:inset 0 1px 0 rgba(255,255,255,.08), 0 10px 24px rgba(0,0,0,.14);
        }
        .ice-label { left:48px; bottom:36px; }
        .ocean-label { right:40px; bottom:38px; color:#bdefff; }
        .case-label { left:48px; top:36px; color:#ffffff; }
        .overlay { position:absolute; inset:0; z-index:4; pointer-events:none; animation: layerFade .42s ease both; }
        .overlay > * { animation: layerFade .52s ease both; }
        @keyframes layerFade { from { opacity:0; transform:translateY(8px) scale(.985); } to { opacity:1; transform:translateY(0) scale(1); } }
        .orbit {
          position:absolute; left:8%; top:7%; width:38px; height:38px; border-radius:50%;
          background:linear-gradient(135deg, #e8fbff, #6fd4ff); box-shadow:0 0 24px rgba(120,220,255,.95);
          animation: satelliteOrbit 7s linear infinite;
        }
        .orbit::after { content:""; position:absolute; left:28px; top:17px; width:150px; height:2px; background:linear-gradient(90deg, rgba(165,235,255,.9), transparent); transform:rotate(10deg); }
        @keyframes satelliteOrbit { 0%{transform:translate(0,0)} 45%{transform:translate(610px,90px)} 100%{transform:translate(0,0)} }
        .altimetry .scan-line {
          position:absolute; top:-30%; width:3px; height:160%; background:linear-gradient(180deg, transparent, rgba(160,235,255,.95), transparent);
          box-shadow:0 0 16px rgba(128,220,255,.9); animation: scanDown 2.4s ease-in-out infinite;
        }
        .altimetry .scan-line:nth-child(1){left:25%; animation-delay:0s}.altimetry .scan-line:nth-child(2){left:42%; animation-delay:.35s}.altimetry .scan-line:nth-child(3){left:59%; animation-delay:.7s}
        @keyframes scanDown { 0%,100%{opacity:.25; transform:translateY(-18px)} 50%{opacity:1; transform:translateY(22px)} }
        .thinning-blob { position:absolute; left:37%; top:34%; width:220px; height:190px; border-radius:50%; background:radial-gradient(circle, rgba(255,100,55,.70), rgba(255,178,60,.38) 45%, transparent 72%); mix-blend-mode:screen; animation:pulse 2.2s ease-in-out infinite; }
        @keyframes pulse { 0%,100%{opacity:.45; transform:scale(.96)} 50%{opacity:.92; transform:scale(1.06)} }
        .insar .vel-arrow { position:absolute; height:4px; background:linear-gradient(90deg, rgba(255,170,55,.15), rgba(255,155,40,1)); border-radius:999px; box-shadow:0 0 12px rgba(255,145,40,.9); animation:flow 1.5s ease-in-out infinite; }
        .insar .vel-arrow::after { content:""; position:absolute; right:-7px; top:-5px; border-left:12px solid rgba(255,155,40,1); border-top:7px solid transparent; border-bottom:7px solid transparent; }
        .insar .a1{left:24%;top:38%;width:120px}.insar .a2{left:31%;top:48%;width:160px;animation-delay:.15s}.insar .a3{left:39%;top:58%;width:190px;animation-delay:.3s}.insar .a4{left:29%;top:64%;width:138px;animation-delay:.45s}
        @keyframes flow { 0%,100%{transform:translateX(-6px);opacity:.55} 50%{transform:translateX(12px);opacity:1} }
        .grace .mass-blob { position:absolute; left:20%; top:24%; width:430px; height:360px; border-radius:50%; background:radial-gradient(circle, rgba(255,68,68,.68), rgba(255,132,60,.42) 42%, rgba(0,120,255,.10) 68%, transparent 78%); filter:blur(2px); mix-blend-mode:screen; animation:pulse 2.8s ease-in-out infinite; }
        .gnss .station { position:absolute; width:16px; height:16px; border-radius:50%; background:#9dffb6; border:2px solid white; box-shadow:0 0 16px rgba(120,255,170,.9); animation:pulse 1.8s infinite; }
        .gnss .station::after { content:"→"; position:absolute; left:14px; top:-18px; color:#9dffb6; font-weight:900; font-size:22px; text-shadow:0 0 12px rgba(120,255,170,.95); }
        .gnss .s1{left:31%;top:42%}.gnss .s2{left:48%;top:57%;animation-delay:.3s}.gnss .s3{left:62%;top:36%;animation-delay:.6s}.gnss .s4{left:24%;top:66%;animation-delay:.9s}
        .radar .radar-line { position:absolute; height:3px; background:rgba(255,255,255,.80); box-shadow:0 0 16px rgba(255,255,255,.88); transform:rotate(-12deg); }
        .radar .r1{left:22%;top:34%;width:340px}.radar .r2{left:26%;top:50%;width:300px}.radar .r3{left:30%;top:65%;width:260px}
        .radar .basin { position:absolute; left:24%; bottom:58px; width:430px; height:92px; border-radius:0 0 60% 60%; border-bottom:4px solid rgba(255,214,82,.95); background:linear-gradient(180deg, transparent, rgba(255,214,82,.20)); box-shadow:0 18px 30px rgba(255,214,82,.25); }
        .cores .core-dot { position:absolute; width:18px; height:18px; border-radius:50%; background:#f6c85f; border:2px solid white; box-shadow:0 0 16px rgba(246,200,95,.9); }
        .cores .c1{left:68%;top:62%}.cores .c2{left:75%;top:50%}.cores .c3{left:61%;top:72%}
        .cores .archive { position:absolute; right:54px; top:88px; width:86px; height:250px; border-radius:14px; background:repeating-linear-gradient(180deg, rgba(255,255,255,.86) 0 18px, rgba(155,210,230,.82) 18px 35px, rgba(80,120,145,.70) 35px 52px); border:1px solid rgba(255,255,255,.55); box-shadow:0 0 20px rgba(255,255,255,.25); }
        .legend-pill { position:absolute; left:32px; bottom:76px; z-index:6; padding:9px 13px; border-radius:999px; background:rgba(2,6,23,.62); border:1px solid rgba(210,238,255,.18); color:#cfeeff; font-size:12px; }
        .side-card {
          position:absolute; right:22px; top:62px; width:30%; height:570px; border-radius:26px; padding:18px;
          z-index:6; background:radial-gradient(circle at 12% 0%, rgba(255,255,255,.12), transparent 34%), linear-gradient(180deg, rgba(12,25,46,.90), rgba(5,13,27,.70)); border:1px solid rgba(210,238,255,.30);
          box-shadow:0 24px 74px rgba(0,0,0,.40), inset 0 1px 0 rgba(255,255,255,.14), inset 0 -1px 0 rgba(126,220,255,.08); backdrop-filter:blur(24px) saturate(1.38); overflow:auto; scrollbar-width:none;
          animation:sensorPanelIn .46s cubic-bezier(.2,.8,.2,1) both;
        }
        .side-card::-webkit-scrollbar{display:none}.badge{display:inline-flex; gap:7px; align-items:center; padding:7px 11px; border-radius:999px; color:#bfe6ff; background:rgba(78,163,241,.14); border:1px solid rgba(142,207,255,.25); font-size:12px; font-weight:700}.side-card h3{margin:15px 0 8px 0; font-size:24px}.meta{color:rgba(235,248,255,.70); font-size:13px; line-height:1.45}.label{margin-top:15px; color:#8ccfff; font-size:11px; text-transform:uppercase; letter-spacing:1px}.side-card p{margin:6px 0 0 0; color:rgba(239,248,255,.86); line-height:1.45; font-size:13px}.insight-card{margin-top:11px; padding:12px 13px; border-radius:17px; background:rgba(255,255,255,.058); border:1px solid rgba(210,238,255,.13); box-shadow: inset 0 1px 0 rgba(255,255,255,.06), inset 0 0 22px rgba(78,163,241,.045); transition:transform .18s ease, border-color .18s ease}.insight-card:hover{transform:translateY(-1px); border-color:rgba(126,220,255,.28)}.insight-card .k{font-size:11px; text-transform:uppercase; letter-spacing:.9px; color:#8ccfff; font-weight:800}.insight-card .v{margin-top:5px; color:rgba(239,248,255,.89); font-size:13px; line-height:1.42}.tool-grid{display:grid; grid-template-columns:1fr 1fr; gap:9px; margin-top:15px}.tool-mini{padding:9px 10px; border-radius:14px; background:rgba(255,255,255,.052); border:1px solid rgba(255,255,255,.12); font-size:12px; color:rgba(239,248,255,.76); transition:transform .18s ease, border-color .18s ease}.tool-mini:hover{transform:translateY(-1px); border-color:rgba(126,220,255,.28)}.tool-mini.layer-on{border-color:rgba(74,222,128,.42); background:rgba(34,197,94,.10); color:#eafff0}.tool-mini.active{border-color:rgba(130,220,255,.85); background:rgba(78,163,241,.22); color:#fff; box-shadow:0 0 18px rgba(78,163,241,.18)}.synthesis{margin-top:16px; padding:13px; border-radius:16px; background:rgba(34,197,94,.08); border:1px solid rgba(74,222,128,.18); color:rgba(235,255,242,.86); font-size:13px; line-height:1.45}.process-chain{margin-top:10px; padding:12px; border-radius:14px; background:rgba(255,255,255,.052); border:1px solid rgba(255,255,255,.12); color:#d8f1ff; font-size:12px; line-height:1.45}.visible-layers{position:absolute; left:32px; top:92px; z-index:7; display:flex; gap:7px; flex-wrap:wrap; max-width:62%}.layer-chip{padding:6px 9px; border-radius:999px; background:rgba(2,6,23,.52); border:1px solid rgba(210,238,255,.18); color:#d9f4ff; font-size:11px; backdrop-filter:blur(10px)}
      </style>
      <div class="sensor-title"><h2>Multi-Sensor Evidence Explorer</h2><p>Case study as the base satellite scene; each observation tool adds a different evidence layer on top.</p></div>
      <div class="sat-frame case-__CASE_CLASS__">
        <div class="sat-image"></div><div class="glacier-outline"></div><div class="orbit"></div>
        <div class="case-label">Location: __CASE_NAME__ · __COORDS__</div><div class="ice-label">Ice / shelf surface</div><div class="ocean-label">Ocean cavity / shelf sea</div>
        <div class="visible-layers">__VISIBLE_LAYER_CHIPS__</div>
        <div class="overlay __OVERLAY_CLASS__">__OVERLAY_HTML__</div>
        <div class="legend-pill">Primary layer: __TOOL_ICON__ __TOOL_NAME__ - __MEASURES__</div>
      </div>
      <div class="side-card">
        <span class="badge">__TOOL_ICON__ Observation layer</span>
        <h3>__CASE_NAME__</h3>
        <div class="meta"><b>Region:</b> __REGION__<br><b>Type:</b> __TYPE__<br><b>Main theme:</b> __THEME__</div>
        <div class="insight-card"><div class="k">Observation</div><div class="v">__OBSERVED__</div></div>
        <div class="insight-card"><div class="k">Measurement</div><div class="v">__MEASURES__</div></div>
        <div class="insight-card"><div class="k">Visual layer</div><div class="v">__VISUAL__</div></div>
        <div class="insight-card"><div class="k">Interpretation</div><div class="v">__INTERPRETATION__</div></div>
        <div class="process-chain">__PROCESS__</div>
        <div class="tool-grid">__TOOL_GRID__</div>
        <div class="synthesis"><b>Evidence logic:</b><br>Different sensors do not duplicate each other. They measure elevation, velocity, gravity/mass, point motion, hidden bed geometry, and past archives. Together they turn one glacier from an image into a scientific system.</div>
      </div>
    </div>
    """

    def _safe_html(value):
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _overlay_for(tool_name):
        if tool_name == "Satellite Altimetry":
            return "altimetry", '<div class="scan-line"></div><div class="scan-line"></div><div class="scan-line"></div><div class="thinning-blob"></div>'
        if tool_name == "InSAR Velocity":
            return "insar", '<div class="vel-arrow a1"></div><div class="vel-arrow a2"></div><div class="vel-arrow a3"></div><div class="vel-arrow a4"></div>'
        if tool_name == "GRACE / GRACE-FO":
            return "grace", '<div class="mass-blob"></div>'
        if tool_name == "GPS / GNSS":
            return "gnss", '<div class="station s1"></div><div class="station s2"></div><div class="station s3"></div><div class="station s4"></div>'
        if tool_name == "Ice-penetrating Radar":
            return "radar", '<div class="radar-line r1"></div><div class="radar-line r2"></div><div class="radar-line r3"></div><div class="basin"></div>'
        return "cores", '<div class="core-dot c1"></div><div class="core-dot c2"></div><div class="core-dot c3"></div><div class="archive"></div>'

    overlay_items = [_overlay_for(layer) for layer in visual_layers]
    overlay_class = " ".join([cls for cls, _ in overlay_items])
    overlay_html = "".join([html for _, html in overlay_items])
    case_class = {
        "thwaites": "thwaites",
        "pine": "pine",
        "totten": "totten",
        "larsen": "larsen",
        "wilkes": "wilkes"
    }.get(case.get("visual_seed", "thwaites"), "thwaites")
    tool_grid = "".join([
        f'<div class="tool-mini {"active" if name == selected_tool else ("layer-on" if name in visual_layers else "")}">{case["tools"][name]["icon"]} {name}</div>'
        for name in tool_order
    ])
    visible_layer_chips = "".join([
        f'<span class="layer-chip">{case["tools"][name]["icon"]} {name}</span>'
        for name in visual_layers
    ])

    replacements = {
        "__CASE_CLASS__": case_class,
        "__CASE_NAME__": _safe_html(selected_case),
        "__COORDS__": _safe_html(case["coords"]),
        "__OVERLAY_CLASS__": overlay_class,
        "__OVERLAY_HTML__": overlay_html,
        "__TOOL_ICON__": _safe_html(tool["icon"]),
        "__TOOL_NAME__": _safe_html(selected_tool),
        "__MEASURES__": _safe_html(tool["measures"]),
        "__REGION__": _safe_html(case["region"]),
        "__TYPE__": _safe_html(case["type"]),
        "__THEME__": _safe_html(case["main_theme"]),
        "__VISUAL__": _safe_html(tool["visual"]),
        "__OBSERVED__": _safe_html(tool["observed"]),
        "__INTERPRETATION__": _safe_html(tool["interpretation"]),
        "__PROCESS__": _safe_html(tool["process"]).replace(" ->", " &nbsp;&rarr;&nbsp; "),
        "__TOOL_GRID__": tool_grid,
        "__VISIBLE_LAYER_CHIPS__": visible_layer_chips
    }
    for k, v in replacements.items():
        explorer_html = explorer_html.replace(k, v)

    components.html(explorer_html, height=675, scrolling=False)

    st.caption("The text summarizes observation logic from the review-paper case studies.")

    r1, r2, r3 = st.columns(3)
    r1.metric("Case", selected_case)
    r2.metric("Primary layer", selected_tool)
    r3.metric("Visible layers", str(len(visual_layers)))

    with st.expander("Build the multi-sensor synthesis", expanded=False):
        selected_layers = st.multiselect(
            "Combine observation layers",
            tool_order,
            default=[selected_tool, "InSAR Velocity", "Satellite Altimetry"] if selected_tool not in ["InSAR Velocity", "Satellite Altimetry"] else [selected_tool, "GRACE / GRACE-FO"],
            key="system_layer_multiselect"
        )
        if selected_layers:
            cards_html = "".join([
                f"""
                <div class="evidence-layer-card">
                  <div class="evidence-layer-title">{case['tools'][layer]['icon']} {layer}</div>
                  <div class="evidence-layer-label">Measures</div>
                  <div class="evidence-layer-text">{case['tools'][layer]['measures']}</div>
                  <div class="evidence-layer-label">Observed</div>
                  <div class="evidence-layer-text">{case['tools'][layer]['observed']}</div>
                </div>
                """
                for layer in selected_layers
            ])
            evidence_builder_html = textwrap.dedent(f"""
            <div class="evidence-builder-wrap">
              <style>
                html, body {{
                  margin: 0;
                  padding: 0;
                  background: transparent;
                  overflow: hidden;
                  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                  color: rgba(245,250,255,.94);
                }}
                .evidence-builder-wrap {{
                  width: 100%;
                  display: block;
                  clear: both;
                  box-sizing: border-box;
                  padding: 0 0 2px 0;
                }}
                .system-note-card {{
                  padding: 0 0 10px 0;
                  background: transparent;
                  border: none;
                  color: rgba(245,250,255,.92);
                  line-height: 1.45;
                  font-size: 14px;
                }}
                .system-note-card b {{
                  font-size: 15px;
                  color: rgba(248,251,255,.98);
                }}
                .evidence-grid-fixed {{
                  display: grid;
                  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                  gap: 12px;
                  margin-top: 4px;
                  margin-bottom: 14px;
                }}
                .evidence-layer-card {{
                  padding: 14px 15px;
                  border-radius: 18px;
                  border: 1px solid rgba(78,163,241,.22);
                  background: rgba(78,163,241,.065);
                  min-height: 154px;
                  box-sizing: border-box;
                }}
                .evidence-layer-title {{
                  font-weight: 800;
                  font-size: 15px;
                  margin-bottom: 12px;
                  color: rgba(248,251,255,.98);
                }}
                .evidence-layer-label {{
                  font-size: 12px;
                  opacity: .68;
                  font-weight: 700;
                  margin-top: 8px;
                }}
                .evidence-layer-text {{
                  font-size: 13px;
                  margin-top: 3px;
                  line-height: 1.4;
                }}
                .synthesis-fixed {{
                  clear: both;
                  margin-top: 14px;
                  padding: 14px 16px;
                  border-radius: 16px;
                  background: rgba(34,197,94,.16);
                  border: 1px solid rgba(74,222,128,.26);
                  color: #49e782;
                  font-size: 15px;
                  line-height: 1.45;
                  font-weight: 650;
                  box-sizing: border-box;
                }}
              </style>
              <div class="system-note-card">
                <b>Evidence Builder</b><br>
                Each selected sensor contributes a different kind of evidence. The goal is not to make the map busier, but to show how a scientific conclusion is assembled.
              </div>
              <div class="evidence-grid-fixed">
                {cards_html}
              </div>
              <div class="synthesis-fixed">
                Synthesis: For <b>{selected_case}</b>, these layers combine different evidence dimensions and support the theme: <b>{case['main_theme']}</b>.
              </div>
            </div>
            """)
            evidence_rows = max(1, int(np.ceil(len(selected_layers) / 2)))
            components.html(evidence_builder_html, height=126 + evidence_rows * 172, scrolling=False)
        else:
            st.info("Select one or more layers to build a scientific synthesis.")

    with st.expander("Physical-process context", expanded=False):
        processes = {
            "Ocean Forcing": "Warm Circumpolar Deep Water can reach the continental shelf and increase basal melting below ice shelves.",
            "Ice Shelf Buttressing": "Floating ice shelves slow inland ice flow by providing back stress; thinning or collapse reduces this support.",
            "Grounding Line Retreat": "The grounding line marks the transition from grounded ice to floating ice; retreat can increase ice discharge.",
            "MISI": "Marine Ice Sheet Instability can occur when retreat on a retrograde bed exposes thicker ice and causes further retreat.",
            "MICI": "Marine Ice Cliff Instability is a proposed rapid-collapse mechanism involving hydrofracturing and cliff failure.",
            "Basal Hydrology": "Subglacial water can reduce basal resistance and affect ice flow speed.",
            "Solid Earth Feedback": "Bedrock uplift and sea-level fingerprints can either amplify or slow ice-sheet retreat."
        }
        selected_process = st.selectbox("Select a process", list(processes.keys()), key="system_process_context")
        st.info(processes[selected_process])
