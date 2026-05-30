## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the data collector once
python collect.py

# Start the scheduler (runs every 6 hours)
python scheduler.py

# Launch the dashboard
streamlit run dashboard.py
```

## Key findings

- ~73% of HN top story titles are classified as **negative** sentiment
- This reflects HN's tendency toward critical, problem-focused titles
- Positive stories (launches, achievements) score higher on average
- Top story: "Claude Opus 4.8" — 1,737 upvotes, POSITIVE (0.992 confidence)

## Limitations

- Sentiment model (DistilBERT SST-2) was trained on movie reviews,
  not tech news — some technical titles are misclassified
- Comment text includes HTML entities that are cleaned before analysis
- Data is limited to current top 100 stories per fetch cycle