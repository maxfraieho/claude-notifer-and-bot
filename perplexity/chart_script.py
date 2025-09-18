import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# Define flowchart nodes with better spacing and positioning
nodes = [
    {"name": "Bot Start", "type": "start", "x": 2, "y": 11},
    {"name": "Lock Create", "type": "process", "x": 2, "y": 10},
    {"name": "Lock Avail?", "type": "decision", "x": 2, "y": 9},
    {"name": "Error Exit", "type": "end", "x": 4, "y": 9},
    {"name": "Signal Setup", "type": "process", "x": 2, "y": 8},
    {"name": "Start Poll", "type": "process", "x": 2, "y": 7},
    {"name": "Proc Update", "type": "process", "x": 2, "y": 6},
    {"name": "Shutdown?", "type": "decision", "x": 2, "y": 5},
    {"name": "Grace Stop", "type": "process", "x": 2, "y": 4},
    {"name": "Lock Clean", "type": "process", "x": 2, "y": 3},
    {"name": "Exit", "type": "end", "x": 2, "y": 2},
]

df = pd.DataFrame(nodes)

# Color mapping using provided palette
color_map = {
    "start": "#1FB8CD",     # Strong cyan
    "process": "#DB4545",   # Bright red  
    "decision": "#2E8B57",  # Sea green
    "end": "#5D878F"        # Cyan
}

# Symbol mapping for flowchart shapes
symbol_map = {
    "start": "circle",
    "process": "square",
    "decision": "diamond",
    "end": "circle"
}

fig = go.Figure()

# Add nodes for each type with larger markers and fonts
for node_type in ["start", "process", "decision", "end"]:
    subset = df[df["type"] == node_type]
    if not subset.empty:
        fig.add_trace(go.Scatter(
            x=subset["x"],
            y=subset["y"],
            mode="markers+text",
            marker=dict(
                symbol=symbol_map[node_type],
                size=50,  # Increased from 30
                color=color_map[node_type],
                line=dict(width=3, color="white")
            ),
            text=subset["name"],
            textposition="middle center",
            textfont=dict(size=12, color="white", family="Arial Black"),  # Increased font size
            name=node_type.capitalize(),
            hovertemplate="%{text}<extra></extra>"
        ))

# Add arrows to show flow with better positioning
arrows = [
    (2, 10.7, 2, 10.3),   # Start to Lock create
    (2, 9.7, 2, 9.3),     # Lock create to Lock avail?
    (2.3, 9, 3.7, 9),     # Lock avail? to Error exit (No)
    (2, 8.7, 2, 8.3),     # Lock avail? to Signal setup (Yes)
    (2, 7.7, 2, 7.3),     # Signal setup to Start poll
    (2, 6.7, 2, 6.3),     # Start poll to Proc update
    (2, 5.7, 2, 5.3),     # Proc update to Shutdown?
    (1.6, 5, 1.6, 6.4),   # Shutdown? back to Proc update (No)
    (2, 4.7, 2, 4.3),     # Shutdown? to Grace stop (Yes)
    (2, 3.7, 2, 3.3),     # Grace stop to Lock clean
    (2, 2.7, 2, 2.3),     # Lock clean to Exit
]

for x1, y1, x2, y2 in arrows:
    fig.add_annotation(
        x=x2, y=y2,
        ax=x1, ay=y1,
        xref="x", yref="y",
        axref="x", ayref="y",
        arrowhead=3,
        arrowsize=1.5,
        arrowwidth=3,
        arrowcolor="#333333",
        showarrow=True
    )

# Add flow labels with better positioning and larger text
fig.add_annotation(x=3, y=9.2, text="No", showarrow=False, font=dict(size=12, color="#333333"))
fig.add_annotation(x=1.6, y=8.5, text="Yes", showarrow=False, font=dict(size=12, color="#333333"))
fig.add_annotation(x=1.2, y=5.7, text="No", showarrow=False, font=dict(size=12, color="#333333"))
fig.add_annotation(x=1.6, y=4.5, text="Yes", showarrow=False, font=dict(size=12, color="#333333"))

fig.update_layout(
    title="Telegram Bot Process Lifecycle",
    showlegend=True,
    legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5),
    xaxis=dict(
        showgrid=False, 
        zeroline=False, 
        showticklabels=False,
        range=[0.5, 4.5]
    ),
    yaxis=dict(
        showgrid=False, 
        zeroline=False, 
        showticklabels=False,
        range=[1.5, 11.5]
    )
)

fig.update_traces(cliponaxis=False)

# Save outputs
fig.write_image("chart.png")
fig.write_image("chart.svg", format="svg")