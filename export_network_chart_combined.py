import sys, csv, os
import networkx as nx
import plotly.graph_objects as go
from plotly.subplots import make_subplots
sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = r"C:\DADS7201\PJ_MIDTERM\Output"
DATA_DIR = r"C:\DADS7201\PJ_MIDTERM\Data"

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
    "Central Department Store": "#607d8b",
    "Robinson Department Store": "#607d8b",
    "Other": "#9e9e9e",
}

ALLIANCE_COLORS = {"CPN": "#e74c3c", "CRC": "#2980b9", "CRG": "#27ae60"}
CATEGORY_ORDER = [
    "Food & Beverage", "Fashion & Apparel", "Beauty & Wellness",
    "Lifestyle & Specialty", "Technology & Electronics",
    "Entertainment", "Services & Education",
    "Bank & Financial Services", "Supermarket", "Other",
]

cat_map = {}
with open(os.path.join(OUT_DIR, "brandnode.csv"), "r", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        t = row["Tenant"].strip()
        cats = row.get("Categories", "").strip()
        if cats:
            cat_map[t] = cats.split(";")[0].strip()

def get_color(t):
    if t in ALLIANCE_COLORS:
        return ALLIANCE_COLORS[t]
    return CATEGORY_COLORS.get(cat_map.get(t, "Other"), "#9e9e9e")

brand_corp = {}
brand_csv = os.path.join(DATA_DIR, "cpn_brand_analysis.csv")
if os.path.exists(brand_csv):
    with open(brand_csv, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            brand = row["store_name"].strip().upper()
            grp = row["group"].strip().upper()
            if grp in ("CRC", "CRG") and brand not in brand_corp:
                brand_corp[brand] = grp

adj_weights = {}
with open(os.path.join(OUT_DIR, "adjacency_list.csv"), "r", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        adj_weights[row["Source"].strip()] = int(row["Weight"])

def build_graph(top_tenants):
    G = nx.Graph()
    for t in top_tenants:
        G.add_node(t)
    for n in ["CPN", "CRC", "CRG"]:
        G.add_node(n)
    for t in top_tenants:
        G.add_edge("CPN", t, weight=adj_weights.get(t, 1), etype="affiliation")
    G.add_edge("CPN", "CRC", weight=1, etype="alliance")
    G.add_edge("CPN", "CRG", weight=1, etype="alliance")
    for t in top_tenants:
        corp = brand_corp.get(t.upper())
        if corp in ("CRC", "CRG"):
            G.add_edge(corp, t, weight=1, etype="ownership")
    return G

def layout_zigzag(top_tenants):
    n = len(top_tenants)
    pos = {}
    label_pos = {}
    pos["CPN"] = (0, 2.5)
    pos["CRC"] = (-2.0, 1.0)
    pos["CRG"] = (2.0, 1.0)
    spread = min(5.0, max(3.0, n * 0.5))
    for i, t in enumerate(top_tenants):
        x = -spread + (2 * spread * i / max(n - 1, 1))
        if i % 2 == 0:
            pos[t] = (x, -1.8)
            label_pos[t] = "top center"
        else:
            pos[t] = (x, -2.9)
            label_pos[t] = "bottom center"
    return pos, spread, label_pos

def load_top10(csv_file):
    result = []
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i >= 10:
                break
            result.append(row["Tenant"].strip())
    return result

EDGE_STYLES = [
    ("CPN\u2192Tenant", "rgba(180,180,180,0.5)", 1.5, None),
    ("Alliance", "rgba(231,76,60,0.85)", 3.5, None),
    ("Ownership", "rgba(52,152,219,0.7)", 2, "dash"),
]

def add_edges(fig, G, pos, **grid_kw):
    for name, color, width, dash in EDGE_STYLES:
        x, y = [], []
        for u, v in G.edges():
            e = G[u][v].get("etype", "")
            cond = (name == "CPN\u2192Tenant" and e == "affiliation") or \
                   (name == "Alliance" and e == "alliance") or \
                   (name == "Ownership" and e == "ownership")
            if cond:
                x.extend([pos[u][0], pos[v][0], None])
                y.extend([pos[u][1], pos[v][1], None])
        if x:
            line = dict(color=color, width=width)
            if dash:
                line["dash"] = dash
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines",
                line=line, hoverinfo="none", showlegend=False), **grid_kw)

def add_nodes(fig, G, pos, label_pos, **grid_kw):
    all_nodes = list(G.nodes())
    colors = [get_color(n) for n in all_nodes]
    sizes = [38 if n in ALLIANCE_COLORS else 24 for n in all_nodes]
    symbols = ["diamond" if n in ALLIANCE_COLORS else "circle" for n in all_nodes]
    textpos = ["top center" if n in ALLIANCE_COLORS else label_pos.get(n, "top center") for n in all_nodes]
    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in all_nodes],
        y=[pos[n][1] for n in all_nodes],
        mode="markers+text",
        marker=dict(color=colors, size=sizes, symbol=symbols, line=dict(width=2, color="#333")),
        text=all_nodes, textposition=textpos, textfont=dict(size=10, color="#111"),
        hoverinfo="text", showlegend=False,
    ), **grid_kw)

