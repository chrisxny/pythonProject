from scipy.stats import norm
from scipy.optimize import brentq
import numpy as np
import pandas as pd

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

# Iterative solve for IV and strike to achieve target delta and target annual return
def iterative_calculate_iv(S, capital, target_annual_return, T_days, r, target_delta, delta_tol, max_iter=20):
    iv_guess = 0.25
    target_delta = -abs(target_delta)  # Ensure negative delta for put
    
    for i in range(max_iter):
        K = find_strike_for_delta(S, T_days, r, target_delta, iv_guess)
        if K is None:
            return {"error": "Unable to find strike for target delta"}

        T = T_days / 365
        contracts = int(capital // (K * 100))
        if contracts == 0:
            return {"error": "Not enough capital to cover even one contract"}

        covered_amount = contracts * K * 100
        monthly_target_income = target_annual_return * covered_amount / 12
        required_price = monthly_target_income / (contracts * 100)

        iv_new = implied_vol_for_target_price(S, K, T, r, required_price)
        if iv_new is None:
            return {"error": "Could not find IV for given price"}

        delta_actual = bs_put_delta(S, K, T, r, iv_new)

        if abs(delta_actual - target_delta) <= delta_tol:
            # 收敛，返回结果
            actual_price = bs_put_price(S, K, T, r, iv_new)
            actual_monthly_income = actual_price * contracts * 100
            annualized_return = actual_monthly_income * 12 / covered_amount

            return {
                "required_iv": round(iv_new * 100, 2),
                "strike_price": round(K, 2),
                "put_price": round(actual_price, 2),
                "delta": round(delta_actual, 4),
                "contracts": contracts,
                "covered_amount": round(covered_amount, 2),
                "monthly_income": round(actual_monthly_income, 2),
                "annualized_return": round(annualized_return * 100, 2),
                "iterations": i + 1
            }
        else:
            # 更新IV猜测继续迭代
            iv_guess = iv_new

    return {"error": "Did not converge within max iterations"}



# 示例调用
result = iterative_calculate_iv(
    S=74,                   # 当前股价
    capital=20000,           # 本金
    target_annual_return=0.30,  # 目标年化收益30%
    T_days=51,                  # 期权到期时间30天
    r=0.03,                   # 无风险利率4%
    target_delta=-0.2,       # 固定卖出delta为-0.2的put
    delta_tol=0.01,          # delta误差容忍±0.01
    max_iter=20

)

print(result)


