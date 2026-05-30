import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import html
import re
from transformers import pipeline

DB_PATH = "hn_data.db"

st.set_page_config(
    page_title="HN AI Sentiment Tracker",
    page_icon="📡",
    layout="wide"
)

@st.cache_resource
def load_sentiment_model():
    return pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        truncation=True,
        max_length=512
    )

@st.cache_data(ttl=300)
def load_stories():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM stories ORDER BY score DESC", conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_comments():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT c.*, s.title as story_title
        FROM comments c
        JOIN stories s ON c.story_id = s.id
    """, conn)
    conn.close()
    return df

def clean_html(text):
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    return text.strip()

def run_sentiment(df, text_col):
    model = load_sentiment_model()
    texts = df[text_col].fillna("").apply(
        lambda x: clean_html(str(x))[:512]
    ).tolist()
    results = model(texts)
    df["sentiment"] = [r["label"] for r in results]
    df["confidence"] = [round(r["score"], 3) for r in results]
    return df

# --- Sidebar ---
st.sidebar.title("HN AI Sentiment Tracker")
st.sidebar.markdown("Hacker News top stories analyzed in real-time.")
page = st.sidebar.radio("View", ["Overview", "Stories", "Comments"])

# --- Overview ---
if page == "Overview":
    st.title("📡 Hacker News Sentiment Dashboard")

    stories = load_stories()
    stories = run_sentiment(stories, "title")

    pos = stories[stories["sentiment"] == "POSITIVE"]
    neg = stories[stories["sentiment"] == "NEGATIVE"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total stories", len(stories))
    col2.metric("Positive", len(pos))
    col3.metric("Negative", len(neg))
    col4.metric("Top score", int(stories["score"].max()))

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Sentiment distribution")
        counts = stories["sentiment"].value_counts().reset_index()
        counts.columns = ["sentiment", "count"]
        fig = px.pie(
            counts, names="sentiment", values="count",
            color="sentiment",
            color_discrete_map={"POSITIVE": "#1D9E75", "NEGATIVE": "#D85A30"}
        )
        fig.update_layout(showlegend=True, height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Avg score by sentiment")
        avg = stories.groupby("sentiment")["score"].mean().reset_index()
        fig2 = px.bar(
            avg, x="sentiment", y="score",
            color="sentiment",
            color_discrete_map={"POSITIVE": "#1D9E75", "NEGATIVE": "#D85A30"}
        )
        fig2.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Top 15 stories")
    top15 = stories.nlargest(15, "score")[["title", "score", "num_comments", "sentiment", "confidence"]]
    st.dataframe(top15, use_container_width=True, hide_index=True)

# --- Stories ---
elif page == "Stories":
    st.title("📰 Stories")

    stories = load_stories()
    stories = run_sentiment(stories, "title")

    sentiment_filter = st.selectbox("Filter by sentiment", ["All", "POSITIVE", "NEGATIVE"])
    if sentiment_filter != "All":
        stories = stories[stories["sentiment"] == sentiment_filter]

    st.dataframe(
        stories[["title", "score", "num_comments", "sentiment", "confidence", "url"]],
        use_container_width=True,
        hide_index=True
    )

# --- Comments ---
elif page == "Comments":
    st.title("💬 Comments")

    comments = load_comments()
    comments["clean_text"] = comments["text"].apply(clean_html)
    comments = comments[comments["clean_text"].str.len() > 20]
    comments = run_sentiment(comments, "clean_text")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total comments", len(comments))
    with col2:
        pos_pct = round(len(comments[comments["sentiment"]=="POSITIVE"]) / len(comments) * 100)
        st.metric("Positive comments", f"{pos_pct}%")

    st.subheader("Comment sentiment by story")
    story_sentiment = comments.groupby(["story_title", "sentiment"]).size().reset_index(name="count")
    fig = px.bar(
        story_sentiment,
        x="count", y="story_title",
        color="sentiment",
        orientation="h",
        color_discrete_map={"POSITIVE": "#1D9E75", "NEGATIVE": "#D85A30"},
        height=500
    )
    fig.update_layout(yaxis_title="", xaxis_title="Comments")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Sample comments")
    sample = comments.sample(min(10, len(comments)))[["story_title", "clean_text", "sentiment", "confidence"]]
    st.dataframe(sample, use_container_width=True, hide_index=True)