from scipy.stats import norm
from scipy.optimize import brentq
import numpy as np
import pandas as pd
from sell_put_strategy import iterative_calculate_iv

# Black-Scholes put price
def bs_put_price(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

# Put delta
def bs_put_delta(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1) - 1

# Find strike K that yields target delta for given IV guess
def find_strike_for_delta(S, T_days, r, target_delta, iv_guess):
    T = T_days / 365
    def objective(K):
        d1 = (np.log(S / K) + (r + 0.5 * iv_guess**2) * T) / (iv_guess * np.sqrt(T))
        delta = norm.cdf(d1) - 1
        return delta - target_delta
    try:
        return brentq(objective, S * 0.5, S * 1.0)
    except ValueError:
        return None

# Solve for IV given target option price
def implied_vol_for_target_price(S, K, T, r, target_price):
    try:
        return brentq(lambda sigma: bs_put_price(S, K, T, r, sigma) - target_price, 1e-6, 3.0)
    except ValueError:
        return None


def calculate_iv_from_csv(input_csv, output_csv, capital, target_annual_return, T_days, r, delta_tol, target_delta=-0.2):
    df = pd.read_csv(input_csv)
    results = []

    for idx, row in df.iterrows():
        symbol = row.get("Symbol", "")
        name = row.get("Company Name", "")
        try:
            S = float(row["Security Price"])
        except (KeyError, ValueError):
            print(f"⚠️  Skipping row {idx} - Invalid price")
            continue

        result = iterative_calculate_iv(
            S=43,
            capital=capital,
            target_annual_return=target_annual_return,
            T_days=T_days,
            r=r,  
            target_delta=target_delta,
            delta_tol=delta_tol
        )

        if "required_iv" in result:
            results.append({
                "Symbol": symbol,
                "Company Name": name,
                "Security Price": S,
                "Required IV (%)": result["required_iv"],
                "Strike Price": result["strike_price"],
                "Put Price": result["put_price"],
                "Contracts": result["contracts"],
                "Covered Amount": result["covered_amount"],
                "Monthly Income": result["monthly_income"],
                "Annualized Return (%)": result["annualized_return"],
                "Delta": result["delta"]
            })
        else:
            print(f"❌ {symbol} - Failed to calculate IV: {result.get('error')}")

    output_df = pd.DataFrame(results)
    output_df.to_csv(output_csv, index=False)
    print(f"✅ Results saved to {output_csv}")

# 输入文件路径（包含Symbol和Security Price等字段）
input_file = "stocks.csv"  # 例如包含股价信息的CSV
output_file = "iv.csv"              # 输出保存IV结果的CSV

# 调用函数计算
calculate_iv_from_csv(
    input_csv=input_file,
    output_csv=output_file,
    capital=30000,                   # 你的本金
    target_annual_return=0.40,       # 目标年化收益率
    T_days=30,                       # 期权期限（天）
    r=0.04,                          # 无风险利率
    target_delta=-0.2,               # 固定卖出 delta = -0.2 的put
    delta_tol=0.01                   # 容忍的delta误差
)