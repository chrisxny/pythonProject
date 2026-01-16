# Copilot Instructions for Sell Put Strategy Analysis

## Project Overview
This Python project analyzes sell put options strategies using Black-Scholes pricing. It screens stocks for optimal put selling opportunities based on target delta (-0.2) and annualized returns.

## Architecture
- **Data Pipeline**: `stocks.csv` → `fmp_batch_fetch.py` → `financials.db` (financial statements)
- **Strategy Calculation**: `stocks.csv` → `sell_put_stock_screening.py` → `iv.csv` (required IV and strike prices)
- **Core Logic**: `sell_put_strategy.py` provides Black-Scholes functions and iterative IV/strike optimization

## Key Components
- `iterative_calculate_iv()`: Finds strike price and implied volatility for target delta and return
- Black-Scholes functions: `bs_put_price()`, `bs_put_delta()`, `find_strike_for_delta()`, `implied_vol_for_target_price()`
- CSV processing: Reads stock data, outputs screening results

## Developer Workflows
- **Run screening**: `python sell_put_stock_screening.py` (uses hardcoded params in script)
- **Fetch financials**: `python fmp_batch_fetch.py` (requires FMP API key)
- **Test strategy**: Modify example call in `sell_put_strategy.py` and run directly

## Conventions
- **Delta notation**: Negative values for put options (e.g., -0.2)
- **Time units**: Days for expiration, converted to years internally (T_days / 365)
- **Error handling**: Returns dict with "error" key on failure
- **CSV format**: Input `stocks.csv` with "Symbol", "Security Price" columns; output `iv.csv` with calculated fields

## Dependencies
Install from `requirement.txt`: scipy, pandas, numpy, requests, sqlite3

## Examples
```python
# Calculate for single stock
result = iterative_calculate_iv(
    S=164.28, capital=30000, target_annual_return=0.40,
    T_days=30, r=0.04, target_delta=-0.2, delta_tol=0.01
)
# Returns: {"required_iv": 76.15, "strike_price": 37.01, ...} or {"error": "..."}
```

## Integration Points
- Financial Modeling Prep API for quarterly income statements
- SQLite database for financial data storage
- CSV files for input/output data exchange