import os, sys, warnings, json, time
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv

DIR = r"C:\DADS7201\PJ_MIDTERM"
OUT = os.path.join(DIR, "Output")
DEVICE = torch.device("cpu")
torch.manual_seed(42)
np.random.seed(42)
t0 = time.time()

# ── 1. Load edges (vectorized) ──
edges = pd.read_csv(os.path.join(OUT, "cooccurrence_edges.csv"))
tenants = sorted(set(edges["Tenant1"].unique()) | set(edges["Tenant2"].unique()))
n_nodes = len(tenants)
tenant2idx = {t: i for i, t in enumerate(tenants)}
print(f"Nodes: {n_nodes}, Edges: {len(edges)}")

max_w = float(edges["Weight"].max())
t1 = edges["Tenant1"].map(tenant2idx).values.astype(np.int64)
t2 = edges["Tenant2"].map(tenant2idx).values.astype(np.int64)
w = (edges["Weight"].values / max_w).astype(np.float32)

edge_index = torch.from_numpy(np.stack([np.concatenate([t1, t2]), np.concatenate([t2, t1])]))
edge_attr = torch.from_numpy(np.concatenate([w, w]).reshape(-1, 1))
print(f"Edge index: {edge_index.shape} ({time.time()-t0:.1f}s)")

# ── 2. Node features (vectorized) ──
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
    # Corporate flag
    if any(k in str(r.get("Corporate", "")).upper() for k in ["CRC", "CRG"]):
        feat_mat[idx, -1] = 1.0
x = torch.tensor(feat_mat, dtype=torch.float)
print(f"Features: {x.shape} ({time.time()-t0:.1f}s)")

# ── 3. Target (vectorized) ──
def zscore(s):
    mu, sd = np.mean(s), np.std(s)
    return (s - mu) / (sd + 1e-8)

deg = np.array([brand_map.get(t, {}).get("Degree", 0) for t in tenants], dtype=float)
bet = np.array([brand_map.get(t, {}).get("Betweenness", 0) for t in tenants], dtype=float)
eig = np.array([brand_map.get(t, {}).get("Eigenvector", 0) for t in tenants], dtype=float)
corp = feat_mat[:, -1]  # reuse

target = 0.4 * zscore(deg) + 0.3 * zscore(bet) + 0.2 * zscore(eig) + 0.1 * corp
target = (target - target.min()) / (target.max() - target.min() + 1e-8)
y = torch.tensor(target, dtype=torch.float).view(-1, 1)

data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr, y=y)
print(f"Target range: [{y.min().item():.4f}, {y.max().item():.4f}] ({time.time()-t0:.1f}s)")

# ── 4. GCN model (faster than GAT for dense graphs) ──
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
optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)

# ── 5. Train ──
idx = torch.randperm(n_nodes)
n_train, n_val = int(0.8 * n_nodes), int(0.1 * n_nodes)
train_idx = idx[:n_train]
val_idx = idx[n_train:n_train+n_val]
test_idx = idx[n_train+n_val:]

for epoch in range(1, 101):
    model.train()
    optimizer.zero_grad()
    out = model(data.x, data.edge_index)
    loss = F.mse_loss(out[train_idx], data.y[train_idx])
    loss.backward()
    optimizer.step()
    if epoch % 20 == 0:
        model.eval()
        with torch.no_grad():
            vl = F.mse_loss(out[val_idx], data.y[val_idx]).item()
        print(f"  Epoch {epoch:3d}: train={loss.item():.6f} val={vl:.6f}")

model.eval()
with torch.no_grad():
    pred = model(data.x, data.edge_index)
    test_loss = F.mse_loss(pred[test_idx], data.y[test_idx]).item()
    r2 = 1 - F.mse_loss(pred, data.y).item() / data.y.var().item()
print(f"\nTest MSE: {test_loss:.6f}, R²: {r2:.4f} ({time.time()-t0:.0f}s)")

# ── 6. Save predictions ──
node_df = pd.DataFrame({"Tenant": tenants, "CompositeScore": data.y.flatten().numpy(), "GNN_Prediction": pred.flatten().numpy()})
node_df["Category"] = node_df["Tenant"].apply(lambda t: str(brand_map.get(t, {}).get("Categories", "?")).split(";")[0].strip())
node_df = node_df.sort_values("GNN_Prediction", ascending=False)
node_df.to_csv(os.path.join(OUT, "gnn_predictions.csv"), index=False, encoding="utf-8-sig")
print(f"\nTop-20 by GNN prediction:\n{node_df.head(20).to_string(index=False)}")

torch.save(model.state_dict(), os.path.join(OUT, "gnn_model.pt"))
print(f"Done ({time.time()-t0:.0f}s)")
