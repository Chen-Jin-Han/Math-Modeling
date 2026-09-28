"""
波浪能最大输出功率设计 - 求解代码
国赛 2022 A题
"""

import numpy as np
from scipy.integrate import solve_ivp
import json
import os
import sys

# 使用项目自带的算法库（dogfooding），而非裸调 scipy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from algorithms import nonlinear_programming

# ============ 物理常数 ============
RHO = 1025.0      # 海水密度 kg/m^3
G = 9.8           # 重力加速度 m/s^2
PI = np.pi

# ============ 波浪参数（题目给定）============
H = 2.0           # 波高 m
T_wave = 8.0      # 波浪周期 s
h = 30.0          # 水深 m


def wave_params(H, T, h):
    """计算波浪参数"""
    omega = 2 * PI / T
    # 色散关系求波数（迭代法）
    kw = omega**2 / G  # 深水近似初值
    for _ in range(100):
        kw_new = omega**2 / (G * np.tanh(kw * h))
        if abs(kw_new - kw) < 1e-10:
            break
        kw = kw_new
    return omega, kw


def radiation_damping_coeff(kw, r):
    """辐射阻尼系数 Cr，作为无量纲参数 kw*r 的函数。

    对垂荡圆柱体，辐射阻尼源于表面波的辐射：低频时几乎无辐射（Cr→0），
    在 kw*r≈1 附近达到峰值，高频时由于波长远小于圆柱尺度而衰减。
    简化拟合 Cr = (kw*r) / (1 + (kw*r)^2)，峰值 0.5 出现在 kw*r=1。
    """
    kwr = kw * r
    return kwr / (1.0 + kwr * kwr)


def added_mass_and_damping(r, d, omega, kw):
    """计算附加质量和辐射阻尼"""
    # 附加质量（圆柱近似）
    Ca = 1.0
    ma = RHO * PI * r**2 * d * Ca
    # 辐射阻尼（Cr 依赖 kw*r，非硬编码常数）
    Cr = radiation_damping_coeff(kw, r)
    cr = RHO * G * PI * r**2 / omega * Cr
    return ma, cr


def excitation_force(r, d, H, kw, h):
    """计算波浪激励力幅值"""
    F0 = RHO * G * PI * r**2 * (H / 2) * np.sinh(kw * d) / np.cosh(kw * h)
    return F0


def average_power(params, omega, kw, H, h):
    """计算平均输出功率（目标函数）"""
    r, d, ks, cd = params

    # 质量
    m = RHO * PI * r**2 * d  # 浮子质量（圆柱）

    # 附加质量和辐射阻尼
    ma, cr = added_mass_and_damping(r, d, omega, kw)

    # 总等效参数
    M = m + ma
    C = cr + cd
    K = ks + RHO * G * PI * r**2

    # 激励力幅值
    F0 = excitation_force(r, d, H, kw, h)

    # 振幅
    denom = np.sqrt((K - M * omega**2)**2 + (C * omega)**2)
    if denom < 1e-10:
        return 0.0
    A = F0 / denom

    # 平均功率
    P = 0.5 * cd * omega**2 * A**2
    return P


