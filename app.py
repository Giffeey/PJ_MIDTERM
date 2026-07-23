import streamlit as st
import pandas as pd
import os
import json
import plotly.graph_objects as go

OUT_DIR = os.path.join(os.path.dirname(__file__), "Output")

st.set_page_config(page_title="CPN Tenant SNA", layout="wide")
st.title("CPN Tenant & Retail Alliance — Social Network Analysis")

CATEGORY_COLORS = {
    "Food & Beverage": "#ff5722",
    "Beauty & Wellness": "#4caf50",
    "Technology & Electronics": "#2196f3",
    "Bank & Financial Services": "#ffc107",
    "Fashion & Apparel": "#e91e63",
    "Lifestyle & Specialty": "#9c27b0",
    "Services & Education": "#00bcd4",
    "Entertainment": "#ff9800",
    "Supermarket": "#795548",
}

cat_map = {}
brandnode_path = os.path.join(OUT_DIR, "brandnode.csv")
if os.path.exists(brandnode_path):
    for _, r in pd.read_csv(brandnode_path).iterrows():
        cats = str(r.get("Categories", "")).strip()
        if cats:
            cat_map[r["Tenant"].strip()] = cats.split(";")[0].strip()

def get_color(tenant):
    return CATEGORY_COLORS.get(cat_map.get(tenant, "Other"), "#9e9e9e")

# ── Data Loaders ──
@st.cache_data
def load_in_degree():
    df = pd.read_csv(os.path.join(OUT_DIR, "in_degree_centrality.csv"))
    return df.rename(columns={"Degree": "Malls"})

@st.cache_data
def load_betweenness():
    return pd.read_csv(os.path.join(OUT_DIR, "betweenness_centrality.csv"))

@st.cache_data
def load_eigenvector():
    return pd.read_csv(os.path.join(OUT_DIR, "eigenvector_centrality.csv"))

@st.cache_data
def load_stats():
    path = os.path.join(OUT_DIR, "graph_stats.txt")
    stats = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                k, v = line.split(":", 1)
                stats[k.strip()] = v.strip()
    return stats

