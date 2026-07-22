import sys
import csv
import os
import glob
import pandas as pd
import networkx as nx
import community as community_louvain
from collections import defaultdict, Counter
import time

# Set stdout to utf-8 to avoid UnicodeEncodeError
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r"C:\DADS7201\PJ_MIDTERM\Data"
OUT_DIR = r"C:\DADS7201\PJ_MIDTERM\Output"
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# STEP 1: Load all tenant-mall edges from central_*_stores.csv files
# ============================================================

CATEGORY_MAP = {
    "Fashion & Accessories": "Fashion & Apparel",
    "Health & Beauty": "Beauty & Wellness",
    "Technology": "Technology & Electronics",
    "Home & Decor": "Lifestyle & Specialty",
    "Home & D\u00e9cor": "Lifestyle & Specialty",
    "Book & Stationeries": "Lifestyle & Specialty",
    "Super Market": "Supermarket",
    "General Service": "Services & Education",
    "Others": "Other",
    "Bank & ATM": "Bank & Financial Services",
    "Edutainment": "Entertainment",
    "Lifestyle": "Lifestyle & Specialty",
    "Government Services Point": "Services & Education",
    "Pet Service": "Lifestyle & Specialty",
    "Attraction": "Entertainment",
    "Food & Beverage": "Food & Beverage",
}

