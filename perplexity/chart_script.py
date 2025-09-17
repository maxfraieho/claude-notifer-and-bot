import plotly.graph_objects as go
import numpy as np

# Create flowchart using scatter plot with custom markers and shapes
fig = go.Figure()

# Define layer data with exact colors from JSON
layers = [
    {"name": "User Interface", "y": 5, "color": "#4CAF50", "components": ["/mcpadd", "/mcplist", "/mcpselect", "/mcpask", "/mcpremove", "/mcpstatus"]},
    {"name": "Handler Layer", "y": 4, "color": "#2196F3", "components": ["MCP Cmd Handlers", "Inline Keyboards", "Wizards"]},
    {"name": "Core Logic", "y": 3, "color": "#FF9800", "components": ["MCP Manager", "Context Handler", "Server Configs", "Status Monitor"]},
    {"name": "Storage", "y": 2, "color": "#9C27B0", "components": ["user_mcp_servers", "user_active_ctx", "mcp_usage_log", "mcp_srv_tmpls"]},
    {"name": "Integration", "y": 1, "color": "#F44336", "components": ["Claude CLI", "MCP Commands", "Server Proc"]}
]

# Add components as scatter points with rectangles
all_x = []
all_y = []
all_text = []
all_colors = []

for layer in layers:
    y_pos = layer["y"]
    components = layer["components"]
    layer_color = layer["color"]
    
    for i, comp in enumerate(components):
        x_pos = i * 1.8 + 1
        comp_text = comp[:15] if len(comp) > 15 else comp
        
        # Add rectangle shape for each component
        fig.add_shape(
            type="rect",
            x0=x_pos-0.7, y0=y_pos-0.25,
            x1=x_pos+0.7, y1=y_pos+0.25,
            fillcolor=layer_color,
            line=dict(color="white", width=2),
            opacity=0.9
        )
        
        all_x.append(x_pos)
        all_y.append(y_pos)
        all_text.append(comp_text)
        all_colors.append(layer_color)

# Add scatter trace for component labels
fig.add_trace(go.Scatter(
    x=all_x,
    y=all_y,
    text=all_text,
    mode='text',
    textfont=dict(size=10, color="white"),
    showlegend=False,
    hoverinfo='none'
))

# Add layer labels on the left
layer_x = []
layer_y = []
layer_text = []

for layer in layers:
    layer_x.append(0.2)
    layer_y.append(layer["y"])
    layer_text.append(layer["name"][:15])

fig.add_trace(go.Scatter(
    x=layer_x,
    y=layer_y,
    text=layer_text,
    mode='text',
    textfont=dict(size=12, color="black"),
    showlegend=False,
    hoverinfo='none'
))

# Add flow arrows between layers
arrows = [
    # User Interface to Handler Layer
    {"x0": 3.5, "y0": 4.75, "x1": 3.5, "y1": 4.25},
    # Handler Layer to Core Logic
    {"x0": 2.5, "y0": 3.75, "x1": 2.5, "y1": 3.25},
    # Core Logic to Storage
    {"x0": 2.5, "y0": 2.75, "x1": 2.5, "y1": 2.25},
    # Core Logic to Integration  
    {"x0": 4.5, "y0": 2.75, "x1": 2.5, "y1": 1.25},
    # Storage to Integration
    {"x0": 1.5, "y0": 1.75, "x1": 1.5, "y1": 1.25}
]

for arrow in arrows:
    fig.add_shape(
        type="line",
        x0=arrow["x0"], y0=arrow["y0"],
        x1=arrow["x1"], y1=arrow["y1"],
        line=dict(color="#13343B", width=3)
    )
    
    # Add arrowhead
    fig.add_shape(
        type="path",
        path=f"M {arrow['x1']},{arrow['y1']} L {arrow['x1']-0.1},{arrow['y1']+0.1} L {arrow['x1']+0.1},{arrow['y1']+0.1} Z",
        fillcolor="#13343B",
        line=dict(color="#13343B")
    )

# Configure layout
fig.update_layout(
    title="MCP Bot Architecture Flow",
    xaxis=dict(
        range=[-0.5, 12],
        showgrid=False,
        showticklabels=False,
        zeroline=False
    ),
    yaxis=dict(
        range=[0.5, 5.5],
        showgrid=False,
        showticklabels=False,
        zeroline=False
    ),
    showlegend=False,
    plot_bgcolor="white"
)

fig.update_traces(cliponaxis=False)

# Save as both PNG and SVG
fig.write_image("chart.png")
fig.write_image("chart.svg", format="svg")

fig.show()