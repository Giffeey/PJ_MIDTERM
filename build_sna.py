import csv
import os
import glob
import pandas as pd
import networkx as nx
import community as community_louvain
from collections import defaultdict
from networkx.algorithms import bipartite

DATA_DIR = r"C:\DADS7201\PJ_MIDTERM\Data"
OUT_DIR = r"C:\DADS7201\PJ_MIDTERM\Output"
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# STEP 1: Load all tenant-mall bipartite edges
# ============================================================
def load_tenant_mall_csv(fpath):
    with open(fpath, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    header_idx = 0
    for i, l in enumerate(lines):
        if l.strip().startswith("Source") and "Target" in l:
            header_idx = i
            break
    csv_lines = lines[header_idx:]
    reader = csv.DictReader(csv_lines)
    result = []
    for row in reader:
        if None in row or row.get("Source") is None or row.get("Target") is None:
            continue
        tenant = row["Source"].strip()
        mall_name = row["Target"].strip()
        try:
            weight = int(row.get("Weight", 1))
        except (ValueError, TypeError):
            weight = 1
        result.append((tenant, mall_name, weight))
    return result

mall_files = glob.glob(os.path.join(DATA_DIR, "Central*.csv")) + [os.path.join(DATA_DIR, "MegaBangna.csv")]
tenant_mall_edges = []
for fpath in sorted(mall_files):
    tenant_mall_edges.extend(load_tenant_mall_csv(fpath))

print(f"Loaded {len(tenant_mall_edges)} tenant-mall edges from {len(mall_files)} files")
tenants = set(e[0] for e in tenant_mall_edges)
malls = set(e[1] for e in tenant_mall_edges)
print(f"  Unique tenants: {len(tenants)}, Unique malls: {len(malls)}")

# ============================================================
# STEP 2: Define company relationship edges (from 2025 One Report)
# ============================================================
company_edges = [
    ("CPN", "Central Group Co. Ltd.", 4, "Ultimate Parent"),
    ("CPN", "Central Holdings Company Limited", 3, "Major Shareholder"),
    ("CPN", "Central Retail Corporation (CRC)", 5, "Anchor Tenant"),
    ("CRC", "Central Department Store", 5, "Retail Brand"),
    ("CRC", "Robinson Department Store", 5, "Retail Brand"),
    ("CRC", "Central Trading", 3, "Retail Brand"),
    ("CRC", "Power Buy", 4, "Retail Brand"),
    ("CRC", "CRC Sports / Supersports", 4, "Retail Brand"),
    ("CRC", "CRC Thai Watsadu", 4, "Retail Brand"),
    ("CRC", "Earth Care", 2, "Retail Brand"),
    ("CRC", "CR Chiangmai", 2, "Retail Brand"),
    ("CRC", "Tops / Tops Food Hall / Tops Daily", 4, "Retail Brand"),
    ("CRC", "Big C / Go!", 4, "Retail Brand"),
    ("CRC", "B2S", 3, "Retail Brand"),
    ("CRC", "OfficeMate", 3, "Retail Brand"),
    ("CRC", "Matsukiyo", 3, "Retail Brand"),
    ("CPN", "Central Restaurant Group (CRG)", 4, "F&B Operator"),
    ("CRG", "Mister Donut", 3, "F&B Brand"),
    ("CRG", "KFC", 3, "F&B Brand"),
    ("CRG", "Auntie Anne's", 3, "F&B Brand"),
    ("CRG", "Pepper Lunch", 3, "F&B Brand"),
    ("CRG", "Yoshinoya", 3, "F&B Brand"),
    ("CRG", "Ootoya", 3, "F&B Brand"),
    ("CRG", "Katsuya", 3, "F&B Brand"),
    ("CRG", "Cold Stone", 3, "F&B Brand"),
    ("CRG", "Somtam Nua", 3, "F&B Brand"),
    ("CRG", "Shinkanzen Sushi", 3, "F&B Brand"),
    ("CRG", "Chabuton", 3, "F&B Brand"),
    ("CRG", "Salad Factory", 3, "F&B Brand"),
    ("CPN", "Central Food Avenue", 4, "Direct Subsidiary"),
    ("CPN", "Central World Co.", 4, "Direct Subsidiary"),
    ("CPN", "Central Pattana Rama 2", 3, "Direct Subsidiary"),
    ("CPN", "Central Pattana Rama 3", 3, "Direct Subsidiary"),
    ("CPN", "Central Pattana Chiangmai", 3, "Direct Subsidiary"),
    ("CPN", "Central Pattana Rattanathibet", 3, "Direct Subsidiary"),
    ("CPN", "Central Pattana Residence", 3, "Direct Subsidiary"),
    ("CPN", "Central Pattana Development", 3, "Direct Subsidiary"),
    ("CPN", "CPN Global", 3, "Direct Subsidiary"),
    ("CPN", "Central Pattana Nine Square", 3, "Direct Subsidiary"),
    ("CPN", "Central Pattana Khon Kaen", 3, "Direct Subsidiary"),
    ("CPN", "CPN Pattaya", 3, "Direct Subsidiary"),
    ("CPN", "CPN Rayong", 3, "Direct Subsidiary"),
    ("CPN", "CPN Korat", 3, "Direct Subsidiary"),
    ("CPN", "CPN Estate", 3, "Direct Subsidiary"),
    ("CPN", "Central Pattana Green Growth", 3, "Direct Subsidiary"),
    ("CPN", "Suanlum Property", 3, "Direct Subsidiary"),
    ("CPN", "Phraram 4 Development", 3, "Direct Subsidiary"),
    ("CPN", "Saladang Property Management", 3, "Direct Subsidiary"),
    ("CPN", "CPN REIT Management", 3, "Direct Subsidiary"),
    ("CPN", "Dara Harbour", 3, "Direct Subsidiary"),
    ("CPN", "CPN Pattaya Hotel", 3, "Direct Subsidiary"),
    ("CPN", "Chanakun Development", 3, "Direct Subsidiary"),
    ("CPN", "CPN Village", 3, "Direct Subsidiary"),
    ("CPN", "Bayswater", 2, "Direct Subsidiary"),
    ("CPN", "CentralPattana Life", 3, "Direct Subsidiary"),
    ("CPN", "Grand Canal Land (GLAND)", 4, "Indirect Subsidiary"),
    ("GLAND", "Belle Development", 3, "Sub-subsidiary"),
    ("GLAND", "Belle Assets", 3, "Sub-subsidiary"),
    ("GLAND", "Sterling Equity", 3, "Sub-subsidiary"),
    ("GLAND", "G Land Property Management", 3, "Sub-subsidiary"),
    ("GLAND", "Praram 9 Square", 3, "Sub-subsidiary"),
    ("GLAND", "Ratchada Asset Holding", 3, "Sub-subsidiary"),
    ("CPN", "Siam Future Development (SF)", 4, "Indirect Subsidiary"),
    ("SF", "Petchkasem Power Center", 3, "Sub-subsidiary"),
    ("SF", "Ekkamai Lifestyle Center", 3, "Sub-subsidiary"),
    ("SF", "Siam Future Property", 3, "Sub-subsidiary"),
    ("SF", "Ratchayothin Avenue", 2, "Sub-subsidiary"),
    ("SF", "Ratchayothin Avenue Management", 2, "Sub-subsidiary"),
    ("CPN", "Bangna Central Property", 3, "Indirect Subsidiary"),
    ("CPN", "Global Retail Development & Investment", 3, "Indirect Subsidiary"),
    ("CPN", "CPN Complex", 3, "Indirect Subsidiary"),
    ("CPN", "CPN City", 3, "Indirect Subsidiary"),
    ("CPN", "C.S. City", 3, "Indirect Subsidiary"),
    ("CPN", "CPN Residence Management", 3, "Indirect Subsidiary"),
    ("CPN", "Pruksachart Property", 3, "Indirect Subsidiary"),
    ("CPN", "CPN Global Vietnam", 3, "Indirect Subsidiary"),
    ("CPN", "Phenomenon Creation", 3, "Indirect Subsidiary"),
    ("CPN", "Chipper Global", 3, "Indirect Subsidiary"),
    ("CPN", "CPN Ventures Sdn. Bhd.", 3, "Indirect Subsidiary"),
    ("CPN", "Central Plaza i-City Real Estate Sdn. Bhd.", 3, "Indirect Subsidiary"),
    ("CPN", "Thai Business Fund 4", 3, "Fund"),
    ("CPN", "CPN Retail Growth Leasehold REIT (CPNREIT)", 4, "Related REIT"),
    ("CPN", "CPN Commercial Growth Leasehold Property Fund (CPNCG)", 3, "Related Fund"),
    ("CPN", "Dusit Thani PCL", 4, "Associate"),
    ("CPN", "Vimarn Suriya Co.", 3, "Associate"),
    ("CPN", "MeSpace Self Storage", 3, "Associate"),
    ("MeSpace", "Mespace Self Storage (Ramintra)", 3, "Sub-associate"),
    ("CPN", "West Bangkok Development", 2, "Associate"),
    ("CPN", "Square Ritz Plaza", 2, "Associate"),
    ("CPN", "Synergistic Property Development", 4, "Joint Venture"),
    ("CPN", "Common Ground (Thailand)", 4, "Joint Venture"),
    ("CPN", "CE Holding Co.", 3, "Joint Venture"),
    ("CE Holding", "Central and Hongkong Land Co.", 4, "Indirect Joint Venture"),
    ("SF", "SF Development Co. (Mega Bangna)", 5, "Indirect Joint Venture"),
    ("SF", "North Bangkok Development", 3, "Indirect Joint Venture"),
    ("CPN", "Porto Worldwide", 2, "Joint Venture"),
    ("CPN", "IKEA", 4, "Strategic Tenant"),
    ("CPN", "Central Plaza Hotel PCL", 3, "Related Party"),
    ("CPN", "Central World Hotel", 3, "Related Party"),
    ("CPN", "Central Village (Mitsubishi Estate JV)", 3, "Joint Venture"),
    ("CPN", "Mitsubishi Estate (Thailand)", 3, "JV Partner"),
]

print(f"Defined {len(company_edges)} company relationship edges")

# Write updated RelatedCompany.csv
with open(os.path.join(DATA_DIR, "RelatedCompany.csv"), "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Source", "Target", "Weight", "Category"])
    for src, tgt, w, cat in company_edges:
        writer.writerow([src, tgt, w, cat])
