import json
import logging
import yfinance as yf
from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-yfinance-server")

# Initialize FastMCP server
mcp = FastMCP("Advanced-Finance-Server")

@mcp.tool()
def get_advanced_stock_metrics(tickers: str) -> str:
    """
    Fetch comprehensive stock data and key metrics for one or more ticker symbols.
    
    This tool retrieves basic info, growth potential, valuation, profitability,
    and financial health metrics from Yahoo Finance to help evaluate the stock's future potential.
    
    Args:
        tickers: A comma-separated list of stock ticker symbols (e.g., 'AAPL' or 'AAPL, MSFT, TSLA').
        
    Returns:
        A JSON string mapping each ticker symbol to its retrieved metrics or error message.
    """
    logger.info(f"Fetching advanced metrics for tickers: {tickers}")
    try:
        # Split by comma and clean up whitespace
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        
        if not ticker_list:
            return json.dumps({"error": "Ticker list cannot be empty. Please provide at least one valid ticker symbol."}, indent=2)
            
        results = {}
        
        for ticker in ticker_list:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # yfinance returns info dict, but if ticker is invalid or has no data, info might be empty or missing key fields like symbol
                if not info or not isinstance(info, dict) or not info.get("symbol"):
                    results[ticker] = {"error": f"No data found for ticker '{ticker}'. Please verify the symbol is correct."}
                    continue
                    
                # Extract the requested metrics safely using .get()
                results[ticker] = {
                    "basic_info": {
                        "symbol": info.get("symbol"),
                        "longName": info.get("longName"),
                        "currentPrice": info.get("currentPrice"),
                        "marketCap": info.get("marketCap"),
                        "sector": info.get("sector"),
                        "industry": info.get("industry"),
                    },
                    "growth_potential": {
                        "pegRatio": info.get("pegRatio"),
                        "earningsGrowth": info.get("earningsGrowth"),
                        "revenueGrowth": info.get("revenueGrowth"),
                    },
                    "valuation_profitability": {
                        "forwardPE": info.get("forwardPE"),
                        "trailingPE": info.get("trailingPE"),
                        "priceToBook": info.get("priceToBook"),
                        "returnOnEquity": info.get("returnOnEquity"),
                        "operatingMargins": info.get("operatingMargins"),
                    },
                    "financial_health_cash": {
                        "totalDebt": info.get("totalDebt"),
                        "freeCashflow": info.get("freeCashflow"),
                        "debtToEquity": info.get("debtToEquity"),
                    }
                }
            except Exception as e:
                logger.error(f"Error fetching data for ticker {ticker}: {str(e)}")
                results[ticker] = {"error": f"An error occurred while fetching metrics: {str(e)}"}
                
        return json.dumps(results, indent=2)
        
    except Exception as e:
        logger.error(f"Error processing tickers string '{tickers}': {str(e)}")
        return json.dumps({"error": f"An error occurred while processing tickers: {str(e)}"}, indent=2)

if __name__ == "__main__":
    mcp.run()
