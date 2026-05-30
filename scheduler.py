import schedule
import time
from collect import init_db, init_comments_table, fetch_and_store, fetch_comments_for_top_stories

def job():
    fetch_and_store()
    fetch_comments_for_top_stories(top_n=20)

# Initialize database on startup
init_db()
init_comments_table()

# Run immediately on start
print("Running initial fetch...")
job()

# Schedule every 6 hours
schedule.every(6).hours.do(job)

print("\nScheduler running. Fetching every 6 hours.")
print("Press Ctrl+C to stop.\n")

while True:
    schedule.run_pending()
    time.sleep(60)