print("Updated RelatedCompany.csv written")

# ============================================================
# STEP 3: Build bipartite graph
# ============================================================
B = nx.Graph()
B.add_nodes_from(tenants, bipartite=0)
B.add_nodes_from(malls, bipartite=1)
for tenant, mall, w in tenant_mall_edges:
    B.add_edge(tenant, mall, weight=w)

print(f"\nBipartite graph: {B.number_of_nodes()} nodes, {B.number_of_edges()} edges")

# Add company edges
for src, tgt, w, cat in company_edges:
    B.add_edge(src, tgt, weight=w, category=cat)

# ============================================================
# STEP 4: In-Degree Centrality
# ============================================================
mall_degrees = {}
tenant_degrees = {}
for tenant, mall, w in tenant_mall_edges:
    tenant_degrees[tenant] = tenant_degrees.get(tenant, 0) + 1
    mall_degrees[mall] = mall_degrees.get(mall, 0) + 1

sorted_tenants = sorted(tenant_degrees.items(), key=lambda x: -x[1])
print(f"\n=== IN-DEGREE CENTRALITY (Tenants by Mall Presence - Top 20) ===")
for t, d in sorted_tenants[:20]:
    print(f"  {t:40s} {d:4d} malls")

sorted_malls = sorted(mall_degrees.items(), key=lambda x: -x[1])
print(f"\n=== IN-DEGREE CENTRALITY (Malls by Tenant Count) ===")
for m, d in sorted_malls:
    print(f"  {m:40s} {d:5d} tenants")

