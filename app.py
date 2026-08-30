import streamlit as st
import math
import pandas as pd
import io

# Browser tab configuration
st.set_page_config(page_title="Plough Catenary Web Analyzer", layout="wide")

st.title("⚓ GC's Subsea Plough Trenching Operational Web Engine")
st.markdown("---")

# Layout columns for data entry
col1, col2 = st.columns(2)

with col1:
    st.header("1. Tow Wire & Plough Data")
    h = st.number_input("Water Depth (m)", value=150.0, step=10.0)
    td_angle = st.number_input("Target Seabed Touchdown Angle (°)", value=15.0, min_value=0.1, max_value=89.9, step=1.0)
    w_air = st.number_input("Wire Air Weight (kg/m)", value=9.48, step=0.1)
    w_umb = st.number_input("Umbilical Submerged Wt (kg/m)", value=3.50, step=0.1)
    # UPDATED: Input changed from kN to Tons
    T_bottom_tons = st.number_input("Required Pull Force at Plough (Tons)", value=51.0, step=5.0)

with col2:
    st.header("2. Product Cable Specification")
    w_prod_tkm = st.number_input("Cable Weight In Water (T/km)", value=4.5, step=0.5)
    cable_dia = st.number_input("Cable Diameter (mm)", value=120.0, step=5.0)
    t_top_prod = st.number_input("Product Top Tension (kN)", value=40.0, step=5.0)

# --- UPDATED FORMULA SYSTEM ---
# Convert the user's input force from Tons to kN (1 Ton = 9.81 kN)
T_bottom = T_bottom_tons * 9.81

# Convert tow line structural weights to kN/m
w_sub_wire = w_air * (1 - 1025 / 7850)
w_total_kn = (w_sub_wire + w_umb) * 9.81 / 1000  

# Proceed with classic seabed-up catenary equations
alpha_rad = math.radians(td_angle)
H = T_bottom * math.cos(alpha_rad)
a = H / w_total_kn

length = math.sqrt(h * (h + 2 * a))
span = a * math.log((length + math.sqrt(length**2 + a**2)) / a)

tan_surface = (length + a * math.tan(alpha_rad)) / a
surface_angle_deg = math.degrees(math.atan(tan_surface))

V_top = w_total_kn * length + (T_bottom * math.sin(alpha_rad))
T_surface = math.sqrt(H**2 + V_top**2)

# Convert resulting required surface tension back to Tons for operational consistency
T_surface_tons = T_surface / 9.81

# Product cable tension tracking
w_prod_kn_m = (w_prod_tkm * 9.81) / 1000
tension_loss = w_prod_kn_m * h
t_seabed_prod = t_top_prod - tension_loss

st.markdown("---")
st.header("3. Combined System Analysis Dashboard")

# Rendering data metrics (Displaying tension outputs in both engineering standards)
res_col1, res_col2, res_col3, res_col4 = st.columns(4)
res_col1.metric(label="Required Wire Length", value=f"{length:.2f} m")
res_col2.metric(label="Total Horizontal Span", value=f"{span:.2f} m")
res_col3.metric(label="Vessel Tow Angle (from Horiz)", value=f"{surface_angle_deg:.2f}°")
res_col4.metric(label="Required Winch Tension", value=f"{T_surface_tons:.1f} Tons", delta=f"{T_surface:.1f} kN")

st.markdown("### Product Cable Integrity Matrix")
if t_seabed_prod < 0:
    st.error(f"⚠️ Cable Seabed Residual Tension: {t_seabed_prod:.2f} kN — CRITICAL RISK OF CABLE BUCKLING INSIDE CHUTE!")
elif t_seabed_prod < 5:
    st.warning(f"⚠️ Cable Seabed Residual Tension: {t_seabed_prod:.2f} kN — Low Tension Limit Warning.")
else:
    st.success(f"✅ Cable Seabed Residual Tension: {t_seabed_prod:.2f} kN — Tension bounds stable.")

# Profile Table Generator for Excel Export
profile_data = []
for z in range(0, int(h) + 10, 10):
    if z > h: z = h
    s_local = math.sqrt(z * (z + 2 * a))
    if s_local == 0:
        x_local = 0.0
    else:
        x_local = a * math.log((s_local + math.sqrt(s_local**2 + a**2)) / a)
    ang_local = math.degrees(math.atan(s_local / a))
    profile_data.append({
        "Vertical Drop (z) [m]": z,
        "Suspended Length (s) [m]": round(s_local, 2),
        "Horizontal Distance (x) [m]": round(x_local, 2),
        "Local Tow Angle (deg)": round(ang_local, 2)
    })
df_profile = pd.DataFrame(profile_data)

# Generate spreadsheet file in web cache memory
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_profile.to_excel(writer, index=False, sheet_name="Catenary Profile Matrix")
buffer.seek(0)

st.markdown("---")
st.download_button(
    label="📥 Export Current Results to Excel (.xlsx)",
    data=buffer,
    file_name="Plough_Catenary_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
