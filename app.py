import streamlit as st
import pandas as pd
import networkx as nx
import community as community_louvain
import csv
import glob
import os
from collections import defaultdict, Counter
from networkx.algorithms import bipartite
import plotly.graph_objects as go

DATA_DIR = os.path.join(os.path.dirname(__file__), "Data")

st.set_page_config(page_title="CPN Tenant SNA Dashboard", layout="wide")
st.title("CPN Tenant & Retail Alliance — Social Network Analysis")

st.markdown("""
**CPN** (Central Pattana) operates Thailand's largest mall network. This analysis builds an **alliance graph** from the Tenant–CPN Adjacency List — each tenant is connected to CPN with a weight (1–5) based on mall presence — plus brand-ownership edges to **CRC** (Central Retail Corporation) and **CRG** (Central Restaurant Group). The graph reveals influence (in-degree), bridging power (betweenness), structural weak points (bridges), and the overall shape of the CPN Retail Alliance.
""")

# ---- CATEGORY KEYWORDS for community labeling ----
CATEGORY_KEYWORDS = {
    "Fashion & Apparel": ["FASHION", "SHOES", "BAG", "JEWEL", "WATCH", "LUXURY",
                          "CLOTH", "WEAR", "APPAREL", "ACCESSORY", "LEATHER",
                          "OPTIC", "EYE", "LENS", "SUNGLASS"],
    "Food & Beverage": ["FOOD", "BEVERAGE", "RESTAURANT", "CAFE", "COFFEE", "TEA",
                         "KITCHEN", "GRILL", "SUSHI", "RAMEN", "PIZZA", "BURGER",
                         "DESSERT", "ICE CREAM", "BAKERY", "JUICE", "CHICKEN",
                         "STEAK", "SEAFOOD", "NOODLE", "HOT POT"],
    "Technology & Electronics": ["TECHNOLOGY", "ELECTRON", "PHONE", "MOBILE",
                                   "CAMERA", "COMPUTER", "GADGET", "DIGITAL",
                                   "GAME", "IT "],
    "Beauty & Wellness": ["BEAUTY", "WELLNESS", "SPA", "CLINIC", "SALON",
                           "COSMETIC", "SKIN", "HAIR", "NAIL", "FRAGRANCE",
                           "MASSAGE", "DENTAL"],
    "Bank & Financial": ["BANK", "FINANCE", "INSURANCE", "CREDIT", "INVESTMENT"],
    "Lifestyle & Specialty": ["LIFESTYLE", "HOME", "FURNITURE", "DECOR",
                               "BOOK", "STATIONERY", "TOY", "KID", "BABY",
                               "PET", "SPORT", "FITNESS"],
    "Services & Education": ["SERVICE", "EDUCATION", "SCHOOL", "ACADEMY",
                              "MUSIC", "DANCE", "STUDIO", "CLEAN", "REPAIR"],
    "Entertainment": ["ENTERTAINMENT", "CINEMA", "THEATER", "ARCADE", "PLAY"],
}

REGION_MAP = {
    "Central Ladprao": "Bangkok", "centralwOrld": "Bangkok", "Central Pinklao": "Bangkok",
    "Central Rama 2": "Bangkok", "Central Rama 3": "Bangkok", "Central Rama 9": "Bangkok",
    "Central Bangna": "Bangkok", "Central Eastville": "Bangkok", "Central Westville": "Bangkok",
    "Central Village": "Bangkok", "Central Ramindra": "Bangkok", "Mega Bangna": "Bangkok",
    "Central Rattanathibet": "Central", "Central Chaengwattana": "Central", "Central Ayutthaya": "Central",
    "Central Salaya": "Central", "Central Mahachai": "Central", "Central Nakhon Pathom": "Central",
    "Central Chiangmai": "Northern", "Central Chiangmai Airport": "Northern", "Central Chiangrai": "Northern",
    "Central Lampang": "Northern", "Central Phitsanulok": "Northern", "Central Nakhon Sawan": "Northern",
    "Central Udon": "Northeastern", "Central Korat": "Northeastern", "Central Khonkaen": "Northeastern",
    "Central Ubon": "Northeastern",
    "Central Pattaya": "Eastern", "Central Chonburi": "Eastern", "Central Siracha": "Eastern",
    "Central Rayong": "Eastern", "Central Chanthaburi": "Eastern",
    "Central Phuket": "Southern", "Central Hatyai": "Southern", "Central Suratthani": "Southern",
    "Central Nakhon Si": "Southern", "Central Marina": "Southern", "Central Samui": "Southern",
}