@st.cache_data
def load_cpi():
    df = pd.read_csv(os.path.join(OUT_DIR, "cpi_data.csv"))
    df["ym"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
    df["ym_label"] = df["monthLabel"]
    return df

@st.cache_data
def load_cci():
    return pd.read_csv(os.path.join(OUT_DIR, "cci_excel_data.csv"))

@st.cache_data
def load_gnn_pred():
    p = os.path.join(OUT_DIR, "gnn_predictions.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

@st.cache_data
def load_gnn_analysis():
    p = os.path.join(OUT_DIR, "gnn_analysis.json")
    if os.path.exists(p):
        with open(p, "r") as f:
            return json.load(f)
    return None

with st.spinner("Loading SNA data..."):
    df_in = load_in_degree()
    df_bet = load_betweenness()
    df_eig = load_eigenvector()
    stats = load_stats()
    df_gnn = load_gnn_pred()
    gnn_analysis = load_gnn_analysis()

top_in = df_in.head(10)
top_bet = df_bet.head(10)
top_eig = df_eig.head(10)

# Extract R² from analysis if available
gnn_r2 = gnn_analysis.get("model", {}).get("r2", 0.0) if gnn_analysis else 0.0

st.markdown("""
This analysis builds a **tenant co-occurrence network** from CPN's 44 mall properties across Thailand.
Two tenants are connected when they appear together in the same mall; edge weight = number of shared malls.
The graph reveals **influence** (degree = mall presence), **bridging power** (betweenness centrality),
**connectedness** (eigenvector centrality), and **GNN-predicted composite significance** within the CPN Retail Alliance.
""")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Shops / Tenants", stats.get("Total unique tenants", "—"))
col2.metric("CPN (Hub)", "1")
col3.metric("Alliance (CRC, CRG)", "2")
col4.metric("Tenant–Mall Edges", stats.get("Total tenant-mall edges", "—"))
col5.metric("Co-occurrence Edges", stats.get("Co-occurrence graph edges", "—"))


def make_bar_chart(df, val_col, label):
    fig = go.Figure()
    for _, row in df.iterrows():
        fig.add_trace(go.Bar(
            x=[row[val_col]], y=[row["Tenant"]], orientation="h",
            marker_color=get_color(row["Tenant"]),
            text=row[val_col], texttemplate="%{x}" if val_col == "Malls" else "%{x:.5f}",
            textposition="outside", showlegend=False, width=0.7,
        ))
    fig.update_layout(
        height=400, margin=dict(l=0, r=30, t=0, b=0),
        xaxis=dict(title=label),
        yaxis=dict(autorange="reversed", type="category"),
        plot_bgcolor="rgba(0,0,0,0)", font=dict(size=12),
    )
    return fig


def make_table(df, val_col, fmt):
    styled = df.style
    if fmt:
        styled = styled.format({val_col: fmt})
    return styled


# ── 1. Top 10 Degree ──
st.subheader("Top 10 by Degree Centrality")
c1, c2 = st.columns([2, 1.2])
c1.plotly_chart(make_bar_chart(top_in, "Malls", "Number of Malls"), use_container_width=True)
c2.dataframe(
    make_table(top_in, "Malls", "{:d}"),
    use_container_width=True, hide_index=True,
    column_config={"Tenant": "Tenant", "Malls": "Malls"},
)

# ── 2. Top 10 Betweenness ──
st.subheader("Top 10 by Betweenness Centrality")
st.caption("Higher betweenness = more tenants depend on this tenant to bridge across different mall clusters")
c3, c4 = st.columns([2, 1.2])
c3.plotly_chart(make_bar_chart(top_bet, "Betweenness", "Betweenness Centrality"), use_container_width=True)
c4.dataframe(
    make_table(top_bet, "Betweenness", "{:.6f}"),
    use_container_width=True, hide_index=True,
    column_config={"Tenant": "Tenant", "Betweenness": st.column_config.NumberColumn("Betweenness", format="%.6f")},
)

# ── 3. Top 10 Eigenvector ──
st.subheader("Top 10 by Eigenvector Centrality")
st.caption("Higher eigenvector = connected to many well-connected tenants (influential neighbors)")
c5, c6 = st.columns([2, 1.2])
c5.plotly_chart(make_bar_chart(top_eig, "Eigenvector", "Eigenvector Centrality"), use_container_width=True)
c6.dataframe(
    make_table(top_eig, "Eigenvector", "{:.6f}"),
    use_container_width=True, hide_index=True,
    column_config={"Tenant": "Tenant", "Eigenvector": st.column_config.NumberColumn("Eigenvector", format="%.6f")},
)

# ── 4. GNN Prediction ──
st.subheader("GNN-Predicted Tenant Significance (Composite Score)")
st.caption(f"GCN model learned from category features + co-occurrence graph | R² = {gnn_r2:.4f} | Target = 0.4·z(Deg) + 0.3·z(Bet) + 0.2·z(Eig) + 0.1·Internal")

if not df_gnn.empty:
    top_gnn = df_gnn.head(10)
    fig_gnn = go.Figure()
    for _, row in top_gnn.iterrows():
        fig_gnn.add_trace(go.Bar(
            x=[row["GNN_Prediction"]], y=[row["Tenant"]], orientation="h",
            marker_color=get_color(row["Tenant"]),
            text=row["GNN_Prediction"], texttemplate="%{x:.3f}",
            textposition="outside", showlegend=False, width=0.7,
        ))
    fig_gnn.update_layout(
        height=400, margin=dict(l=0, r=30, t=0, b=0),
        xaxis=dict(title="GNN Predicted Score"),
        yaxis=dict(autorange="reversed", type="category"),
        plot_bgcolor="rgba(0,0,0,0)", font=dict(size=12),
    )
    col_g1, col_g2 = st.columns([2, 1.2])
    col_g1.plotly_chart(fig_gnn, use_container_width=True)
    col_g2.dataframe(
        top_gnn[["Tenant", "Category", "CompositeScore", "GNN_Prediction"]].style.format({"CompositeScore": "{:.4f}", "GNN_Prediction": "{:.4f}"}),
        use_container_width=True, hide_index=True,
    )

if gnn_analysis:
    with st.expander("Per-Category GNNExplainer Insights — Top tenant & key connections by category"):
        for cat_info in gnn_analysis.get("categories", []):
            nbrs = cat_info["top_neighbors"]
            nbr_str = ", ".join(f'{n["tenant"]} ({n["category"]})' for n in nbrs)
            st.markdown(f"**{cat_info['category']}** ({cat_info['count']} nodes)")
            st.markdown(f"- Top tenant: `{cat_info['top_tenant']}` (score: {cat_info['top_score']:.4f})")
            st.markdown(f"- Key neighbor: `{nbrs[0]['tenant']}` ({nbrs[0]['category']}, edge importance: {nbrs[0]['importance']:.3f})")
            st.markdown(f"- Top 5 neighbors: {nbr_str}")
            st.markdown("---")

# ── 5. CPI Section ──
st.subheader("Consumer Price Index (CPI)")
st.caption("Source: CPI-G Report (TPSO), base year 2566 = 100")
df_cpi = load_cpi()
regions = df_cpi[["regionCode", "regionName"]].drop_duplicates().set_index("regionCode")["regionName"].to_dict()
selected = st.selectbox("Select region", options=list(regions.keys()), format_func=lambda c: regions[c], index=0)

cpi_sel = df_cpi[df_cpi["regionCode"] == selected].sort_values(["year", "month"])

fig_cpi = go.Figure()
fig_cpi.add_trace(go.Scatter(
    x=cpi_sel["ym_label"], y=cpi_sel["index"], mode="lines+markers",
    name=f"CPI - {regions[selected]}",
    line=dict(color="#2196f3", width=2), marker=dict(size=6),
))
for rc, rn in regions.items():
    if rc == selected:
        continue
    sub = df_cpi[df_cpi["regionCode"] == rc].sort_values(["year", "month"])
    fig_cpi.add_trace(go.Scatter(
        x=sub["ym_label"], y=sub["index"], mode="lines",
        name=rn, line=dict(width=1, dash="dot"), opacity=0.4, showlegend=True,
    ))
fig_cpi.update_layout(
    height=400, margin=dict(l=0, r=30, t=0, b=40),
    xaxis=dict(title=""), yaxis=dict(title="CPI Index (base 2566)"),
    plot_bgcolor="rgba(0,0,0,0)", font=dict(size=12), hovermode="x unified",
)
col_cpi1, col_cpi2 = st.columns([2.5, 1.2])
col_cpi1.plotly_chart(fig_cpi, use_container_width=True)
latest = cpi_sel.iloc[-1]
col_cpi2.metric("Latest CPI", f"{latest['index']:.2f}", f"{latest['change']:+.2f} (MoM)")
col_cpi2.metric("Period", f"{cpi_sel['ym_label'].iloc[0]} to {cpi_sel['ym_label'].iloc[-1]}")
col_cpi2.metric("Avg CPI", f"{cpi_sel['index'].mean():.2f}")
col_cpi2.metric("Regions Available", str(len(regions)))

# ── 6. CCI Section ──
st.subheader("Consumer Confidence Index (CCI)")
st.caption("Source: CCI Report (TPSO), มิ.ย.2568 – มิ.ย.2569")
df_cci = load_cci()
df_cci = df_cci.sort_values("ym")

fig_cci = go.Figure()
fig_cci.add_trace(go.Scatter(
    x=df_cci["ym"], y=df_cci["รวม"], mode="lines+markers",
    name="Overall CCI", line=dict(color="#ff5722", width=2),
))
fig_cci.add_trace(go.Scatter(
    x=df_cci["ym"], y=df_cci["ปัจจุบัน"], mode="lines+markers",
    name="Present Situation", line=dict(color="#ffc107", width=2, dash="dash"),
))
fig_cci.add_trace(go.Scatter(
    x=df_cci["ym"], y=df_cci["อนาคต"], mode="lines+markers",
    name="Future Expectation", line=dict(color="#4caf50", width=2, dash="dot"),
))
fig_cci.update_layout(
    height=400, margin=dict(l=0, r=30, t=0, b=40),
    xaxis=dict(title=""), yaxis=dict(title="CCI Index"),
    plot_bgcolor="rgba(0,0,0,0)", font=dict(size=12),
    hovermode="x unified", legend=dict(orientation="h", y=1.12),
)
col_cci1, col_cci2 = st.columns([2.5, 1.2])
col_cci1.plotly_chart(fig_cci, use_container_width=True)
clatest = df_cci.iloc[-1]
col_cci2.metric("Latest CCI", f"{clatest['รวม']:.1f}", f"{clatest['ปัจจุบัน']:.1f} / {clatest['อนาคต']:.1f} (P/F)")
col_cci2.metric("Period", f"{df_cci['ym'].iloc[0]} to {df_cci['ym'].iloc[-1]}")
