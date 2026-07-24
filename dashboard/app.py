"""
ACR Runtime Dashboard - Real-time Visualization

Visualizes the complete ACR runtime stack:
- Runtime metrics and operation counts
- Tile health and allocation status
- Instruction execution timeline
- Drift and refresh monitoring
- MLP inference accuracy tracking

Run from the acr/ directory:
    pip install -r requirements.txt
    streamlit run dashboard/app.py
"""

import json
import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from runtime.pulse_compiler import compile_pulse
from runtime.telemetry import RuntimeTelemetry

st.set_page_config(page_title="ACR Runtime Dashboard", layout="wide")

st.markdown(
    """
    <style>
    html, body, [class*="css"]  { font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif; }
    .stApp { background-color: #0f1117; }
    h1, h2, h3 { color: #e8e6e3; }
    .stCaption, p, label { color: #b9b6b0 !important; }
    div[data-testid="stMetricValue"] { color: #7fb3a3; }
    .metric-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #7fb3a3;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    .status-healthy { color: #3fb950; }
    .status-warning { color: #d29922; }
    .status-critical { color: #f85149; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar for data source selection
st.sidebar.title("ACR Runtime Control")

DATA_CANDIDATES = [
    "device_profile.json",
    "runtime/device_profile.json",
    "mock_device_profile.json",
    "dashboard/mock_device_profile.json",
]

TELEMETRY_CANDIDATES = [
    "telemetry_data.json",
    "runtime/telemetry_data.json",
    "../telemetry_data.json",
]


def load_profile():
    for path in DATA_CANDIDATES:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)["cells"], path
    return None, None


def load_telemetry():
    for path in TELEMETRY_CANDIDATES:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f), path
    return None, None


# Load data
cells, source_path = load_profile()
telemetry_data, telemetry_path = load_telemetry()

# Main title
st.title("Analog Compute Runtime — Dashboard")
st.caption("Real-time visualization of analog crossbar execution and runtime management")

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs([
    "Runtime Overview",
    "Tile Management",
    "Operation Timeline",
    "Device Calibration"
])

with tab1:
    st.header("Runtime Metrics Overview")
    
    if telemetry_data:
        metrics = telemetry_data.get("metrics", {})
        timeseries = telemetry_data.get("timeseries", {})
        
        # Key metrics cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Operations",
                value=metrics.get("total_operations", 0),
                delta=None
            )
        
        with col2:
            st.metric(
                label="MVM Operations",
                value=metrics.get("total_mvm", 0),
                delta=None
            )
        
        with col3:
            st.metric(
                label="Peak Tile Usage",
                value=f"{metrics.get('peak_tile_usage', 0)} tiles",
                delta=None
            )
        
        with col4:
            st.metric(
                label="Drift Compensations",
                value=metrics.get("total_drift_compensation", 0),
                delta=None
            )
        
        # Time series charts
        if timeseries.get("timestamps"):
            st.subheader("Runtime Performance Over Time")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Tile Usage Over Time**")
                tile_usage_df = pd.DataFrame({
                    "Time (s)": timeseries["timestamps"],
                    "Tiles Allocated": timeseries["tile_usage"]
                })
                st.line_chart(tile_usage_df.set_index("Time (s)"))
            
            with col2:
                st.write("**Queue Depth Over Time**")
                queue_df = pd.DataFrame({
                    "Time (s)": timeseries["timestamps"],
                    "Queue Depth": timeseries["queue_depth"]
                })
                st.line_chart(queue_df.set_index("Time (s)"))
        
        # Operation breakdown
        st.subheader("Operation Breakdown")
        op_data = {
            "Operation Type": ["MVM", "Program", "Refresh", "Calibrate"],
            "Count": [
                metrics.get("total_mvm", 0),
                metrics.get("total_programs", 0),
                metrics.get("total_refreshes", 0),
                metrics.get("total_calibrations", 0),
            ]
        }
        st.bar_chart(pd.DataFrame(op_data).set_index("Operation Type"))
    
    else:
        st.info(
            "No telemetry data available. Run the benchmark first:\n\n"
            "```bash\npython runtime/benchmark.py\n```"
        )
        
        # Show demo metrics
        st.subheader("Demo Metrics (simulated)")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Total Operations", value=150)
        with col2:
            st.metric(label="MVM Operations", value=100)
        with col3:
            st.metric(label="Peak Tile Usage", value="8 tiles")
        with col4:
            st.metric(label="Drift Compensations", value=12)

with tab2:
    st.header("Tile Management")
    
    if telemetry_data:
        tile_metrics = telemetry_data.get("tile_metrics", {})
        
        if tile_metrics:
            st.subheader("Tile Health Status")
            
            # Create tile health visualization
            tile_data = []
            for tile_id, metrics in tile_metrics.items():
                tile_data.append({
                    "Tile ID": int(tile_id),
                    "Total Operations": metrics.get("total_operations", 0),
                    "MVM Count": metrics.get("mvm_count", 0),
                    "Program Count": metrics.get("program_count", 0),
                    "Refresh Count": metrics.get("refresh_count", 0),
                    "Drift Accumulated": f"{metrics.get('drift_accumulated', 0):.3f}",
                })
            
            st.dataframe(pd.DataFrame(tile_data), use_container_width=True, hide_index=True)
            
            # Tile utilization chart
            st.subheader("Tile Utilization")
            utilization_data = {
                "Tile ID": [f"Tile {td['Tile ID']}" for td in tile_data],
                "Operations": [td["Total Operations"] for td in tile_data],
            }
            st.bar_chart(pd.DataFrame(utilization_data).set_index("Tile ID"))
        else:
            st.info("No tile metrics available yet.")
    
    else:
        st.info("Run the benchmark to see tile management data.")
        
        # Demo tile grid
        st.subheader("Demo Tile Grid (8 tiles)")
        demo_tiles = []
        for i in range(8):
            demo_tiles.append({
                "Tile ID": i,
                "Status": "Allocated" if i < 4 else "Available",
                "Health": f"{1.0 - (i * 0.05):.2f}",
                "Operations": 50 - (i * 5),
            })
        st.dataframe(pd.DataFrame(demo_tiles), use_container_width=True, hide_index=True)

with tab3:
    st.header("Operation Timeline")
    
    if telemetry_data:
        events = telemetry_data.get("events", [])
        
        if events:
            st.subheader("Recent Events")
            
            # Display recent events
            event_display = []
            for event in events[-50:]:  # Last 50 events
                event_display.append({
                    "Timestamp": f"{event['timestamp']:.3f}s",
                    "Event Type": event["event_type"],
                    "Tile ID": event["tile_id"],
                    "Details": str(event.get("payload", {}))[:100],
                })
            
            st.dataframe(pd.DataFrame(event_display), use_container_width=True, hide_index=True)
            
            # Event type distribution
            st.subheader("Event Distribution")
            event_counts = {}
            for event in events:
                event_type = event["event_type"]
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            st.bar_chart(pd.DataFrame(
                list(event_counts.items()),
                columns=["Event Type", "Count"]
            ).set_index("Event Type"))
        else:
            st.info("No events recorded yet.")
    
    else:
        st.info("Run the benchmark to see operation timeline.")

with tab4:
    st.header("Device Calibration")
    
    if cells:
        st.subheader("Per-cell Calibration Parameters")
        st.dataframe(pd.DataFrame(cells), use_container_width=True, hide_index=True)
        
        # Pulse compiler test
        st.subheader("Pulse Compiler Test")
        ids = [c["cell_id"] for c in cells]
        cell_id = st.selectbox("Select Cell", ids)
        profile = next(c for c in cells if c["cell_id"] == cell_id)
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_g = st.slider("Current Conductance (normalized)", 0.0, 1.0, 0.3)
            target_g = st.slider("Target Conductance (normalized)", 0.0, 1.0, 0.7)
        
        with col2:
            if st.button("Compile Pulse Plan", type="primary"):
                plan = compile_pulse(profile, current_g, target_g)
                st.write(f"**{len(plan)} pulses planned**")
                st.json(plan)
                
                # Simulate trajectory
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
                
                st.caption("Simulated Conductance Trajectory")
                st.line_chart(trajectory)
    else:
        st.info(
            "No device profile data available. Generate mock data:\n\n"
            "```bash\npython dashboard/mock_data.py\n```"
        )

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### ACR Runtime v0.3.0")
st.sidebar.markdown("Phase 3: Runtime Architecture")
if telemetry_path:
    st.sidebar.markdown(f"Telemetry: `{telemetry_path}`")
if source_path:
    st.sidebar.markdown(f"Device Profile: `{source_path}`")