REGION_COLORS = {
    "Bangkok": "#e74c3c", "Central": "#f39c12", "Northern": "#3498db",
    "Northeastern": "#2ecc71", "Eastern": "#9b59b6", "Southern": "#1abc9c",
}

@st.cache_data
def load_tenant_mall_edges():
    mall_files = glob.glob(os.path.join(DATA_DIR, "Central*.csv")) + [os.path.join(DATA_DIR, "MegaBangna.csv")]
    edges = []
    for fpath in sorted(mall_files):
        with open(fpath, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        hdr_idx = 0
        for i, l in enumerate(lines):
            if l.strip().startswith("Source") and "Target" in l:
                hdr_idx = i
                break
        reader = csv.DictReader(lines[hdr_idx:])
        for row in reader:
            if None in row or row.get("Source") is None or row.get("Target") is None:
                continue
            tenant = row["Source"].strip()
            mall = row["Target"].strip()
            try:
                w = int(row.get("Weight", 1))
            except (ValueError, TypeError):
                w = 1
            edges.append((tenant, mall, w))
    return edges

@st.cache_data
def compute_sna(edges):
    tenants = set(e[0] for e in edges)
    malls = set(e[1] for e in edges)

    uniq_pairs = set((t, m) for t, m, _ in edges)
    tdeg = defaultdict(int)
    mdeg = defaultdict(int)
    for t, m in uniq_pairs:
        tdeg[t] += 1
        mdeg[m] += 1
    in_deg = sorted(tdeg.items(), key=lambda x: -x[1])
    mall_deg = sorted(mdeg.items(), key=lambda x: -x[1])

    B = nx.Graph()
    B.add_nodes_from(tenants, bipartite=0)
    B.add_nodes_from(malls, bipartite=1)
    for t, m, w in edges:
        B.add_edge(t, m, weight=w)

    G = bipartite.weighted_projected_graph(B, tenants, ratio=False)
    G2 = nx.Graph()
    for u, v, d in G.edges(data=True):
        if d["weight"] >= 2:
            G2.add_edge(u, v, weight=d["weight"])

    n_nodes = G2.number_of_nodes()
    k = min(500, n_nodes)
    bet = nx.betweenness_centrality(G2, weight="weight", normalized=True, k=k)
    sorted_bet = sorted(bet.items(), key=lambda x: -x[1])

    try:
        bridges = list(nx.bridges(G2))
        br_list = []
        for u, v in bridges:
            w = G2[u][v]["weight"]
            br_list.append((w, u, v))
        br_list.sort(key=lambda x: -x[0])
    except Exception:
        br_list = []

    partition = community_louvain.best_partition(G2, weight="weight")
    comms = defaultdict(list)
    for node, cid in partition.items():
        comms[cid].append(node)
    sorted_comms = sorted(comms.items(), key=lambda x: -len(x[1]))

    return in_deg, mall_deg, sorted_bet, br_list, sorted_comms, G2, partition

def guess_community_name(members):
    scores = Counter()
    for m in members:
        up = m.upper()
        for cat, kws in CATEGORY_KEYWORDS.items():
            for kw in kws:
                if kw in up:
                    scores[cat] += 1
                    break
    if scores:
        return scores.most_common(1)[0][0]
    return "Mixed / General"

# ---- STORE CATEGORY from CSV for diagram coloring ----
def load_all_categories(edges):
    mall_files = glob.glob(os.path.join(DATA_DIR, "Central*.csv")) + [os.path.join(DATA_DIR, "MegaBangna.csv")]
    cat_map = {}
    for fpath in sorted(mall_files):
        with open(fpath, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        hdr_idx = 0
        for i, l in enumerate(lines):
            if l.strip().startswith("Source") and "Target" in l:
                hdr_idx = i
                break
        reader = csv.DictReader(lines[hdr_idx:])
        for row in reader:
            if None in row or row.get("Source") is None:
                continue
            t = row["Source"].strip()
            cat = row.get("Category", "").strip()
            if cat and t not in cat_map:
                cat_map[t] = cat
    return cat_map

@st.cache_data
def load_corporate_brands():
    """Load corporate→brand mapping from corporate_brands.csv."""
    corp_path = os.path.join(DATA_DIR, "corporate_brands.csv")
    brand_corp = {}
    corp_color = {}
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]
    if os.path.exists(corp_path):
        with open(corp_path, "r", encoding="utf-8-sig") as f:
            corp_set = set()
            for row in csv.DictReader(f):
                corp = row["Corporate"].strip()
                brand = row["Brand"].strip().upper()
                brand_corp[brand] = corp
                corp_set.add(corp)
            for i, c in enumerate(sorted(corp_set)):
                corp_color[c] = colors[i % len(colors)]
    return brand_corp, corp_color

with st.spinner("Loading tenant data and computing SNA metrics..."):
    edges = load_tenant_mall_edges()
    in_deg, mall_deg, bet_list, br_list, comms, G, partition = compute_sna(edges)
    cat_map = load_all_categories(edges)
    brand_corp, corp_color_map = load_corporate_brands()

# ---- Label communities ----
named_comms = []
for cid, members in comms:
    name = guess_community_name(members)
    named_comms.append((cid, name, members))

st.sidebar.header("Alliance Graph Summary")
st.sidebar.metric("Tenant–Mall Edges", f"{len(edges):,}")
st.sidebar.metric("Co-occurrence Nodes", f"{G.number_of_nodes():,}")
st.sidebar.metric("Co-occurrence Edges", f"{G.number_of_edges():,}")
st.sidebar.metric("Alliance Nodes", "CPN · CRC · CRG + tenants")
st.sidebar.markdown(
    "<small>◆ CPN = Mall operator &nbsp;&nbsp;◆ CRC = Retail &nbsp;&nbsp;◆ CRG = F&B</small>",
    unsafe_allow_html=True,
)

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    " In-Degree",
    " Betweenness",
    " Bridges",
    " Network Diagram",
])

