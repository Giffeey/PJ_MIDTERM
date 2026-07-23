import csv, os, sys
import plotly.graph_objects as go
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
}

# Build category map
cat_map = {}
with open(os.path.join(OUT_DIR, 'brandnode.csv'), 'r', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        t = row['Tenant'].strip()
        cats = row.get('Categories', '').strip()
        if cats:
            cat_map[t] = cats.split(';')[0].strip()

def get_color(tenant):
    return CATEGORY_COLORS.get(cat_map.get(tenant, "Other"), "#9e9e9e")

def export_chart(csv_file, value_col, title, prefix):
    data = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i >= 10: break
            data.append((row['Tenant'].strip(), float(row[value_col])))

    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    colors = [get_color(t) for t in labels]
    max_val = max(values) if values else 1

    # ── Bar chart ──
    fig = go.Figure()
    for t, v, c in zip(labels, values, colors):
        fmt = '%{x}' if value_col == 'Degree' else '%{x:.6f}'
        fig.add_trace(go.Bar(
            x=[v], y=[t], orientation='h',
            marker=dict(color=c, line=dict(width=1, color='#333')),
            texttemplate=fmt, textposition='outside',
            hoverinfo='y+x', showlegend=False,
            width=0.7,
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis=dict(title=value_col, showgrid=True, gridcolor='#eee',
                   range=[0, max_val * 1.2]),
        yaxis=dict(autorange='reversed', showgrid=False),
        height=400, width=700,
        margin=dict(l=10, r=30, t=50, b=30),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='white',
        font=dict(size=12),
    )

    # Category color legend
    cats_used = set()
    for t in labels:
        c = cat_map.get(t, "Other")
        if c in CATEGORY_COLORS:
            cats_used.add(c)
    items = [f'<span style="color:{CATEGORY_COLORS[c]}">&#9632;</span> {c}' for c in sorted(cats_used)]
    if items:
        fig.add_annotation(x=0.5, y=-0.18, xref='paper', yref='paper',
            text='&nbsp;&nbsp;&nbsp;'.join(items),
            showarrow=False, font=dict(size=9, color='#444'),
            xanchor='center', yanchor='top')

    fig.write_image(os.path.join(OUT_DIR, f'{prefix}.svg'))
    fig.write_image(os.path.join(OUT_DIR, f'{prefix}.png'), scale=2)
    print(f'  Saved: {prefix}.svg / .png')

    # ── Table ──
    fig2 = go.Figure()
    fig2.add_trace(go.Table(
        header=dict(values=['Rank', 'Tenant', value_col],
                    fill_color='#2c3e50', font=dict(color='white', size=13), align='center'),
        cells=dict(values=[list(range(1, 11)), labels,
                           [f'{v:.6f}' if value_col != 'Degree' else str(int(v)) for v in values]],
                   fill_color=[[colors[i] if i % 2 == 0 else '#f9f9f9' for i in range(10)]],
                   font=dict(size=12), align='center', height=28),
    ))
    fig2.update_layout(
        title=dict(text=title + ' (Table)', font=dict(size=14)),
        height=450, width=600,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig2.write_image(os.path.join(OUT_DIR, f'{prefix}_table.svg'))
    print(f'  Saved: {prefix}_table.svg')

# ── Export all 3 ──
print("=== Degree (Mall Presence) ===")
export_chart(os.path.join(OUT_DIR, 'in_degree_centrality.csv'), 'Degree',
             'Top 10 by Degree Centrality', 'top10_degree')

print("\n=== Betweenness Centrality ===")
export_chart(os.path.join(OUT_DIR, 'betweenness_centrality.csv'), 'Betweenness',
             'Top 10 by Betweenness Centrality', 'top10_betweenness')

print("\n=== Eigenvector Centrality ===")
export_chart(os.path.join(OUT_DIR, 'eigenvector_centrality.csv'), 'Eigenvector',
             'Top 10 by Eigenvector Centrality', 'top10_eigenvector')
