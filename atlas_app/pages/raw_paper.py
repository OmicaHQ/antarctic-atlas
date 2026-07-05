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

def render_raw_paper(pages, total_pages):
    st.markdown("<div class='atlas-module-title'><h1>&#128196; Read Raw Paper</h1></div>", unsafe_allow_html=True)
    search_query = st.text_input("Search within extracted paper text", placeholder="Example: grounding line, basal melt, Thwaites")
    search_keywords = extract_keywords(search_query) if search_query.strip() else []
    if search_query.strip():
        matches = search_pages(pages, search_keywords, max_results=8)
        if matches:
            page_options = [r["page"] for r in matches]
            selected_page = st.selectbox("Matching pages", page_options, format_func=lambda p: f"Page {p}")
            st.markdown("#### Search matches")
            for match in matches[:4]:
                excerpt = build_search_excerpt(match["text"], search_keywords)
                st.markdown(
                    f"""
                    <div class="ios-result-card">
                      <div class="ios-kicker">Page {match['page']} · score {match['score']}</div>
                      <div class="ios-muted">{excerpt}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.warning("No matching pages found. Showing page 1.")
            selected_page = 1
    else:
        selected_page = st.slider("Select page", 1, total_pages, 1)
    st.text_area(f"Page {selected_page}", pages[selected_page - 1]["text"], height=600)