# ============================================================
# STEP 5: Weighted tenant co-occurrence projection (efficient)
# ============================================================
print("\nComputing weighted tenant projection (co-occurrence)...")
# Use bipartite.weighted_projected_graph with a ratio threshold
# Only connect tenants that co-occur in at least 2 malls
G = bipartite.weighted_projected_graph(B, tenants, ratio=False)

# Filter edges with weight >= 2 (co-occur in at least 2 malls)
G2 = nx.Graph()
for u, v, d in G.edges(data=True):
    w = d["weight"]
    if w >= 2:
        G2.add_edge(u, v, weight=w)

print(f"Tenant co-occurrence graph (>=2 co-malls): {G2.number_of_nodes()} nodes, {G2.number_of_edges()} edges")

# ============================================================
# STEP 6: Betweenness Centrality (on co-occurrence graph)
# ============================================================
print("Computing betweenness centrality (this may take a moment)...")
# Use a sample if too large - but with our filtered graph it should be ok
betweenness = nx.betweenness_centrality(G2, weight="weight", normalized=True, k=min(500, G2.number_of_nodes()))
sorted_bet = sorted(betweenness.items(), key=lambda x: -x[1])

print(f"\n=== BETWEENNESS CENTRALITY (Top 20) ===")
for t, b in sorted_bet[:20]:
    print(f"  {t:40s} {b:12.6f}")

