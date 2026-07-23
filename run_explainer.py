import os, sys, warnings, json, time
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
from captum.attr import Saliency

DIR = r"C:\DADS7201\PJ_MIDTERM"
OUT = os.path.join(DIR, "Output")
DEVICE = torch.device("cpu")
t0 = time.time()

# ── Rebuild graph ──
edges = pd.read_csv(os.path.join(OUT, "cooccurrence_edges.csv"))
tenants = sorted(set(edges["Tenant1"].unique()) | set(edges["Tenant2"].unique()))
n_nodes = len(tenants)
tenant2idx = {t: i for i, t in enumerate(tenants)}

max_w = float(edges["Weight"].max())
t1 = edges["Tenant1"].map(tenant2idx).values.astype(np.int64)
t2 = edges["Tenant2"].map(tenant2idx).values.astype(np.int64)

edge_index = torch.from_numpy(np.stack([np.concatenate([t1, t2]), np.concatenate([t2, t1])]))

brands = pd.read_csv(os.path.join(OUT, "brandnode.csv"))
brands = brands[brands["Tenant"].isin(tenants)].copy()
brand_map = brands.set_index("Tenant").to_dict("index")

CATEGORIES = ["Food & Beverage", "Fashion & Apparel", "Beauty & Wellness",
    "Lifestyle & Specialty", "Technology & Electronics",
    "Bank & Financial Services", "Services & Education", "Entertainment", "Supermarket"]
cat_to_idx = {c: i for i, c in enumerate(CATEGORIES)}

feat_mat = np.zeros((n_nodes, 10), dtype=np.float32)
for _, r in brands.iterrows():
    idx = tenant2idx[r["Tenant"]]
    cats = str(r.get("Categories", "")).split(";")
    prim = cats[0].strip() if cats[0].strip() else "Other"
    if prim in cat_to_idx:
        feat_mat[idx, cat_to_idx[prim]] = 1.0
    else:
        feat_mat[idx, -2] = 1.0
    if any(k in str(r.get("Corporate", "")).upper() for k in ["CRC", "CRG"]):
        feat_mat[idx, -1] = 1.0
x = torch.tensor(feat_mat, dtype=torch.float)

def zscore(s):
    mu, sd = np.mean(s), np.std(s)
    return (s - mu) / (sd + 1e-8)

deg = np.array([brand_map.get(t, {}).get("Degree", 0) for t in tenants], dtype=float)
bet = np.array([brand_map.get(t, {}).get("Betweenness", 0) for t in tenants], dtype=float)
eig = np.array([brand_map.get(t, {}).get("Eigenvector", 0) for t in tenants], dtype=float)
corp = feat_mat[:, -1]

target = 0.4 * zscore(deg) + 0.3 * zscore(bet) + 0.2 * zscore(eig) + 0.1 * corp
target = (target - target.min()) / (target.max() - target.min() + 1e-8)
y = torch.tensor(target, dtype=torch.float)

# ── Model (same as build_gnn.py) ──
class GCNRegressor(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = GCNConv(10, 128)
        self.conv2 = GCNConv(128, 64)
        self.lin = torch.nn.Linear(64, 1)
    def forward(self, x, edge_index, edge_mask=None):
        if edge_mask is not None:
            x = self.conv1(x, edge_index, edge_weight=edge_mask).relu()
        else:
            x = self.conv1(x, edge_index).relu()
        x = F.dropout(x, p=0.3, training=self.training)
        if edge_mask is not None:
            x = self.conv2(x, edge_index, edge_weight=edge_mask).relu()
        else:
            x = self.conv2(x, edge_index).relu()
        return self.lin(x)

model = GCNRegressor()
model.load_state_dict(torch.load(os.path.join(OUT, "gnn_model.pt"), map_location="cpu", weights_only=True))
model.eval()
print(f"Model loaded ({time.time()-t0:.1f}s)")

# ── Category grouping (same top-tenant selection as before) ──
CATEGORIES_FULL = CATEGORIES + ["Other"]
category_groups = {c: [] for c in CATEGORIES_FULL}
for t, i in tenant2idx.items():
    b = brand_map.get(t, {})
    prim = str(b.get("Categories", "")).split(";")[0].strip() if str(b.get("Categories", "")).strip() else "Other"
    if prim in category_groups:
        category_groups[prim].append(i)
    else:
        category_groups["Other"].append(i)

results = []
sorted_cats = sorted(category_groups.items(), key=lambda kv: len(kv[1]), reverse=True)

# ── Captum explainer ──
print(f"Running Captum Saliency...")

for cat, nodes_in_cat in sorted_cats:
    if not nodes_in_cat or cat == "Other":
        continue

    top_node = max(nodes_in_cat, key=lambda n: y[n].item())
    top_score = y[top_node].item()
    t_start = time.time()

    # ── Feature importance via Saliency (gradient × input) ──
    def predict_node(feat):
        out = model(feat, edge_index)
        return out[top_node]

    saliency = Saliency(predict_node)
    attr = saliency.attribute(x)
    feat_imp = attr[top_node].detach().abs().numpy()

    feature_labels = CATEGORIES + ["OtherCat", "IsInternal"]
    feat_dict = {feature_labels[i]: float(feat_imp[i]) for i in range(10)}

    # ── Edge importance via gradient on edge_mask ──
    edge_mask = torch.ones(edge_index.size(1), requires_grad=True, dtype=torch.float)
    pred = model(x, edge_index, edge_mask=edge_mask)
    pred = pred[top_node, 0]
    grads = torch.autograd.grad(pred, edge_mask, retain_graph=False)[0]
    edge_imp = grads.abs().detach().numpy()

    # Aggregate to undirected importance (max of the two directed entries)
    n_undirected = len(t1)
    undirected_imp = np.maximum(edge_imp[:n_undirected], edge_imp[n_undirected:])

    # Get top-5 neighbor edges
    edge_tenant_pairs = list(zip(edges["Tenant1"], edges["Tenant2"]))
    neighbor_scores = []
    for ei, (t_a, t_b) in enumerate(edge_tenant_pairs):
        if t_a == tenants[top_node]:
            neighbor_scores.append((t_b, undirected_imp[ei]))
        elif t_b == tenants[top_node]:
            neighbor_scores.append((t_a, undirected_imp[ei]))
    neighbor_scores.sort(key=lambda x: x[1], reverse=True)
    top_nbrs = []
    for nbr_tenant, imp in neighbor_scores[:5]:
        nbr_cat = str(brand_map.get(nbr_tenant, {}).get("Categories", "Other")).split(";")[0].strip()
        if nbr_cat not in CATEGORIES:
            nbr_cat = "Other"
        top_nbrs.append({"tenant": nbr_tenant, "category": nbr_cat, "importance": round(float(imp), 4)})

    elapsed = time.time() - t_start
    print(f"  {cat:30s}: {len(nodes_in_cat):4d} nodes, top={tenants[top_node]:25s} score={top_score:.4f} ({elapsed:.0f}s)")

    results.append({
        "category": cat,
        "count": len(nodes_in_cat),
        "top_tenant": tenants[top_node],
        "top_score": round(float(top_score), 4),
        "feature_importance": feat_dict,
        "top_neighbors": top_nbrs,
    })

output = {"model": "GCNRegressor (Captum Saliency)", "categories": results}
with open(os.path.join(OUT, "gnn_analysis.json"), "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\nSaved: {os.path.join(OUT, 'gnn_analysis.json')} ({time.time()-t0:.0f}s)")
