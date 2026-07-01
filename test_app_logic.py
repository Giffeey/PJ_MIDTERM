import sys, os
sys.path.insert(0, r"C:\DADS7201\PJ_MIDTERM")
# Test the computation functions (without streamlit)
import csv, glob
from collections import defaultdict
from networkx.algorithms import bipartite
import networkx as nx
import community as community_louvain

DATA_DIR = r"C:\DADS7201\PJ_MIDTERM\Data"

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

print(f"Edges loaded: {len(edges)}")
tenants = set(e[0] for e in edges)
malls = set(e[1] for e in edges)

tdeg = defaultdict(int)
for t, m, _ in edges:
    tdeg[t] += 1
in_deg = sorted(tdeg.items(), key=lambda x: -x[1])
print(f"Top 5 in-degree: {in_deg[:5]}")

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
print(f"Co-occurrence graph: {G2.number_of_nodes()} nodes, {G2.number_of_edges()} edges")

k = min(500, G2.number_of_nodes())
bet = nx.betweenness_centrality(G2, weight="weight", normalized=True, k=k)
sorted_bet = sorted(bet.items(), key=lambda x: -x[1])
print(f"Top betweenness: {sorted_bet[:3]}")

try:
    bridges = list(nx.bridges(G2))
    print(f"Bridges: {len(bridges)}")
except Exception as e:
    print(f"Bridge error: {e}")

partition = community_louvain.best_partition(G2, weight="weight")
comms = defaultdict(list)
for node, cid in partition.items():
    comms[cid].append(node)
print(f"Communities: {len(comms)}")

print("ALL OK")
