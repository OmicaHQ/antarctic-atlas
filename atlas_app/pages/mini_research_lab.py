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

def render_mini_research_lab(pages, total_pages):
    st.markdown("<div class='atlas-module-title'><h1>&#129514; Mini Research Lab</h1></div>", unsafe_allow_html=True)
    lab_choice = st.radio(
        "Choose an experiment",
        ["Glacier Flow Simulator", "Ice Shelf Buttressing Lab", "Hydrofracture & Ice Shelf Collapse Lab"],
        horizontal=True
    )

    if lab_choice == "Glacier Flow Simulator":
        st.header("Interactive Antarctic Ice Sheet Simulator")

        with st.expander("Legend and visual guide", expanded=False):
            st.markdown("""
            - **White-blue surface:** Grounded ice sheet. Darker blue means thicker ice.
            - **Light blue floating surface:** Floating ice shelf extending over the ocean.
            - **Brown surface:** Bedrock beneath the ice.
            - **Transparent blue plane:** Ocean surface.
            - **Red line:** Grounding line, where grounded ice begins to float.
            - **Orange line arrows:** Ice flow direction.
            - **Cyan moving particles:** Ice parcels moving downstream.
            - **Orange/red subsurface patch:** Warm Circumpolar Deep Water intrusion.
            """)


        preset = st.selectbox(
            "Preset glacier mode",
            ["Custom", "Thwaites-like", "Pine Island-like", "Totten-like"]
        )
        st.caption(
            "Choose a conceptual glacier setting. The preset changes the default ocean forcing, ice shelf thickness, "
            "basal friction, and bed slope to resemble different Antarctic glacier styles."
        )

        if preset == "Thwaites-like":
            default_ocean_temp = 2.0
            default_snowfall = 1.0
            default_shelf = 160.0
            default_friction = 0.25
            default_slope = 3.2
        elif preset == "Pine Island-like":
            default_ocean_temp = 1.7
            default_snowfall = 1.1
            default_shelf = 180.0
            default_friction = 0.30
            default_slope = 2.8
        elif preset == "Totten-like":
            default_ocean_temp = 1.2
            default_snowfall = 1.5
            default_shelf = 240.0
            default_friction = 0.45
            default_slope = 2.0
        else:
            default_ocean_temp = 0.0
            default_snowfall = 1.0
            default_shelf = 200.0
            default_friction = 0.5
            default_slope = 1.0

        col1, col2, col3 = st.columns(3)

        with col1:
            year = st.slider("Simulation Year", 2025, 2100, 2025, 5)
            st.caption("Controls long-term climate forcing. Later years increase ocean warming and ice shelf thinning.")

            air_temp = st.slider("Air Temperature (°C)", -50.0, 0.0, -20.0, 1.0)
            st.caption("Represents atmospheric warming. Higher air temperature increases surface-related ice loss.")

            ocean_temp = st.slider("Ocean Temperature / CDW Forcing (°C)", -2.0, 5.0, default_ocean_temp, 0.1)
            st.caption("Represents warm ocean water forcing beneath ice shelves. Higher values enhance basal melting and retreat.")

        with col2:
            snowfall = st.slider("Snowfall / Accumulation (m/yr)", 0.0, 5.0, default_snowfall, 0.1)
            st.caption("Represents annual snow accumulation. More snowfall thickens the ice and partly offsets melting.")

            ice_shelf_thickness = st.slider("Ice Shelf Thickness (m)", 50.0, 500.0, default_shelf, 10.0)
            st.caption("Represents the strength of the floating ice shelf. Thicker shelves provide stronger buttressing.")

            basal_friction = st.slider("Basal Friction (0=low, 1=high)", 0.0, 1.0, default_friction, 0.05)
            st.caption("Controls resistance at the ice-bed interface. Lower friction allows faster ice flow.")

        with col3:
            bed_slope = st.slider("Bed Slope / Retrograde Bed Strength (°)", 0.0, 5.0, default_slope, 0.1)
            st.caption("Represents how strongly the bed deepens inland. Higher values make MISI-like retreat easier.")

            misi_on = st.checkbox("Enable MISI feedback", value=True)
            st.caption("Turns on Marine Ice Sheet Instability feedback. When active, retreat can accelerate on retrograde beds.")

            shelf_collapse = st.checkbox("Ice Shelf Collapse", value=False)
            st.caption("Simulates loss of ice shelf buttressing. When active, grounded ice flows faster toward the ocean.")

            cdw_intrusion = st.checkbox("CDW Warm Water Intrusion", value=True)
            st.caption("Adds warm Circumpolar Deep Water beneath the ice shelf, increasing basal melt and grounding-line retreat.")

        time_factor = (year - 2025) / (2100 - 2025)

        effective_ocean = ocean_temp + (1.2 * time_factor if cdw_intrusion else 0.2 * time_factor)
        effective_shelf = ice_shelf_thickness * (1 - 0.45 * time_factor if shelf_collapse else 1 - 0.12 * time_factor)
        effective_shelf = max(effective_shelf, 20.0)

        retreat = (
            8
            + effective_ocean * 7.0
            + bed_slope * 5.0
            - effective_shelf * 0.045
            - basal_friction * 9.0
        )

        if misi_on and bed_slope > 1.5 and effective_ocean > 0.5:
            misi_factor = 1 + 0.55 * bed_slope + 0.25 * effective_ocean
            retreat *= misi_factor

        if shelf_collapse:
            retreat *= 1.45

        if cdw_intrusion:
            retreat *= 1.18

        retreat = float(np.clip(retreat, 0, 68))
        glacier_length = 92 - retreat
        grounding_line_x = glacier_length

        nx, ny = 115, 62
        x = np.linspace(0, 105, nx)
        y = np.linspace(-32, 32, ny)
        X, Y = np.meshgrid(x, y)

        base_thickness = (
            620
            + snowfall * 110
            - effective_ocean * 55
            + effective_shelf * 0.35
            - bed_slope * 38
            - time_factor * 80
        )

        base_thickness = max(base_thickness, 120)

        center_shape = np.exp(-(Y / 20) ** 2)
        downstream_thinning = np.clip(1 - X / 112, 0, 1) ** 1.45
        surface_texture = 1 + 0.04 * np.sin(X / 7) * np.cos(Y / 6)

        thickness = base_thickness * center_shape * downstream_thinning * surface_texture
        thickness = np.clip(thickness, 12, None)

        bed = -150 - bed_slope * X * 9 + 65 * np.exp(-(Y / 25) ** 2)

        grounded_mask = X <= grounding_line_x
        shelf_mask = (X > grounding_line_x) & (X <= grounding_line_x + 18) & (not shelf_collapse)

        grounded_ice = np.where(grounded_mask, thickness, np.nan)

        shelf_thickness = effective_shelf * 0.55 * np.exp(-((X - grounding_line_x) / 22)) * np.exp(-(Y / 27) ** 2)
        shelf_surface = 70 + shelf_thickness
        floating_shelf = np.where(shelf_mask, shelf_surface, np.nan)

        bed_visible = np.where(X <= grounding_line_x + 22, bed, np.nan)

        ocean_level = np.zeros_like(X)
        ocean = np.where(X >= grounding_line_x - 3, ocean_level, np.nan)

        velocity_strength = max(
            0.08,
            0.35
            + effective_ocean * 0.30
            + (1 - basal_friction) * 1.45
            + bed_slope * 0.18
            + time_factor * 0.45
        )

        if misi_on and retreat > 20:
            velocity_strength *= 1.45

        if shelf_collapse:
            velocity_strength *= 1.35

        local_speed = velocity_strength * (0.25 + X / 95) * (thickness / np.nanmax(thickness))

        fig = go.Figure()

        fig.add_trace(go.Surface(
            z=bed_visible,
            x=X,
            y=Y,
            colorscale=[[0.0, "rgb(80,55,35)"], [0.5, "rgb(150,110,70)"], [1.0, "rgb(215,190,135)"]],
            opacity=0.36,
            showscale=False,
            name="Bedrock"
        ))

        fig.add_trace(go.Surface(
            z=ocean,
            x=X,
            y=Y,
            colorscale=[[0.0, "rgb(135,210,245)"], [1.0, "rgb(135,210,245)"]],
            opacity=0.32,
            showscale=False,
            name="Ocean"
        ))

        glacier_colorscale = [
            [0.00, "rgb(252,254,255)"],
            [0.20, "rgb(220,245,255)"],
            [0.45, "rgb(135,215,250)"],
            [0.70, "rgb(45,145,220)"],
            [1.00, "rgb(0,55,160)"]
        ]

        fig.add_trace(go.Surface(
            z=grounded_ice,
            x=X,
            y=Y,
            surfacecolor=thickness,
            colorscale=glacier_colorscale,
            opacity=0.97,
            colorbar=dict(title="Ice thickness (m)"),
            name="Grounded Ice",
            hovertemplate="Grounded ice<br>x=%{x:.1f} km<br>y=%{y:.1f} km<br>thickness=%{z:.1f} m<extra></extra>"
        ))

        fig.add_trace(go.Surface(
            z=floating_shelf,
            x=X,
            y=Y,
            colorscale=[[0.0, "rgb(205,245,255)"], [1.0, "rgb(150,230,255)"]],
            opacity=0.72,
            showscale=False,
            name="Floating Ice Shelf",
            hovertemplate="Floating ice shelf<br>x=%{x:.1f} km<br>y=%{y:.1f} km<extra></extra>"
        ))

        gl_y = np.linspace(-30, 30, 80)
        gl_x = np.full_like(gl_y, grounding_line_x)
        gl_z = np.full_like(gl_y, 90)

        fig.add_trace(go.Scatter3d(
            x=gl_x,
            y=gl_y,
            z=gl_z,
            mode="lines",
            line=dict(color="rgb(230,30,30)", width=8),
            name="Grounding Line"
        ))

        if cdw_intrusion:
            plume_y = np.linspace(-18, 18, 30)
            plume_x = np.linspace(grounding_line_x - 8, grounding_line_x + 22, 30)
            PX, PY = np.meshgrid(plume_x, plume_y)
            PZ = -25 + 5 * np.sin(PX / 6)
            fig.add_trace(go.Surface(
                z=PZ,
                x=PX,
                y=PY,
                colorscale=[[0.0, "rgb(255,210,80)"], [1.0, "rgb(255,70,20)"]],
                opacity=0.38,
                showscale=False,
                name="CDW Intrusion"
            ))

        arrow_x, arrow_y, arrow_z = [], [], []
        for i in range(8, nx - 15, 14):
            for j in range(7, ny - 7, 13):
                if not np.isfinite(grounded_ice[j, i]):
                    continue

                speed = local_speed[j, i]
                dx = 3.6 * (0.9 + 0.22 * speed)
                dy = -Y[j, i] / 44 * 1.2

                x0 = X[j, i]
                y0 = Y[j, i]
                z0 = grounded_ice[j, i] + 10
                x1 = x0 + dx
                y1 = y0 + dy
                z1 = z0 + 1

                arrow_x += [x0, x1, None]
                arrow_y += [y0, y1, None]
                arrow_z += [z0, z1, None]

                arrow_x += [x1, x1 - 0.9, None, x1, x1 - 0.9, None]
                arrow_y += [y1, y1 + 0.45, None, y1, y1 - 0.45, None]
                arrow_z += [z1, z1, None, z1, z1, None]

        fig.add_trace(go.Scatter3d(
            x=arrow_x,
            y=arrow_y,
            z=arrow_z,
            mode="lines",
            line=dict(color="rgb(255,155,45)", width=4),
            name="Ice Flow Direction"
        ))

        n_streams = 8
        n_particles_each = 18
        stream_ys = np.linspace(-17, 17, n_streams)

        # Particle animation fix:
        # The previous version used modulo wrapping:
        #     px = (x0 + speed * t) % grounding_line_x
        # When a particle crossed the grounding line, Plotly sometimes interpolated it
        # from the downstream end back to the upstream start, which looked like reverse flow
        # under high-speed / short-glacier parameter combinations.
        # This version uses one-way particles: they enter from upstream, move downstream,
        # and disappear after crossing the grounding line. No point is ever moved backward.
        flow_length = max(grounding_line_x, 8)
        particle_x0, particle_y0 = [], []
        for sy in stream_ys:
            for k in range(n_particles_each):
                particle_x0.append(-0.75 * flow_length + (k / (n_particles_each - 1)) * 1.65 * flow_length)
                particle_y0.append(sy)

        particle_x0 = np.array(particle_x0)
        particle_y0 = np.array(particle_y0)

        frame_count = 72
        downstream_step = (1.55 * flow_length / frame_count) * (0.65 + 0.18 * velocity_strength)

        def particle_frame(t):
            px_raw = particle_x0 + t * downstream_step
            visible = (px_raw >= 0) & (px_raw <= flow_length)

            px = np.where(visible, px_raw, np.nan)
            py = np.where(visible, particle_y0 + 1.2 * np.sin(px_raw / 9 + particle_y0 / 5), np.nan)

            p_center = np.exp(-(py / 20) ** 2)
            p_down = np.clip(1 - px / 112, 0, 1) ** 1.45
            p_texture = 1 + 0.04 * np.sin(px / 7) * np.cos(py / 6)

            pz = base_thickness * p_center * p_down * p_texture + 14
            pz = np.where(visible, pz, np.nan)
            return px, py, pz

        px, py, pz = particle_frame(0)

        fig.add_trace(go.Scatter3d(
            x=px,
            y=py,
            z=pz,
            mode="markers",
            marker=dict(size=3.0, color="rgb(0,235,210)", opacity=0.9),
            name="Moving Ice Particles"
        ))

        particle_trace_index = len(fig.data) - 1

        frames = []
        for t in range(frame_count):
            px, py, pz = particle_frame(t)
            frames.append(go.Frame(
                data=[go.Scatter3d(
                    x=px,
                    y=py,
                    z=pz,
                    mode="markers",
                    marker=dict(size=3.0, color="rgb(0,235,210)", opacity=0.9)
                )],
                traces=[particle_trace_index],
                name=str(t)
            ))

        fig.frames = frames

        fig.update_layout(
            height=760,
            margin=dict(l=0, r=0, t=35, b=0),
            scene=dict(
                xaxis_title="Distance downstream (km)",
                yaxis_title="Glacier width (km)",
                zaxis_title="Elevation / Thickness (m)",
                bgcolor="white",
                camera=dict(eye=dict(x=1.65, y=-1.9, z=1.15))
            ),
            updatemenus=[dict(
                type="buttons",
                direction="left",
                showactive=False,
                x=0.02,
                y=0.95,
                buttons=[
                    dict(
                        label="Play ice flow",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 85, "redraw": True},
                            "fromcurrent": True,
                            "mode": "immediate",
                            "transition": {"duration": 0},
                            "loop": False
                        }]
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "transition": {"duration": 0}
                        }]
                    )
                ]
            )]
        )

        # Render the animated Plotly figure inside an isolated HTML iframe.
        # This keeps the animation button while avoiding Streamlit's frontend DOM
        # removeChild conflict that can happen with st.plotly_chart + 3D frames.
        plot_html = fig.to_html(
            include_plotlyjs="inline",
            full_html=False,
            config={"responsive": True, "displayModeBar": True}
        )
        components.html(plot_html, height=790, scrolling=False)

        ice_loss = (
            (abs(air_temp) * 0.04 + max(effective_ocean, 0) * 2.6)
            * (1.25 - basal_friction * 0.65)
            / (snowfall + 0.5)
        )
        sea_level = retreat * 0.013
        velocity = velocity_strength * 1.8

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ice Loss", f"{ice_loss:.2f}")
        c2.metric("Grounding Line Retreat", f"{retreat:.1f} km")
        c3.metric("Ice Flow Velocity", f"{velocity:.2f} km/yr")
        c4.metric("Sea Level Contribution", f"{sea_level:.2f} m")


    elif lab_choice == "Ice Shelf Buttressing Lab":
        st.header("Ice Shelf Buttressing Lab")

        with st.expander("Legend and mechanism guide", expanded=False):
            st.markdown("""
            - **Dark blue block:** Grounded ice sheet flowing toward the ocean.
            - **Light blue block:** Floating ice shelf.
            - **Orange arrows:** Relative ice-flow speed.
            - **Brown bump:** Pinning point / local topographic resistance.
            - **Red dashed line:** Grounding line.
            - **Gray removed zone:** Calved or collapsed ice-shelf area.
            - **Blue back-stress arrows:** Buttressing force pushing back against grounded ice.
            """)


        st.caption(
            "This conceptual lab focuses on one mechanism: a floating ice shelf can provide back stress "
            "that slows down inland grounded ice. When the shelf thins, calves, or loses pinning points, "
            "buttressing weakens and grounded ice accelerates."
        )

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            shelf_thickness = st.slider("Ice Shelf Thickness (m)", 50.0, 700.0, 260.0, 10.0, key="buttress_shelf_thickness")
            st.caption("Thicker ice shelves provide stronger mechanical support to inland grounded ice.")

            ocean_temp_b = st.slider("Ocean Temperature Forcing (°C)", -2.0, 5.0, 1.0, 0.1, key="buttress_ocean_temp")
            st.caption("Warmer ocean water increases basal melting and weakens the ice shelf from below.")

        with col_b:
            pinning_strength = st.slider("Pinning Point Strength (%)", 0.0, 100.0, 55.0, 5.0, key="buttress_pinning")
            st.caption("Pinning points are bedrock highs or obstacles that help the ice shelf resist flow.")

            calving_extent = st.slider("Calving / Shelf Loss (%)", 0.0, 100.0, 20.0, 5.0, key="buttress_calving")
            st.caption("Larger calving extent removes floating shelf area and reduces buttressing.")

        with col_c:
            lateral_confinement = st.slider("Lateral Confinement (%)", 0.0, 100.0, 60.0, 5.0, key="buttress_lateral")
            st.caption("Narrow embayments and side walls can strengthen buttressing by resisting shelf spreading.")

            bed_slope_b = st.slider("Retrograde Bed Slope (°)", 0.0, 5.0, 1.5, 0.1, key="buttress_bed_slope")
            st.caption("A stronger retrograde bed makes grounding-line retreat more unstable.")

        thickness_factor = shelf_thickness / 700.0
        pinning_factor = pinning_strength / 100.0
        lateral_factor = lateral_confinement / 100.0
        calving_factor = calving_extent / 100.0
        ocean_factor = max(ocean_temp_b, 0.0) / 5.0

        buttressing_index = (
            100
            * (0.45 * thickness_factor + 0.30 * pinning_factor + 0.25 * lateral_factor)
            * (1 - 0.75 * calving_factor)
            * (1 - 0.45 * ocean_factor)
        )
        buttressing_index = float(np.clip(buttressing_index, 0, 100))

        velocity = 180 + (100 - buttressing_index) * 8.5 + ocean_factor * 260 + bed_slope_b * 55
        retreat_b = float(np.clip((100 - buttressing_index) * 0.18 + ocean_factor * 8 + bed_slope_b * 2.0, 0, 45))
        sea_level_b = retreat_b * 0.011

        grounding_line_x = 42
        shelf_full_length = 42
        remaining_shelf_length = shelf_full_length * (1 - calving_factor)
        shelf_end = grounding_line_x + remaining_shelf_length
        removed_start = shelf_end
        removed_end = grounding_line_x + shelf_full_length

        fig = go.Figure()

        fig.add_shape(
            type="rect",
            x0=grounding_line_x,
            x1=92,
            y0=-1.6,
            y1=1.6,
            line=dict(width=0),
            fillcolor="rgba(120,210,245,0.35)",
            layer="below"
        )

        bed_x = np.linspace(0, 92, 180)
        bed_y = -1.35 - 0.006 * bed_slope_b * bed_x + 0.16 * np.exp(-((bed_x - 56) / 6) ** 2)
        fig.add_trace(go.Scatter(
            x=bed_x,
            y=bed_y,
            mode="lines",
            line=dict(color="rgb(130,85,45)", width=5),
            name="Bedrock"
        ))

        ice_top = 0.82
        ice_bottom = -0.35
        fig.add_shape(
            type="rect",
            x0=0,
            x1=grounding_line_x,
            y0=ice_bottom,
            y1=ice_top,
            line=dict(color="rgb(0,55,160)", width=2),
            fillcolor="rgba(20,110,210,0.86)",
            layer="above"
        )

        shelf_thick_vis = 0.28 + 0.55 * thickness_factor
        fig.add_shape(
            type="rect",
            x0=grounding_line_x,
            x1=shelf_end,
            y0=-shelf_thick_vis / 2,
            y1=shelf_thick_vis / 2,
            line=dict(color="rgb(70,170,220)", width=2),
            fillcolor="rgba(170,235,255,0.80)",
            layer="above"
        )

        if calving_extent > 0:
            fig.add_shape(
                type="rect",
                x0=removed_start,
                x1=removed_end,
                y0=-0.42,
                y1=0.42,
                line=dict(color="rgba(120,120,120,0.7)", width=1, dash="dash"),
                fillcolor="rgba(150,150,150,0.18)",
                layer="above"
            )
            fig.add_annotation(
                x=(removed_start + removed_end) / 2,
                y=0.65,
                text="calved / lost shelf area",
                showarrow=False,
                font=dict(size=12, color="gray")
            )

        pin_x = grounding_line_x + remaining_shelf_length * 0.58 if remaining_shelf_length > 5 else grounding_line_x + 3
        pin_size = 0.16 + 0.45 * pinning_factor
        if remaining_shelf_length > 4 and pinning_strength > 0:
            fig.add_shape(
                type="circle",
                x0=pin_x - 2.4 * pin_size,
                x1=pin_x + 2.4 * pin_size,
                y0=-0.75 - pin_size,
                y1=-0.75 + pin_size,
                line=dict(color="rgb(120,70,35)", width=2),
                fillcolor="rgba(155,95,45,0.85)",
                layer="above"
            )
            fig.add_annotation(
                x=pin_x,
                y=-1.05,
                text="pinning point",
                showarrow=False,
                font=dict(size=12, color="rgb(100,65,35)")
            )

        fig.add_trace(go.Scatter(
            x=[grounding_line_x, grounding_line_x],
            y=[-1.25, 1.2],
            mode="lines",
            line=dict(color="red", width=4, dash="dash"),
            name="Grounding Line"
        ))

        arrow_count = 6
        speed_scale = np.clip((velocity - 180) / 950, 0.15, 1.0)
        for k in range(arrow_count):
            y_arrow = -0.05 + (k - (arrow_count - 1) / 2) * 0.17
            x0 = 8 + k * 4.5
            x1 = x0 + 6 + 9 * speed_scale
            fig.add_annotation(
                x=x1,
                y=y_arrow,
                ax=x0,
                ay=y_arrow,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1.4,
                arrowwidth=2.8 + 2.8 * speed_scale,
                arrowcolor="rgb(255,140,40)"
            )

        backstress = buttressing_index / 100
        for k in range(4):
            yb = -0.35 + k * 0.23
            fig.add_annotation(
                x=grounding_line_x - 7 * backstress,
                y=yb,
                ax=grounding_line_x + 9 * backstress,
                ay=yb,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1.1,
                arrowwidth=1.5 + 3 * backstress,
                arrowcolor="rgba(40,90,190,0.8)"
            )

        fig.add_annotation(x=18, y=1.05, text="<b>Grounded ice</b>", showarrow=False, font=dict(size=14, color="white"))
        fig.add_annotation(x=grounding_line_x + max(remaining_shelf_length, 5) / 2, y=0.55, text="<b>Floating ice shelf</b>", showarrow=False, font=dict(size=13, color="rgb(20,85,130)"))
        fig.add_annotation(x=75, y=-1.05, text="<b>Ocean</b>", showarrow=False, font=dict(size=14, color="rgb(30,120,170)"))

        fig.update_layout(
            title="Conceptual Ice Shelf Buttressing Experiment",
            height=520,
            margin=dict(l=20, r=20, t=60, b=20),
            xaxis=dict(title="Distance downstream (km)", range=[0, 92], showgrid=False),
            yaxis=dict(visible=False, range=[-1.65, 1.35]),
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True, key="plot_buttressing_lab")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Buttressing Index", f"{buttressing_index:.0f} / 100")
        c2.metric("Ice Flow Velocity", f"{velocity:.0f} m/yr")
        c3.metric("Grounding Line Retreat", f"{retreat_b:.1f} km")
        c4.metric("Sea Level Contribution", f"{sea_level_b:.2f} m")

        st.markdown("""
        **How to read this lab:**
        When the ice shelf is thick, laterally confined, and pinned to bedrock highs, it pushes back against the grounded ice.
        This reduces ice velocity and stabilizes the grounding line. When the shelf thins or calves away, the back stress weakens,
        orange flow arrows become stronger, and the grounding-line retreat estimate increases.
        """)


    elif lab_choice == "Hydrofracture & Ice Shelf Collapse Lab":
        st.header("Hydrofracture & Ice Shelf Collapse Lab")

        with st.expander("Legend and collapse sequence", expanded=False):
            st.markdown("""
            - **Ice-blue slab:** Floating ice shelf.
            - **Deep blue ponds:** Surface meltwater ponds.
            - **Red cracks:** Hydrofracture pathways driven by water-filled crevasses.
            - **Gray separated blocks:** Collapsed / fragmented ice shelf pieces.
            - **Orange arrows:** Post-collapse acceleration of inland ice.
            - **Dark ocean background:** Open ocean beneath and around the floating shelf.
            """)


        st.caption(
            "This conceptual lab visualizes how atmospheric warming can create surface meltwater, "
            "how meltwater can deepen crevasses through hydrofracture, and how an ice shelf can fragment. "
            "It is designed for visual explanation rather than numerical prediction."
        )

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            surface_melt = st.slider("Surface Melt Intensity (%)", 0.0, 100.0, 45.0, 5.0, key="hydro_surface_melt")
            st.caption("Higher surface melt produces more melt ponds on top of the ice shelf.")

            firn_capacity = st.slider("Firn Air Capacity (%)", 0.0, 100.0, 45.0, 5.0, key="hydro_firn")
            st.caption("Higher firn capacity absorbs meltwater and delays ponding and fracture.")

        with col_b:
            crevasse_density = st.slider("Crevasse Density (%)", 0.0, 100.0, 40.0, 5.0, key="hydro_crevasse_density")
            st.caption("More pre-existing crevasses make hydrofracture easier once meltwater is present.")

            ice_shelf_strength = st.slider("Ice Shelf Strength (%)", 0.0, 100.0, 60.0, 5.0, key="hydro_shelf_strength")
            st.caption("Stronger ice resists crack propagation and large-scale breakup.")

        with col_c:
            ocean_swell = st.slider("Ocean Swell / Flexure (%)", 0.0, 100.0, 35.0, 5.0, key="hydro_swell")
            st.caption("Ocean swell and flexure can help existing fractures widen and connect.")

            play_stage = st.slider("Collapse Stage", 0, 4, 2, 1, key="hydro_stage")
            st.caption("Manually move through the collapse sequence: intact shelf ->ponds ->cracks ->fragmentation ->post-collapse acceleration.")

        ponding_index = np.clip((surface_melt * 0.75 - firn_capacity * 0.45 + 20) / 100, 0, 1)
        fracture_index = np.clip(
            0.45 * ponding_index
            + 0.30 * (crevasse_density / 100)
            + 0.20 * (ocean_swell / 100)
            - 0.25 * (ice_shelf_strength / 100),
            0, 1
        )
        collapse_risk = np.clip(
            100 * (0.55 * fracture_index + 0.35 * ponding_index + 0.10 * (ocean_swell / 100)),
            0, 100
        )

        if collapse_risk < 25:
            auto_stage = 0
        elif collapse_risk < 45:
            auto_stage = 1
        elif collapse_risk < 65:
            auto_stage = 2
        elif collapse_risk < 82:
            auto_stage = 3
        else:
            auto_stage = 4

        stage = max(play_stage, auto_stage)

        buttressing_remaining = np.clip(100 - collapse_risk * 0.85 - (stage >= 3) * 25, 0, 100)
        post_collapse_velocity = 300 + (100 - buttressing_remaining) * 18
        sea_level_signal = (100 - buttressing_remaining) * 0.018

        st.info(
            f"Auto-diagnosed stage from the sliders: **{auto_stage}**. "
            f"The displayed stage is the larger of the auto-diagnosed stage and the manual Collapse Stage slider."
        )

        fig = go.Figure()

        # Ocean background
        fig.add_shape(
            type="rect",
            x0=0,
            x1=100,
            y0=0,
            y1=44,
            line=dict(width=0),
            fillcolor="rgba(10,45,85,0.92)",
            layer="below"
        )

        # Ice shelf base geometry
        shelf_y0, shelf_y1 = 12, 32
        shelf_x0, shelf_x1 = 8, 92

        if stage < 3:
            # Intact or cracking shelf
            fig.add_shape(
                type="rect",
                x0=shelf_x0,
                x1=shelf_x1,
                y0=shelf_y0,
                y1=shelf_y1,
                line=dict(color="rgb(120,220,250)", width=2),
                fillcolor="rgba(185,240,255,0.92)",
                layer="above"
            )
        else:
            # Fragmented shelf blocks
            blocks = [
                (8, 25, 13, 31, -1.2),
                (28, 42, 11, 28, 1.5),
                (46, 60, 15, 33, -0.8),
                (64, 78, 10, 27, 1.0),
                (81, 93, 14, 30, -1.6),
            ]
            for x0, x1, y0, y1, dy in blocks:
                fig.add_shape(
                    type="rect",
                    x0=x0,
                    x1=x1,
                    y0=y0 + dy,
                    y1=y1 + dy,
                    line=dict(color="rgb(165,220,235)", width=2),
                    fillcolor="rgba(200,245,255,0.78)",
                    layer="above"
                )

            # Open-water gaps
            for gx in [26, 44, 62, 79]:
                fig.add_shape(
                    type="rect",
                    x0=gx,
                    x1=gx + 2.8,
                    y0=8,
                    y1=36,
                    line=dict(width=0),
                    fillcolor="rgba(5,35,75,0.92)",
                    layer="above"
                )

        # Grounded ice / inland side
        fig.add_shape(
            type="rect",
            x0=0,
            x1=15,
            y0=10,
            y1=34,
            line=dict(color="rgb(0,65,160)", width=2),
            fillcolor="rgba(40,120,215,0.92)",
            layer="above"
        )
        fig.add_annotation(x=7.5, y=35.5, text="<b>Grounded ice</b>", showarrow=False, font=dict(color="rgb(0,45,120)", size=13))
        fig.add_annotation(x=50, y=34.8, text="<b>Floating ice shelf</b>", showarrow=False, font=dict(color="rgb(15,100,145)", size=15))
        fig.add_annotation(x=82, y=6.5, text="<b>Ocean</b>", showarrow=False, font=dict(color="white", size=15))

        # Surface melt ponds
        pond_positions = [
            (22, 27.5, 5.2, 1.5),
            (37, 25.0, 6.0, 1.7),
            (52, 28.5, 5.6, 1.4),
            (67, 24.3, 6.3, 1.8),
            (80, 27.8, 4.6, 1.3),
        ]
        n_ponds = int(np.clip(round(ponding_index * len(pond_positions) + (stage >= 1) * 2), 0, len(pond_positions)))
        if stage >= 1:
            for px, py, w, h in pond_positions[:n_ponds]:
                fig.add_shape(
                    type="circle",
                    x0=px - w / 2,
                    x1=px + w / 2,
                    y0=py - h / 2,
                    y1=py + h / 2,
                    line=dict(color="rgb(0,95,210)", width=2),
                    fillcolor="rgba(0,120,255,0.80)",
                    layer="above"
                )

        # Hydrofracture cracks
        crack_xs = [25, 39, 55, 70, 83]
        crack_depth = 3 + 18 * fracture_index + stage * 3
        if stage >= 2:
            for c_i, cx in enumerate(crack_xs[:max(2, int(2 + crevasse_density / 25))]):
                y_top = shelf_y1 - 1.5
                y_bottom = max(shelf_y0 - 4, y_top - crack_depth)
                fig.add_trace(go.Scatter(
                    x=[cx, cx + 0.8 * np.sin(c_i), cx - 0.5 * np.cos(c_i)],
                    y=[y_top, (y_top + y_bottom) / 2, y_bottom],
                    mode="lines",
                    line=dict(color="rgb(220,20,35)", width=5 if stage < 4 else 7),
                    name="Hydrofracture" if c_i == 0 else None,
                    showlegend=(c_i == 0)
                ))

        # Collapse burst lines / fragments
        if stage >= 4:
            burst_center = (55, 22)
            for angle in np.linspace(0, 2 * np.pi, 18, endpoint=False):
                r1 = 5
                r2 = 16 + 5 * np.sin(3 * angle)
                fig.add_trace(go.Scatter(
                    x=[burst_center[0] + r1 * np.cos(angle), burst_center[0] + r2 * np.cos(angle)],
                    y=[burst_center[1] + r1 * np.sin(angle), burst_center[1] + r2 * np.sin(angle)],
                    mode="lines",
                    line=dict(color="rgba(255,255,255,0.75)", width=2),
                    showlegend=False
                ))
            fig.add_annotation(
                x=55,
                y=22,
                text="<b>ICE SHELF BREAKUP</b>",
                showarrow=False,
                font=dict(size=22, color="rgb(255,70,50)")
            )

        # Inland acceleration arrows
        speed_scale = np.clip((post_collapse_velocity - 300) / 1800, 0.15, 1)
        arrow_n = 5
        for k in range(arrow_n):
            y_arrow = 15 + k * 3.4
            x0 = 3
            x1 = 16 + 14 * speed_scale
            fig.add_annotation(
                x=x1,
                y=y_arrow,
                ax=x0,
                ay=y_arrow,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1.6,
                arrowwidth=2.4 + 5 * speed_scale,
                arrowcolor="rgb(255,140,35)"
            )

        # Stage labels
        stage_labels = [
            "0 Intact shelf",
            "1 Melt ponds form",
            "2 Water-filled cracks deepen",
            "3 Shelf fragments",
            "4 Breakup and flow acceleration"
        ]
        fig.add_annotation(
            x=50,
            y=40.5,
            text=f"<b>{stage_labels[stage]}</b>",
            showarrow=False,
            font=dict(size=18, color="white")
        )

        fig.update_layout(
            title="Hydrofracture & Ice Shelf Collapse Experiment",
            height=620,
            margin=dict(l=20, r=20, t=65, b=25),
            xaxis=dict(visible=False, range=[0, 100]),
            yaxis=dict(visible=False, range=[0, 44]),
            plot_bgcolor="rgb(8,35,70)",
            paper_bgcolor="white",
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True, key="plot_hydrofracture_lab")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ponding Index", f"{ponding_index * 100:.0f} / 100")
        c2.metric("Fracture Index", f"{fracture_index * 100:.0f} / 100")
        c3.metric("Buttressing Remaining", f"{buttressing_remaining:.0f} / 100")
        c4.metric("Post-collapse Velocity", f"{post_collapse_velocity:.0f} m/yr")

        st.metric("Conceptual Sea-level Signal", f"{sea_level_signal:.2f} m")

        st.markdown("""
        **How to read this lab:**
        Surface melt creates ponds on the ice shelf. If firn cannot absorb enough meltwater, water can fill crevasses.
        Water pressure helps cracks propagate downward, a process called **hydrofracture**. Once fractures connect,
        the shelf can fragment, buttressing is lost, and inland ice can accelerate toward the ocean.
        """)
