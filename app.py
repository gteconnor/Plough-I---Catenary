import io
import math
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Page setup
st.set_page_config(
    page_title="Subsea Catenary Web Analyzer", layout="wide"
)

# Custom CSS styling
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- HEADER LAYOUT ---
title_col, logo_col = st.columns([4, 1])

with title_col:
    st.title("⚓ Subsea Trenching Operational Web Engine")

with logo_col:
    logo_filename = "logo.jpg" if os.path.exists("logo.jpg") else "logo.jpeg"
    if os.path.exists(logo_filename):
        st.image(logo_filename, width=150)
    else:
        st.caption("*(Upload logo.jpg or logo.jpeg to repository)*")

st.markdown("---")

# --- INPUT SECTION ---
col1, col2, col3 = st.columns(3)

with col1:
    with st.container(border=True):
        st.header("1. Tow Wire & Plough Data")
        h = st.number_input(
            "Water Depth (m)", value=100.0, step=10.0, key="depth"
        )
        td_angle = st.number_input(
            "Tow Wire Target Seabed Angle (°)",
            value=15.0,
            min_value=0.1,
            max_value=89.9,
            step=1.0,
        )
        w_sub_wire_kg = st.number_input(
            "Tow Wire Submerged Weight (kg/m)", value=8.24, step=0.1
        )
        T_bottom_tons = st.number_input(
            "Target Plough Tow Force (Tons)", value=15.0, step=5.0
        )

with col2:
    with st.container(border=True):
        st.header("2. Umbilical Specification")
        w_umb_buoyant_kg = st.number_input(
            "Net Buoyant Weight (kg/m)", 
            value=-0.10, 
            step=0.01,
            format="%.2f",
            help="Negative value denotes net positive buoyancy (+0.10 kg/m upward uplift)."
        )
        t_umb_top_tons = st.slider(
            "Umbilical Winch Set Tension (Tons)",
            min_value=0.1,
            max_value=8.0,
            value=2.0,
            step=0.1,
            help="Option A: Winch render threshold drives payout length and geometry dynamically.",
        )

with col3:
    with st.container(border=True):
        st.header("3. Product Cable Specification")
        w_prod_tkm = st.number_input(
            "Cable Weight In Water (T/km)", value=5, step=0.1
        )
        cable_dia = st.number_input(
            "Cable Diameter (mm)", value=38.0, step=1.0
        )
        t_top_prod = st.number_input(
            "Product Top Tension (kN)", value=10.0, step=1.0
        )

# ==========================================
# 1. TOW WIRE MATHEMATICAL ENGINE
# ==========================================
T_bottom = T_bottom_tons * 0.980665  # Convert Tonnes force to Te equivalent
w_wire_te = w_sub_wire_kg / 1000.0   # Te/m

alpha_rad = math.radians(td_angle)
H_wire = T_bottom * math.cos(alpha_rad)
a_wire = H_wire / w_wire_te

wire_length = math.sqrt(h * (h + 2.0 * a_wire))
wire_span = a_wire * math.log(
    (wire_length + math.sqrt(wire_length**2 + a_wire**2)) / a_wire
)

V_wire_top = w_wire_te * wire_length + (T_bottom * math.sin(alpha_rad))
T_wire_surface = math.sqrt(H_wire**2 + V_wire_top**2)

# ==========================================
# 2. UMBILICAL MATHEMATICAL ENGINE (FIXED OPTION A)
# ==========================================
w_umb_net_te = w_umb_buoyant_kg / 1000.0  # -0.00010 Te/m
X_plough = wire_span

# Signed horizontal catenary parameter (negative for net buoyant)
a_umb = t_umb_top_tons / w_umb_net_te

# Bisection search to solve exact horizontal offset x0_umb for pinned boundaries
def solve_x0_umb(X_target, Z_target, a_val):
    low, high = -50000.0, 50000.0
    for _ in range(100):
        mid = (low + high) / 2.0
        z_end = a_val * (math.cosh((X_target - mid) / a_val) - math.cosh(-mid / a_val))
        if z_end < Z_target:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0

