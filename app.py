import streamlit as st
import pandas as pd
import networkx as nx
import community as community_louvain
import csv
import glob
import os
from collections import defaultdict
from networkx.algorithms import bipartite

DATA_DIR = os.path.join(os.path.dirname(__file__), "Data")

st.set_page_config(page_title="CPN Tenant SNA Dashboard", layout="wide")
st.title("CPN Tenant & Retail Alliance — Social Network Analysis")

# ---- LOAD DATA ----
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

    # ---- In-Degree ----
    tdeg = defaultdict(int)
    mdeg = defaultdict(int)
    for t, m, _ in edges:
        tdeg[t] += 1
        mdeg[m] += 1
    in_deg = sorted(tdeg.items(), key=lambda x: -x[1])
    mall_deg = sorted(mdeg.items(), key=lambda x: -x[1])

    # ---- Co-occurrence graph ----
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

    # ---- Betweenness ----
    n_nodes = G2.number_of_nodes()
    k = min(500, n_nodes)
    bet = nx.betweenness_centrality(G2, weight="weight", normalized=True, k=k)
    sorted_bet = sorted(bet.items(), key=lambda x: -x[1])

    # ---- Bridges ----
    try:
        bridges = list(nx.bridges(G2))
        br_list = []
        for u, v in bridges:
            w = G2[u][v]["weight"]
            br_list.append((w, u, v))
        br_list.sort(key=lambda x: -x[0])
    except Exception:
        br_list = []

    # ---- Communities ----
    partition = community_louvain.best_partition(G2, weight="weight")
    comms = defaultdict(list)
    for node, cid in partition.items():
        comms[cid].append(node)
    sorted_comms = sorted(comms.items(), key=lambda x: -len(x[1]))

    return in_deg, mall_deg, sorted_bet, br_list, sorted_comms, G2

with st.spinner("Loading tenant data and computing SNA metrics..."):
    edges = load_tenant_mall_edges()
    in_deg, mall_deg, bet_list, br_list, comms, G = compute_sna(edges)

st.sidebar.header("Graph Summary")
st.sidebar.metric("Tenant–Mall Edges", f"{len(edges):,}")
st.sidebar.metric("Co-occurrence Nodes", f"{G.number_of_nodes():,}")
st.sidebar.metric("Co-occurrence Edges", f"{G.number_of_edges():,}")
st.sidebar.metric("Communities Found", len(comms))

# ============================================================
# PAGE 1 — In-Degree Centrality
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    " In-Degree Centrality",
    " Betweenness Centrality",
    " Bridges",
    " Communities",
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
    st.subheader("Malls by tenant count")
    df_mall = pd.DataFrame(mall_deg, columns=["Mall", "Tenants"])
    st.bar_chart(df_mall.set_index("Mall"), height=400)

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
    for cid, members in comms:
        with st.expander(f"Community {cid} — {len(members)} members"):
            df_c = pd.DataFrame({"Tenant": sorted(members)})
            st.dataframe(df_c, use_container_width=True, hide_index=True)
