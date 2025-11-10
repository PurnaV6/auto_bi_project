# app.py (colorful)
from modules.data_cleaner import clean_dataframe
from modules.schema_infer import infer_schema
import json
import pandas as pd
import streamlit as st
import plotly.express as px

# -------------------- THEME SETTINGS (live controls) --------------------
st.set_page_config(page_title="Auto-BI • Color Edition", layout="wide", page_icon="🎨")

# Sidebar Theme Controls
with st.sidebar:
    st.header("🎨 Theme")
    mode = st.radio("Mode", ["Light", "Dark"], horizontal=True, index=0)
    primary = st.color_picker("Primary color", value="#5E60CE")
    accent = st.color_picker("Accent color", value="#4EA8DE")

    st.markdown("---")
    st.header("📊 Charts")
    # A few nice Plotly palettes
    palette_name = st.selectbox(
        "Palette",
        [
            "Plotly", "D3", "G10", "T10",
            "Pastel", "Set2", "Bold", "Antique"
        ],
        index=0
    )
    palette_map = {
        "Plotly": px.colors.qualitative.Plotly,
        "D3": px.colors.qualitative.D3,
        "G10": px.colors.qualitative.G10,
        "T10": px.colors.qualitative.T10,
        "Pastel": px.colors.qualitative.Pastel,
        "Set2": px.colors.qualitative.Set2,
        "Bold": px.colors.qualitative.Bold,
        "Antique": px.colors.qualitative.Antique
    }
    COLOR_SEQ = palette_map[palette_name]

# -------------------- GLOBAL STYLE (CSS) --------------------
# light / dark backgrounds
bg_light = "#0b1021"  # header gradient start (used as overlay)
bg_dark = "#0b1021"
text_light = "#0b1021"
text_dark = "#E6E6E6"

is_dark = (mode == "Dark")
body_text = text_dark if is_dark else text_light
panel_bg = "#111827" if is_dark else "#FFFFFF"
card_bg = "#0f172a" if is_dark else "#ffffff"
card_border = "#233044" if is_dark else "#e5e7eb"

