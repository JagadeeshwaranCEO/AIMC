"""
ACR Day 1 - Runtime Dashboard (Streamlit)

Reads whichever device_profile.json it can find (mock data today,
real data once the Mac side lands it in the same spot) and renders:
  - per-cell calibration parameters
  - an interactive pulse-compiler test, with the resulting trajectory

Run from the acr/ directory:
    pip install -r requirements.txt
    streamlit run dashboard/app.py
"""

import json
import os
import sys

import pandas as pd
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from runtime.pulse_compiler import compile_pulse

st.set_page_config(page_title="ACR Runtime Dashboard", layout="wide")

st.markdown(
    """
    <style>
    html, body, [class*="css"]  { font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif; }
    .stApp { background-color: #0f1117; }
    h1, h2, h3 { color: #e8e6e3; }
    .stCaption, p, label { color: #b9b6b0 !important; }
    div[data-testid="stMetricValue"] { color: #7fb3a3; }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_CANDIDATES = [
    "device_profile.json",
    "runtime/device_profile.json",
    "mock_device_profile.json",
    "dashboard/mock_device_profile.json",
]


def load_profile():
    for path in DATA_CANDIDATES:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)["cells"], path
    st.error(
        "No device_profile.json found.\n\n"
        "Run `python dashboard/mock_data.py` for mock data, "
        "or `python runtime/profiler.py` for real data."
    )
    st.stop()


cells, source_path = load_profile()
is_mock = "mock" in source_path

st.title("Analog Compute Runtime — Day 1 Dashboard")
st.caption(f"Data source: `{source_path}`  ·  {len(cells)} cells" + ("  ·  MOCK DATA" if is_mock else "  ·  REAL DATA"))

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Per-cell calibration")
    st.dataframe(pd.DataFrame(cells), use_container_width=True, hide_index=True)

with col2:
    st.subheader("Pulse compiler test")
    ids = [c["cell_id"] for c in cells]
    cell_id = st.selectbox("Cell", ids)
    profile = next(c for c in cells if c["cell_id"] == cell_id)

    current_g = st.slider("Current conductance (normalized)", 0.0, 1.0, 0.3)
    target_g = st.slider("Target conductance (normalized)", 0.0, 1.0, 0.7)

    if st.button("Compile pulse plan", type="primary"):
        plan = compile_pulse(profile, current_g, target_g)
        st.write(f"**{len(plan)} pulses planned**")
        st.json(plan)

        g = current_g
        trajectory = [g]
        for step in plan:
            gamma = profile["gamma_up_est"] if step["direction"] == "SET" else profile["gamma_down_est"]
            base = profile["pulse_gain_est"] * step["pulse_width"]
            if step["direction"] == "SET":
                g += base * ((1 - g) ** gamma)
            else:
                g -= base * (g ** gamma)
            g = max(0.0, min(1.0, g))
            trajectory.append(g)

        st.caption("Simulated conductance trajectory (open-loop)")
        st.line_chart(trajectory)
