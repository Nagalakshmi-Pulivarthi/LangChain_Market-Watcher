import yfinance as yf
import pandas as pd
import logging
from duckduckgo_search import DDGS
from langchain_core.tools import tool
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from utils import validate_ticker, logger

# Configure logging for tools
logger = logging.getLogger("market_watcher_tools")

@tool
def why_stock_moved(symbol: str) -> Dict[str, Any]:
    """
    Explains the 'why' behind a stock's recent price action.
    Returns structured data including price changes, news headlines, and web catalysts.
    """
    symbol = validate_ticker(symbol)
    logger.info(f"Analyzing why {symbol} moved")
    
    result = {
        "symbol": symbol,
        "price_change": {},
        "news": [],
        "web_catalysts": []
    }

    try:
        ticker = yf.Ticker(symbol)
        
        # 1. Price Change Analysis
        hist = ticker.history(period="5d")
        if not hist.empty and len(hist) >= 2:
            current_close = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2])
            change_pct = ((current_close - prev_close) / prev_close) * 100
            result["price_change"] = {
                "1d_pct": round(float(change_pct), 2),
                "current_price": round(float(current_close), 2),
                "is_up": bool(change_pct > 0)
            }

        # 2. yfinance News (Enhanced)
        raw_news = ticker.news
        if raw_news:
            for item in raw_news[:5]:
                content = item.get('content', {})
                result["news"].append({
                    "title": content.get('title', item.get('title', 'No Title')),
                    "publisher": content.get('provider', {}).get('displayName', item.get('publisher', 'Unknown')),
                    "link": content.get('canonicalUrl', {}).get('url', item.get('link', '')),
                    "published": content.get('pubDate', item.get('providerPublishTime', 'Unknown'))
                })

        # 3. Web Search Catalysts (Enhanced)
        with DDGS() as ddgs:
            search_query = f"{symbol} stock price move catalyst news"
            search_results = list(ddgs.text(search_query, max_results=5))
            for r in search_results:
                result["web_catalysts"].append({
                    "title": r['title'],
                    "snippet": r['body'],
                    "source": r.get('href', 'Unknown')
                })

        return result
    except Exception as e:
        logger.error(f"Error in why_stock_moved for {symbol}: {str(e)}")
        return {"error": str(e), "symbol": symbol}

@tool
def analyze_price_trend_news_correlation(symbol: str) -> Dict[str, Any]:
    """
    Analyzes the relationship between a stock's price trend (technical) and recent news sentiment.
    Returns technical indicators and recent sentiment-related headlines.
    """
    symbol = validate_ticker(symbol)
    logger.info(f"Analyzing trend-news correlation for {symbol}")
    
    result = {
        "symbol": symbol,
        "technicals": {},
        "sentiment_context": []
    }

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="3mo")
        if hist.empty or len(hist) < 20:
            # Try shorter period if 3mo fails or is too short
            hist = ticker.history(period="1mo")
            if hist.empty or len(hist) < 2:
                return {"error": f"Insufficient price history for {symbol}", "symbol": symbol}
            
        # Technical Analysis
        current_price = float(hist['Close'].iloc[-1])
        sma_20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
        sma_50 = float(hist['Close'].rolling(window=50).mean().iloc[-1]) if len(hist) >= 50 else None
        
        trend = "Neutral"
        if sma_20:
            trend = "Bullish" if current_price > sma_20 else "Bearish"

        result["technicals"] = {
            "current_price": round(float(current_price), 2),
            "sma_20": round(float(sma_20), 2) if sma_20 else None,
            "sma_50": round(float(sma_50), 2) if sma_50 else None,
            "trend": trend,
            "dist_from_sma20_pct": round(((current_price - sma_20) / sma_20) * 100, 2) if sma_20 else None
        }
        
        # Sentiment Context via Search
        with DDGS() as ddgs:
            search_query = f"{symbol} stock sentiment analyst rating news"
            search_results = list(ddgs.text(search_query, max_results=5))
            for r in search_results:
                result["sentiment_context"].append({
                    "title": r['title'],
                    "snippet": r['body']
                })

        return result
    except Exception as e:
        logger.error(f"Error in analyze_correlation for {symbol}: {str(e)}")
        return {"error": str(e), "symbol": symbol}

@tool
def what_changed_recently(symbol: str) -> Dict[str, Any]:
    """
    Compares the current market state of a stock to its recent history (last 7-30 days).
    Returns a structured comparison of price, volume, and volatility.
    """
    symbol = validate_ticker(symbol)
    logger.info(f"Checking what changed recently for {symbol}")
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2mo")
        if len(hist) < 2:
            return {"error": "Insufficient history", "symbol": symbol}
            
        current = hist.iloc[-1]
        week_ago = hist.iloc[-6] if len(hist) >= 6 else hist.iloc[0]
        month_ago = hist.iloc[-21] if len(hist) >= 21 else hist.iloc[0]
        
        def calc_change(curr, prev):
            return round(float(((curr - prev) / prev) * 100), 2)

        vol_avg = float(hist['Volume'].tail(30).mean())
        
        return {
            "symbol": symbol,
            "price_performance": {
                "7d_change_pct": calc_change(current['Close'], week_ago['Close']),
                "30d_change_pct": calc_change(current['Close'], month_ago['Close']),
                "current_price": round(float(current['Close']), 2)
            },
            "volume_analysis": {
                "current_volume": int(current['Volume']),
                "avg_30d_volume": int(vol_avg),
                "relative_volume": round(float(current['Volume'] / vol_avg), 2)
            },
            "volatility": {
                "daily_range_pct": calc_change(current['High'], current['Low'])
            }
        }
    except Exception as e:
        logger.error(f"Error in what_changed_recently for {symbol}: {str(e)}")
        return {"error": str(e), "symbol": symbol}

@tool
def get_market_alerts_and_levels(symbol: str) -> Dict[str, Any]:
    """
    Identifies critical price levels (support/resistance) and upcoming calendar events.
    """
    symbol = validate_ticker(symbol)
    logger.info(f"Getting alerts and levels for {symbol}")
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="6mo")
        if hist.empty:
            return {"error": "No data", "symbol": symbol}
            
        return {
            "symbol": symbol,
            "current_price": round(float(hist['Close'].iloc[-1]), 2),
            "key_levels": {
                "6m_high_resistance": round(float(hist['High'].max()), 2),
                "6m_low_support": round(float(hist['Low'].min()), 2),
                "avg_price": round(float(hist['Close'].mean()), 2)
            },
            "upcoming_events": ticker.calendar if ticker.calendar is not None else "No upcoming events found"
        }
    except Exception as e:
        logger.error(f"Error in get_market_alerts for {symbol}: {str(e)}")
        return {"error": str(e), "symbol": symbol}

# Export the list of tools
tools = [
    why_stock_moved,
    analyze_price_trend_news_correlation,
    what_changed_recently,
    get_market_alerts_and_levels
]
