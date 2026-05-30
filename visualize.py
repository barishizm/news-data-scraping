import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

df = pd.read_csv("hn_sentiment.csv")

# --- Chart 1: Sentiment distribution ---
sentiment_counts = df["sentiment"].value_counts().reset_index()
sentiment_counts.columns = ["sentiment", "count"]

fig1 = px.pie(
    sentiment_counts,
    names="sentiment",
    values="count",
    title="Sentiment Distribution — HN Top Stories",
    color="sentiment",
    color_discrete_map={"POSITIVE": "#2ecc71", "NEGATIVE": "#e74c3c"}
)
fig1.write_html("chart_sentiment_distribution.html")
print("Saved: chart_sentiment_distribution.html")

# --- Chart 2: Score vs sentiment ---
fig2 = px.box(
    df,
    x="sentiment",
    y="score",
    color="sentiment",
    title="Upvote Score by Sentiment",
    color_discrete_map={"POSITIVE": "#2ecc71", "NEGATIVE": "#e74c3c"},
    points="all",
    hover_data=["title"]
)
fig2.write_html("chart_score_by_sentiment.html")
print("Saved: chart_score_by_sentiment.html")

# --- Chart 3: Top 15 stories bubble chart ---
top15 = df.nlargest(15, "score")

fig3 = px.scatter(
    top15,
    x="score",
    y="num_comments",
    color="sentiment",
    size="confidence",
    hover_data=["title"],
    title="Top 15 Stories: Score vs Comments",
    color_discrete_map={"POSITIVE": "#2ecc71", "NEGATIVE": "#e74c3c"},
    labels={"score": "Upvotes", "num_comments": "Comments"}
)
fig3.write_html("chart_top15_bubble.html")
print("Saved: chart_top15_bubble.html")

# --- Summary stats ---
pos = df[df["sentiment"] == "POSITIVE"]
neg = df[df["sentiment"] == "NEGATIVE"]

print(f"\n--- Summary ---")
print(f"POSITIVE: {len(pos)} stories | avg score: {pos['score'].mean():.0f}")
print(f"NEGATIVE: {len(neg)} stories | avg score: {neg['score'].mean():.0f}")
print(f"\nTop 3 POSITIVE stories:")
print(pos.nlargest(3, "score")[["title", "score"]].to_string(index=False))
print(f"\nTop 3 NEGATIVE stories:")
print(neg.nlargest(3, "score")[["title", "score"]].to_string(index=False))