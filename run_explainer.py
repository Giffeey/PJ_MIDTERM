import os, sys, warnings, json, time
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
from torch_geometric.explain import Explainer, GNNExplainer

DIR = r"C:\DADS7201\PJ_MIDTERM"
OUT = os.path.join(DIR, "Output")
DEVICE = torch.device("cpu")
t0 = time.time()

# ── Rebuild graph (same as training) ──
edges = pd.read_csv(os.path.join(OUT, "cooccurrence_edges.csv"))
tenants = sorted(set(edges["Tenant1"].unique()) | set(edges["Tenant2"].unique()))
n_nodes = len(tenants)
tenant2idx = {t: i for i, t in enumerate(tenants)}

max_w = float(edges["Weight"].max())
t1 = edges["Tenant1"].map(tenant2idx).values.astype(np.int64)
t2 = edges["Tenant2"].map(tenant2idx).values.astype(np.int64)
w = (edges["Weight"].values / max_w).astype(np.float32)

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

# Target
deg = np.array([brand_map.get(t, {}).get("Degree", 0) for t in tenants], dtype=float)
bet = np.array([brand_map.get(t, {}).get("Betweenness", 0) for t in tenants], dtype=float)
eig = np.array([brand_map.get(t, {}).get("Eigenvector", 0) for t in tenants], dtype=float)
def zscore(s):
    mu, sd = np.mean(s), np.std(s)
    return (s - mu) / (sd + 1e-8)
target = 0.4 * zscore(deg) + 0.3 * zscore(bet) + 0.2 * zscore(eig) + 0.1 * feat_mat[:, -1]
target = (target - target.min()) / (target.max() - target.min() + 1e-8)
y = torch.tensor(target, dtype=torch.float).view(-1, 1)

# ── Load model ──
class GCNRegressor(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = GCNConv(10, 128)
        self.conv2 = GCNConv(128, 64)
        self.lin = torch.nn.Linear(64, 1)
    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = F.dropout(x, p=0.3, training=self.training)
        x = self.conv2(x, edge_index).relu()
        return self.lin(x)

model = GCNRegressor()
model.load_state_dict(torch.load(os.path.join(OUT, "gnn_model.pt"), weights_only=True))
model.eval()
print(f"Model loaded ({time.time()-t0:.1f}s)")

# ── GNNExplainer on top-3 categories, 15 epochs ──
print("Running GNNExplainer (fast mode)...")
explainer = Explainer(
    model=model,
    algorithm=GNNExplainer(epochs=15),
    explanation_type="model",
    node_mask_type="attributes",
    edge_mask_type="object",
    model_config=dict(mode="regression", task_level="node", return_type="raw"),
)

category_groups = {c: [] for c in CATEGORIES}
for t, i in tenant2idx.items():
    b = brand_map.get(t, {})
    prim = str(b.get("Categories", "")).split(";")[0].strip() if str(b.get("Categories", "")).strip() else "Other"
    if prim in category_groups:
        category_groups[prim].append(i)

results = []
sorted_cats = sorted(category_groups.items(), key=lambda kv: len(kv[1]), reverse=True)
for cat, nodes_in_cat in sorted_cats:
    if not nodes_in_cat:
        continue
    top_node = max(nodes_in_cat, key=lambda n: y[n].item())
    top_score = y[top_node].item()
    print(f"  {cat:30s}: {len(nodes_in_cat):4d} nodes, top={tenants[top_node]:30s} score={top_score:.4f}", end=" ", flush=True)

    explanation = explainer(x, edge_index, index=top_node)

    # Feature importance
    nm = explanation.node_mask.detach().cpu().numpy().flatten()
    feat_names = CATEGORIES + ["OtherCat", "IsInternal"]
    feat_imp = {feat_names[i]: float(nm[i]) for i in range(len(feat_names))}

    # Edge importance (neighbors)
    top_neighbors = []
    em = explanation.edge_mask
    if em is not None:
        em_np = em.detach().cpu().numpy().flatten()
        is_top = (edge_index[0] == top_node) | (edge_index[1] == top_node)
        top_edge_idx = is_top.nonzero().flatten()
        sorted_ei = top_edge_idx[em_np[top_edge_idx].argsort()[::-1].copy()[:5]]
        for ei in sorted_ei:
            other = edge_index[1, ei].item() if edge_index[0, ei].item() == top_node else edge_index[0, ei].item()
            tname = tenants[other]
            tcat = str(brand_map.get(tname, {}).get("Categories", "?")).split(";")[0].strip()
            top_neighbors.append({"tenant": tname, "category": tcat, "importance": float(em_np[ei])})

    results.append({
        "category": cat,
        "count": len(nodes_in_cat),
        "top_tenant": tenants[top_node],
        "top_score": top_score,
        "feature_importance": feat_imp,
        "top_neighbors": top_neighbors,
    })
    print(f"(feat={list(feat_imp.keys())[np.argmax(list(feat_imp.values()))]}:{max(feat_imp.values()):.3f}) ({time.time()-t0:.0f}s)")

out_path = os.path.join(OUT, "gnn_analysis.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "model": {"type": "GCNRegressor", "nodes": n_nodes, "edges": len(edges)},
        "categories": results,
    }, f, ensure_ascii=False, indent=2)
print(f"\nSaved: {out_path} ({time.time()-t0:.0f}s)")
