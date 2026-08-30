import io
import math
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from scipy.optimize import fsolve
except ImportError:
    fsolve = None

# Browser tab configuration
st.set_page_config(
    page_title="GC's Plough Catenary Web Analyzer", layout="wide"
)

# Custom CSS styling
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
        }
        .logo-container {
            display: flex;
            align-items: center;
            justify-content: flex-end;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- HEADER LAYOUT ---
title_col, logo_col = st.columns([4, 1])

with title_col:
    st.title("⚓ GC's Subsea Trenching Operational Web Engine - For Kearnsy")

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
            "Water Depth (m)", value=150.0, step=10.0, key="depth"
        )
        td_angle = st.number_input(
            "Tow Wire Target Seabed Angle (°)",
            value=15.0,
            min_value=0.1,
            max_value=89.9,
            step=1.0,
        )
        w_air = st.number_input("Wire Air Weight (kg/m)", value=9.48, step=0.1)
        T_bottom_tons = st.number_input(
            "Target Plough Tow Force (Tons)", value=51.0, step=5.0
        )

with col2:
    with st.container(border=True):
        st.header("2. Umbilical Specification")
        w_umb_sub = st.number_input(
            "Umbilical Submerged Wt (kg/m)", value=3.50, step=0.1
        )
        st.caption(
            "Note: Fixed boundary condition $(x, z) = (0, 0) \\rightarrow (x_{\\text{plough}}, h)$ enforced. Tension and payout length derived directly from weight profile."
        )

with col3:
    with st.container(border=True):
        st.header("3. Product Cable Specification")
        w_prod_tkm = st.number_input(
            "Cable Weight In Water (T/km)", value=4.5, step=0.5
        )
        cable_dia = st.number_input(
            "Cable Diameter (mm)", value=120.0, step=5.0
        )
        t_top_prod = st.number_input(
            "Product Top Tension (kN)", value=40.0, step=5.0
        )

# ==========================================
# MATHEMATICAL ENGINE 1: TOW WIRE (ESTABLISHES PLOUGH LOCATION)
# ==========================================
T_bottom = T_bottom_tons * 9.81  # Convert to kN
w_sub_wire = w_air * (1.0 - (1025.0 / 7850.0))
w_wire_kn = (w_sub_wire * 9.81) / 1000.0  # kN/m

alpha_rad = math.radians(td_angle)
H_wire = T_bottom * math.cos(alpha_rad)
a_wire = H_wire / w_wire_kn

wire_length = math.sqrt(h * (h + 2.0 * a_wire))
wire_span = a_wire * math.log(
    (wire_length + math.sqrt(wire_length**2 + a_wire**2)) / a_wire
)

tan_wire_surface = (wire_length + a_wire * math.tan(alpha_rad)) / a_wire
wire_surface_angle_horiz = math.degrees(math.atan(tan_wire_surface))
wire_surface_angle_vertical = 90.0 - wire_surface_angle_horiz

V_wire_top = w_wire_kn * wire_length + (T_bottom * math.sin(alpha_rad))
T_wire_surface = math.sqrt(H_wire**2 + V_wire_top**2)
T_wire_surface_tons = T_wire_surface / 9.81

# ==========================================
# MATHEMATICAL ENGINE 2: UMBILICAL (ENFORCED 0,0 TO X_PLOUGH,H BOUNDARY)
# ==========================================
w_umb_kn = (w_umb_sub * 9.81) / 1000.0  # kN/m
x_plough = wire_span


# Root finder for catenary parameter 'a' satisfying x(h) = x_plough given (0,0) origin
def calc_a_from_endpoints(X, H):
    if fsolve is not None:

        def func(a):
            return a * math.acosh(1.0 + H / a) - X

        res = fsolve(func, 100.0)[0]
        return max(float(res), 1e-3)
    else:
        # Bisection fallback
        low, high = 1e-3, 100000.0
        for _ in range(100):
            mid = (low + high) / 2.0
            val = mid * math.acosh(1.0 + H / mid)
            if val < X:
                low = mid
            else:
                high = mid
        return (low + high) / 2.0


a_umb = calc_a_from_endpoints(x_plough, h)
umb_length = a_umb * math.sinh(x_plough / a_umb)
umb_span = x_plough

H_umb = a_umb * w_umb_kn
T_umb_surface = w_umb_kn * h + H_umb
umb_surface_angle_vert = math.degrees(math.atan(H_umb / (w_umb_kn * umb_length)))
payout_delta = umb_length - wire_length

# ==========================================
# MATHEMATICAL ENGINE 3: PRODUCT CABLE
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
# DISPLAY DASHBOARD
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
            value=f"{T_wire_surface_tons:.1f} Tons",
            delta=f"{T_wire_surface:.1f} kN",
        )
        st.metric(
            label="Vessel Wire Entry Angle (from VERTICAL)",
            value=f"{wire_surface_angle_vertical:.2f}°",
        )
        st.metric(
            label="Plough Layback Span (x_plough)",
            value=f"{wire_span:.2f} m",
        )

with out_col2:
    with st.container(border=True):
        st.subheader("🔌 Umbilical System Outputs (Pinned (0,0) to Plough)")
        st.metric(
            label="Required Umbilical Payout Length",
            value=f"{umb_length:.2f} m",
            delta=f"{payout_delta:+.2f} m vs Tow Wire",
        )
        st.metric(
            label="Calculated Deck Tension Required",
            value=f"{T_umb_surface:.2f} kN",
        )
        st.metric(
            label="Vessel Departure Angle (from VERTICAL)",
            value=f"{umb_surface_angle_vert:.2f}°",
        )
        st.metric(
            label="Horizontal Layback Span",
            value=f"{umb_span:.2f} m",
            delta="Matched to Plough Position",
        )

