import streamlit as st
import math
import pandas as pd
import io
import os

# Browser tab configuration
st.set_page_config(page_title="GC's Plough Catenary Web Analyzer", layout="wide")

# CUSTOM CSS: Reduced top spacing layout parameters by half
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }
        /* Aligns the logo vertically with the title text */
        .logo-container {
            display: flex;
            align-items: center;
            justify-content: flex-end;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- FIXED HEADER LAYOUT: Added ratio dimensions [4, 1] ---
title_col, logo_col = st.columns([4, 1])

with title_col:
    st.title("⚓ GC's Subsea Trenching Operational Web Engine - For Kearnsy")

with logo_col:
    # Checks for either standard .jpg or .jpeg file extensions
    logo_filename = "logo.jpg"
    if not os.path.exists(logo_filename):
        logo_filename = "logo.jpeg"
        
    if os.path.exists(logo_filename):
        st.image(logo_filename, width=150)
    else:
        st.caption("*(Upload logo.jpg or logo.jpeg to GitHub)*")

st.markdown("---")

# Layout columns for data entry (3 separate columns)
col1, col2, col3 = st.columns(3)

with col1:
    st.header("1. Tow Wire & Plough Data")
    h = st.number_input("Water Depth (m)", value=150.0, step=10.0, key="depth")
    td_angle = st.number_input("Tow Wire Target Seabed Angle (°)", value=15.0, min_value=0.1, max_value=89.9, step=1.0)
    w_air = st.number_input("Wire Air Weight (kg/m)", value=9.48, step=0.1)
    T_bottom_tons = st.number_input("Target Plough Tow Force (Tons)", value=51.0, step=5.0)

with col2:
    st.header("2. Free-Rendering Umbilical Data")
    w_umb_sub = st.number_input("Umbilical Submerged Wt (kg/m)", value=3.50, step=0.1)
    umb_td_angle = st.number_input("Umbilical Allowable Angle at Plough Chute (° from Horiz)", value=60.0, min_value=5.0, max_value=89.9, step=1.0)

with col3:
    st.header("3. Product Cable Specification")
    w_prod_tkm = st.number_input("Cable Weight In Water (T/km)", value=4.5, step=0.5)
    cable_dia = st.number_input("Cable Diameter (mm)", value=120.0, step=5.0)
    t_top_prod = st.number_input("Product Top Tension (kN)", value=40.0, step=5.0)

# ==========================================
# MATHEMATICAL ENGINE 1: INDEPENDENT TOW WIRE
# ==========================================
T_bottom = T_bottom_tons * 9.81  # Convert to kN
w_sub_wire = w_air * (1 - 1025 / 7850)
w_wire_kn = (w_sub_wire * 9.81) / 1000  # kN/m

alpha_rad = math.radians(td_angle)
H_wire = T_bottom * math.cos(alpha_rad)
a_wire = H_wire / w_wire_kn

wire_length = math.sqrt(h * (h + 2 * a_wire))
wire_span = a_wire * math.log((wire_length + math.sqrt(wire_length**2 + a_wire**2)) / a_wire)

tan_wire_surface = (wire_length + a_wire * math.tan(alpha_rad)) / a_wire
wire_surface_angle_horiz = math.degrees(math.atan(tan_wire_surface))
wire_surface_angle_vertical = 90.0 - wire_surface_angle_horiz

V_wire_top = w_wire_kn * wire_length + (T_bottom * math.sin(alpha_rad))
T_wire_surface = math.sqrt(H_wire**2 + V_wire_top**2)
T_wire_surface_tons = T_wire_surface / 9.81

# ==========================================
# MATHEMATICAL ENGINE 2: FREE UMBILICAL
# ==========================================
w_umb_kn = (w_umb_sub * 9.81) / 1000  # kN/m
umb_alpha_rad = math.radians(umb_td_angle)

sin_alpha = math.sin(umb_alpha_rad)
cos_alpha = math.cos(umb_alpha_rad)

if umb_td_angle == 90.0:
    a_umb = h
else:
    a_umb = h / (1.0 / cos_alpha - 1.0) if cos_alpha > 0 else h

if a_umb <= 0 or math.isnan(a_umb):
    a_umb = 10.0

umb_length = math.sqrt(h * (h + 2 * a_umb))
umb_span = a_umb * math.log((umb_length + math.sqrt(umb_length**2 + a_umb**2)) / a_umb) if a_umb > 0 else 0.0

H_umb = a_umb * w_umb_kn
tan_umb_surface = (umb_length + a_umb * math.tan(umb_alpha_rad)) / a_umb
umb_surface_angle_horiz = math.degrees(math.atan(tan_umb_surface))
umb_surface_angle_vertical = 90.0 - umb_surface_angle_horiz

T_umb_surface = w_umb_kn * h + (H_umb / cos_alpha if cos_alpha > 0 else H_umb)

# ==========================================
# MATHEMATICAL ENGINE 3: PRODUCT CABLE
# ==========================================
w_prod_kn_m = (w_prod_tkm * 9.81) / 1000
tension_loss = w_prod_kn_m * h
t_seabed_prod = t_top_prod - tension_loss

# ==========================================
# DISPLAY DASHBOARD
# ==========================================
st.markdown("---")
st.header("4. Operational Performance Summary")

out_col1, out_col2 = st.columns(2)

with out_col1:
    st.subheader("⛓️ Tow Wire System Outputs")
    st.metric(label="Required Tow Wire Payout Length", value=f"{wire_length:.2f} m")
    st.metric(label="Winch Surface Tension Required", value=f"{T_wire_surface_tons:.1f} Tons", delta=f"{T_wire_surface:.1f} kN")
    st.metric(label="Vessel Wire Entry Angle (from VERTICAL)", value=f"{wire_surface_angle_vertical:.2f}°")
    st.metric(label="Wire Horizontal Span", value=f"{wire_span:.2f} m")

with out_col2:
    st.subheader("🔌 Free-Rendering Umbilical Outputs")
    st.metric(label="Calculated Umbilical Payout Length", value=f"{umb_length:.2f} m")
    st.metric(label="Total Vertical Hanging Weight at Deck", value=f"{T_umb_surface:.2f} kN")
    st.metric(label="Vessel Umbilical Departure Angle (from VERTICAL)", value=f"{umb_surface_angle_vertical:.2f}°")
    st.metric(label="Umbilical Horizontal Span", value=f"{umb_span:.2f} m")

st.markdown("---")
st.header("5. Product Cable Integrity Matrix")
if t_seabed_prod < 0:
    st.error(f"⚠️ Cable Seabed Residual Tension: {t_seabed_prod:.2f} kN — CRITICAL RISK OF CABLE BUCKLING INSIDE CHUTE!")
elif t_seabed_prod < 5:
    st.warning(f"⚠️ Cable Seabed Residual Tension: {t_seabed_prod:.2f} kN — Low Tension Limit Warning.")
else:
    st.success(f"✅ Cable Seabed Residual Tension: {t_seabed_prod:.2f} kN — Tension bounds stable.")

# ==========================================
# PROFILE GENERATOR FOR EXCEL EXPORT
# ==========================================
max_rows = int(h) // 10 + 1
profile_data = []
for i in range(max_rows):
    z = i * 10
    if z > h: z = h
    
    s_w = math.sqrt(z * (z + 2 * a_wire))
    x_w = a_wire * math.log((s_w + math.sqrt(s_w**2 + a_wire**2)) / a_wire) if s_w > 0 else 0.0
    ang_w_horiz = math.degrees(math.atan(s_w / a_wire))
    ang_w_vertical = 90.0 - ang_w_horiz if z > 0 else 90.0
    
    s_u = math.sqrt(z * (z + 2 * a_umb))
    x_u = a_umb * math.log((s_u + math.sqrt(s_u**2 + a_umb**2)) / a_umb) if s_u > 0 and a_umb > 0 else 0.0
    ang_u_horiz = math.degrees(math.atan(s_u / a_umb)) if a_umb > 0 else 90.0
    ang_u_vertical = 90.0 - ang_u_horiz if z > 0 else 90.0
    
    profile_data.append({
        "Vertical Drop (z) [m]": z,
        "Wire Suspended Length [m]": round(s_w, 2),
        "Wire Horizontal Dist [m]": round(x_w, 2),
        "Wire Angle (from Vertical) [deg]": round(ang_w_vertical, 2),
        "Umbilical Suspended Length [m]": round(s_u, 2),
        "Umbilical Horizontal Dist [m]": round(x_u, 2),
        "Umbilical Angle (from Vertical) [deg]": round(ang_u_vertical, 2),
    })

df_profile = pd.DataFrame(profile_data)

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_profile.to_excel(writer, index=False, sheet_name="Catenary Profile Matrix")
buffer.seek(0)

st.download_button(
    label="📥 Export Dynamic Profiling Curves to Excel (.xlsx)",
    data=buffer,
    file_name="Independent_Plough_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

