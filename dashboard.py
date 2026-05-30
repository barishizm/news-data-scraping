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
        model="ProsusAI/finbert",
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
page = st.sidebar.radio("View", ["Overview", "Stories", "Comments", "Trends"])

# --- Overview ---
if page == "Overview":
    st.title("📡 Hacker News Sentiment Dashboard")

    stories = load_stories()
    stories = run_sentiment(stories, "title")

    pos = stories[stories["sentiment"] == "positive"]
    neg = stories[stories["sentiment"] == "negative"]

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
            color_discrete_map={"positive": "#1D9E75", "negative": "#D85A30"}
        )
        fig.update_layout(showlegend=True, height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Avg score by sentiment")
        avg = stories.groupby("sentiment")["score"].mean().reset_index()
        fig2 = px.bar(
            avg, x="sentiment", y="score",
            color="sentiment",
            color_discrete_map={"positive": "#1D9E75", "negative": "#D85A30"}
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

    sentiment_filter = st.selectbox("Filter by sentiment", ["All", "positive", "negative"])
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
        pos_pct = round(len(comments[comments["sentiment"]=="positive"]) / len(comments) * 100)
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
    
elif page == "Trends":
    st.title("📈 Trends")

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT
            date(datetime(created_at, 'unixepoch')) as date,
            COUNT(*) as story_count,
            AVG(score) as avg_score,
            AVG(num_comments) as avg_comments
        FROM stories
        GROUP BY date
        ORDER BY date
    """, conn)
    conn.close()

    if len(df) < 2:
        st.info("Not enough data yet for trend analysis. The scheduler will collect more data every 6 hours.")
        st.metric("Days of data collected", len(df))
        st.metric("Total stories", df["story_count"].sum() if len(df) > 0 else 0)
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Stories per day")
            fig = px.bar(df, x="date", y="story_count", color_discrete_sequence=["#1D9E75"])
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Avg score per day")
            fig2 = px.line(df, x="date", y="avg_score", color_discrete_sequence=["#D85A30"], markers=True)
            fig2.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Avg comments per day")
        fig3 = px.line(df, x="date", y="avg_comments", color_discrete_sequence=["#378ADD"], markers=True)
        fig3.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    # Top keywords
    st.subheader("Top keywords in titles")
    conn = sqlite3.connect(DB_PATH)
    titles = pd.read_sql("SELECT title FROM stories", conn)["title"].tolist()
    conn.close()

    stopwords = {"the","a","an","of","in","to","and","for","is","are","that",
                 "it","with","on","at","by","from","as","how","my","i","we",
                 "its","this","your","our","their","was","be","or","not","can",
                 "but","so","about","has","have","what","why","–","-"}

    words = []
    for title in titles:
        for word in title.lower().split():
            word = word.strip(".,!?:;\"'()")
            if word and word not in stopwords and len(word) > 2:
                words.append(word)

    word_freq = pd.Series(words).value_counts().head(20).reset_index()
    word_freq.columns = ["word", "count"]

    fig4 = px.bar(
        word_freq, x="count", y="word",
        orientation="h",
        color="count",
        color_continuous_scale=["#9FE1CB", "#0F6E56"],
        height=500
    )
    fig4.update_layout(showlegend=False, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig4, use_container_width=True)