# ==========================================
# 5. DYNAMIC SUBSEA CATENARY PROFILE VISUALIZER
# ==========================================
st.markdown("---")
st.header("5. Dynamic Subsea Catenary Profile Visualizer")

# Plot points evaluation from Surface (x=0, z=0) to Seabed (x=span, z=h)
# Tow Wire Curve: z(x) = a * (cosh(x/a) - 1) adjusted to end at x_plough
x_w_arr = np.linspace(0, wire_span, 100)
z_w_arr = a_wire * (np.cosh(x_w_arr / a_wire) - 1.0)
# Scale depth exact to h at endpoint to handle numerical rounding
z_w_arr = (z_w_arr / z_w_arr[-1]) * h

# Umbilical Curve: Starts at (0,0), ends at (x_plough, h)
x_u_arr = np.linspace(0, umb_span, 100)
z_u_arr = a_umb * (np.cosh(x_u_arr / a_umb) - 1.0)
z_u_arr = (z_u_arr / z_u_arr[-1]) * h

# Product Cable Curve: Starts at (0,0), ends at (prod_span, h)
x_p_arr = np.linspace(0, prod_span, 100)
z_p_arr = a_prod * (np.cosh(x_p_arr / a_prod) - 1.0)
z_p_arr = (z_p_arr / z_p_arr[-1]) * h

fig = go.Figure()

# Tow Wire (Steel Blue)
fig.add_trace(
    go.Scatter(
        x=x_w_arr,
        y=z_w_arr,
        mode="lines",
        name=f"Tow Wire (Span: {wire_span:.1f}m | Length: {wire_length:.1f}m)",
        line=dict(color="#1f77b4", width=3),
        hovertemplate="<b>Tow Wire</b><br>Horizontal Distance: %{x:.2f} m<br>Water Depth: %{y:.2f} m<extra></extra>",
    )
)

# Umbilical (Orange)
fig.add_trace(
    go.Scatter(
        x=x_u_arr,
        y=z_u_arr,
        mode="lines",
        name=f"Umbilical (Span: {umb_span:.1f}m | Length: {umb_length:.1f}m)",
        line=dict(color="#ff7f0e", width=3, dash="dash"),
        hovertemplate="<b>Umbilical</b><br>Horizontal Distance: %{x:.2f} m<br>Water Depth: %{y:.2f} m<extra></extra>",
    )
)

# Product Cable (Green)
fig.add_trace(
    go.Scatter(
        x=x_p_arr,
        y=z_p_arr,
        mode="lines",
        name=f"Product Cable (Span: {prod_span:.1f}m | Length: {prod_length:.1f}m)",
        line=dict(color="#2ca02c", width=3, dash="dot"),
        hovertemplate="<b>Product Cable</b><br>Horizontal Distance: %{x:.2f} m<br>Water Depth: %{y:.2f} m<extra></extra>",
    )
)

# Touchdown / Termination Markers
fig.add_trace(
    go.Scatter(
        x=[wire_span, umb_span, prod_span],
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

# Draw Seabed Reference Line
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
# CABLE INTEGRITY MATRIX
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
# PROFILE GENERATOR & EXCEL EXPORT
# ==========================================
@st.cache_data
def generate_profile_excel(h, a_wire, a_umb, a_prod, wire_span, umb_span, prod_span):
    x_steps = np.linspace(0, max(wire_span, prod_span), 20)

    profile_data = []
    for x in x_steps:
        # Tow Wire profile
        if x <= wire_span:
            z_w = a_wire * (math.cosh(x / a_wire) - 1.0)
            s_w = a_wire * math.sinh(x / a_wire)
        else:
            z_w, s_w = h, wire_length

        # Umbilical profile
        if x <= umb_span:
            z_u = a_umb * (math.cosh(x / a_umb) - 1.0)
            s_u = a_umb * math.sinh(x / a_umb)
        else:
            z_u, s_u = h, umb_length

        # Product Cable profile
        if x <= prod_span:
            z_p = a_prod * (math.cosh(x / a_prod) - 1.0)
            s_p = a_prod * math.sinh(x / a_prod)
        else:
            z_p, s_p = h, prod_length

        profile_data.append(
            {
                "Horizontal Dist (x) [m]": round(x, 2),
                "Wire Depth (z) [m]": round(min(z_w, h), 2),
                "Wire Suspended Length [m]": round(s_w, 2),
                "Umbilical Depth (z) [m]": round(min(z_u, h), 2),
                "Umbilical Suspended Length [m]": round(s_u, 2),
                "Product Depth (z) [m]": round(min(z_p, h), 2),
                "Product Suspended Length [m]": round(s_p, 2),
            }
        )

    df_profile = pd.DataFrame(profile_data)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_profile.to_excel(
            writer, index=False, sheet_name="Catenary Profile Matrix"
        )
    buffer.seek(0)
    return buffer


excel_buffer = generate_profile_excel(
    h, a_wire, a_umb, a_prod, wire_span, umb_span, prod_span
)

st.download_button(
    label="📥 Export Dynamic Profiling Curves to Excel (.xlsx)",
    data=excel_buffer,
    file_name="Plough_Catenary_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
