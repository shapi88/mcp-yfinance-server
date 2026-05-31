# mcp-yfinance-server

[![PyPI version](https://img.shields.io/pypi/v/mcp-yfinance-server.svg)](https://pypi.org/project/mcp-yfinance-server/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mcp-yfinance-server.svg)](https://pypi.org/project/mcp-yfinance-server/)
[![License](https://img.shields.io/pypi/l/mcp-yfinance-server.svg)](LICENSE)

A Model Context Protocol (MCP) server that provides Yahoo Finance data through yfinance.

## Features

- Get comprehensive stock metrics and key financial ratios
- Retrieve a full, normalised stock profile with every non-deprecated yfinance field
- Access 5-year historical data across price, volume, dividends, splits, and financial statements
- Identify and score the top 10 main investment drivers for any stock
- Fetch analyst recommendations and price targets

## Installation

### Option 1: Install from PyPI

```bash
pip install mcp-yfinance-server
```

### Option 2: Install from source

```bash
git clone https://github.com/shapi88/mcp-yfinance-server.git
cd mcp-yfinance-server
pip install -e .
```

## Usage

### Running the server

```bash
python server.py
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `get_advanced_stock_metrics` | Key metrics snapshot for one or more tickers |
| `get_enhanced_stock_details` | Full normalised profile for a single ticker |
| `get_stock_5y_history` | 5-year historical data across all dimensions |
| `get_top_stock_drivers` | Top 10 scored investment drivers |

### Claude Desktop Configuration

Add this to your Claude Desktop config file:

```json
{
  "mcpServers": {
    "yfinance": {
      "command": "python",
      "args": ["/path/to/mcp-yfinance-server/server.py"]
    }
  }
}
```

---

## Tool Reference

### `get_advanced_stock_metrics`

Returns basic info, growth potential, valuation/profitability, and financial health
for one or more comma-separated tickers.

**Input:**
```json
{"tickers": "AAPL, MSFT, TSLA"}
```

**Output (truncated):**
```json
{
  "AAPL": {
    "basic_info": { "symbol": "AAPL", "currentPrice": 190.0, ... },
    "growth_potential": { "pegRatio": 2.1, "earningsGrowth": 0.12, ... },
    "valuation_profitability": { "forwardPE": 25.0, "returnOnEquity": 1.5, ... },
    "financial_health_cash": { "freeCashflow": 100000000000, ... }
  }
}
```

---

### `get_enhanced_stock_details`

Returns a comprehensive, normalised stock profile for a **single** ticker,
aggregating all non-deprecated yfinance data sources.

**Categories returned:**

| Category | Contents |
|----------|----------|
| `identity` | Company name, exchange, sector, industry, description |
| `price_market` | Current price, 52-week range, moving averages, volume, market cap |
| `valuation` | PE, forward PE, P/B, EV/EBITDA, PEG |
| `dividends` | Yield, payout ratio, ex-dividend date, 5-year avg yield |
| `financials` | Revenue/earnings growth, margins, ROE/ROA, debt, free cash flow |
| `shares_ownership` | Shares outstanding, float, short interest, insider/institutional % |
| `analyst_targets` | Recommendation mean/key, target prices, analyst count |
| `governance_risk` | Audit, board, compensation, shareholder rights, overall risk scores |
| `earnings_dates` | Most recent quarter, fiscal year ends, earnings timestamps |
| `annual_income_statement` | Last 4 annual income statements |
| `annual_balance_sheet` | Last 4 annual balance sheets |
| `annual_cash_flow` | Last 4 annual cash-flow statements |
| `quarterly_*` | Same as annual variants but quarterly |
| `analyst_price_targets` | Structured price target data |
| `earnings_calendar` | Upcoming earnings calendar |

**Input:**
```json
{"symbol": "AAPL"}
```

**Output (truncated):**
```json
{
  "AAPL": {
    "identity": { "symbol": "AAPL", "longName": "Apple Inc.", "sector": "Technology", ... },
    "valuation": { "trailingPE": 28.0, "forwardPE": 25.0, "pegRatio": 2.1, ... },
    "annual_income_statement": [
      { "date": "2023-09-30", "Total Revenue": 400000000000, ... }
    ],
    ...
  }
}
```

---

### `get_stock_5y_history`

Returns 5-year historical data for a **single** ticker across all available dimensions.
Each dimension degrades gracefully — if unavailable for the symbol, it returns an empty list.

**Dimensions returned:**

| Key | Contents |
|-----|----------|
| `price_history_weekly` | Weekly OHLCV + dividends + splits for 5 years |
| `dividends` | Full dividend payment history |
| `stock_splits` | Full stock split history |
| `annual_income_statement` | Annual income statement time series |
| `annual_balance_sheet` | Annual balance sheet time series |
| `annual_cash_flow` | Annual cash-flow time series |
| `quarterly_income_statement` | Quarterly income statement time series |
| `quarterly_balance_sheet` | Quarterly balance sheet time series |
| `quarterly_cash_flow` | Quarterly cash-flow time series |

**Input:**
```json
{"symbol": "AAPL"}
```

**Output (truncated):**
```json
{
  "symbol": "AAPL",
  "price_history_weekly": [
    { "date": "2019-06-03", "open": 175.0, "high": 180.0, "low": 173.0,
      "close": 179.5, "volume": 120000000, "dividends": 0.0, "stock_splits": 0.0 },
    ...
  ],
  "dividends": [
    { "date": "2024-02-09", "value": 0.24 }, ...
  ],
  "annual_income_statement": [
    { "date": "2023-09-30", "Total Revenue": 400000000000, ... }, ...
  ],
  ...
}
```

---

### `get_top_stock_drivers`

Identifies and scores the **top 10 main investment drivers** for a single stock.
Each driver is scored 0–4 (weakest to strongest) using industry-standard thresholds,
then weighted to produce an overall score and signal.

**The 10 drivers:**

| # | Driver | Key Metrics | Weight |
|---|--------|-------------|--------|
| 1 | Valuation | Forward PE, P/B, EV/EBITDA | 14% |
| 2 | Growth | Revenue growth, earnings growth, PEG | 14% |
| 3 | Profitability | Operating margins, net margins, ROE | 12% |
| 4 | Financial Health | Debt/equity, current ratio, FCF yield | 12% |
| 5 | Price Momentum | 52-week position, vs 50/200-day MA | 10% |
| 6 | Analyst Sentiment | Recommendation mean, target upside | 12% |
| 7 | Dividend Quality | Dividend yield, payout ratio | 8% |
| 8 | Earnings Quality | EPS trend, quarterly earnings growth | 8% |
| 9 | Short Interest | Short % of float | 5% |
| 10 | Institutional Support | % held by institutions & insiders | 5% |

**Signals:** `Strong Buy` (≥3.2) · `Buy` (≥2.4) · `Hold` (≥1.6) · `Sell` (≥0.8) · `Strong Sell` (<0.8)

**Input:**
```json
{"symbol": "AAPL"}
```

**Output (truncated):**
```json
{
  "symbol": "AAPL",
  "overall_score": 2.85,
  "signal": "Buy",
  "score_scale": "0 (weakest) to 4 (strongest)",
  "drivers": [
    {
      "rank": 6,
      "driver": "Analyst Sentiment",
      "score": 4,
      "weight": 0.12,
      "weighted_score": 0.48,
      "metrics": {
        "recommendationMean": 1.8,
        "recommendationKey": "buy",
        "numberOfAnalystOpinions": 40,
        "targetMeanPrice": 210.0,
        "targetUpsidePct": 0.105
      },
      "explanation": "Aggregates professional analyst ratings and price targets..."
    },
    ...
  ]
}
```

---

## Development

### Requirements

- Python 3.8+
- `mcp[cli]>=0.1.0`
- `yfinance>=0.2.0`
- `pandas>=1.5.0`

### Running tests

```bash
pip install pytest
pytest tests/ -v
```

## License

MIT License