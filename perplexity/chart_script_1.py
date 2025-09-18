import plotly.graph_objects as go
import pandas as pd

# Data from the provided JSON
data = {
    "solutions": [
        {"method": "File Locking (fcntl)", "complexity": "Medium", "effectiveness": "High", "use_case": "Production environments, preventing multiple instances"},
        {"method": "Process Detection & Kill (psutil)", "complexity": "Medium", "effectiveness": "High", "use_case": "Cleanup existing processes, development"},
        {"method": "Signal Handling (SIGINT/SIGTERM)", "complexity": "Simple", "effectiveness": "High", "use_case": "Graceful shutdown, process management"},
        {"method": "Application.stop_running()", "complexity": "Simple", "effectiveness": "High", "use_case": "Programmatic bot shutdown"},
        {"method": "PID Files", "complexity": "Simple", "effectiveness": "Medium", "use_case": "Simple single-instance check"},
        {"method": "Context Manager Pattern", "complexity": "Simple", "effectiveness": "High", "use_case": "Modern python-telegram-bot v21+"},
        {"method": "Polling Configuration", "complexity": "Simple", "effectiveness": "Medium", "use_case": "Drop pending updates, timeout handling"}
    ]
}

# Create DataFrame
df = pd.DataFrame(data["solutions"])

# Map categorical values to numbers for visualization
complexity_map = {"Simple": 1, "Medium": 2, "Advanced": 3}
effectiveness_map = {"Low": 1, "Medium": 2, "High": 3}

df["complexity_num"] = df["complexity"].map(complexity_map)
df["effectiveness_num"] = df["effectiveness"].map(effectiveness_map)

# Abbreviate method names to fit 15-char limit
method_abbrev = {
    "File Locking (fcntl)": "File Lock",
    "Process Detection & Kill (psutil)": "Proc Kill", 
    "Signal Handling (SIGINT/SIGTERM)": "Signal Hand",
    "Application.stop_running()": "App.stop()",
    "PID Files": "PID Files",
    "Context Manager Pattern": "CtxMgr",
    "Polling Configuration": "Poll Config"
}
df["method_short"] = df["method"].map(method_abbrev)

# Abbreviate use_case to fit 15-char limit
use_case_map = {
    "Production environments, preventing multiple instances": "Prod multi-prev",
    "Cleanup existing processes, development": "Dev cleanup",
    "Graceful shutdown, process management": "Grace shutdown",
    "Programmatic bot shutdown": "Bot shutdown",
    "Simple single-instance check": "Single check",
    "Modern python-telegram-bot v21+": "Modern py-v21+",
    "Drop pending updates, timeout handling": "Drop updates"
}
df["use_case_short"] = df["use_case"].map(use_case_map)

# Use colors specified in instructions
bar_colors = ["#1FB8CD", "#DB4545"]

fig = go.Figure()

# Complexity bar
fig.add_trace(go.Bar(
    name="Complexity",
    x=df["method_short"],
    y=df["complexity_num"],
    marker_color=bar_colors[0],
    text=df["complexity"],
    textposition="auto",
    hovertemplate=(
        '<b>%{x}</b><br>' +
        'Complexity: %{text}<br>' +
        'Use Case: %{customdata}<extra></extra>'
    ),
    customdata=df["use_case_short"]
))

# Effectiveness bar
fig.add_trace(go.Bar(
    name="Effectiveness",
    x=df["method_short"],
    y=df["effectiveness_num"],
    marker_color=bar_colors[1],
    text=df["effectiveness"],
    textposition="auto",
    hovertemplate=(
        '<b>%{x}</b><br>' +
        'Effectiveness: %{text}<br>' +
        'Use Case: %{customdata}<extra></extra>'
    ),
    customdata=df["use_case_short"]
))

fig.update_layout(
    title="Bot Error Solution Comparison",
    xaxis_title="Method",
    yaxis_title="Lvl: 1=Low, 2=M, 3=Hi",
    barmode='group',
    legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5)
)

fig.update_yaxes(
    tickvals=[1, 2, 3],
    ticktext=["Low/Smp", "Med", "Hi/Adv"]
)

fig.update_traces(cliponaxis=False)

fig.write_image("chart.png")
fig.write_image("chart.svg", format="svg")

fig.show()