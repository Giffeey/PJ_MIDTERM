import sys, csv, os
import networkx as nx
import plotly.graph_objects as go
from plotly.subplots import make_subplots
sys.stdout.reconfigure(encoding='utf-8')

OUT_DIR = r'C:\DADS7201\PJ_MIDTERM\Output'
DATA_DIR = r'C:\DADS7201\PJ_MIDTERM\Data'

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
with open(os.path.join(OUT_DIR, 'brandnode.csv'), 'r', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        t = row['Tenant'].strip()
        cats = row.get('Categories', '').strip()
        if cats:
            cat_map[t] = cats.split(';')[0].strip()

def get_color(t):
    if t in ALLIANCE_COLORS:
        return ALLIANCE_COLORS[t]
    return CATEGORY_COLORS.get(cat_map.get(t, "Other"), "#9e9e9e")

brand_corp = {}
brand_csv = os.path.join(DATA_DIR, "cpn_brand_analysis.csv")
if os.path.exists(brand_csv):
    with open(brand_csv, 'r', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            brand = row['store_name'].strip().upper()
            grp = row['group'].strip().upper()
            if grp in ("CRC", "CRG") and brand not in brand_corp:
                brand_corp[brand] = grp

adj_weights = {}
with open(os.path.join(OUT_DIR, 'adjacency_list.csv'), 'r', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        adj_weights[row['Source'].strip()] = int(row['Weight'])

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
    """Zigzag layout: even tenants on top row, odd on bottom row to avoid label overlap."""
    n = len(top_tenants)
    pos = {}
    label_pos = {}
    pos["CPN"] = (0, 2.5)
    pos["CRC"] = (-2.0, 1.0)
    pos["CRG"] = (2.0, 1.0)
    spread = min(5.0, max(3.0, n * 0.5))
    row1_y = -1.8  # even tenants (top row)
    row2_y = -2.9  # odd tenants (bottom row)
    for i, t in enumerate(top_tenants):
        x = -spread + (2 * spread * i / max(n - 1, 1))
        if i % 2 == 0:
            pos[t] = (x, row1_y)
            label_pos[t] = 'top center'
        else:
            pos[t] = (x, row2_y)
            label_pos[t] = 'bottom center'
    return pos, spread, label_pos

def load_top10(csv_file):
    result = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i >= 10: break
            result.append(row['Tenant'].strip())
    return result

EDGE_STYLES = [
    ("CPN\u2192Tenant", "rgba(180,180,180,0.5)", 1.5, None),
    ("Alliance", "rgba(231,76,60,0.85)", 3.5, None),
    ("Ownership", "rgba(52,152,219,0.7)", 2, "dash"),
]

def add_edges(fig, G, pos, show_legend=True, **grid_kw):
    for name, color, width, dash in EDGE_STYLES:
        x, y = [], []
        for u, v in G.edges():
            e = G[u][v].get("etype", "")
            if name == "CPN\u2192Tenant" and e == "affiliation":
                x.extend([pos[u][0], pos[v][0], None])
                y.extend([pos[u][1], pos[v][1], None])
            elif name == "Alliance" and e == "alliance":
                x.extend([pos[u][0], pos[v][0], None])
                y.extend([pos[u][1], pos[v][1], None])
            elif name == "Ownership" and e == "ownership":
                x.extend([pos[u][0], pos[v][0], None])
                y.extend([pos[u][1], pos[v][1], None])
        if x:
            fig.add_trace(go.Scatter(x=x, y=y, mode='lines',
                line=dict(color=color, width=width, dash=dash) if dash else dict(color=color, width=width),
                hoverinfo='none', showlegend=show_legend, name=name), **grid_kw)

def add_nodes(fig, G, pos, label_pos, show_legend=True, **grid_kw):
    all_nodes = list(G.nodes())
    colors = [get_color(n) for n in all_nodes]
    sizes = [38 if n in ALLIANCE_COLORS else 24 for n in all_nodes]
    symbols = ["diamond" if n in ALLIANCE_COLORS else "circle" for n in all_nodes]
    text = all_nodes
    textpos = []
    for n in all_nodes:
        if n in ALLIANCE_COLORS:
            textpos.append('top center')
        else:
            textpos.append(label_pos.get(n, 'top center'))

    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in all_nodes],
        y=[pos[n][1] for n in all_nodes],
        mode='markers+text',
        marker=dict(color=colors, size=sizes, symbol=symbols, line=dict(width=2, color='#333')),
        text=text, textposition=textpos, textfont=dict(size=10, color='#111'),
        hoverinfo='text', showlegend=False,
    ), **grid_kw)

