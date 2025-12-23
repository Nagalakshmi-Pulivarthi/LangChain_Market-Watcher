# Market Watcher Agent 🚀

A sophisticated LangChain & LangGraph-powered terminal agent for professional stock market analysis.

## Key Features
- **Transparent Reasoning**: The agent displays its internal `[AGENT THOUGHTS]` before taking any action, explaining its logic.
- **Human-in-the-Loop (HITL)**: Uses LangGraph interrupts to ask for user approval before executing any data tools, putting you in the supervisor's seat.
- **Strict No-Advice Policy**: Built-in safety logic that refuses to give subjective "Buy/Sell" advice, focusing instead on objective risk data.
- **Intent Discovery**: Proactively asks for clarification and presents analysis options when vague ticker-only queries are provided.
- **Structured Analysis**: Delivers professional Markdown reports directly in your terminal with tables and bulleted catalysts.

## Specialized Tools
1. **News & Catalysts (`why_stock_moved`)**: Explains the "Why" behind price moves using Yahoo Finance & DuckDuckGo.
2. **Technical Levels (`get_market_alerts_and_levels`)**: Identifies 6-month support/resistance floors and price ceilings.
3. **Sentiment Correlation (`analyze_price_trend_news_correlation`)**: Analyzes how news sentiment is driving technical trends (SMA20/50).
4. **Historical Comparison (`what_changed_recently`)**: Compares current performance against 7-day and 30-day benchmarks (Price, Volume, Volatility).

## Setup
1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Set up environment**:
   Create a `.env` file and add your Google API key:
   ```bash
   GOOGLE_API_KEY=your_api_key_here
   ```
3. **Run the agent**:
   ```bash
   python agent.py
   ```

## Usage
Ask the agent complex, multi-part questions to see its reasoning in action:
- *"Why is NVDA dropping today and where is the next floor?"*
- *"Is the current move in TSLA backed by news or just technical?"*
- *"I'm worried about AAPL. Give me a 30-day comparison and the nearest floor."*

You can also simply type a ticker like `MSFT` to trigger the **Discovery Menu**.
