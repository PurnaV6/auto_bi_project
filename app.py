# app.py
# MIT Licensed © 2025 Purna Vemula (github.com/PurnaV6/auto_bi_project)
import json
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Auto-BI Basic", layout="wide")
st.title("Auto-BI Basic — Upload • Clean • Recommend • Build")

# ---------- Helpers ----------
def guess_role(s: pd.Series):
    """Infer simple roles: dimension vs measure."""
    if pd.api.types.is_datetime64_any_dtype(s) or pd.api.types.is_bool_dtype(s):
        return "dimension"
    if pd.api.types.is_numeric_dtype(s):
        return "measure" if s.nunique(dropna=True) > 15 else "dimension"
    # heuristic: low-unique text → dimension
    return "dimension" if s.nunique(dropna=True) <= max(50, len(s)//20) else "measure"

def infer_schema(df: pd.DataFrame):
    return {
        "row_count": len(df),
        "fields": {
            c: {
                "role": guess_role(df[c]),
                "dtype": str(df[c].dtype),
                "distinct": int(df[c].nunique(dropna=True)),
            }
            for c in df.columns
        },
    }

def clean_dataframe(df: pd.DataFrame):
    """Trim strings, coerce types, drop dupes, basic imputes."""
    X = df.copy()

    # trim strings
    for c in X.select_dtypes(include=["object", "string"]).columns:
        X[c] = X[c].astype(str).str.strip()

    # try numeric/datetime conversion for object cols
    for c in X.columns:
        if X[c].dtype == "object":
            try:
                X[c] = pd.to_numeric(X[c])
                continue
            except Exception:
                pass
            try:
                X[c] = pd.to_datetime(X[c], errors="raise", infer_datetime_format=True)
            except Exception:
                pass

    # drop duplicates
    before = len(X)
    X = X.drop_duplicates()
    dropped = before - len(X)

    # simple imputations
    for c in X.select_dtypes(include=["float", "int", "Int64", "Float64"]).columns:
        X[c] = X[c].fillna(X[c].median())
    for c in X.select_dtypes(include=["object", "string", "category"]).columns:
        X[c] = X[c].fillna("Missing")

    report = {"actions": [f"drop_duplicates: {dropped} removed",
                          "trim_strings", "fix_types", "simple_impute"]}
    return X, report

def build_chart(df: pd.DataFrame, spec: dict):
    """Render a chart from a spec: type, x, y, color, agg, (optional) z."""
    t = spec["type"]
    x = spec.get("x")
    y = spec.get("y")
    color = spec.get("color")
    agg = spec.get("agg", "sum")
    title = spec.get("title", "")

    if t in ("bar", "line"):
        if y and pd.api.types.is_numeric_dtype(df[y]):
            d = getattr(df.groupby(x)[y], agg)().reset_index()
            fig = px.bar(d, x=x, y=y, color=color) if t == "bar" else px.line(d, x=x, y=y, color=color)
        else:
            d = df.groupby(x).size().reset_index(name="count")
            fig = px.bar(d, x=x, y="count", color=color) if t == "bar" else px.line(d, x=x, y="count", color=color)

    elif t == "histogram":
        fig = px.histogram(df, x=x, color=color)

    elif t == "scatter":
        fig = px.scatter(df, x=x, y=y, color=color)

    elif t == "box":
        target = y or x
        fig = px.box(df, y=target, color=color)

    elif t == "heatmap":
        # needs x (dim), y (dim), z (measure)
        z = spec.get("z")
        if not z:
            if y and pd.api.types.is_numeric_dtype(df[y]):
                z = y
            else:
                nums = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                z = nums[0] if nums else None
        if z is None:
            cols = df.columns.tolist()
            fig = px.scatter(df, x=cols[0], y=cols[1] if len(cols) > 1 else None)
        else:
            d = getattr(df.groupby([x, y])[z], agg)().reset_index()
            fig = px.density_heatmap(d, x=x, y=y, z=z, histfunc="avg")
    else:
        cols = df.columns.tolist()
        fig = px.scatter(df, x=cols[0], y=cols[1] if len(cols) > 1 else None)

    fig.update_layout(title=title)
    return fig

# ---------- UI ----------
uploaded = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls", "parquet"])

if not uploaded:
    st.info("Upload a dataset to get started. CSV is recommended for the first run.")
    st.stop()

# Read uploaded file
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
st.subheader("1) Preview")
st.dataframe(df.head())

# 2) Schema
st.subheader("2) Schema & quick stats")
schema = infer_schema(df)
st.json(schema)

# 3) Cleaning
st.subheader("3) Auto-clean")
df_clean, report = clean_dataframe(df)
st.success(f"Cleaned rows: {len(df_clean)} (from {len(df)})")
with st.expander("Cleaning report"):
    st.json(report)

# 4) Recommended charts
st.subheader("4) Recommended charts")
dims = [c for c, v in schema["fields"].items() if v["role"] == "dimension"]
meas = [c for c, v in schema["fields"].items() if v["role"] == "measure"]
dates = [c for c in df_clean.columns if "datetime" in str(df_clean[c].dtype)]

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

# 5) Build your own chart
st.subheader("5) Build your own chart")
chart_type = st.selectbox("Chart type", ["bar", "line", "scatter", "histogram", "box", "heatmap"])
x = st.selectbox("X axis", dims + meas, index=0 if (dims or meas) else 0)
y = st.selectbox("Y axis (optional)", [""] + dims + meas, index=0)
color = st.selectbox("Color (optional)", [""] + dims + meas, index=0)
agg = st.selectbox("Aggregation (if measure)", ["sum", "mean", "count", "min", "max"], index=0)

if st.button("Render custom chart"):
    spec = {
        "type": chart_type,
        "x": x,
        "y": y or None,
        "color": color or None,
        "agg": agg,
        "title": f"{chart_type.title()} — {x}" + (f" vs {y}" if y else "")
    }
    fig = build_chart(df_clean, spec)
    st.plotly_chart(fig, use_container_width=True)

# 6) Export
st.subheader("6) Export")
st.download_button(
    "⬇️ Download cleaned CSV",
    df_clean.to_csv(index=False).encode("utf-8"),
    file_name="cleaned_data.csv",
    mime="text/csv",
)
st.download_button(
    "⬇️ Download chart specs (JSON)",
    json.dumps({"schema": schema, "recommendations": recs}, indent=2).encode("utf-8"),
    file_name="chart_specs.json",
    mime="application/json",
)
