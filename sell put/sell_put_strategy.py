import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq

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
        current_return = (price / K) / T
        return current_return - target_return
    try:
        return brentq(objective, S * 0.5, S * 1.0)
    except ValueError:
        return None

# --- 基于 IVP 与 HVP 复合考量生成动态风控阈值（带逻辑链追溯） ---
def get_combined_thresholds_with_trace(ivp, hvp):
    ivp_clipped = np.clip(ivp, 0, 100)
    hvp_clipped = np.clip(hvp, 0, 100)
    
    # 1. 第一决定因素：由 IVP 绝对值决定【基准风控框架】
    ivp_nodes = [30, 40, 50, 60, 70, 80, 90, 100]
    base_delta_nodes = [-0.35, -0.30, -0.25, -0.22, -0.18, -0.15, -0.12, -0.08] 
    base_return_nodes = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.58, 0.60]
    
    base_delta = float(np.interp(ivp_clipped, ivp_nodes, base_delta_nodes))
    base_return = float(np.interp(ivp_clipped, ivp_nodes, base_return_nodes))
    
    # 2. 第二决定因素：利用 HVP 绝对值作为风险调节阀
    if ivp > hvp:
        delta_multiplier = float(np.interp(hvp_clipped, [10, 30, 60], [1.3, 1.0, 0.8]))
        return_multiplier = float(np.interp(hvp_clipped, [10, 30, 60], [1.2, 1.0, 0.9]))
        env_desc = f"IVP({ivp}) > HVP({hvp}) 存在波动率溢价，依据 HVP 绝对值调节"
    else:
        delta_multiplier = 0.7
        return_multiplier = 0.8
        env_desc = f"IVP({ivp}) <= HVP({hvp}) 波动率未充分覆盖现实风险，触发防御性惩罚缩水"
        
    # 3. 计算最终联合作用阈值
    final_limit_delta = base_delta * delta_multiplier
    final_ideal_return = base_return * return_multiplier
    
    # 严格兜底
    final_limit_delta = float(np.clip(final_limit_delta, -0.42, -0.05))
    
    # 构建逻辑链说明文本
    trace_msg = (
        f"[风控推导] ① 基准定位(由IVP决定) -> 基准 Delta: {base_delta:.4f} | 基准收益率: {base_return*100:.2f}%\n"
        f"[风控推导] ② 联合调整(由HVP决定) -> 环境判断: {env_desc}\n"
        f"[风控推导]    调整系数 -> Delta 乘数: {delta_multiplier:.2f} | 收益率乘数: {return_multiplier:.2f}\n"
        f"[风控推导] ③ 最终计算 -> 最大 Delta 底 = {base_delta:.4f} * {delta_multiplier:.2f} = {final_limit_delta:.4f}\n"
        f"[风控推导]             -> 目标收益率 = {base_return*100:.2f}% * {return_multiplier:.2f} = {final_ideal_return*100:.2f}%"
    )
    
    return final_limit_delta, final_ideal_return, trace_msg

# --- 主测算引擎 ---
def find_optimal_strikes_with_alert(S, iv30, ivp, hvp, T_days, absolute_min_return=0.30, yield_step=0.01, r=0.03, step=0.5):
    iv30_val = parse_percentage(iv30)
    
    # 熔断检查
    if ivp < 30:
        print(f"【系统熔断】IVP: {ivp}th 低于 30th 硬性底线，禁止开仓。")
        return
    vp_diff = ivp - hvp
    if vp_diff < -40:
        print(f"【系统熔断】IVP-HVP 恶性背离({vp_diff})，禁止开仓。")
        return
    if iv30_val < 0.20:
        print(f"【系统熔断】绝对 IV30({iv30_val*100:.2f}%) 过低，禁止开仓。")
        return

    # 获取风控参数及逻辑链文本
    limit_delta, ideal_return, trace_msg = get_combined_thresholds_with_trace(ivp, hvp)
    
    print(f"\n[环境评估] 当前股价: ${S} | IV30: {iv30_val*100:.2f}%")
    print(f"[波动排位] IVP: {ivp}th | HVP: {hvp}th | 排位差(IVP-HVP): {vp_diff}")
    print(trace_msg) # 打印逻辑链说明
    print(f"[动态风控] 联合调整后允许的最大 Delta 底线为: {limit_delta:.4f}")
    print(f"[动态风控] 联合调整后校准的目标年化收益率为: {ideal_return*100:.2f}%")

    T = T_days / 365
    max_strike = np.floor(S)
    min_strike = S * 0.5
    strikes_to_test = np.arange(max_strike, min_strike, -step)

    def scan_strikes(target_yield):
        results = []
        for K in strikes_to_test:
            price = bs_put_price(S, K, T, r, iv30_val)
            delta = bs_put_delta(S, K, T, r, iv30_val)
            ann_return = (price / K) / T
            if limit_delta <= delta <= -0.02 and ann_return >= target_yield:
                true_margin_of_safety = (S - (K - price)) / S
                results.append({
                    "Strike": round(K, 2), 
                    "Price": round(price, 2), 
                    "Delta": round(delta, 4), 
                    "Return (%)": round(ann_return * 100, 2), 
                    "MOS (%)": round(true_margin_of_safety * 100, 2)
                })
        return results

    # 计算精准的底线参考数据（包含权利金）
    k_30 = find_strike_for_target_return(S, iv30_val, T_days, absolute_min_return, r)
    p_30 = bs_put_price(S, k_30, T, r, iv30_val) if k_30 else 0
    d_30 = bs_put_delta(S, k_30, T, r, iv30_val) if k_30 else 0
    bottom_line_str = f"【底线参考】年化 {absolute_min_return*100:.2f}% 对应行权价: ${k_30:.2f}, 权利金: ${p_30:.2f}, Delta: {d_30:.4f}"

    ideal_results = scan_strikes(ideal_return)
    if ideal_results:
        df = pd.DataFrame(ideal_results)
        df.insert(4, 'Target (%)', round(ideal_return * 100, 2))
        print("-> 完美匹配交易建议：\n")
        print(df.sort_values(by="MOS (%)", ascending=False).to_markdown(index=False))
        return

    # 妥协流
    current_target = ideal_return - yield_step
    while current_target >= absolute_min_return - 1e-6:
        compromise_results = scan_strikes(current_target)
        if compromise_results:
            df = pd.DataFrame(compromise_results)
            df.insert(4, 'Target (%)', round(current_target * 100, 2))
            print(f"-> 妥协匹配：在收益率 {current_target*100:.2f}% 下找到匹配项。\n")
            print(df.sort_values(by="MOS (%)", ascending=False).to_markdown(index=False))
            return
        current_target -= yield_step

    print(f"【无可执行方案】环境及收益底线无法同时满足。")
    print(f"{bottom_line_str}\n")

if __name__ == "__main__":
    find_optimal_strikes_with_alert(S=243, iv30="87%", ivp=100, hvp=38, T_days=46)