# ============================================================
# STEP 7: Bridge detection
# ============================================================
print("Detecting bridges...")
try:
    bridges = list(nx.bridges(G2))
    bridge_info = []
    for u, v in bridges:
        w = G2[u][v]["weight"]
        bridge_info.append((w, u, v))
    bridge_info.sort(key=lambda x: -x[0])
    print(f"Found {len(bridges)} bridges")
    print(f"\n=== BRIDGES (Top 20) ===")
    for w, u, v in bridge_info[:20]:
        print(f"  {u:30s} - {v:30s}  (co-malls: {w})")
except Exception as e:
    print(f"Bridge detection skipped: {e}")
    bridge_info = []

# ============================================================
# STEP 8: Community Detection (Louvain)
# ============================================================
print("Detecting communities (Louvain)...")
partition = community_louvain.best_partition(G2, weight="weight")

communities = defaultdict(list)
for node, com_id in partition.items():
    communities[com_id].append(node)

sorted_coms = sorted(communities.items(), key=lambda x: -len(x[1]))
print(f"Found {len(sorted_coms)} communities")
for com_id, members in sorted_coms[:8]:
    print(f"\nCommunity {com_id} ({len(members)} members):")
    for m in members[:12]:
        print(f"  - {m}")
    if len(members) > 12:
        print(f"  ... and {len(members)-12} more")

# ============================================================
# STEP 9: Company relationship graph analysis
# ============================================================
C = nx.Graph()
for src, tgt, w, cat in company_edges:
    C.add_edge(src, tgt, weight=w, category=cat)

print(f"\n=== COMPANY RELATIONSHIP GRAPH ===")
print(f"Nodes: {C.number_of_nodes()}, Edges: {C.number_of_edges()}")

c_bet = nx.betweenness_centrality(C, weight="weight", normalized=True)
sorted_c_bet = sorted(c_bet.items(), key=lambda x: -x[1])
print(f"\nCompany Betweenness Centrality (Top 15):")
for n, b in sorted_c_bet[:15]:
    print(f"  {n:45s} {b:12.6f}")

c_partition = community_louvain.best_partition(C, weight="weight")
c_communities = defaultdict(list)
for node, com_id in c_partition.items():
    c_communities[com_id].append(node)
print(f"\nCompany Graph Communities:")
for com_id, members in sorted(c_communities.items(), key=lambda x: -len(x[1])):
    print(f"  Community {com_id}: {', '.join(members)}")

# ============================================================
# STEP 10: Save all outputs
# ============================================================
pd.DataFrame(sorted_tenants, columns=["Tenant", "MallCount"]).to_csv(
    os.path.join(OUT_DIR, "in_degree_centrality.csv"), index=False)
pd.DataFrame(sorted_malls, columns=["Mall", "TenantCount"]).to_csv(
    os.path.join(OUT_DIR, "mall_tenant_counts.csv"), index=False)
pd.DataFrame(sorted_bet, columns=["Tenant", "Betweenness"]).to_csv(
    os.path.join(OUT_DIR, "betweenness_centrality.csv"), index=False)
if bridge_info:
    pd.DataFrame(bridge_info, columns=["Weight", "Tenant1", "Tenant2"]).to_csv(
        os.path.join(OUT_DIR, "bridges.csv"), index=False)

rows = []
for com_id, members in sorted(communities.items(), key=lambda x: -len(x[1])):
    for m in members:
        rows.append({"Community": com_id, "Tenant": m})
pd.DataFrame(rows).to_csv(os.path.join(OUT_DIR, "tenant_communities.csv"), index=False)

# Combined graph statistics
stats = {
    "Total unique tenants": len(tenants),
    "Total unique malls": len(malls),
    "Total tenant-mall edges": len(tenant_mall_edges),
    "Co-occurrence graph nodes": G2.number_of_nodes(),
    "Co-occurrence graph edges": G2.number_of_edges(),
    "Number of communities": len(sorted_coms),
    "Company relationship nodes": C.number_of_nodes(),
    "Company relationship edges": C.number_of_edges(),
}
with open(os.path.join(OUT_DIR, "graph_stats.txt"), "w", encoding="utf-8") as f:
    for k, v in stats.items():
        f.write(f"{k}: {v}\n")

print(f"\n{'='*60}")
print(f"All outputs saved to {OUT_DIR}")
for f in sorted(os.listdir(OUT_DIR)):
    size = os.path.getsize(os.path.join(OUT_DIR, f))
    print(f"  {f:40s} {size:>8,} bytes")
print(f"{'='*60}")
