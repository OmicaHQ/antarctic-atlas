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

def render_research_universe(pages, total_pages):

    research_areas = {
        "Ocean": {
            "color": "#4EA3F1",
            "angle": 160,
            "key_question": "How does Southern Ocean heat reach ice-shelf cavities?",
            "importance": "Controls basal melting and ice-shelf thinning.",
            "topics": [
                {
                    "name": "CDW Intrusion",
                    "key_question": "When and where can Circumpolar Deep Water access the continental shelf?",
                    "why": "Warm CDW is a major driver of sub-ice-shelf melt in vulnerable sectors.",
                    "status": "Active frontier",
                    "regions": "Amundsen Sea, Bellingshausen Sea, Totten Glacier"
                },
                {
                    "name": "Cross-shelf Heat Transport",
                    "key_question": "How do winds, eddies, tides, and bathymetry move heat toward the coast?",
                    "why": "Determines which ice shelves receive ocean heat.",
                    "status": "High uncertainty",
                    "regions": "Antarctic continental shelf"
                },
                {
                    "name": "Ice-shelf Basal Melt",
                    "key_question": "How fast do ice shelves melt from below?",
                    "why": "Basal melt thins ice shelves and weakens buttressing.",
                    "status": "Observed but hard to model",
                    "regions": "Pine Island, Thwaites, Totten"
                },
                {
                    "name": "Freshwater Feedback",
                    "key_question": "Can meltwater freshening trap subsurface heat?",
                    "why": "Links ice loss back to ocean stratification and future melt.",
                    "status": "Emerging feedback",
                    "regions": "Southern Ocean"
                }
            ]
        },
        "Ice Dynamics": {
            "color": "#FF8A65",
            "angle": 25,
            "key_question": "How does ice flow accelerate after ice shelves weaken?",
            "importance": "Connects local forcing to large-scale ice discharge.",
            "topics": [
                {
                    "name": "Buttressing",
                    "key_question": "How much resistance do ice shelves provide to inland ice?",
                    "why": "Loss of buttressing allows grounded ice to flow faster.",
                    "status": "Core mechanism",
                    "regions": "Antarctic Peninsula, Amundsen Sea"
                },
                {
                    "name": "Grounding Line Retreat",
                    "key_question": "What controls the retreat of the grounded-to-floating transition?",
                    "why": "Grounding line position strongly controls ice discharge.",
                    "status": "Central research target",
                    "regions": "Thwaites, Pine Island, Totten"
                },
                {
                    "name": "MISI",
                    "key_question": "Can retreat become self-sustaining on a retrograde bed?",
                    "why": "Marine Ice Sheet Instability may drive rapid, long-lasting retreat.",
                    "status": "High-impact uncertainty",
                    "regions": "WAIS, Wilkes Subglacial Basin"
                },
                {
                    "name": "MICI",
                    "key_question": "Can tall marine ice cliffs fail rapidly after ice-shelf collapse?",
                    "why": "Marine Ice Cliff Instability could raise high-end sea-level projections.",
                    "status": "Debated mechanism",
                    "regions": "Potentially marine-based Antarctic margins"
                },
                {
                    "name": "Basal Sliding",
                    "key_question": "How do basal water and sediment affect ice velocity?",
                    "why": "Basal conditions strongly control fast ice streams.",
                    "status": "Difficult to observe",
                    "regions": "Fast-flowing outlet glaciers"
                }
            ]
        },
        "Solid Earth": {
            "color": "#9CCC65",
            "angle": 270,
            "key_question": "How do bedrock, heat flow, and rebound affect ice stability?",
            "importance": "Sets boundary conditions and feedbacks for ice-sheet retreat.",
            "topics": [
                {
                    "name": "GIA",
                    "key_question": "How does bedrock rebound after ice loss?",
                    "why": "Glacial Isostatic Adjustment can alter relative sea level near grounding lines.",
                    "status": "Important feedback",
                    "regions": "West Antarctica"
                },
                {
                    "name": "Bed Topography",
                    "key_question": "Where do retrograde beds and subglacial basins create vulnerability?",
                    "why": "Bed geometry controls MISI-like retreat potential.",
                    "status": "Critical boundary data",
                    "regions": "Thwaites, Wilkes, Aurora, Sabrina"
                },
                {
                    "name": "Geothermal Heat Flux",
                    "key_question": "How much heat enters the ice base from below?",
                    "why": "Affects basal meltwater, sliding, and ice dynamics.",
                    "status": "Sparse observations",
                    "regions": "West Antarctica, South Pole region"
                },
                {
                    "name": "Subglacial Hydrology",
                    "key_question": "How does water move beneath the ice sheet?",
                    "why": "Water can lubricate the bed and modify ice flow.",
                    "status": "Hard-to-access frontier",
                    "regions": "Subglacial lakes and drainage systems"
                }
            ]
        },
        "Observations": {
            "color": "#9575CD",
            "angle": 90,
            "key_question": "How do we measure change in such a remote environment?",
            "importance": "Provides constraints for mechanisms and models.",
            "topics": [
                {
                    "name": "Satellite Altimetry",
                    "key_question": "Where is the ice surface thinning or thickening?",
                    "why": "Tracks elevation change over large areas.",
                    "status": "Mature remote sensing tool",
                    "regions": "Continent-wide"
                },
                {
                    "name": "InSAR Velocity",
                    "key_question": "How fast is the ice moving?",
                    "why": "Maps glacier acceleration and grounding-zone motion.",
                    "status": "Highly relevant to Bryan's field",
                    "regions": "Fast outlet glaciers"
                },
                {
                    "name": "GRACE / GRACE-FO",
                    "key_question": "How is total ice mass changing?",
                    "why": "Measures gravity change related to ice mass balance.",
                    "status": "Powerful but needs GIA correction",
                    "regions": "Continent-wide"
                },
                {
                    "name": "Radar & Field Data",
                    "key_question": "What lies beneath the ice?",
                    "why": "Reveals bed topography, internal layers, and basal conditions.",
                    "status": "Essential but incomplete",
                    "regions": "Ice streams, grounding zones, subglacial basins"
                }
            ]
        },
        "Paleoclimate": {
            "color": "#F6C85F",
            "angle": 215,
            "key_question": "What did the AIS do in past warm periods?",
            "importance": "Extends evidence beyond the short satellite record.",
            "topics": [
                {
                    "name": "Pliocene",
                    "key_question": "How much smaller was the AIS in a warmer-than-present world?",
                    "why": "Provides analogs for long-term future warmth.",
                    "status": "Important but uncertain",
                    "regions": "WAIS and marine-based EAIS"
                },
                {
                    "name": "Last Interglacial",
                    "key_question": "How did Antarctica contribute to high sea level?",
                    "why": "Tests model sensitivity to warm climate states.",
                    "status": "Useful constraint",
                    "regions": "Antarctic margins"
                },
                {
                    "name": "Ice Cores",
                    "key_question": "What do past temperature and accumulation records show?",
                    "why": "Records atmosphere and climate history.",
                    "status": "Foundational evidence",
                    "regions": "Interior Antarctica"
                },
                {
                    "name": "Marine Sediments",
                    "key_question": "Where and when did the ice margin retreat?",
                    "why": "Reconstructs past ice-sheet extent and ocean conditions.",
                    "status": "Key paleo archive",
                    "regions": "Continental shelf and deep ocean"
                }
            ]
        },
        "Future Projections": {
            "color": "#2F5597",
            "angle": 325,
            "key_question": "How much will Antarctica contribute to future sea-level rise?",
            "importance": "Connects science to societal risk.",
            "topics": [
                {
                    "name": "Sea-level Contribution",
                    "key_question": "How large and how fast could Antarctic sea-level rise be?",
                    "why": "Central societal impact of AIS change.",
                    "status": "Uncertain but crucial",
                    "regions": "Global coastlines"
                },
                {
                    "name": "Coupled Models",
                    "key_question": "How can ice, ocean, atmosphere, and solid Earth be simulated together?",
                    "why": "Feedbacks require coupled Earth-system modeling.",
                    "status": "Major modeling frontier",
                    "regions": "Antarctica and global climate system"
                },
                {
                    "name": "Uncertainty Quantification",
                    "key_question": "Which processes dominate projection uncertainty?",
                    "why": "Needed for useful risk assessment.",
                    "status": "High priority",
                    "regions": "Model ensembles"
                },
                {
                    "name": "AI for Earth Observation",
                    "key_question": "Can AI organize observations and detect patterns in ice-sheet change?",
                    "why": "Relevant to literature mapping, satellite analysis, and interactive learning tools.",
                    "status": "Emerging opportunity",
                    "regions": "Remote sensing and research synthesis"
                }
            ]
        }
    }

    def build_universe_topic_index(research_areas):
        topic_index = {
            "Antarctic Ice Sheet": {
                "parent": "Core system",
                "keywords": [
                    "antarctic ice sheet", "ais", "ice sheet", "antarctica",
                    "climate forcing", "earth system", "sea level"
                ]
            }
        }
        manual_keywords = {
            "Ocean": ["ocean", "southern ocean", "cdw", "circumpolar deep water", "basal melt", "heat transport", "shelf break", "warm water", "ocean forcing"],
            "CDW Intrusion": ["cdw", "circumpolar deep water", "intrusion", "warm deep water", "amundsen", "bellingshausen", "totten"],
            "Cross-shelf Heat Transport": ["cross shelf", "heat transport", "eddy", "eddies", "tide", "winds", "shelf break", "slope front"],
            "Ice-shelf Basal Melt": ["basal melt", "ice shelf melt", "melting from below", "sub ice shelf", "cavity"],
            "Freshwater Feedback": ["freshwater", "meltwater", "stratification", "aabw", "feedback"],
            "Ice Dynamics": ["ice dynamics", "ice flow", "grounding line", "buttressing", "misi", "mici", "basal sliding"],
            "Buttressing": ["buttressing", "back stress", "ice shelf support", "pinning point"],
            "Grounding Line Retreat": ["grounding line", "grounding zone", "retreat", "migration"],
            "MISI": ["misi", "marine ice sheet instability", "retrograde bed", "self sustaining retreat"],
            "MICI": ["mici", "marine ice cliff instability", "ice cliff", "hydrofracture", "cliff failure"],
            "Basal Sliding": ["basal sliding", "basal slip", "sliding", "friction", "till deformation", "water pressure"],
            "Solid Earth": ["solid earth", "bedrock", "gia", "topography", "geothermal", "subglacial hydrology"],
            "GIA": ["gia", "glacial isostatic adjustment", "isostatic", "bedrock uplift", "rebound", "viscosity"],
            "Bed Topography": ["bed topography", "bedmap", "subglacial basin", "trough", "bathymetry", "retrograde bed"],
            "Geothermal Heat Flux": ["geothermal", "heat flux", "basal temperature", "volcanism"],
            "Subglacial Hydrology": ["subglacial hydrology", "subglacial lake", "basal water", "drainage", "hydrology"],
            "Observations": ["observation", "satellite", "remote sensing", "insar", "grace", "altimetry", "radar"],
            "Satellite Altimetry": ["altimetry", "icesat", "cryosat", "elevation", "surface height"],
            "InSAR Velocity": ["insar", "sar", "velocity", "ice velocity", "interferometry"],
            "GRACE / GRACE-FO": ["grace", "grace-fo", "gravity", "mass balance", "gravimetry"],
            "Radar & Field Data": ["radar", "field data", "ice penetrating radar", "apres", "gnss", "gps"],
            "Paleoclimate": ["paleoclimate", "pliocene", "last interglacial", "ice core", "marine sediment", "past climate"],
            "Pliocene": ["pliocene", "mid pliocene", "warm period"],
            "Last Interglacial": ["last interglacial", "lig", "eemian"],
            "Ice Cores": ["ice core", "accumulation", "temperature record", "isotope"],
            "Marine Sediments": ["marine sediment", "sediment core", "paleo record", "foraminifera"],
            "Future Projections": ["future", "projection", "sea level", "uncertainty", "model", "rcp", "2100", "2300"],
            "Sea-level Contribution": ["sea level", "gmsl", "sea-level rise", "coast", "contribution"],
            "Coupled Models": ["coupled model", "ice ocean model", "earth system model", "ismip", "misomip"],
            "Uncertainty Quantification": ["uncertainty", "ensemble", "probability", "risk", "projection uncertainty"],
            "AI for Earth Observation": ["ai", "machine learning", "deep learning", "earth observation", "knowledge graph"]
        }
        for area_name, area in research_areas.items():
            topic_index[area_name] = {
                "parent": "Research area",
                "keywords": list(set([area_name.lower(), area.get("key_question", ""), area.get("importance", "")] + manual_keywords.get(area_name, [])))
            }
            for topic in area["topics"]:
                name = topic["name"]
                topic_index[name] = {
                    "parent": area_name,
                    "keywords": list(set([name.lower(), topic.get("key_question", ""), topic.get("why", ""), topic.get("status", ""), topic.get("regions", "")] + manual_keywords.get(name, [])))
                }
        return topic_index

    def classify_universe_question(question, topic_index):
        """Keyword fallback classifier. Used only when the AI classifier is unavailable or invalid."""
        q = question.lower().replace("-", "-")
        best_topic = "Antarctic Ice Sheet"
        best_score = 0
        for topic, meta in topic_index.items():
            score = 0
            topic_lower = topic.lower()
            if topic_lower in q:
                score += 12
            for kw in meta.get("keywords", []):
                kw = str(kw).lower().strip()
                if not kw:
                    continue
                if kw in q:
                    score += max(2, min(8, len(kw) // 3))
                else:
                    for part in re.findall(r"[a-zA-Z]{3,}", kw):
                        if part in q:
                            score += 1
            if score > best_score:
                best_score = score
                best_topic = topic
        return best_topic, topic_index.get(best_topic, {}).get("parent", "Research area"), best_score, "keyword_fallback"

    def classify_universe_question_with_ai(question, topic_index, backend="Local Ollama"):
        """
        AI classifier: chooses exactly one node from the Research Universe.
        DeepSeek API is used when selected; otherwise local Ollama is used.
        If the selected backend fails or returns an invalid node, fallback to keyword matching.
        """
        if backend == "Evidence only":
            return classify_universe_question(question, topic_index)
        if backend == "DeepSeek API":
            ds_result = classify_universe_question_with_deepseek(question, topic_index)
            if ds_result:
                return ds_result
            return classify_universe_question(question, topic_index)
        if backend == "OpenAI API":
            openai_result = classify_universe_question_with_openai(question, topic_index)
            if openai_result:
                return openai_result
            return classify_universe_question(question, topic_index)
        valid_topics = list(topic_index.keys())
        topic_lines = []
        for topic in valid_topics:
            parent = topic_index.get(topic, {}).get("parent", "Research area")
            topic_lines.append(f"- {topic} | parent: {parent}")

        prompt = f"""
You are a strict classifier for an Antarctic Ice Sheet research knowledge graph.
Choose exactly ONE best matching node from the allowed node list.
Return only valid JSON. Do not explain.

Allowed nodes:
{chr(10).join(topic_lines)}

Question:
{question}

Return JSON in this exact format:
{{"topic":"one allowed node name", "confidence":0.0}}
"""
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_ctx": 4096, "num_gpu": -1}
            }
            r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=90)
            r.raise_for_status()
            raw = r.json().get("response", "").strip()

            # Be tolerant if the model wraps JSON in text or markdown.
            match = re.search(r"\{.*\}", raw, re.S)
            obj = json.loads(match.group(0) if match else raw)
            topic = str(obj.get("topic", "")).strip()
            confidence = float(obj.get("confidence", 0.0) or 0.0)

            # Exact match first; then case-insensitive match.
            if topic not in valid_topics:
                lowered = {t.lower(): t for t in valid_topics}
                topic = lowered.get(topic.lower(), "")
            if topic in valid_topics:
                return topic, topic_index.get(topic, {}).get("parent", "Research area"), confidence, "ai"
        except Exception:
            pass

        return classify_universe_question(question, topic_index)

    universe_topic_index = build_universe_topic_index(research_areas)

    # Build the payload used by the JavaScript universe component.
    # It must be defined before research_universe_html is rendered.
    universe_payload = {
        "center": {
            "name": "Antarctic Ice Sheet",
            "type": "Core system",
            "color": "#DDEEFF",
            "key_question": "How does the Antarctic Ice Sheet respond to climate forcing?",
            "importance": "The central system linking atmosphere, ocean, ice dynamics, solid Earth, observations, paleoclimate evidence, and future sea-level risk.",
            "status": "Research hub",
            "regions": "Antarctica and global coastlines"
        },
        "areas": research_areas
    }

    initial_focus_topic = st.session_state.get("universe_focus_topic", "")
    initial_focus_source = st.session_state.get("universe_focus_source", "manual")
    initial_focus_token = st.session_state.get("universe_focus_token", 0)

    research_universe_html = """
    <div id="research-universe-root">
      <style>
        #research-universe-root {
          height: 700px; width: 100%; overflow: hidden; position: relative; border-radius: 30px; isolation:isolate;
          background:
            radial-gradient(circle at 24% 24%, rgba(78,163,241,0.20), rgba(78,163,241,0.08) 24%, transparent 48%),
            radial-gradient(circle at 74% 68%, rgba(149,117,205,0.20), rgba(149,117,205,0.07) 26%, transparent 50%),
            radial-gradient(circle at 48% 45%, rgba(221,238,255,0.08), rgba(221,238,255,0.035) 24%, transparent 48%),
            #050d1b;
          background-size: 100% 100%;
          font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          color: #eef6ff; box-shadow: inset 0 0 90px rgba(78,163,241,0.13), 0 26px 80px rgba(0,0,0,.34);
        }
        #research-universe-root::before,
        #research-universe-root::after { content:""; position:absolute; inset:-18%; pointer-events:none; z-index:1; }
        #research-universe-root::before {
          background:
            radial-gradient(circle at 30% 24%, rgba(190,240,255,.08), transparent 34%),
            radial-gradient(circle at 70% 64%, rgba(126,220,255,.05), transparent 38%);
          mix-blend-mode:screen; opacity:.36;
        }
        #research-universe-root::after {
          background: radial-gradient(ellipse at 50% 50%, transparent 35%, rgba(2,6,23,.38) 82%);
          z-index:1;
        }
        @keyframes ruCardIn {
          from { opacity:0; transform:translateY(12px) scale(.985); }
          to { opacity:1; transform:translateY(0) scale(1); }
        }
        @keyframes ruLinkFlow { to { stroke-dashoffset:-40; } }
        @keyframes ruNodeBreath {
          0%,100% { filter:drop-shadow(0 0 14px rgba(130,210,255,.60)); }
          50% { filter:drop-shadow(0 0 24px rgba(210,245,255,.85)); }
        }
        #research-universe-root .title { position:absolute; top:22px; left:26px; z-index:7; width:46%; max-width:390px; min-width:290px; padding:15px 17px; border-radius:20px; overflow:hidden; background:linear-gradient(180deg, rgba(14,27,49,.62), rgba(4,12,25,.40)); border:1px solid rgba(210,238,255,.20); backdrop-filter:blur(18px) saturate(1.3); box-shadow:inset 0 1px 0 rgba(255,255,255,.13), 0 16px 44px rgba(0,0,0,.18); animation:ruCardIn .38s cubic-bezier(.2,.8,.2,1) both; }
        #research-universe-root .title::before { content:""; position:absolute; inset:-80% -35%; background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.10) 38%, rgba(126,220,255,.18) 48%, transparent 66%); transform:translateX(-30%) rotate(10deg); opacity:.70; pointer-events:none; }
        #research-universe-root .title h2 { margin:0; font-size:22px; color:#f8fbff; letter-spacing:.2px; }
        #research-universe-root .title p { margin:7px 0 0 0; color:rgba(231,245,255,.72); line-height:1.38; font-size:13px; }
        #research-universe-svg { position:absolute; inset:0; width:100%; height:100%; z-index:2; }
        #research-universe-root .star { position:absolute; width:2px; height:2px; border-radius:50%; background:rgba(255,255,255,.75); box-shadow:0 0 9px rgba(255,255,255,.55); animation:twinkle 3.5s infinite ease-in-out alternate; }
        @keyframes twinkle { from { opacity:.25; transform:scale(.8); } to { opacity:.95; transform:scale(1.25); } }
        #research-universe-root .card { position:absolute; right:22px; top:28px; width:35%; max-width:275px; min-width:235px; overflow:hidden; z-index:6; border:1px solid rgba(210,238,255,.30); border-radius:24px; padding:19px; background:radial-gradient(circle at 12% 0%, rgba(255,255,255,.10), transparent 34%), linear-gradient(180deg,rgba(12,25,46,.88),rgba(5,13,27,.68)); backdrop-filter:blur(22px) saturate(1.38); box-shadow:0 24px 70px rgba(0,0,0,.38), inset 0 1px 0 rgba(255,255,255,.14), inset 0 -1px 0 rgba(126,220,255,.08); opacity:1; transform:translateY(0); transition:opacity .24s ease, transform .24s ease, border-color .24s ease, box-shadow .24s ease; animation:ruCardIn .42s cubic-bezier(.2,.8,.2,1) both; }
        #research-universe-root .card::before { content:""; position:absolute; inset:0; background:radial-gradient(circle at 18% 0%, rgba(255,255,255,.10), transparent 44%); opacity:.45; pointer-events:none; }
        #research-universe-root .card::-webkit-scrollbar { display:none; }
        #research-universe-root .card.is-fading { opacity:0; transform:translateY(10px) scale(.985); }
        #research-universe-root .badge { display:inline-block; padding:6px 10px; border-radius:999px; background:rgba(78,163,241,.14); border:1px solid rgba(142,207,255,.25); color:#bfe6ff; font-size:12px; letter-spacing:.25px; margin-bottom:14px; }
        #research-universe-root .card h3 { margin:0 0 10px 0; font-size:20px; color:#fff; }
        #research-universe-root .card .label { margin-top:14px; color:#8ccfff; font-size:11px; text-transform:uppercase; letter-spacing:1px; }
        #research-universe-root .card p { margin:5px 0 0 0; color:rgba(239,248,255,.84); line-height:1.45; font-size:13px; }
        #research-universe-root .hint { position:absolute; left:32px; bottom:24px; max-width:calc(100% - 64px); color:rgba(231,245,255,.64); font-size:13px; z-index:5; padding:8px 11px; border-radius:999px; background:rgba(2,6,23,.30); border:1px solid rgba(210,238,255,.10); backdrop-filter:blur(10px); }
        @media (max-width: 640px) {
          #research-universe-root .title { display:none; }
          #research-universe-root .card { left:26px; right:auto; top:24px; width:300px; max-width:calc(100% - 52px); min-width:0; }
        }
        .ru-link { stroke:rgba(118,200,255,.30); stroke-linecap:round; transition:all .55s ease; }
        .ru-link.active { stroke-dasharray:9 10; animation:ruLinkFlow 1.55s linear infinite; filter:drop-shadow(0 0 9px rgba(126,220,255,.55)); }
        .ru-node { cursor:pointer; transition:opacity .55s ease; }
        .ru-node circle.main { filter:drop-shadow(0 0 14px rgba(130,210,255,.65)); transition:all .55s ease; animation:ruNodeBreath 4.2s ease-in-out infinite; }
        .ru-node.focused circle.main { filter:drop-shadow(0 0 34px rgba(255,255,255,.96)); }
        .ru-node text { pointer-events:none; fill:rgba(246,251,255,.94); font-weight:650; text-anchor:middle; paint-order:stroke; stroke:rgba(2,6,23,.90); stroke-width:4px; stroke-linejoin:round; }
        .ru-node.ai-target-pulse circle.main { animation: aiTargetPulse .78s ease-in-out 2; }
        .ru-node.ai-target-pulse text { animation: aiTextPulse .78s ease-in-out 2; }
        @keyframes aiTargetPulse {
          0% { stroke-width:2px; filter:drop-shadow(0 0 14px rgba(130,210,255,.65)); }
          50% { stroke-width:7px; filter:drop-shadow(0 0 38px rgba(255,255,255,1)); }
          100% { stroke-width:2px; filter:drop-shadow(0 0 14px rgba(130,210,255,.65)); }
        }
        @keyframes aiTextPulse {
          0% { fill:rgba(246,251,255,.94); }
          50% { fill:#ffffff; }
          100% { fill:rgba(246,251,255,.94); }
        }
      </style>
      <div class="title"><h2>Antarctic Research Universe</h2><p>Ask a question; AI locates the matching node. You can also click any sphere manually.</p></div>
      <div class="card" id="knowledge-card"></div>
      <div class="hint">Click a sphere · Ask below · matched module auto-focuses here</div>
      <svg id="research-universe-svg" viewBox="0 0 1180 760" preserveAspectRatio="xMidYMid meet"></svg>
    </div>

    <script>
    (function () {
      const data = __DATA__;
      const root = document.getElementById("research-universe-root");
      const svg = document.getElementById("research-universe-svg");
      const card = document.getElementById("knowledge-card");
      const NS = "http://www.w3.org/2000/svg";
      const cx = 430, cy = 405;
      let focusedId = null;
      const initialFocus = __INITIAL_FOCUS__;
      const initialFocusSource = __INITIAL_FOCUS_SOURCE__;
      const initialFocusToken = __INITIAL_FOCUS_TOKEN__;
      const storageKey = "antarctic_research_universe_state_v3";

      for (let i = 0; i < 95; i++) {
        const s = document.createElement("div");
        s.className = "star";
        s.style.left = Math.random() * 100 + "%";
        s.style.top = Math.random() * 100 + "%";
        s.style.animationDelay = Math.random() * 4 + "s";
        root.appendChild(s);
      }

      function el(name, attrs = {}) {
        const e = document.createElementNS(NS, name);
        Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
        return e;
      }
      function polar(angleDeg, r) {
        const a = (angleDeg - 90) * Math.PI / 180;
        return { x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r };
      }
      function safe(t) { return String(t ?? "").replace(/[&<>]/g, m => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[m])); }

      const nodes = [];
      const links = [];
      nodes.push({ id:data.center.name, parent:null, group:"Core", level:0, r:56, color:data.center.color,
        question:data.center.key_question, why:data.center.importance, status:data.center.status, regions:data.center.regions,
        home:{x:cx, y:cy} });

      Object.entries(data.areas).forEach(([areaName, area]) => {
        const p = polar(area.angle, 205);
        nodes.push({ id:areaName, parent:data.center.name, group:areaName, level:1, r:38, color:area.color,
          question:area.key_question, why:area.importance, status:"Research area", regions:area.topics.map(t => t.name).join(" - "), home:p });
        links.push({source:data.center.name, target:areaName, type:"area"});
        area.topics.forEach((topic, i) => {
          const localAngle = area.angle + (i - (area.topics.length - 1) / 2) * 19;
          const tp = polar(localAngle, 330 + (i % 2) * 28);
          nodes.push({ id:topic.name, parent:areaName, group:areaName, level:2, r:22, color:area.color,
            question:topic.key_question, why:topic.why, status:topic.status, regions:topic.regions, home:tp });
          links.push({source:areaName, target:topic.name, type:"topic"});
        });
      });

      const nodeById = new Map(nodes.map(n => [n.id, n]));
      function related(id) {
        const n = nodeById.get(id);
        const set = new Set([id]);
        links.forEach(l => { if (l.source === id) set.add(l.target); if (l.target === id) set.add(l.source); });
        if (n && n.parent) set.add(n.parent);
        if (n && n.level === 1) nodes.filter(x => x.parent === n.id).forEach(x => set.add(x.id));
        if (n && n.level === 2) nodes.filter(x => x.parent === n.parent).forEach(x => set.add(x.id));
        return set;
      }

      const defs = el("defs");
      defs.innerHTML = `<filter id="ruGlow"><feGaussianBlur stdDeviation="4.5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>`;
      svg.appendChild(defs);
      const linkLayer = el("g"), nodeLayer = el("g");
      svg.appendChild(linkLayer); svg.appendChild(nodeLayer);

      const linkEls = links.map(l => {
        const a = nodeById.get(l.source), b = nodeById.get(l.target);
        const line = el("line", { class:"ru-link", x1:a.home.x, y1:a.home.y, x2:b.home.x, y2:b.home.y, "stroke-width": l.type === "area" ? 2.2 : 1.25 });
        line.dataset.source = l.source; line.dataset.target = l.target;
        linkLayer.appendChild(line);
        return line;
      });

      function addWrappedText(g, text, fs) {
        const words = text.split(/\\s+/);
        const lines = text.length > 15 && words.length > 1 ? [words.slice(0, Math.ceil(words.length/2)).join(" "), words.slice(Math.ceil(words.length/2)).join(" ")] : [text];
        const t = el("text", { "font-size": fs });
        lines.forEach((line, i) => {
          const sp = el("tspan", { x:0, dy: i === 0 && lines.length > 1 ? "-0.15em" : (i === 0 ? "0.35em" : "1.15em") });
          sp.textContent = line;
          t.appendChild(sp);
        });
        g.appendChild(t);
      }

      const nodeEls = nodes.map(n => {
        const g = el("g", { class:"ru-node", transform:`translate(${n.home.x},${n.home.y})` });
        g.dataset.id = n.id;
        const c1 = el("circle", { class:"main", r:n.r, fill:n.color, "fill-opacity": n.level === 2 ? .70 : .88, stroke:"rgba(255,255,255,.76)", "stroke-width": n.level === 0 ? 2.6 : 1.5, filter:"url(#ruGlow)" });
        const c2 = el("circle", { r:n.r*.58, fill:"rgba(255,255,255,.22)" });
        g.appendChild(c1); g.appendChild(c2);
        addWrappedText(g, n.id, n.level === 0 ? 14 : n.level === 1 ? 12 : 10);
        g.addEventListener("click", ev => { ev.stopPropagation(); focusedId === n.id ? resetUniverse() : focusNode(n); });
        nodeLayer.appendChild(g);
        return g;
      });

      nodes.forEach(n => {
        n.x = n.home.x;
        n.y = n.home.y;
        n.startX = n.x;
        n.startY = n.y;
        n.targetX = n.x;
        n.targetY = n.y;
        n.scale = 1;
        n.targetScale = 1;
      });

      function persistUniverseState() {
        try {
          const state = {
            focusedId: focusedId,
            nodes: nodes.map(n => ({ id:n.id, x:n.x, y:n.y, scale:n.scale, targetX:n.targetX, targetY:n.targetY, targetScale:n.targetScale })),
            styles: nodeEls.map(g => {
              const main = g.querySelector("circle.main");
              return {
                id:g.dataset.id,
                opacity:g.style.opacity || "1",
                strokeWidth:main.getAttribute("stroke-width"),
                fillOpacity:main.getAttribute("fill-opacity")
              };
            }),
            links: linkEls.map(line => ({
              source:line.dataset.source,
              target:line.dataset.target,
              stroke:line.getAttribute("stroke"),
              strokeWidth:line.getAttribute("stroke-width")
            }))
          };
          window.localStorage.setItem(storageKey, JSON.stringify(state));
        } catch (e) {}
      }

      function restoreUniverseState() {
        try {
          const raw = window.localStorage.getItem(storageKey);
          if (!raw) return false;
          const state = JSON.parse(raw);
          if (!state || !Array.isArray(state.nodes)) return false;
          focusedId = state.focusedId || null;
          state.nodes.forEach(saved => {
            const n = nodeById.get(saved.id);
            if (!n) return;
            n.x = Number.isFinite(saved.x) ? saved.x : n.home.x;
            n.y = Number.isFinite(saved.y) ? saved.y : n.home.y;
            n.scale = Number.isFinite(saved.scale) ? saved.scale : 1;
            n.targetX = Number.isFinite(saved.targetX) ? saved.targetX : n.x;
            n.targetY = Number.isFinite(saved.targetY) ? saved.targetY : n.y;
            n.targetScale = Number.isFinite(saved.targetScale) ? saved.targetScale : n.scale;
          });
          if (Array.isArray(state.styles)) {
            state.styles.forEach(saved => {
              const g = nodeEls.find(el => el.dataset.id === saved.id);
              if (!g) return;
              const main = g.querySelector("circle.main");
              g.style.opacity = saved.opacity || "1";
              if (saved.strokeWidth) main.setAttribute("stroke-width", saved.strokeWidth);
              if (saved.fillOpacity) main.setAttribute("fill-opacity", saved.fillOpacity);
            });
          }
          if (Array.isArray(state.links)) {
            state.links.forEach(saved => {
              const line = linkEls.find(el => el.dataset.source === saved.source && el.dataset.target === saved.target);
              if (!line) return;
              if (saved.stroke) line.setAttribute("stroke", saved.stroke);
              if (saved.strokeWidth) line.setAttribute("stroke-width", saved.strokeWidth);
            });
          }
          if (focusedId && nodeById.has(focusedId)) {
            const rel = related(focusedId);
            nodeEls.forEach(g => g.classList.toggle("focused", g.dataset.id === focusedId));
            linkEls.forEach(line => {
              const on = rel.has(line.dataset.source) && rel.has(line.dataset.target);
              line.classList.toggle("active", on);
            });
          }
          draw();
          if (focusedId && nodeById.has(focusedId)) updateCard(nodeById.get(focusedId), false);
          else updateCard(nodeById.get(data.center.name), false);
          return true;
        } catch (e) {
          return false;
        }
      }

      function setNodeTarget(n, x, y, scale = 1) {
        n.targetX = x;
        n.targetY = y;
        n.targetScale = scale;
      }
      function draw() {
        nodeEls.forEach(g => {
          const n = nodeById.get(g.dataset.id);
          g.setAttribute("transform", `translate(${n.x},${n.y}) scale(${n.scale})`);
        });
        linkEls.forEach(line => {
          const a = nodeById.get(line.dataset.source), b = nodeById.get(line.dataset.target);
          line.setAttribute("x1", a.x); line.setAttribute("y1", a.y); line.setAttribute("x2", b.x); line.setAttribute("y2", b.y);
        });
      }
      let activeAnimation = null;
      function animateToTargets(duration = 850) {
        if (activeAnimation) cancelAnimationFrame(activeAnimation);
        nodes.forEach(n => {
          n.startX = n.x;
          n.startY = n.y;
          n.startScale = n.scale;
        });
        const startTime = performance.now();
        function step(now) {
          const t = Math.min((now - startTime) / duration, 1);
          const ease = 1 - Math.pow(1 - t, 3);
          nodes.forEach(n => {
            n.x = n.startX + (n.targetX - n.startX) * ease;
            n.y = n.startY + (n.targetY - n.startY) * ease;
            n.scale = n.startScale + (n.targetScale - n.startScale) * ease;
          });
          draw();
          if (t < 1) {
            activeAnimation = requestAnimationFrame(step);
          } else {
            persistUniverseState();
          }
        }
        activeAnimation = requestAnimationFrame(step);
      }
      function updateCard(d, animated = true) {
        const html = `<div class="badge">${d.level === 0 ? "Core system" : d.level === 1 ? "Research area" : safe(d.group)}</div>
          <h3>${safe(d.id)}</h3><div class="label">Key question</div><p>${safe(d.question)}</p>
          <div class="label">Why it matters</div><p>${safe(d.why)}</p><div class="label">Research status</div><p>${safe(d.status)}</p>
          <div class="label">Key regions / linked topics</div><p>${safe(d.regions)}</p>`;
        if (!animated) {
          card.innerHTML = html;
          return;
        }
        card.classList.add("is-fading");
        window.setTimeout(() => {
          card.innerHTML = html;
          card.classList.remove("is-fading");
        }, 180);
      }
      function focusNode(d) {
        focusedId = d.id;
        const rel = related(d.id);
        updateCard(d, true);
        const pos = new Map();
        pos.set(d.id, {x:cx, y:cy});
        const orbit = nodes.filter(n => n.parent === d.id);
        const siblings = d.parent ? nodes.filter(n => n.parent === d.parent && n.id !== d.id) : [];
        const shown = orbit.length ? orbit : (siblings.length ? siblings : nodes.filter(n => n.level === 1 && n.id !== d.id));
        shown.forEach((n, i) => {
          const a = 2 * Math.PI * i / shown.length - Math.PI / 2;
          const r = d.level === 2 ? 170 : 210;
          pos.set(n.id, {x:cx + Math.cos(a)*r, y:cy + Math.sin(a)*r});
        });
        if (d.parent) pos.set(d.parent, {x:cx - 245, y:cy - 190});
        nodes.filter(n => !pos.has(n.id)).forEach((n, i, arr) => {
          const a = 2 * Math.PI * i / Math.max(1, arr.length);
          pos.set(n.id, {x:cx + Math.cos(a)*345, y:cy + Math.sin(a)*285});
        });
        nodes.forEach(n => {
          const p = pos.get(n.id);
          setNodeTarget(n, p.x, p.y, n.id === d.id ? 1.22 : 1);
        });
        animateToTargets(850);
        nodeEls.forEach(g => {
          const n = nodeById.get(g.dataset.id), main = g.querySelector("circle.main");
          g.classList.toggle("focused", n.id === d.id);
          g.style.opacity = (rel.has(n.id) || n.group === d.group) ? 1 : .24;
          main.setAttribute("stroke-width", n.id === d.id ? 4.4 : rel.has(n.id) ? 2.8 : 1);
          main.setAttribute("fill-opacity", n.id === d.id ? 1 : rel.has(n.id) ? .92 : .30);
        });
        linkEls.forEach(line => {
          const on = rel.has(line.dataset.source) && rel.has(line.dataset.target);
          line.classList.toggle("active", on);
          line.setAttribute("stroke", on ? "rgba(163,226,255,.92)" : "rgba(118,200,255,.12)");
          line.setAttribute("stroke-width", on ? 3.2 : 1);
        });
      }
      function resetUniverse(animated = true) {
        focusedId = null;
        updateCard(nodeById.get(data.center.name), animated);
        nodes.forEach(n => setNodeTarget(n, n.home.x, n.home.y, 1));
        if (animated) animateToTargets(850);
        else { nodes.forEach(n => { n.x = n.targetX; n.y = n.targetY; n.scale = n.targetScale; }); draw(); }
        nodeEls.forEach(g => {
          const n = nodeById.get(g.dataset.id), main = g.querySelector("circle.main");
          g.classList.remove("focused");
          g.style.opacity = 1;
          main.setAttribute("stroke-width", n.level === 0 ? 2.6 : 1.5);
          main.setAttribute("fill-opacity", n.level === 2 ? .70 : .88);
        });
        linkEls.forEach(line => {
          const type = links.find(l => l.source === line.dataset.source && l.target === line.dataset.target).type;
          line.classList.remove("active");
          line.setAttribute("stroke", "rgba(118,200,255,.30)");
          line.setAttribute("stroke-width", type === "area" ? 2.2 : 1.25);
        });
      }
      function pulseThenFocus(id) {
        const n = nodeById.get(id);
        if (!n) return;
        const g = nodeEls.find(el => el.dataset.id === id);
        if (!g) {
          focusNode(n);
          return;
        }
        g.classList.add("ai-target-pulse");
        window.setTimeout(() => {
          g.classList.remove("ai-target-pulse");
          focusNode(n);
        }, 1250);
      }

      svg.addEventListener("click", () => resetUniverse(true));

      // On Streamlit reruns, restore the last in-browser graph state first.
      // This avoids jumping back to the core layout before an AI-triggered focus.
      const restored = restoreUniverseState();
      if (!restored) resetUniverse(false);

      if (initialFocus && nodeById.has(initialFocus)) {
        window.setTimeout(() => {
          // initialFocusToken is intentionally read so the iframe content changes on every AI ask,
          // even when the matched node is the same as the previous question.
          if (initialFocusSource === "ai") {
            pulseThenFocus(initialFocus);
          } else {
            focusNode(nodeById.get(initialFocus));
          }
        }, 350);
      }
    })();
    </script>
    """.replace("__DATA__", json.dumps(universe_payload, ensure_ascii=False)).replace("__INITIAL_FOCUS__", json.dumps(initial_focus_topic, ensure_ascii=False)).replace("__INITIAL_FOCUS_SOURCE__", json.dumps(initial_focus_source, ensure_ascii=False)).replace("__INITIAL_FOCUS_TOKEN__", json.dumps(initial_focus_token, ensure_ascii=False))


    # Page title sits above the workspace.
    # The explanatory caption is placed inside the left column so the Copilot can start slightly higher,
    # close to the caption line rather than down at the map top.
    st.markdown("<div class='atlas-module-title'><h1>&#127756; Research Universe Explorer</h1></div>", unsafe_allow_html=True)

    # Two-column explorer layout:
    # Left: Research Universe caption + map. Right: lightweight Copilot input and classification status only.
    # Retrieved passages and generated answer are rendered below the two-column workspace.
    universe_col, copilot_col = st.columns([0.76, 0.24], gap="large")

    ai_backend = st.session_state.get("ai_backend", "Evidence only")
    ok, model_names, err = check_ollama()

    with universe_col:
        st.caption("Explore the review paper as a knowledge universe. Ask on the right; the map stays visible, locates the matching node, and updates the concise card inside the map.")
        components.html(research_universe_html, height=720, scrolling=False)

    with copilot_col:
        # Start the Copilot at the same vertical level as the caption above the map.
        st.subheader("Research Copilot")

        backend_options = ["Evidence only", "Local Ollama", "DeepSeek API", "OpenAI API"]
        current_backend = st.session_state.get("ai_backend", "Evidence only")
        ai_backend = st.selectbox(
            "AI Backend",
            backend_options,
            index=backend_options.index(current_backend) if current_backend in backend_options else 0,
            key="ai_backend",
            help="Evidence only always works locally. AI backends add generated answers when configured."
        )

        # If the user switches backend, remove old classification/result text.
        # This prevents a previous DeepSeek status card from remaining after switching back to Ollama.
        previous_backend = st.session_state.get("ai_backend_last_rendered")
        if previous_backend is not None and previous_backend != ai_backend:
            for stale_key in [
                "universe_question",
                "universe_focus_topic",
                "universe_focus_parent",
                "universe_match_score",
                "universe_classifier_source",
                "universe_focus_source",
                "universe_focus_token",
                "universe_pending_question",
                "universe_enter_submitted",
            ]:
                st.session_state.pop(stale_key, None)
            st.session_state["universe_question_input"] = ""
            st.session_state["ai_backend_last_rendered"] = ai_backend
            st.rerun()
        st.session_state["ai_backend_last_rendered"] = ai_backend

        if ai_backend == "Evidence only":
            st.info("Evidence-only mode is active. Questions will focus the map and retrieve relevant passages without calling an AI API.")
        elif ai_backend == "Local Ollama":
            if ok:
                st.success(f"Local Ollama is connected. Current local model: {OLLAMA_MODEL}")
            else:
                st.warning(f"Local Ollama is not ready for {OLLAMA_MODEL}. You can still retrieve paper passages, but local AI answers need this model available in Ollama.")
                if err:
                    with st.expander("Connection error"):
                        st.code(err)
                if model_names:
                    st.write("Detected Ollama models:", model_names)
                    st.caption(f"Switch Ollama to {OLLAMA_MODEL}, or run `ollama pull {OLLAMA_MODEL}` if it is not installed.")
                else:
                    st.caption(f"Start Ollama and make sure the local model dropdown is set to {OLLAMA_MODEL}.")
        elif ai_backend == "DeepSeek API":
            deepseek_models = [DEEPSEEK_MODEL, "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"]
            current_deepseek_model = st.session_state.get("deepseek_model_select", DEEPSEEK_MODEL)
            selected_deepseek_model = st.selectbox(
                "DeepSeek Model",
                deepseek_models,
                index=deepseek_models.index(current_deepseek_model) if current_deepseek_model in deepseek_models else 0,
                key="deepseek_model_select",
                help=f"{DEEPSEEK_MODEL} is the default DeepSeek V4 Pro API model; deepseek-v4-flash and legacy compatibility models remain available."
            )

            # Keep the API key in a stable session-state field so it survives form submits and reruns.
            if "deepseek_api_key_saved" not in st.session_state:
                st.session_state["deepseek_api_key_saved"] = ""
            if "deepseek_verified" not in st.session_state:
                st.session_state["deepseek_verified"] = False
            if "deepseek_status_message" not in st.session_state:
                st.session_state["deepseek_status_message"] = ""

            configured_key = get_deepseek_api_key()
            if configured_key and st.session_state.get("deepseek_verified", False):
                st.success(f"DeepSeek API is connected, current model: {selected_deepseek_model}")
            elif configured_key:
                st.info("DeepSeek API key is saved. Click Test DeepSeek Connection once to verify it.")
            else:
                st.warning("DeepSeek API key is not configured.")

            with st.expander("DeepSeek API settings", expanded=not bool(configured_key)):
                st.caption("For local testing, enter the key here; it will stay saved during this Streamlit session.")
                key_input = st.text_input(
                    "DeepSeek API Key",
                    type="password",
                    value=st.session_state.get("deepseek_api_key_saved", ""),
                    placeholder="sk-...",
                    key="deepseek_api_key_input"
                )
                if st.button("Save & Test DeepSeek", type="secondary", use_container_width=True):
                    st.session_state["deepseek_api_key_saved"] = key_input.strip()
                    ok_ds, msg_ds = test_deepseek_connection(st.session_state["deepseek_api_key_saved"], selected_deepseek_model)
                    st.session_state["deepseek_verified"] = ok_ds
                    st.session_state["deepseek_status_message"] = msg_ds
                    st.rerun()
                if st.session_state.get("deepseek_status_message"):
                    if st.session_state.get("deepseek_verified", False):
                        st.success(st.session_state["deepseek_status_message"])
                    else:
                        st.error(st.session_state["deepseek_status_message"])

        elif ai_backend == "OpenAI API":
            openai_models = OPENAI_MODEL_OPTIONS
            current_openai_model = st.session_state.get("openai_model_select", OPENAI_MODEL)
            selected_openai_model = st.selectbox(
                "OpenAI Model",
                openai_models,
                index=openai_models.index(current_openai_model) if current_openai_model in openai_models else 0,
                key="openai_model_select",
                help="Choose the official OpenAI model used for classification and paper-grounded answers."
            )

            if "openai_api_key_saved" not in st.session_state:
                st.session_state["openai_api_key_saved"] = ""
            if "openai_verified" not in st.session_state:
                st.session_state["openai_verified"] = False
            if "openai_status_message" not in st.session_state:
                st.session_state["openai_status_message"] = ""

            configured_openai_key = get_openai_api_key()
            if configured_openai_key and st.session_state.get("openai_verified", False):
                st.success(f"OpenAI API is connected, current model: {selected_openai_model}")
            elif configured_openai_key:
                st.info("OpenAI API key is saved. Click Test OpenAI Connection once to verify it.")
            else:
                st.warning("OpenAI API key is not configured.")

            with st.expander("OpenAI API settings", expanded=not bool(configured_openai_key)):
                st.caption("For local testing, enter the key here; it will stay saved during this Streamlit session.")
                openai_key_input = st.text_input(
                    "OpenAI API Key",
                    type="password",
                    value=st.session_state.get("openai_api_key_saved", ""),
                    placeholder="sk-...",
                    key="openai_api_key_input"
                )
                if st.button("Save & Test OpenAI", type="secondary", use_container_width=True):
                    st.session_state["openai_api_key_saved"] = openai_key_input.strip()
                    ok_openai, msg_openai = test_openai_connection(st.session_state["openai_api_key_saved"], selected_openai_model)
                    st.session_state["openai_verified"] = ok_openai
                    st.session_state["openai_status_message"] = msg_openai
                    st.rerun()
                if st.session_state.get("openai_status_message"):
                    if st.session_state.get("openai_verified", False):
                        st.success(st.session_state["openai_status_message"])
                    else:
                        st.error(st.session_state["openai_status_message"])

        def submit_universe_question():
            q = st.session_state.get("universe_question_input", "").strip()
            if q:
                st.session_state["universe_pending_question"] = q

        if "universe_question_input" not in st.session_state:
            st.session_state["universe_question_input"] = st.session_state.get("universe_question", "")

        st.markdown("Ask a question about the Antarctic Ice Sheet review paper:")
        st.text_input(
            "Ask a question about the Antarctic Ice Sheet review paper",
            key="universe_question_input",
            placeholder="Example: Why is grounding line retreat important for future sea-level rise?",
            label_visibility="collapsed",
            on_change=submit_universe_question
        )
        ask_button_label = "Search evidence" if ai_backend == "Evidence only" else "Ask AI and focus map"
        if st.button(ask_button_label, type="primary", use_container_width=True):
            submit_universe_question()

        pending_question = st.session_state.pop("universe_pending_question", "").strip()
        feedback_box = st.empty()

        if pending_question:
            if st.session_state.get("ai_backend", "Evidence only") == "Evidence only":
                feedback_box.info("Searching the paper and focusing the matching knowledge module...")
            else:
                feedback_box.info("AI is locating the matching knowledge module and retrieving paper passages...")
            matched_topic, matched_parent, score, classifier_source = classify_universe_question_with_ai(pending_question, universe_topic_index, backend=st.session_state.get("ai_backend", "Evidence only"))
            st.session_state["universe_question"] = pending_question
            st.session_state["universe_focus_topic"] = matched_topic
            st.session_state["universe_focus_parent"] = matched_parent
            st.session_state["universe_match_score"] = score
            st.session_state["universe_classifier_source"] = classifier_source
            st.session_state["universe_focus_source"] = "ai"
            st.session_state["universe_focus_token"] = st.session_state.get("universe_focus_token", 0) + 1
            st.rerun()

        active_question = st.session_state.get("universe_question", "").strip()
        if active_question:
            matched_topic = st.session_state.get("universe_focus_topic", "Antarctic Ice Sheet")
            matched_parent = st.session_state.get("universe_focus_parent", "Core system")
            display_module = matched_topic if matched_parent in ["Core system", "Research area"] else f"{matched_parent} / {matched_topic}"
            classifier_source = st.session_state.get("universe_classifier_source", "keyword_fallback")
            if classifier_source in ["ai", "deepseek", "openai"]:
                backend_name = "DeepSeek" if classifier_source == "deepseek" else ("OpenAI" if classifier_source == "openai" else "AI")
                st.info(f"{backend_name} matched this question to **{display_module}**. The map is focused above; evidence and generated content appear below.")
            else:
                st.info(f"This question matches **{display_module}**. Evidence-only mode used keyword matching; paper passages appear below.")

    # Full-width evidence and answer area below the map + Copilot workspace.
    active_question = st.session_state.get("universe_question", "").strip()
    if active_question:
        matched_topic = st.session_state.get("universe_focus_topic", "Antarctic Ice Sheet")
        matched_parent = st.session_state.get("universe_focus_parent", "Core system")
        display_module = matched_topic if matched_parent in ["Core system", "Research area"] else f"{matched_parent} / {matched_topic}"
        classifier_source = st.session_state.get("universe_classifier_source", "keyword_fallback")

        topic_keywords = [matched_topic]
        if matched_parent not in ["Core system", "Research area"]:
            topic_keywords.append(matched_parent)
        keywords = list(dict.fromkeys(extract_keywords(active_question) + extract_keywords(" ".join(topic_keywords))))
        results = search_pages(pages, keywords, 5)

        st.divider()
        st.subheader("Evidence and AI Answer")
        if classifier_source in ["ai", "deepseek", "openai"]:
            backend_name = "DeepSeek" if classifier_source == "deepseek" else ("OpenAI" if classifier_source == "openai" else "AI")
            st.info(f"{backend_name} matched this question to **{display_module}**. The map is focused above.")
        else:
            st.info(f"This question matches **{display_module}**. Evidence-only mode used keyword matching.")

        if not results:
            st.warning("No relevant passages found.")
        else:
            with st.expander("Retrieved passages from the paper", expanded=False):
                for r in results:
                    st.markdown(f"**Page {r['page']} | Score: {r['score']}**")
                    st.write(r["text"][:1600] + "...")

            current_backend = st.session_state.get("ai_backend", "Evidence only")
            backend_ready = (current_backend == "DeepSeek API" and bool(get_deepseek_api_key())) or (current_backend == "OpenAI API" and bool(get_openai_api_key())) or (current_backend == "Local Ollama" and ok)
            if backend_ready:
                st.subheader("AI Answer")
                progress_bar = st.progress(0.0)
                text_box = st.empty()
                if classifier_source in ["ai", "deepseek", "openai"]:
                    backend_name = "DeepSeek" if classifier_source == "deepseek" else ("OpenAI" if classifier_source == "openai" else "AI")
                    answer_prefix = f"{backend_name} matched this question to **{display_module}**. "
                else:
                    answer_prefix = f"This question matches **{display_module}**. "
                try:
                    stream_ai_answer(st.session_state.get("ai_backend", "Local Ollama"), active_question, results, text_box, progress_bar, answer_prefix=answer_prefix)
                    st.success("Generation completed")
                except Exception as e:
                    st.error(f"{st.session_state.get('ai_backend', 'Local Ollama')} call failed")
                    st.code(str(e))
            else:
                st.info("AI answer generation is off or unavailable, so only retrieved paper passages are shown.")
