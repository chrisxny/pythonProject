import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq

# --- 终端表格对齐设置 ---
pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('display.unicode.ambiguous_as_wide', True)

# --- 智能百分比解析器 ---
def parse_percentage(val):
    if isinstance(val, str):
        if '%' in val:
            return float(val.replace('%', '')) / 100.0
        val = float(val)
    if val > 3.0: 
        return val / 100.0
    return float(val)

# --- Black-Scholes 定价与 Delta 计算 ---
def bs_put_price(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return float(K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))

def bs_put_delta(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return float(norm.cdf(d1) - 1)

# --- 反向求解：给定目标收益率，求行权价 ---
def find_strike_for_target_return(S, iv30, T_days, target_return, r=0.03):
    T = T_days / 365
    def objective(K):
        price = bs_put_price(S, K, T, r, iv30)
        # 年化收益率公式：(Price/K) / T
        current_return = (price / K) / T
        return current_return - target_return
    try:
        # 在股价的 50% 到 100% 之间寻找行权价
        return brentq(objective, S * 0.5, S * 1.0)
    except ValueError:
        return None

# --- 基于 IVP 动态生成风控阈值 ---
def get_ivp_thresholds(ivp):
    ivp_clipped = np.clip(ivp, 0, 100)
    ivp_nodes = [0, 30, 40, 50, 60, 70, 80, 90, 100]
    delta_nodes = [-0.4, -0.35, -0.30, -0.25, -0.22, -0.20, -0.18, -0.15, -0.10] 
    return_nodes = [0.15, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.58, 0.60]
    limit_delta = np.interp(ivp_clipped, ivp_nodes, delta_nodes)
    ideal_return = np.interp(ivp_clipped, ivp_nodes, return_nodes)
    return float(limit_delta), float(ideal_return)

# --- 主测算引擎 ---
def find_optimal_strikes_with_alert(S, iv30, ivp, T_days, absolute_min_return=0.30, yield_step=0.01, r=0.03, step=0.5):
    iv30 = parse_percentage(iv30)
    
    # 1. 极低波动率熔断
    MIN_IVP_THRESHOLD = 30
    if ivp < MIN_IVP_THRESHOLD:
        return f"【系统熔断】当前 IVP 为 {ivp}，低于红线 ({MIN_IVP_THRESHOLD})。禁止交易。"

    limit_delta, ideal_return = get_ivp_thresholds(ivp)
    
    print(f"[环境评估] 当前股价: ${S} | IV30: {iv30*100:.2f}% | IVP: {ivp}th")
    print(f"[动态风控] 自动设定 Delta 底线为: {limit_delta:.4f} (需更接近0)")
    print(f"  -> 逻辑解释: 当前 IVP 为 {ivp}，限制被行权概率高于 {abs(limit_delta)*100:.2f}% 的合约。")
    print(f"[动态风控] 自动设定年化收益率底线为: {ideal_return*100:.2f}%")
    print(f"  -> 逻辑解释: 高风险需高溢价，需索要 {ideal_return*100:.2f}% 的回报。\n")

    T = T_days / 365
    max_strike = np.floor(S)
    min_strike = S * 0.5
    strikes_to_test = np.arange(max_strike, min_strike, -step)

    def scan_strikes(target_yield):
        results = []
        for K in strikes_to_test:
            price = bs_put_price(S, K, T, r, iv30)
            delta = bs_put_delta(S, K, T, r, iv30)
            ann_return = (price / K) / T
            if limit_delta <= delta <= -0.02 and ann_return >= target_yield:
                true_margin_of_safety = (S - (K - price)) / S
                results.append({"Strike": round(K, 2), "Price": round(price, 2), "Delta": round(delta, 4), "Return (%)": round(ann_return * 100, 2), "MOS (%)": round(true_margin_of_safety * 100, 2)})
        return results

    # 尝试理想收益率
    ideal_results = scan_strikes(ideal_return)
    
    # --- 准备“30%底线理论值” ---
    k_30 = find_strike_for_target_return(S, iv30, T_days, absolute_min_return, r)
    p_30 = bs_put_price(S, k_30, T, r, iv30) if k_30 else 0
    d_30 = bs_put_delta(S, k_30, T, r, iv30) if k_30 else 0
    
    bottom_line_str = f"【底线参考】满足 {absolute_min_return*100:.2f}% 收益率的理论档位: Strike {k_30:.2f} | Price {p_30:.2f} | Delta {d_30:.4f}"

    if ideal_results:
        df = pd.DataFrame(ideal_results)
        df.insert(4, 'Target (%)', round(ideal_return * 100, 2))
        print("-> 完美匹配：满足全额风险溢价。\n")
        print(df.sort_values(by="MOS (%)", ascending=False).to_markdown(index=False))
        print(f"\n{bottom_line_str}")
        return

    print(f"【红线警报】未找到符合条件的行权价（收益率需 {ideal_return*100:.2f}%）。")
    print(f"-> 启动迭代向下妥协，直至绝对底线 {absolute_min_return*100:.2f}%...\n")

    current_target = ideal_return - yield_step
    while current_target >= absolute_min_return - 1e-6:
        compromise_results = scan_strikes(current_target)
        if compromise_results:
            df = pd.DataFrame(compromise_results)
            df.insert(4, 'Target (%)', round(current_target * 100, 2))
            print(f"-> 妥协成功：在目标收益率 {current_target*100:.2f}% 下找到匹配项。\n")
            print(df.sort_values(by="MOS (%)", ascending=False).to_markdown(index=False))
            print(f"\n{bottom_line_str}")
            return
        current_target -= yield_step

    print(f"【迭代结束】妥协到底线仍无解。")
    print(f"{bottom_line_str}")

# --- 执行测算 ---
if __name__ == "__main__":
    find_optimal_strikes_with_alert(
        S=18.6,
        iv30="67%",
        ivp=49,
        T_days=17
    )