x0_umb = solve_x0_umb(X_plough, h, a_umb)

# Profile array generation
x_grid_umb = np.linspace(0, X_plough, 200)
z_u_plot = a_umb * (np.cosh((x_grid_umb - x0_umb) / a_umb) - np.cosh(-x0_umb / a_umb))

# Derive true payout length (S_umb)
s_start = a_umb * np.sinh(-x0_umb / a_umb)
s_end = a_umb * np.sinh((X_plough - x0_umb) / a_umb)
umb_length = float(abs(s_end - s_start))

# Swivel angle at plough
theta_swivel_rad = math.atan(math.sinh((X_plough - x0_umb) / a_umb))
theta_swivel_deg = math.degrees(theta_swivel_rad)

# ==========================================
# 3. PRODUCT CABLE MATHEMATICAL ENGINE
# ==========================================
w_prod_kn_m = (w_prod_tkm * 9.81) / 1000.0
tension_loss = w_prod_kn_m * h
t_seabed_prod = t_top_prod - tension_loss

a_prod = max(t_top_prod / w_prod_kn_m, 1e-4)
prod_length = math.sqrt(h * (h + 2.0 * a_prod))
prod_span = a_prod * math.log(
    (prod_length + math.sqrt(prod_length**2 + a_prod**2)) / a_prod
)

# ==========================================
# 4. DISPLAY DASHBOARD METRICS
# ==========================================
st.markdown("---")
st.header("4. Operational Performance Summary")

out_col1, out_col2 = st.columns(2)

with out_col1:
    with st.container(border=True):
        st.subheader("⛓️ Tow Wire System Outputs")
        st.metric(
            label="Required Tow Wire Payout Length",
            value=f"{wire_length:.2f} m",
        )
        st.metric(
            label="Winch Surface Tension Required",
            value=f"{T_wire_surface:.1f} Te",
        )
        st.metric(
            label="Plough Layback Span (X_plough)",
            value=f"{wire_span:.2f} m",
        )

with out_col2:
    with st.container(border=True):
        st.subheader("🔌 Umbilical System Outputs (Option A - Tension Driven)")
        st.metric(
            label="Dynamic Required Payout Length",
            value=f"{umb_length:.2f} m",
            delta=f"{umb_length - wire_length:+.2f} m vs Tow Wire",
        )
        st.metric(
            label="Selected Winch Render Tension",
            value=f"{t_umb_top_tons:.2f} Te",
        )
        st.metric(
            label="Swivel Entry Angle at Plough",
            value=f"{theta_swivel_deg:.2f}°",
            delta="Relative to Horizontal",
        )

# ==========================================
# 5. DYNAMIC PROFILE VISUALIZER
# ==========================================
st.markdown("---")
st.header("5. Dynamic Subsea Catenary Profile Visualizer")

# Tow Wire Curve
z_plot = np.linspace(0, h, 100)
z_from_bottom = h - z_plot
s_w_plot = np.sqrt(z_from_bottom * (z_from_bottom + 2.0 * a_wire))
x_w_plot = np.where(
    s_w_plot > 0,
    a_wire * np.log((s_w_plot + np.sqrt(s_w_plot**2 + a_wire**2)) / a_wire),
    0.0,
)
x_w_vessel = wire_span - x_w_plot

# Product Cable Curve
s_p_plot = np.sqrt(z_from_bottom * (z_from_bottom + 2.0 * a_prod))
x_p_plot = np.where(
    s_p_plot > 0,
    a_prod * np.log((s_p_plot + np.sqrt(s_p_plot**2 + a_prod**2)) / a_prod),
    0.0,
)
x_p_vessel = prod_span - x_p_plot

fig = go.Figure()

# Tow Wire Trace
fig.add_trace(
    go.Scatter(
        x=x_w_vessel,
        y=z_plot,
        mode="lines",
        name=f"Tow Wire (Span: {wire_span:.1f}m | Length: {wire_length:.1f}m)",
        line=dict(color="#1f77b4", width=3),
        hovertemplate="<b>Tow Wire</b><br>Distance: %{x:.2f} m<br>Depth: %{y:.2f} m<extra></extra>",
    )
)

