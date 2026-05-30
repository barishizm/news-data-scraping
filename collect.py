import requests
import pandas as pd
import sqlite3
import time
from datetime import datetime

DB_PATH = "hn_data.db"

# Keywords used to decide whether a story is about AI.
AI_KEYWORDS = [
    "openai", "anthropic", "google deepmind", "gpt", "claude", "gemini",
    "llm", "chatgpt", "mistral", "ai agent", "machine learning",
    "deep learning", "transformer", "diffusion model", "rag"
]

def is_ai_related(title):
    """Return True if the title mentions any AI-related keyword."""
    if not title:
        return False
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in AI_KEYWORDS)

def detect_company(title):
    """Map a title to the AI company it is most likely about."""
    if not title:
        return "other"
    t = title.lower()
    if "openai" in t or "chatgpt" in t or "gpt" in t:
        return "OpenAI"
    if "claude" in t or "anthropic" in t:
        return "Anthropic"
    if "gemini" in t or "deepmind" in t or "google ai" in t:
        return "Google"
    if "mistral" in t:
        return "Mistral"
    if "llama" in t or "meta ai" in t:
        return "Meta"
    return "other"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY,
            title TEXT,
            score INTEGER,
            by TEXT,
            created_at INTEGER,
            url TEXT,
            num_comments INTEGER,
            fetched_at TEXT,
            company TEXT DEFAULT 'other'
        )
    """)
    # Migrate older databases that predate the "company" column.
    cols = [row[1] for row in cursor.execute("PRAGMA table_info(stories)").fetchall()]
    if "company" not in cols:
        cursor.execute("ALTER TABLE stories ADD COLUMN company TEXT DEFAULT 'other'")
    conn.commit()
    conn.close()
    print("Database initialized.")

def get_top_story_ids():
    url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    response = requests.get(url)
    return response.json()[:200]

def get_story_detail(story_id):
    url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
    response = requests.get(url)
    return response.json()

def save_stories(stories):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0

    for story in stories:
        cursor.execute("""
            INSERT OR IGNORE INTO stories
            (id, title, score, by, created_at, url, num_comments, fetched_at, company)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            story["id"],
            story["title"],
            story["score"],
            story["by"],
            story["created_at"],
            story["url"],
            story["num_comments"],
            story["fetched_at"],
            story["company"]
        ))
        if cursor.rowcount > 0:
            new_count += 1

    conn.commit()
    conn.close()
    return new_count

def fetch_and_store():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Fetching top stories...")
    story_ids = get_top_story_ids()
    stories = []

    for i, story_id in enumerate(story_ids):
        story = get_story_detail(story_id)

        if story and story.get("type") == "story":
            title = story.get("title")
            # Only keep stories that are about AI.
            if is_ai_related(title):
                stories.append({
                    "id": story.get("id"),
                    "title": title,
                    "score": story.get("score"),
                    "by": story.get("by"),
                    "created_at": story.get("time"),
                    "url": story.get("url", ""),
                    "num_comments": story.get("descendants", 0),
                    "fetched_at": datetime.utcnow().isoformat(),
                    "company": detect_company(title)
                })

        if i % 20 == 0:
            print(f"  Progress: {i}/{len(story_ids)}...")

        time.sleep(0.1)

    print(f"  Found {len(stories)} AI-related stories out of {len(story_ids)} fetched.")
    new_count = save_stories(stories)
    print(f"  Done! {new_count} new stories saved to database.")

    # Quick summary
    conn = sqlite3.connect(DB_PATH)
    total = pd.read_sql("SELECT COUNT(*) as count FROM stories", conn).iloc[0]["count"]
    conn.close()
    print(f"  Total stories in database: {total}")

if __name__ == "__main__":
    init_db()
    fetch_and_store()

def init_comments_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY,
            story_id INTEGER,
            text TEXT,
            by TEXT,
            created_at INTEGER,
            fetched_at TEXT,
            FOREIGN KEY (story_id) REFERENCES stories(id)
        )
    """)
    conn.commit()
    conn.close()
    print("Comments table ready.")

def get_comments(story_id, max_comments=10):
    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
    story = requests.get(story_url).json()
    
    kids = story.get("kids", [])[:max_comments]
    comments = []

    for kid_id in kids:
        url = f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json"
        comment = requests.get(url).json()

        if comment and comment.get("type") == "comment" and comment.get("text"):
            comments.append({
                "id": comment.get("id"),
                "story_id": story_id,
                "text": comment.get("text", ""),
                "by": comment.get("by", ""),
                "created_at": comment.get("time"),
                "fetched_at": datetime.utcnow().isoformat()
            })
        time.sleep(0.05)

    return comments

def save_comments(comments):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0

    for c in comments:
        cursor.execute("""
            INSERT OR IGNORE INTO comments
            (id, story_id, text, by, created_at, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (c["id"], c["story_id"], c["text"], c["by"], c["created_at"], c["fetched_at"]))
        if cursor.rowcount > 0:
            new_count += 1

    conn.commit()
    conn.close()
    return new_count

def fetch_comments_for_top_stories(top_n=20):
    """Fetch comments for the top N stories by score."""
    conn = sqlite3.connect(DB_PATH)
    top_stories = pd.read_sql(
        f"SELECT id, title FROM stories ORDER BY score DESC LIMIT {top_n}", conn
    )
    conn.close()

    print(f"\nFetching comments for top {top_n} stories...")
    total_new = 0

    for i, row in top_stories.iterrows():
        print(f"  [{i+1}/{top_n}] {row['title'][:60]}...")
        comments = get_comments(row["id"], max_comments=10)
        new = save_comments(comments)
        total_new += new

    print(f"\nDone! {total_new} new comments saved.")

if __name__ == "__main__":
    init_db()
    init_comments_table()
    fetch_and_store()
    fetch_comments_for_top_stories(top_n=20)