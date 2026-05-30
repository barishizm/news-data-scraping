# AI Company Sentiment Tracker

Tracks how Hacker News talks about the major AI companies. The collector pulls the
HN front page, keeps only AI-related stories, tags each one with the company it's
about (OpenAI, Anthropic, Google, Mistral, Meta, or other), and a Streamlit
dashboard runs sentiment analysis and breaks the results down per company.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the data collector once (fetches top 200, keeps AI stories only)
python collect.py

# Start the scheduler (runs every 6 hours)
python scheduler.py

# Launch the dashboard
streamlit run dashboard.py
```

## How it works

- **collect.py** fetches the top 200 HN stories and keeps only those whose titles
  match an AI keyword (`openai`, `anthropic`, `claude`, `gpt`, `gemini`, `llm`,
  `mistral`, `ai agent`, `machine learning`, etc.). Each kept story is tagged with a
  `company` based on its title.
- **dashboard.py** classifies story titles with a sentiment model and serves several
  views, including an **AI Companies** page with:
  - story count per company
  - average score per company
  - sentiment breakdown (positive / neutral / negative) per company
  - the top 5 stories for each company

## Company detection

| Company   | Title keywords                |
|-----------|-------------------------------|
| OpenAI    | openai, chatgpt, gpt          |
| Anthropic | claude, anthropic             |
| Google    | gemini, deepmind, google ai   |
| Mistral   | mistral                       |
| Meta      | llama, meta ai                |
| other     | everything else AI-related    |

## Limitations

- Classification is keyword-based on titles only, so a story mentioning multiple
  companies is assigned to the first match in precedence order (OpenAI → Anthropic →
  Google → Mistral → Meta).
- Sentiment runs on titles, which are short and sometimes neutral/ambiguous.
- Data is limited to AI stories found in the current top 200 per fetch cycle.