# Buoyant Umbilical Trace
fig.add_trace(
    go.Scatter(
        x=x_grid_umb,
        y=z_u_plot,
        mode="lines",
        name=f"Umbilical (Winch Set: {t_umb_top_tons:.1f}T | Length: {umb_length:.1f}m)",
        line=dict(color="#ff7f0e", width=3, dash="dash"),
        hovertemplate="<b>Umbilical</b><br>Distance: %{x:.2f} m<br>Depth: %{y:.2f} m<extra></extra>",
    )
)

# Product Cable Trace
fig.add_trace(
    go.Scatter(
        x=x_p_vessel,
        y=z_plot,
        mode="lines",
        name=f"Product Cable (Span: {prod_span:.1f}m | Length: {prod_length:.1f}m)",
        line=dict(color="#2ca02c", width=3, dash="dot"),
        hovertemplate="<b>Product Cable</b><br>Distance: %{x:.2f} m<br>Depth: %{y:.2f} m<extra></extra>",
    )
)

# Terminations
fig.add_trace(
    go.Scatter(
        x=[wire_span, wire_span, prod_span],
        y=[h, h, h],
        mode="markers",
        name="Seabed Terminations",
        marker=dict(
            size=10, symbol="diamond", color=["#1f77b4", "#ff7f0e", "#2ca02c"]
        ),
        hoverinfo="skip",
    )
)

fig.update_layout(
    title=dict(
        text="Subsea Catenary Profiles (Vessel Stern Origin x=0, z=0)",
        x=0.0,
        font=dict(size=18),
    ),
    xaxis_title="Horizontal Distance from Vessel Stern (m)",
    yaxis=dict(
        title="Water Depth (m)",
        autorange="reversed",
    ),
    xaxis=dict(
        range=[-10, max(wire_span, prod_span) * 1.05],
    ),
    template="plotly_dark",
    height=550,
    hovermode="closest",
    legend=dict(
        yanchor="top",
        y=0.98,
        xanchor="right",
        x=0.98,
        bgcolor="rgba(0, 0, 0, 0.5)",
    ),
)

# Seabed Reference Line
fig.add_shape(
    type="line",
    x0=0,
    y0=h,
    x1=max(wire_span, prod_span) * 1.1,
    y1=h,
    line=dict(color="Brown", width=2, dash="dashdot"),
)

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. CABLE INTEGRITY MATRIX
# ==========================================
st.markdown("---")
st.header("6. Product Cable Integrity Matrix")
if t_seabed_prod < 0:
    st.error(
        f"⚠️ Cable Seabed Residual Tension: {t_seabed_prod:.2f} kN — CRITICAL RISK OF CABLE BUCKLING INSIDE CHUTE!"
    )
elif t_seabed_prod < 5:
    st.warning(
        f"⚠️ Cable Seabed Residual Tension: {t_seabed_prod:.2f} kN — Low Tension Limit Warning."
    )
else:
    st.success(
        f"✅ Cable Seabed Residual Tension: {t_seabed_prod:.2f} kN — Tension bounds stable."
    )

# ==========================================
# EXCEL REPORT EXPORT
# ==========================================
@st.cache_data
def generate_profile_excel(h, wire_span, prod_span, x_grid_umb, z_u_plot):
    df_profile = pd.DataFrame({
        "Horizontal Distance (m)": np.round(x_grid_umb, 2),
        "Umbilical Depth (m)": np.round(z_u_plot, 2)
    })
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_profile.to_excel(
            writer, index=False, sheet_name="Catenary Profile Matrix"
        )
    buffer.seek(0)
    return buffer

excel_buffer = generate_profile_excel(h, wire_span, prod_span, x_grid_umb, z_u_plot)

st.download_button(
    label="📥 Export Dynamic Profiling Curves to Excel (.xlsx)",
    data=excel_buffer,
    file_name="Plough_Catenary_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