with tab1:
    st.subheader("Tenants with the most mall presences")
    top_n = st.slider("Show top N", 5, 100, 30, key="indeg_n")
    df_in = pd.DataFrame(in_deg[:top_n], columns=["Tenant", "Malls"])
    c1, c2 = st.columns([2, 1])
    with c1:
        st.bar_chart(df_in.set_index("Tenant"), height=500)
    with c2:
        st.dataframe(df_in, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Malls by tenant count (grouped by region)")
    top_per = st.slider("Show top N malls per region (0 = show all)", 0, 10, 3, key="top_per_region")
    df_mall = pd.DataFrame(mall_deg, columns=["Mall", "Tenants"])
    df_mall["Region"] = df_mall["Mall"].map(REGION_MAP).fillna("Other")
    region_order = ["Bangkok", "Central", "Northern", "Northeastern", "Eastern", "Southern"]
    df_mall["Region"] = pd.Categorical(df_mall["Region"], categories=region_order, ordered=True)
    if top_per > 0:
        df_mall = df_mall.groupby("Region", observed=True).head(top_per).reset_index(drop=True)
    df_mall = df_mall.sort_values(["Region", "Tenants"], ascending=[True, False])
    fig = go.Figure()
    for region in region_order:
        subset = df_mall[df_mall["Region"] == region]
        if not subset.empty:
            fig.add_trace(go.Bar(
                x=subset["Tenants"], y=subset["Mall"],
                orientation="h", marker_color=REGION_COLORS[region],
                name=region, text=subset["Tenants"], textposition="outside",
            ))
    fig.update_layout(
        height=650, margin=dict(l=0, r=0, t=0, b=0),
        xaxis_title="Tenants", yaxis=dict(autorange="reversed"),
        legend=dict(title="Region", orientation="h", y=1.08),
        plot_bgcolor="rgba(0,0,0,0)",
        barmode="stack",
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Top connectors (Betweenness Centrality)")
    st.caption("Higher betweenness = more tenants depend on this tenant to bridge across different mall clusters")
    top_b = st.slider("Show top N", 5, 100, 30, key="bet_n")
    df_bet = pd.DataFrame(bet_list[:top_b], columns=["Tenant", "Betweenness"])
    c1, c2 = st.columns([2, 1])
    with c1:
        st.bar_chart(df_bet.set_index("Tenant"), height=500)
    with c2:
        st.dataframe(df_bet.style.format({"Betweenness": "{:.6f}"}), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Critical edges (Bridges)")
    st.caption("Edges whose removal would disconnect the tenant co-occurrence graph")
    if br_list:
        df_br = pd.DataFrame(br_list, columns=["Co-malls", "Tenant A", "Tenant B"])
        st.dataframe(df_br.style.format({"Co-malls": "{:d}"}), use_container_width=True, hide_index=True)
    else:
        st.info("No bridges found — the graph is fully connected beyond single-link edges.")

with tab4:
    st.subheader("CPN Tenant & Retail Alliance — Network")
    st.caption("Circles = tenants  ◆  diamonds = corporate entities. Light gray = CPN→tenant affiliation. Dashed = brand ownership. Bold = alliance. Solid = co-occurrence.")

    color_mode = st.radio("Color by", ["Community", "Corporate Group"], horizontal=True)
    max_nodes = st.slider("Max tenants to show (largest by mall count)", 20, 300, 80, key="net_n")

    top_tenants = [t for t, _ in in_deg[:max_nodes]]
    H = G.subgraph(top_tenants).copy()

    # ---- Build alliance graph ----
    H2 = nx.Graph()
    H2.add_nodes_from(H.nodes())
    for u, v in H.edges():
        if u in top_tenants and v in top_tenants:
            H2.add_edge(u, v, weight=G[u][v]["weight"])

    # Add CPN, CRC, CRG
    ALLIANCE_NODES = {"CPN": "#e74c3c", "CRC": "#3498db", "CRG": "#2ecc71"}
    for node in ALLIANCE_NODES:
        H2.add_node(node)

    # CPN → tenant edges from adjacency_list.csv
    adj_path = os.path.join(DATA_DIR, "..", "Output", "adjacency_list.csv")
    if os.path.exists(adj_path):
        with open(adj_path, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                tenant = row["Source"].strip()
                w = int(row["Weight"])
                if tenant in H2:
                    H2.add_edge("CPN", tenant, weight=w, etype="affiliation")

    # CRC/CRG → brand ownership edges
    for brand, corp in brand_corp.items():
        if brand in H2 and corp in ("CRC", "CRG"):
            H2.add_edge(corp, brand, weight=1, etype="ownership")

    # CPN ↔ CRC / CPN ↔ CRG alliance
    for corp in ("CRC", "CRG"):
        H2.add_edge("CPN", corp, weight=1, etype="alliance")

    # ---- Colors ----
    com_colors = [
        "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
        "#1abc9c", "#e67e22", "#34495e", "#e91e63", "#00bcd4",
    ]
    node_colors = {}
    if color_mode == "Corporate Group":
        other_color = "#95a5a6"
        for n in H2.nodes():
            if n in ALLIANCE_NODES:
                node_colors[n] = ALLIANCE_NODES[n]
            else:
                corp = brand_corp.get(n, "")
                node_colors[n] = corp_color_map.get(corp, other_color)
    else:
        for n in H2.nodes():
            if n in ALLIANCE_NODES:
                node_colors[n] = ALLIANCE_NODES[n]
            else:
                cid = partition.get(n, 0)
                node_colors[n] = com_colors[cid % len(com_colors)]

    # ---- Layout ----
    pos = nx.spring_layout(H2, k=2.0, iterations=60, seed=42)

    # ---- Build Plotly traces ----
    traces = []

    # 1. CPN → tenant edges (light, thin)
    for tenant in H2.neighbors("CPN"):
        if tenant in ("CRC", "CRG"):
            continue
        x0, y0 = pos["CPN"]
        x1, y1 = pos[tenant]
        w = H2["CPN"][tenant].get("weight", 1)
        traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            line=dict(width=w * 0.6, color="rgba(180,180,180,0.35)"),
            hoverinfo="none", mode="lines",
        ))

    # 2. Co-occurrence edges (tenant ↔ tenant)
    for u, v, d in H2.edges(data=True):
        if d.get("etype") in ("affiliation", "ownership", "alliance"):
            continue
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        w = d.get("weight", 1)
        traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            line=dict(width=min(w * 1.5, 6), color="rgba(150,150,150,0.35)"),
            hoverinfo="none", mode="lines",
        ))

    # 3. Ownership edges (dashed)
    for corp, clr in [("CRC", "#3498db"), ("CRG", "#2ecc71")]:
        if corp not in H2:
            continue
        cx, cy = pos[corp]
        for brand in H2.neighbors(corp):
            if brand == "CPN":
                continue
            bx, by = pos[brand]
            traces.append(go.Scatter(
                x=[cx, bx, None], y=[cy, by, None],
                line=dict(width=1.5, color=clr, dash="dash"),
                hoverinfo="none", mode="lines",
            ))

    # 4. Alliance edges (CPN ↔ CRC / CPN ↔ CRG) — bold
    for corp in ("CRC", "CRG"):
        if corp not in H2 or "CPN" not in H2:
            continue
        x0, y0 = pos["CPN"]
        x1, y1 = pos[corp]
        traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            line=dict(width=3, color=ALLIANCE_NODES[corp]),
            hoverinfo="none", mode="lines",
        ))

    # 5. Tenant nodes
    node_x, node_y, node_text, node_size, node_color_list = [], [], [], [], []
    for n in H2.nodes():
        if n in ALLIANCE_NODES:
            continue
        node_x.append(pos[n][0])
        node_y.append(pos[n][1])
        degree = H2.degree(n)
        node_size.append(min(degree * 2.5 + 5, 36))
        corp = brand_corp.get(n, "")
        cat_label = cat_map.get(n, "")
        corp_line = f"<br>Corporate: {corp}" if corp else ""
        cat_line = f"<br>Category: {cat_label}" if cat_label else ""
        node_text.append(f"{n}<br>Mall presence: {dict(in_deg).get(n, 0)} malls<br>Co-occurrences: {degree}{corp_line}{cat_line}")
        node_color_list.append(node_colors[n])

    traces.append(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=[n for n in H2.nodes() if n not in ALLIANCE_NODES],
        textposition="top center",
        textfont=dict(size=8, color="#333"),
        marker=dict(size=node_size, color=node_color_list,
                    line=dict(width=1, color="#fff")),
        hoverinfo="text", hovertext=node_text,
    ))

    # 6. Corporate nodes (diamond)
    corp_names = sorted(ALLIANCE_NODES.keys())
    corp_x = [pos[c][0] for c in corp_names]
    corp_y = [pos[c][1] for c in corp_names]
    corp_clrs = [ALLIANCE_NODES[c] for c in corp_names]
    corp_hover = []
    for c in corp_names:
        if c == "CPN":
            n_tenants = sum(1 for nb in H2.neighbors("CPN") if nb not in ("CRC", "CRG"))
            corp_hover.append(f"CPN — Mall Operator<br>Tenants in view: {n_tenants}")
        elif c == "CRC":
            n_brands = sum(1 for nb in H2.neighbors("CRC") if nb != "CPN")
            corp_hover.append(f"CRC — Central Retail Corp<br>Brands in view: {n_brands}")
        else:
            n_brands = sum(1 for nb in H2.neighbors("CRG") if nb != "CPN")
            corp_hover.append(f"CRG — Central Restaurant Group<br>Brands in view: {n_brands}")

    traces.append(go.Scatter(
        x=corp_x, y=corp_y, mode="markers+text",
        text=corp_names,
        textposition="bottom center",
        textfont=dict(size=13, color="#222"),
        marker=dict(size=26, color=corp_clrs, symbol="diamond",
                    line=dict(width=2, color="#fff")),
        hoverinfo="text", hovertext=corp_hover,
    ))

    fig = go.Figure(data=traces,
                    layout=go.Layout(
                        showlegend=False,
                        hovermode="closest",
                        margin=dict(b=0, l=0, r=0, t=0),
                        xaxis=dict(showgrid=False, zeroline=False, visible=False),
                        yaxis=dict(showgrid=False, zeroline=False, visible=False),
                        height=750,
                        plot_bgcolor="rgba(0,0,0,0)",
                    ))
    st.plotly_chart(fig, use_container_width=True)

    if corp_color_map:
        st.markdown("**Corporate Group Legend**")
        all_grps = {"CPN": "#e74c3c"} | corp_color_map
        cols = st.columns(len(all_grps))
        for col, (grp, clr) in zip(cols, sorted(all_grps.items())):
            col.markdown(f'<span style="display:inline-block;width:12px;height:12px;background:{clr};border-radius:50%;margin-right:6px"></span> {grp}', unsafe_allow_html=True)