def solve_optimization():
    """求解优化问题"""
    omega, kw = wave_params(H, T_wave, h)

    print(f"波浪参数: omega={omega:.4f} rad/s, kw={kw:.4f} rad/m")
    print(f"波长 L={2*PI/kw:.2f} m")
    print()

    # 约束条件
    bounds = [
        (0.5, 5.0),      # r 浮子半径
        (0.5, 10.0),     # d 吃水深度
        (1000, 1e6),     # ks 弹簧刚度
        (100, 1e5),      # cd 阻尼系数
    ]

    # 使用项目自带算法库 nonlinear_programming 求解（dogfooding）
    def objective(params):
        return average_power(params, omega, kw, H, h)

    # 多起点优化
    best_P = 0
    best_params = None

    for i in range(50):
        # 随机初始点
        x0 = np.array([
            np.random.uniform(0.5, 5.0),
            np.random.uniform(0.5, 10.0),
            np.random.uniform(1000, 1e6),
            np.random.uniform(100, 1e5),
        ])

        result = nonlinear_programming(
            objective, x0, bounds=bounds, method='SLSQP', maximize=True,
        )

        if result['success'] and result['fun'] > best_P:
            best_P = result['fun']
            best_params = result['x']

    if best_params is None:
        raise RuntimeError("50 个优化起点均未得到可行解")

    r, d, ks, cd = best_params
    m = RHO * PI * r**2 * d
    ma, cr = added_mass_and_damping(r, d, omega, kw)
    M = m + ma
    K = ks + RHO * G * PI * r**2
    F0 = excitation_force(r, d, H, kw, h)
    C_total = cr + cd
    A = F0 / np.sqrt((K - M * omega**2)**2 + (C_total * omega)**2)

    print("=" * 50)
    print("最优解")
    print("=" * 50)
    print(f"浮子半径 r    = {r:.4f} m")
    print(f"吃水深度 d    = {d:.4f} m")
    print(f"弹簧刚度 ks   = {ks:.2f} N/m")
    print(f"阻尼系数 cd   = {cd:.2f} N·s/m")
    print()
    print(f"浮子质量 m    = {m:.2f} kg")
    print(f"附加质量 ma   = {ma:.2f} kg")
    print(f"总质量 M      = {M:.2f} kg")
    print(f"辐射阻尼 cr   = {cr:.2f} N·s/m")
    print(f"激励力幅值 F0 = {F0:.2f} N")
    print(f"振幅 A        = {A:.4f} m")
    print(f"最大功率 P    = {best_P:.2f} W")
    print()

    # 灵敏度分析
    print("=" * 50)
    print("灵敏度分析")
    print("=" * 50)
    param_names = ['r', 'd', 'ks', 'cd']
    for idx, name in enumerate(param_names):
        for delta_pct in [-10, +10]:
            params_test = best_params.copy()
            params_test[idx] *= (1 + delta_pct / 100)
            # 检查边界
            params_test[idx] = np.clip(params_test[idx], bounds[idx][0], bounds[idx][1])
            P_test = average_power(params_test, omega, kw, H, h)
            change = (P_test - best_P) / best_P * 100
            print(f"  {name} {'+' if delta_pct > 0 else ''}{delta_pct}%: P={P_test:.2f}W ({change:+.2f}%)")
    print()

    # 时间历程模拟
    print("=" * 50)
    print("时间历程模拟")
    print("=" * 50)
    t = np.linspace(0, 4 * T_wave, 1000)
    M_total = m + ma
    C_total = cr + cd
    K_total = ks + RHO * G * PI * r**2

    def motion_eq(t, y, M, C, K, F0, omega):
        z, zdot = y
        zddot = (F0 * np.cos(omega * t) - C * zdot - K * z) / M
        return [zdot, zddot]

    y0 = [0, 0]
    sol = solve_ivp(
        motion_eq, (t[0], t[-1]), y0, t_eval=t,
        args=(M_total, C_total, K_total, F0, omega), method='RK45',
    )

    z_t = sol.y[0]
    zdot_t = sol.y[1]
    P_inst = cd * zdot_t**2

    print(f"  稳态振幅（数值）: {np.max(z_t[-200:]):.4f} m")
    print(f"  稳态平均功率（数值）: {np.mean(P_inst[-200:]):.2f} W")

    # 保存结果
    results = {
        "optimal_params": {
            "r": round(r, 4),
            "d": round(d, 4),
            "ks": round(ks, 2),
            "cd": round(cd, 2),
        },
        "derived": {
            "m": round(m, 2),
            "ma": round(ma, 2),
            "M": round(M, 2),
            "cr": round(cr, 2),
            "F0": round(F0, 2),
            "A": round(A, 4),
        },
        "max_power_W": round(best_P, 2),
        "wave_params": {
            "H": H,
            "T": T_wave,
            "h": h,
            "omega": round(omega, 4),
            "kw": round(kw, 4),
            "wavelength": round(2 * PI / kw, 2),
        },
    }

    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存到 {results_path}")

    return results


if __name__ == "__main__":
    np.random.seed(42)
    results = solve_optimization()