# Load mall_code -> mall_name mapping
mall_map = {}
mall_csv = os.path.join(DATA_DIR, "cpn_all_malls_summary.csv")
if os.path.exists(mall_csv):
    with open(mall_csv, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            mall_map[row["mall_code"].strip().lower()] = row["mall_name"].strip()

import glob
store_files = sorted(glob.glob(os.path.join(DATA_DIR, "*_stores.csv")))
tenant_mall_edges = []
cat_map_raw = {}
for fpath in store_files:
    fname = os.path.basename(fpath)
    # Extract mall code from filename: central_{code}_stores.csv
    code = fname.replace("central_", "").replace("_stores.csv", "").replace("_", "")
    mall_name = mall_map.get(code, fname)
    with open(fpath, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            tenant = row["name"].strip()
            if not tenant:
                continue
            cat = row.get("categories", "").strip()
            mapped_cat = CATEGORY_MAP.get(cat, cat)
            tenant_mall_edges.append((tenant, mall_name, 1))
            if tenant not in cat_map_raw:
                cat_map_raw[tenant] = mapped_cat

# Strip sub-brand suffix → brand, AND add department store node in same mall
DEPT_STORE_SUFFIX = {
    " | CENTRAL DEPARTMENT STORE": "Central Department Store",
    " | ROBINSON DEPARTMENT STORE": "Robinson Department Store",
}
new_edges = []
for t, m, w in tenant_mall_edges:
    upper = t.upper()
    matched = None
    for suffix, dept_name in DEPT_STORE_SUFFIX.items():
        if suffix in upper:
            brand = t.rsplit(" | ", 1)[0].strip()
            new_edges.append((brand, m, w))
            matched = dept_name
            break
    if matched:
        new_edges.append((matched, m, w))
    else:
        new_edges.append((t, m, w))
tenant_mall_edges = new_edges

# Normalize case variants so "CENTRAL DEPARTMENT STORE" and "Central Department Store" are the same
CASE_NORMALIZE = {
    "CENTRAL DEPARTMENT STORE": "Central Department Store",
    "ROBINSON DEPARTMENT STORE": "Robinson Department Store",
}
tenant_mall_edges = [
    (CASE_NORMALIZE.get(t.upper().strip(), t), m, w) for t, m, w in tenant_mall_edges
]

# Update cat_map: strip suffix key → brand + department store
new_cat_map = {}
for old_name, cat in cat_map_raw.items():
    upper = old_name.upper()
    matched_dept = None
    for suffix, dept_name in DEPT_STORE_SUFFIX.items():
        if suffix in upper:
            brand = old_name.rsplit(" | ", 1)[0].strip()
            matched_dept = dept_name
            break
    if matched_dept:
        new_cat_map.setdefault(brand, cat)
        new_cat_map.setdefault(matched_dept, cat)
    else:
        new_cat_map.setdefault(old_name, cat)
cat_map_raw = new_cat_map

# Normalize cat_map keys for case variants
for old_name in list(cat_map_raw.keys()):
    normalized = CASE_NORMALIZE.get(old_name.upper().strip(), old_name)
    if normalized != old_name:
        cat_map_raw.setdefault(normalized, cat_map_raw[old_name])
        del cat_map_raw[old_name]

# Deduplicate (tenant, mall) pairs
seen = set()
deduped = []
for t, m, w in tenant_mall_edges:
    key = (t, m)
    if key not in seen:
        seen.add(key)
        deduped.append((t, m, w))
tenant_mall_edges = deduped

print(f"Loaded {len(tenant_mall_edges)} tenant-mall edges from {len(store_files)} files")
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
try:
    with open(os.path.join(DATA_DIR, "RelatedCompany.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Source", "Target", "Weight", "Category"])
        for src, tgt, w, cat in company_edges:
            writer.writerow([src, tgt, w, cat])
    print("Updated RelatedCompany.csv written")
except PermissionError:
    print("Skipped RelatedCompany.csv (file locked)")

# ============================================================
# STEP 3-5: Co-occurrence graph (manual projection, threshold >= 3)
# ============================================================
from collections import Counter

print("\nBuilding tenant co-occurrence graph (manual projection)...")
t1 = time.time()

# Group tenants by mall
mall_tenants = defaultdict(list)
for t, m, _ in tenant_mall_edges:
    mall_tenants[m].append(t)

# Count co-occurring pairs
pair_counts = Counter()
for mall, tenants_list in mall_tenants.items():
    n = len(tenants_list)
    if n < 2:
        continue
    tenants_list.sort()
    for i in range(n):
        t1_name = tenants_list[i]
        for j in range(i+1, n):
            t2_name = tenants_list[j]
            key = (t1_name, t2_name) if t1_name < t2_name else (t2_name, t1_name)
            pair_counts[key] += 1

t2 = time.time()
print(f"  Pair counting: {t2-t1:.1f}s  |  Total pairs: {len(pair_counts)}")

# Degree (mall presence count)
uniq_pairs = set((t, m) for t, m, _ in tenant_mall_edges)
tenant_degrees = defaultdict(int)
mall_degrees_dict = defaultdict(int)
for t, m in uniq_pairs:
    tenant_degrees[t] += 1
    mall_degrees_dict[m] += 1

# Build filtered graph (weight >= 3)
COOC_THRESHOLD = 3
G2 = nx.Graph()
for (u, v), w in pair_counts.items():
    if w >= COOC_THRESHOLD:
        G2.add_edge(u, v, weight=w)

t3 = time.time()
print(f"  Filter (weight>={COOC_THRESHOLD}): {t3-t2:.1f}s")
print(f"Tenant co-occurrence graph: {G2.number_of_nodes()} nodes, {G2.number_of_edges()} edges")
del pair_counts  # free memory

# In-Degree Centrality (from tenant_mall_edges)

sorted_tenants = sorted(tenant_degrees.items(), key=lambda x: -x[1])
print(f"\n=== DEGREE CENTRALITY (Tenants by Mall Presence - Top 20) ===")
for t, d in sorted_tenants[:20]:
    print(f"  {t:40s} {d:4d} malls")

sorted_malls = sorted(mall_degrees_dict.items(), key=lambda x: -x[1])
print(f"\n=== MALLS BY TENANT COUNT ===")
for m, d in sorted_malls:
    print(f"  {m:40s} {d:5d} tenants")

# ============================================================
# STEP 5-6: Betweenness Centrality (on co-occurrence graph)
# ============================================================
import time
print("Computing betweenness centrality (this may take a moment)...")
t_bet = time.time()
BET_K = min(100, G2.number_of_nodes())
betweenness = nx.betweenness_centrality(G2, weight="weight", normalized=True, k=BET_K, seed=42)
sorted_bet = sorted(betweenness.items(), key=lambda x: -x[1])
print(f"  Betweenness done ({time.time()-t_bet:.1f}s, k={BET_K})")

print(f"\n=== BETWEENNESS CENTRALITY (Top 20) ===")
for t, b in sorted_bet[:20]:
    print(f"  {t:40s} {b:12.6f}")

# Eigenvector Centrality
print("\nComputing eigenvector centrality...")
t_eig = time.time()
eigenvector = nx.eigenvector_centrality_numpy(G2, weight="weight")
sorted_eig = sorted(eigenvector.items(), key=lambda x: -x[1])
print(f"  Eigenvector done ({time.time()-t_eig:.1f}s)")
print(f"\n=== EIGENVECTOR CENTRALITY (Top 20) ===")
for t, e in sorted_eig[:20]:
    print(f"  {t:40s} {e:12.6f}")

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
t_comm = time.time()
partition = community_louvain.best_partition(G2, weight="weight")
print(f"  Communities done ({time.time()-t_comm:.1f}s)")

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
# STEP 9b: Load corporate brand relationships
# ============================================================
# STEP 9b: Load corporate brand relationships from cpn_brand_analysis.csv (CRC/CRG groups)
# ============================================================
corp_brands = defaultdict(set)
brand_corp = {}
corp_path = os.path.join(DATA_DIR, "cpn_brand_analysis.csv")
if os.path.exists(corp_path):
    with open(corp_path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            grp = row["group"].strip().upper()
            if grp in ("CRC", "CRG"):
                brand = row["store_name"].strip().upper()
                if brand not in brand_corp:
                    brand_corp[brand] = grp
                    corp_brands[grp].add(brand)
    print(f"\nLoaded {len(brand_corp)} corporate brand mappings from {len(corp_brands)} groups")
else:
    print("\nNo cpn_brand_analysis.csv found — skipping CRC/CRG brand mapping")

# ============================================================
# STEP 10: Save all outputs
# ============================================================
pd.DataFrame(sorted_tenants, columns=["Tenant", "Degree"]).to_csv(
    os.path.join(OUT_DIR, "in_degree_centrality.csv"), index=False)
pd.DataFrame(sorted_malls, columns=["Mall", "TenantCount"]).to_csv(
    os.path.join(OUT_DIR, "mall_tenant_counts.csv"), index=False)
pd.DataFrame(sorted_bet, columns=["Tenant", "Betweenness"]).to_csv(
    os.path.join(OUT_DIR, "betweenness_centrality.csv"), index=False)
pd.DataFrame(sorted_eig, columns=["Tenant", "Eigenvector"]).to_csv(
    os.path.join(OUT_DIR, "eigenvector_centrality.csv"), index=False)
if bridge_info:
    pd.DataFrame(bridge_info, columns=["Weight", "Tenant1", "Tenant2"]).to_csv(
        os.path.join(OUT_DIR, "bridges.csv"), index=False)

rows = []
for com_id, members in sorted(communities.items(), key=lambda x: -len(x[1])):
    for m in members:
        rows.append({"Tenant": m, "Community": com_id,
                     "Corporate": brand_corp.get(m, ""),
                     "Degree": tenant_degrees.get(m, 0)})
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

# Save co-occurrence edges (for app.py Tab 4 graph)
pd.DataFrame(
    [(u, v, d['weight']) for u, v, d in G2.edges(data=True)],
    columns=["Tenant1", "Tenant2", "Weight"]
).to_csv(os.path.join(OUT_DIR, "cooccurrence_edges.csv"), index=False)
print(f"  cooccurrence_edges.csv written with {G2.number_of_edges()} edges")

# Brand node CSV: full tenant reference
bn_rows = []
for t in sorted(tenants):
    malls_list = sorted(set(m for tt, m, _ in tenant_mall_edges if tt == t))
    cats = [cat_map_raw.get(t, "")]
    bn_rows.append({"Tenant": t, "Degree": tenant_degrees.get(t, 0),
                    "Malls": "; ".join(malls_list),
                    "Categories": "; ".join(c for c in cats if c),
                    "Community": partition.get(t, ""),
                    "Corporate": brand_corp.get(t, ""),
                    "Betweenness": round(betweenness.get(t, 0), 6),
                    "Eigenvector": round(eigenvector.get(t, 0), 6)})
pd.DataFrame(bn_rows).to_csv(os.path.join(OUT_DIR, "brandnode.csv"), index=False)
print(f"  brandnode.csv written with {len(bn_rows)} tenants")

# Adjacency list (tenant→CPN with weight = degree/mall count)
adj_rows = sorted([(t, c) for t, c in sorted_tenants], key=lambda x: -x[1])
pd.DataFrame(adj_rows, columns=["Source", "Weight"]).to_csv(
    os.path.join(OUT_DIR, "adjacency_list.csv"), index=False)
print(f"  adjacency_list.csv written with {len(adj_rows)} tenants")

print(f"\n{'='*60}")
print(f"All outputs saved to {OUT_DIR}")
for f in sorted(os.listdir(OUT_DIR)):
    size = os.path.getsize(os.path.join(OUT_DIR, f))
    print(f"  {f:40s} {size:>8,} bytes")
print(f"{'='*60}")
