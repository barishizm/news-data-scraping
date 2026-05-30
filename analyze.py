import pandas as pd
from transformers import pipeline
import time

# Load data
df = pd.read_csv("hn_stories.csv")
print(f"Loaded {len(df)} stories")

# Load sentiment model
print("Loading sentiment model (first time may take a minute)...")
sentiment = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english",
    truncation=True,
    max_length=512
)

# Run sentiment analysis on titles
print("Analyzing sentiment...")
results = []

for i, row in df.iterrows():
    title = str(row["title"])
    result = sentiment(title)[0]
    results.append({
        "id": row["id"],
        "title": title,
        "score": row["score"],
        "num_comments": row["num_comments"],
        "sentiment": result["label"],
        "confidence": round(result["score"], 3)
    })
    
    if i % 20 == 0:
        print(f"Progress: {i}/{len(df)}")

# Save results
result_df = pd.DataFrame(results)
result_df.to_csv("hn_sentiment.csv", index=False)

# Quick summary
print("\n--- Summary ---")
print(result_df["sentiment"].value_counts())
print(f"\nAverage score for POSITIVE stories: {result_df[result_df['sentiment']=='POSITIVE']['score'].mean():.0f}")
print(f"Average score for NEGATIVE stories: {result_df[result_df['sentiment']=='NEGATIVE']['score'].mean():.0f}")
print("\nTop 5 most upvoted stories:")
print(result_df.nlargest(5, "score")[["title", "score", "sentiment"]].to_string())