def add_category_legend(fig, **grid_kw):
    # Dummy trace for alliance entities (diamond)
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(color='#e74c3c', size=14, symbol='diamond', line=dict(width=1, color='#333')),
        name='Alliance Entity (CPN/CRC/CRG)', showlegend=True,
    ), **grid_kw)
    # Dummy trace per category (circle)
    for cat in CATEGORY_ORDER:
        color = CATEGORY_COLORS.get(cat, "#9e9e9e")
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker=dict(color=color, size=10, symbol='circle', line=dict(width=1, color='#333')),
            name=cat, showlegend=True,
        ), **grid_kw)

def export_single(title, fname, top_list):
    G = build_graph(top_list)
    pos, spread, label_pos = layout_zigzag(top_list)
    ax = spread + 1.8
    fig = go.Figure()
    add_edges(fig, G, pos, show_legend=True)
    add_nodes(fig, G, pos, label_pos)
    add_category_legend(fig)
    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(range=[-ax, ax], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-3.6, 3.5], showgrid=False, zeroline=False, visible=False),
        height=700, width=950,
        margin=dict(l=10, r=10, t=50, b=40),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='white',
        font=dict(size=11),
        legend=dict(x=0.01, y=0.99, xanchor='left', yanchor='top',
                    bgcolor='rgba(255,255,255,0.85)', bordercolor='#ccc', borderwidth=1, font=dict(size=10)),
        hovermode='closest',
    )
    fig.write_image(os.path.join(OUT_DIR, f'{fname}.svg'))
    fig.write_image(os.path.join(OUT_DIR, f'{fname}.png'), scale=2)
    print(f'Saved: {fname}.svg / .png')

def export_combined(tenants_dict, fname):
    n_plots = len(tenants_dict)
    fig = make_subplots(rows=1, cols=n_plots,
        subplot_titles=[v[0] for v in tenants_dict.values()],
        horizontal_spacing=0.02)
    max_ax = 0
    graphs_data = {}
    for key, (_, top_list) in tenants_dict.items():
        G = build_graph(top_list)
        pos, spread, label_pos = layout_zigzag(top_list)
        graphs_data[key] = (G, pos, label_pos)
        max_ax = max(max_ax, spread)
    ax = max_ax + 1.8
    for idx, key in enumerate(tenants_dict, 1):
        G, pos, label_pos = graphs_data[key]
        add_edges(fig, G, pos, show_legend=(idx==1), row=1, col=idx)
        add_nodes(fig, G, pos, label_pos, row=1, col=idx)
        add_category_legend(fig, row=1, col=idx)
        fig.update_xaxes(range=[-ax, ax], showgrid=False, zeroline=False, visible=False, row=1, col=idx)
        fig.update_yaxes(range=[-3.6, 3.5], showgrid=False, zeroline=False, visible=False, row=1, col=idx)
    fig.update_layout(
        height=650, width=400 * n_plots,
        margin=dict(l=10, r=10, t=50, b=30),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='white',
        font=dict(size=11),
        legend=dict(x=0.01, y=0.99, xanchor='left', yanchor='top',
                    bgcolor='rgba(255,255,255,0.85)', bordercolor='#ccc', borderwidth=1, font=dict(size=9)),
        hovermode='closest',
    )
    fig.write_image(os.path.join(OUT_DIR, f'{fname}.svg'))
    fig.write_image(os.path.join(OUT_DIR, f'{fname}.png'), scale=2)
    print(f'Saved: {fname}.svg / .png')

# ── Load data ──
top_deg = load_top10(os.path.join(OUT_DIR, 'in_degree_centrality.csv'))
top_bet = load_top10(os.path.join(OUT_DIR, 'betweenness_centrality.csv'))
top_eig = load_top10(os.path.join(OUT_DIR, 'eigenvector_centrality.csv'))

print("Degree:", top_deg)
print("Betweenness:", top_bet)
print("Eigenvector:", top_eig)

export_single("Top 10 by Degree Centrality", "network_top10_degree", top_deg)
export_single("Top 10 by Betweenness Centrality", "network_top10_betweenness", top_bet)
export_single("Top 10 by Eigenvector Centrality", "network_top10_eigenvector", top_eig)

export_combined({
    "deg": ("Degree", top_deg),
    "bet": ("Betweenness", top_bet),
    "eig": ("Eigenvector", top_eig),
}, "network_top10_combined")

export_combined({
    "deg": ("Degree", top_deg),
    "bet": ("Betweenness", top_bet),
}, "network_top10_deg_bet")
