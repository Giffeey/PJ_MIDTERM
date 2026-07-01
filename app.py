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
**CPN** (Central Pattana) operates Thailand's largest mall network. **CRC** (Central Retail Corporation) and **CRG** (Central Restaurant Group) are its key retail-alliance partners — CRC anchors malls with department stores & specialty retail while CRG supplies the F&B lineup. This analysis maps how 3,800+ tenants co-occur across 39 CPN malls to reveal influence (in-degree), bridging power (betweenness), structural weak points (bridges), and natural clusters (communities).
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

st.sidebar.header("Network Summary")
st.sidebar.metric("Tenant–Mall Edges", f"{len(edges):,}")
st.sidebar.metric("Co-occurrence Nodes", f"{G.number_of_nodes():,}")
st.sidebar.metric("Co-occurrence Edges", f"{G.number_of_edges():,}")
st.sidebar.metric("Communities Found", len(comms))
st.sidebar.metric("Corporate Entities", "CPN · CRC · CRG")
st.sidebar.markdown(
    "<small>◆ CPN = Mall operator &nbsp;&nbsp;◆ CRC = Retail &nbsp;&nbsp;◆ CRG = F&B</small>",
    unsafe_allow_html=True,
)

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    " In-Degree",
    " Betweenness",
    " Bridges",
    " Communities",
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
    st.subheader("Tenant communities (Louvain detection)")
    for cid, name, members in named_comms:
        with st.expander(f"**{name}** — {len(members)} members"):
            rows = []
            for m in sorted(members):
                corp = brand_corp.get(m, "")
                cat_label = cat_map.get(m, "")
                mall_cnt = dict(in_deg).get(m, 0)
                rows.append({"Tenant": m, "Malls": mall_cnt, "Category": cat_label,
                             "Corporate": corp})
            df_c = pd.DataFrame(rows)
            st.dataframe(df_c, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("CPN Tenant & Retail Alliance — Co-occurrence Network")
    st.caption("Circles = tenants ◆ diamonds = corporate entities (CPN, CRC, CRG). Dashed lines = brand ownership. Edges = co-occur in ≥2 same malls.")

    color_mode = st.radio("Color by", ["Community", "Corporate Group"], horizontal=True)
    max_nodes = st.slider("Max tenants to show (largest by mall count)", 20, 300, 80, key="net_n")

    top_tenants = [t for t, _ in in_deg[:max_nodes]]
    H = G.subgraph(top_tenants).copy()
    H2 = nx.Graph()
    H2.add_nodes_from(H.nodes())
    for u, v in H.edges():
        if u in top_tenants and v in top_tenants:
            H2.add_edge(u, v, weight=G[u][v]["weight"])

    com_colors = [
        "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
        "#1abc9c", "#e67e22", "#34495e", "#e91e63", "#00bcd4",
    ]
    node_colors = {}
    if color_mode == "Corporate Group":
        other_color = "#95a5a6"
        for n in H2.nodes():
            corp = brand_corp.get(n, "")
            node_colors[n] = corp_color_map.get(corp, other_color)
    else:
        for n in H2.nodes():
            cid = partition.get(n, 0)
            node_colors[n] = com_colors[cid % len(com_colors)]

    pos = nx.spring_layout(H2, k=2.5, iterations=50, seed=42)

    # ---- Corporate entity nodes (CPN, CRC, CRG) ----
    CORP_NODES = {"CPN": "#e74c3c", "CRC": "#3498db", "CRG": "#2ecc71"}
    corp_children = {c: [] for c in CORP_NODES}
    for brand, corp in brand_corp.items():
        if brand in H2 and corp in CORP_NODES:
            corp_children[corp].append(brand)

    # Position each corporate at outward offset from its brand centroid
    corp_pos = {}
    for corp in CORP_NODES:
        children = corp_children[corp]
        if children:
            xs = [pos[b][0] for b in children]
            ys = [pos[b][1] for b in children]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            d = (cx**2 + cy**2)**0.5
            if d < 0.1:
                off = {"CPN": (2.5, 1.5), "CRC": (1.5, -2.5), "CRG": (-2.5, 1.5)}
                corp_pos[corp] = (cx + off[corp][0], cy + off[corp][1])
            else:
                scale = 1 + max(1.8 / d, 0.5)
                corp_pos[corp] = (cx * scale, cy * scale)
        else:
            default = {"CPN": (3.0, 1.5), "CRC": (1.5, -3.0), "CRG": (-3.0, 1.5)}
            corp_pos[corp] = default[corp]

    traces = []

    # 1. Tenant co-occurrence edges
    for u, v, d in H2.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        w = d.get("weight", 1)
        traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            line=dict(width=min(w * 1.5, 6), color="rgba(150,150,150,0.4)"),
            hoverinfo="none", mode="lines",
        ))

    # 2. Corporate → Brand dashed edges
    for corp, clr in CORP_NODES.items():
        cx, cy = corp_pos[corp]
        for brand in corp_children[corp]:
            bx, by = pos[brand]
            traces.append(go.Scatter(
                x=[cx, bx, None], y=[cy, by, None],
                line=dict(width=1.5, color=clr, dash="dash"),
                hoverinfo="none", mode="lines",
            ))

    # 3. Tenant nodes
    node_x, node_y, node_text, node_size, node_color_list = [], [], [], [], []
    for n in H2.nodes():
        node_x.append(pos[n][0])
        node_y.append(pos[n][1])
        degree = H2.degree(n)
        node_size.append(min(degree * 3 + 5, 40))
        corp = brand_corp.get(n, "")
        cat_label = cat_map.get(n, "")
        corp_line = f"<br>Corporate: {corp}" if corp else ""
        cat_line = f"<br>Category: {cat_label}" if cat_label else ""
        node_text.append(f"{n}<br>Mall presence: {dict(in_deg).get(n, 0)} malls<br>Co-occurrences: {degree}{corp_line}{cat_line}")
        node_color_list.append(node_colors[n])

    traces.append(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=[n for n in H2.nodes()],
        textposition="top center",
        textfont=dict(size=8, color="#333"),
        marker=dict(size=node_size, color=node_color_list,
                    line=dict(width=1, color="#fff")),
        hoverinfo="text", hovertext=node_text,
    ))

    # 4. Corporate nodes (diamond markers)
    corp_names = list(CORP_NODES.keys())
    corp_x = [corp_pos[c][0] for c in corp_names]
    corp_y = [corp_pos[c][1] for c in corp_names]
    corp_clrs = [CORP_NODES[c] for c in corp_names]
    corp_hover = [f"{c}<br>Brands in view: {len(corp_children[c])}" for c in corp_names]

    traces.append(go.Scatter(
        x=corp_x, y=corp_y, mode="markers+text",
        text=corp_names,
        textposition="bottom center",
        textfont=dict(size=13, color="#222"),
        marker=dict(size=24, color=corp_clrs, symbol="diamond",
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
        cols = st.columns(len(corp_color_map))
        for col, (corp, clr) in zip(cols, sorted(corp_color_map.items())):
            col.markdown(f'<span style="display:inline-block;width:12px;height:12px;background:{clr};border-radius:50%;margin-right:6px"></span> {corp}', unsafe_allow_html=True)
