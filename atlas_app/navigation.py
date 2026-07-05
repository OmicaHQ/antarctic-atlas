import streamlit as st


SIDEBAR_MODULE_MAP = {
    "Research Universe": "Research Universe Explorer",
    "Antarctic System": "Antarctic System Explorer",
    "AI Visualizer": "AI Visualizer",
    "Mini Research Lab": "Mini Research Lab",
    "Research Directions": "Research Directions",
    "Read Raw Paper": "Read Raw Paper",
}


def render_landing(total_pages):
    if "entered_project" not in st.session_state:
        st.session_state["entered_project"] = False

    if not st.session_state["entered_project"]:
        st.markdown("""
        <style>
          [data-testid="stSidebar"] { display: none; }
          [data-testid="collapsedControl"] { display: none; }
          .block-container {
            max-width: 100% !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
          }
          .landing-wrap {
            min-height: 92vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background:
              radial-gradient(circle at 24% 22%, rgba(78,163,241,0.20), transparent 30%),
              radial-gradient(circle at 76% 70%, rgba(149,117,205,0.18), transparent 32%),
              linear-gradient(135deg, #030712 0%, #07111f 45%, #020617 100%);
            border-radius: 28px;
            color: #eef6ff;
            box-shadow: inset 0 0 90px rgba(78,163,241,0.12);
          }
          .landing-card {
            width: min(760px, 92vw);
            padding: 56px 58px;
            border-radius: 30px;
            border: 1px solid rgba(170,215,255,0.22);
            background: linear-gradient(180deg, rgba(8,18,34,0.80), rgba(7,15,29,0.62));
            backdrop-filter: blur(16px);
            box-shadow: 0 24px 80px rgba(0,0,0,0.42);
            text-align: center;
          }
          .landing-card h1 {
            margin: 0;
            font-size: 44px;
            letter-spacing: .2px;
          }
          .landing-card p {
            color: rgba(238,246,255,.78);
            font-size: 16px;
            margin: 18px 0 0 0;
          }
          .pdf-loaded {
            margin: 28px auto 22px auto;
            display: inline-block;
            padding: 10px 16px;
            border-radius: 999px;
            background: rgba(34,197,94,.12);
            border: 1px solid rgba(74,222,128,.28);
            color: #7CFF9B;
            font-weight: 650;
          }
          div.stButton > button {
            border-radius: 999px;
            padding: 0.7rem 1.35rem;
            font-weight: 700;
          }
        </style>
        <div class="landing-wrap">
          <div class="landing-card">
            <h1>&#127758; Antarctic Ice Sheet Research Atlas</h1>
            <p>An interactive research universe for exploring the Antarctic Ice Sheet review paper.</p>
            <div class="pdf-loaded">PDF loaded successfully, __TOTAL_PAGES__ pages</div>
          </div>
        </div>
        """.replace("__TOTAL_PAGES__", str(total_pages)), unsafe_allow_html=True)
        _, c, _ = st.columns([0.42, 0.16, 0.42])
        with c:
            if st.button("Enter Project", type="primary", use_container_width=True):
                st.session_state["entered_project"] = True
                st.rerun()
        st.stop()



def select_module():
    st.sidebar.title("Navigation")
    selected_sidebar_label = st.sidebar.radio(
        "Select",
        list(SIDEBAR_MODULE_MAP.keys()),
        key="sidebar_module_select",
    )
    return SIDEBAR_MODULE_MAP[selected_sidebar_label]