custom_css = f"""
<style>
/* Page background */
.stApp {{
  background: linear-gradient(135deg, {primary}22 0%, {accent}11 100%);
}}

header[data-testid="stHeader"] {{
  background: linear-gradient(90deg, {primary} 0%, {accent} 100%);
  padding-bottom: 0.25rem;
  box-shadow: 0 2px 10px #00000033;
}}
header [data-testid="stHeader"] * {{
  color: white !important;
}}

h1, h2, h3, h4, h5 {{
  color: {"#ffffff" if is_dark else "#111827"} !important;
}}

.section-card {{
  background: {card_bg};
  border: 1px solid {card_border};
  border-radius: 16px;
  padding: 18px 18px 8px 18px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
  margin-bottom: 16px;
}}

.small-badge {{
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: {primary}22;
  color: {primary};
  border: 1px solid {primary}55;
  font-size: 0.8rem;
  margin-left: 6px;
}}

.stButton>button {{
  background: {primary};
  color: white;
  border: 0;
  border-radius: 12px;
  padding: 0.5rem 0.9rem;
  font-weight: 600;
  box-shadow: 0 6px 14px {primary}33;
}}
.stButton>button:hover {{
  transform: translateY(-1px);
  box-shadow: 0 10px 18px {primary}55;
}}

.block-title {{
  display:flex; align-items:center; gap:.5rem;
}}
.block-title:before {{
  content:"";
  width:10px; height:10px; border-radius:3px;
  background:{accent};
  display:inline-block;
}}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


def build_chart(df: pd.DataFrame, spec: dict):
    t = spec["type"]; x = spec.get("x"); y = spec.get("y")
    color = spec.get("color"); agg = spec.get("agg", "sum")
    title = spec.get("title", "")

    common_kwargs = {"color_discrete_sequence": COLOR_SEQ}
    if color:
        common_kwargs["color"] = color

    if t in ("bar", "line"):
        if y and pd.api.types.is_numeric_dtype(df[y]):
            d = getattr(df.groupby(x)[y], agg)().reset_index()
            fig = px.bar(d, x=x, y=y, **common_kwargs) if t == "bar" else px.line(d, x=x, y=y, **common_kwargs)
        else:
            d = df.groupby(x).size().reset_index(name="count")
            fig = px.bar(d, x=x, y="count", **common_kwargs) if t == "bar" else px.line(d, x=x, y="count", **common_kwargs)
    elif t == "histogram":
        fig = px.histogram(df, x=x, **common_kwargs)
    elif t == "scatter":
        fig = px.scatter(df, x=x, y=y, **common_kwargs)
    elif t == "box":
        target = y or x
        fig = px.box(df, y=target, **common_kwargs)
    elif t == "heatmap":
        z = spec.get("z")
        if not z:
            if y and pd.api.types.is_numeric_dtype(df[y]): z = y
            else:
                nums = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                z = nums[0] if nums else None
        if z is None:
            cols = df.columns.tolist()
            fig = px.scatter(df, x=cols[0], y=cols[1] if len(cols) > 1 else None, **common_kwargs)
        else:
            d = getattr(df.groupby([x, y])[z], agg)().reset_index()
            fig = px.density_heatmap(d, x=x, y=y, z=z, histfunc="avg", color_continuous_scale="Bluered")
    else:
        cols = df.columns.tolist()
        fig = px.scatter(df, x=cols[0], y=cols[1] if len(cols) > 1 else None, **common_kwargs)

    fig.update_layout(
        title=title,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0.02)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=13),
    )
    return fig

# -------------------- UI --------------------
st.markdown(f"<h1 class='block-title'>Auto-BI <span class='small-badge'>{palette_name} palette</span></h1>", unsafe_allow_html=True)
st.caption("Upload → Clean → Recommend → Build • Now with themes & palettes")

uploaded = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls", "parquet"])

if not uploaded:
    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.info("Upload a dataset to get started. CSV is recommended for the first run.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# read file
try:
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded)
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded)
    else:
        df = pd.read_parquet(uploaded)
except Exception as e:
    st.error(f"Could not read the file: {e}")
    st.stop()

# 1) Preview
st.markdown("<div class='section-card'>", unsafe_allow_html=True)
st.subheader("1) Preview")
st.dataframe(df.head(), use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# 2) Schema
st.markdown("<div class='section-card'>", unsafe_allow_html=True)
st.subheader("2) Schema & quick stats")
schema = infer_schema(df)
st.json(schema)
st.markdown("</div>", unsafe_allow_html=True)

# 3) Cleaning
st.markdown("<div class='section-card'>", unsafe_allow_html=True)
st.subheader("3) Auto-clean")
df_clean, report = clean_dataframe(df)
st.success(f"Cleaned rows: {len(df_clean)} (from {len(df)})")
with st.expander("Cleaning report"):
    st.json(report)
st.markdown("</div>", unsafe_allow_html=True)

# 4) Recommended charts
dims = [c for c, v in schema["fields"].items() if v["role"] == "dimension"]
meas = [c for c, v in schema["fields"].items() if v["role"] == "measure"]
dates = [c for c in df_clean.columns if "datetime" in str(df_clean[c].dtype)]

st.markdown("<div class='section-card'>", unsafe_allow_html=True)
st.subheader("4) Recommended charts")
recs = []
if dates and meas:
    recs.append({"type": "line", "x": dates[0], "y": meas[0], "agg": "sum",
                 "title": f"{meas[0]} over time", "why": "Date + measure → line"})
if dims and meas:
    recs.append({"type": "bar", "x": dims[0], "y": meas[0], "agg": "sum",
                 "title": f"Top {dims[0]} by {meas[0]}", "why": "Dim + measure → bar"})
if meas:
    recs.append({"type": "histogram", "x": meas[0],
                 "title": f"Distribution of {meas[0]}", "why": "Univariate measure → histogram"})
if len(meas) >= 2:
    recs.append({"type": "scatter", "x": meas[0], "y": meas[1],
                 "title": f"{meas[0]} vs {meas[1]}", "why": "Two measures → scatter"})
if len(dims) >= 2 and meas:
    recs.append({"type": "heatmap", "x": dims[0], "y": dims[1], "z": meas[0], "agg": "sum",
                 "title": f"Heatmap of {meas[0]} by {dims[0]} and {dims[1]}",
                 "why": "Two dims + measure → heatmap"})

for i, spec in enumerate(recs, 1):
    st.markdown(f"**{i}. {spec.get('title','(untitled)')}** — {spec.get('why','')}")
    fig = build_chart(df_clean, spec)
    st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# 5) Build your own chart
st.markdown("<div class='section-card'>", unsafe_allow_html=True)
st.subheader("5) Build your own chart")
chart_type = st.selectbox("Chart type", ["bar", "line", "scatter", "histogram", "box", "heatmap"])
x = st.selectbox("X axis", dims + meas, index=0 if (dims or meas) else 0)
y = st.selectbox("Y axis (optional)", [""] + dims + meas, index=0)
color = st.selectbox("Color (optional)", [""] + dims + meas, index=0)
agg = st.selectbox("Aggregation (if measure)", ["sum", "mean", "count", "min", "max"], index=0)

if st.button("Render custom chart"):
    spec = {
        "type": chart_type, "x": x, "y": y or None,
        "color": color or None, "agg": agg,
        "title": f"{chart_type.title()} — {x}" + (f" vs {y}" if y else "")
    }
    fig = build_chart(df_clean, spec)
    st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# 6) Export
st.markdown("<div class='section-card'>", unsafe_allow_html=True)
st.subheader("6) Export")
c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "⬇️ Download cleaned CSV",
        df_clean.to_csv(index=False).encode("utf-8"),
        file_name="cleaned_data.csv",
        mime="text/csv",
    )
with c2:
    st.download_button(
        "⬇️ Download chart specs (JSON)",
        json.dumps({"schema": schema, "recommendations": recs}, indent=2).encode("utf-8"),
        file_name="chart_specs.json",
        mime="application/json",
    )
st.markdown("</div>", unsafe_allow_html=True)
