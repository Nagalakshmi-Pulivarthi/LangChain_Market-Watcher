import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_watcher_utils")

def validate_ticker(symbol: str) -> str:
    """
    Validates and formats a stock ticker symbol.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string.")
    
    # Remove any whitespace and convert to uppercase
    clean_symbol = symbol.strip().upper()
    
    # Basic regex for ticker symbols (1-5 alphanumeric characters)
    if not re.match(r'^[A-Z0-9]{1,5}$', clean_symbol):
        logger.warning(f"Invalid ticker format detected: {clean_symbol}")
        # We still return it but log a warning, as some exotic tickers might exist
        # However, for common markets, this regex is a good filter.
    
    return clean_symbol



