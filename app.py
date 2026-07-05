import streamlit as st

from atlas_app.navigation import render_landing, select_module
from atlas_app.paper import load_pdf
from atlas_app.pages.ai_visualizer import render_ai_visualizer
from atlas_app.pages.antarctic_system import render_antarctic_system
from atlas_app.pages.mini_research_lab import render_mini_research_lab
from atlas_app.pages.raw_paper import render_raw_paper
from atlas_app.pages.research_directions import render_research_directions
from atlas_app.pages.research_universe import render_research_universe
from atlas_app.styles import apply_global_styles


st.set_page_config(page_title="Antarctic Research Atlas", layout="wide", initial_sidebar_state="collapsed")

pages = load_pdf()
total_pages = len(pages)

render_landing(total_pages)
module = select_module()
apply_global_styles()

if module == "Research Universe Explorer":
    render_research_universe(pages, total_pages)
elif module == "Research Directions":
    render_research_directions(pages, total_pages)
elif module == "Antarctic System Explorer":
    render_antarctic_system(pages, total_pages)
elif module == "AI Visualizer":
    render_ai_visualizer(pages, total_pages)
elif module == "Mini Research Lab":
    render_mini_research_lab(pages, total_pages)
elif module == "Read Raw Paper":
    render_raw_paper(pages, total_pages)