def build_bar_trace(values, labels, colors, value_col):
    traces = []
    for t, v, c in zip(labels, values, colors):
        fmt = "%{x}" if value_col == "Degree" else "%{x:.6f}"
        traces.append(go.Bar(
            x=[v], y=[t], orientation="h",
            marker=dict(color=c, line=dict(width=1, color="#333")),
            texttemplate=fmt, textposition="outside",
            hoverinfo="y+x", showlegend=False, width=0.7,
        ))
    return traces

def export_combined(metric_name, value_col, csv_file, fname):
    top_list = load_top10(csv_file)
    data = []
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i >= 10:
                break
            data.append((row["Tenant"].strip(), float(row[value_col])))

    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    colors = [get_color(t) for t in labels]
    max_val = max(values) if values else 1

    G = build_graph(top_list)
    pos, spread, label_pos = layout_zigzag(top_list)
    ax = spread + 1.8

    fig = make_subplots(rows=1, cols=2,
        subplot_titles=[f"Network: {metric_name}", f"Bar Chart: {metric_name}"],
        column_widths=[0.6, 0.4], horizontal_spacing=0.05)

    add_edges(fig, G, pos, row=1, col=1)
    add_nodes(fig, G, pos, label_pos, row=1, col=1)

    bar_traces = build_bar_trace(values, labels, colors, value_col)
    for tr in bar_traces:
        fig.add_trace(tr, row=1, col=2)

    # Category legend (dummy traces on col 1)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
        marker=dict(color="#e74c3c", size=14, symbol="diamond", line=dict(width=1, color="#333")),
        name="Alliance Entity", showlegend=True), row=1, col=1)
    for cat in CATEGORY_ORDER:
        c = CATEGORY_COLORS.get(cat, "#9e9e9e")
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
            marker=dict(color=c, size=10, symbol="circle", line=dict(width=1, color="#333")),
            name=cat, showlegend=True), row=1, col=1)

    fig.update_xaxes(range=[-ax, ax], showgrid=False, zeroline=False, visible=False, row=1, col=1)
    fig.update_yaxes(range=[-3.6, 3.5], showgrid=False, zeroline=False, visible=False, row=1, col=1)
    fig.update_xaxes(title=value_col, showgrid=True, gridcolor="#eee", range=[0, max_val * 1.2], row=1, col=2)
    fig.update_yaxes(autorange="reversed", showgrid=False, row=1, col=2)

    fig.update_layout(
        title=dict(text=metric_name, font=dict(size=16)),
        height=700, width=1400,
        margin=dict(l=10, r=30, t=60, b=30),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="white",
        font=dict(size=11),
        legend=dict(x=0.01, y=0.99, xanchor="left", yanchor="top",
                    bgcolor="rgba(255,255,255,0.85)", bordercolor="#ccc", borderwidth=1, font=dict(size=9)),
        hovermode="closest",
    )

    fig.write_image(os.path.join(OUT_DIR, f"{fname}.svg"))
    fig.write_image(os.path.join(OUT_DIR, f"{fname}.png"), scale=2)
    print(f"Saved: {fname}.svg / .png")

# ── Export all 3 ──
export_combined("Top 10 by Degree Centrality", "Degree",
    os.path.join(OUT_DIR, "in_degree_centrality.csv"), "combined_degree")

export_combined("Top 10 by Betweenness Centrality", "Betweenness",
    os.path.join(OUT_DIR, "betweenness_centrality.csv"), "combined_betweenness")

export_combined("Top 10 by Eigenvector Centrality", "Eigenvector",
    os.path.join(OUT_DIR, "eigenvector_centrality.csv"), "combined_eigenvector")
