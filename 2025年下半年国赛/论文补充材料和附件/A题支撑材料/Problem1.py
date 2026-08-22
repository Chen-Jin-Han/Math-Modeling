# -*- coding: utf-8 -*-
"""
自适应 L3（全目标遮蔽）判定：空间参考点邻域 + 时间边界双重细化

数学判据（L3：完整笼罩圆柱体目标）：
1) 角度包含：目标圆柱 T 在导弹视点 M(t) 的全部可见方向集合 D_T(t) 包含于由烟幕球 S(t) 诱导的遮蔽圆锥 K(t)。
   等价为 α_max(t) ≤ θ_s(t)，其中
     α_max(t) = sup_{p∈∂T} angle( (p - M)/||p - M||, (C - M)/||C - M|| ),
     θ_s(t)   = arcsin( r / ||C - M|| ).
2) 深度次序（先遇烟幕再遇目标）： ||C - M|| - r ≤ dist(M(t), T)。

"""
from __future__ import annotations
import numpy as np, pandas as pd, math
from dataclasses import dataclass
from typing import List, Tuple

# ========= 题面常量=========
g = 9.8                 # m/s^2
v_m = 300.0             # m/s  导弹速度
v_u = 120.0             # m/s  无人机速度
r = 10.0                # m    烟幕球半径
sink_v = 3.0            # m/s  云团中心下沉速度
R, H = 7.0, 10.0        # m    圆柱半径/高度（目标）
t_d = 1.5
t_e = t_d + 3.6
T_MIN, T_MAX = t_e, t_e + 20.0

# ========= 轨迹 =========
M0 = np.array([20000.0, 0.0, 2000.0])          # 导弹初始位置
F0 = np.array([17800.0, 0.0, 1800.0])          # 无人机初始位置
dm = - M0 / np.linalg.norm(M0)                 # 导弹指向原点的单位向量
du = np.array([-1.0, 0.0, 0.0])                # 无人机等高度朝原点（x 负向）

def M_pos(t: float) -> np.ndarray:
    """导弹位置 M(t)"""
    return M0 + v_m * dm * t

def bomb_pos_after_drop(t: float) -> np.ndarray:
    """投放后弹体位置（自由落体；以绝对时刻 t 为自变量）"""
    tau = t - t_d
    x = (F0[0] + v_u * du[0] * t_d) + v_u * du[0] * (t - t_d)  # 17620 - 120*tau
    y = 0.0
    z = F0[2] - 0.5 * g * (tau ** 2)
    return np.array([x, y, z])

def cloud_center(t: float) -> np.ndarray:
    """云团中心 C(t)：起爆点 E，之后以 sink_v 沿 z 负向匀速下沉"""
    E = bomb_pos_after_drop(t_e)
    return E + np.array([0.0, 0.0, -sink_v * (t - t_e)])

# ========= 距离与角度 =========
def dist_point_capped_cylinder(P: np.ndarray) -> float:
    """
    点到“有限圆柱集合” T 的欧氏距离闭式：
    T = { (x,y,z) : x^2+(y-200)^2 ≤ R^2, 0 ≤ z ≤ H }。
    """
    x, y, z = float(P[0]), float(P[1]), float(P[2])
    rho = math.hypot(x, y - 200.0)
    dr = max(rho - R, 0.0)
    if z < 0.0: dz = -z
    elif z > H: dz = z - H
    else: dz = 0.0
    return math.hypot(dr, dz)

def theta_s_from_MC(M: np.ndarray, C: np.ndarray) -> float:
    """
    遮蔽圆锥半角：
    - 若导弹在云内（d≤r）：整球遮蔽 → 半角 π；
    - 否则：θ_s = arcsin( r / d )（带裁剪）。
    """
    d = np.linalg.norm(C - M)
    if d <= r:
        return math.pi
    val = min(1.0, r / d)
    return math.asin(val)

def alpha_at(M: np.ndarray, C: np.ndarray, P: np.ndarray) -> np.ndarray:
    """返回数组 P 中每个点的 α(p) = angle( (p-M)/||p-M||, (C-M)/||C-M|| )"""
    w = C - M
    d = np.linalg.norm(w)
    V = P - M
    Vn = np.linalg.norm(V, axis=1)
    eps = 1e-15
    cos_a = (V @ w) / (np.maximum(Vn, eps) * max(d, eps))
    cos_a = np.clip(cos_a, -1.0, 1.0)
    return np.arccos(cos_a)

# ========= 空间胞元（θ,z）定义与认证 =========
@dataclass
class Cell:
    th0: float
    th1: float
    z0: float
    z1: float
    depth: int

    def center(self) -> Tuple[float, float]:
        return 0.5*(self.th0 + self.th1), 0.5*(self.z0 + self.z1)

    def metric_radius(self) -> float:
        """胞元中心到最远角点的弧长度量半径：s_cell = 0.5 * sqrt( (R Δθ)^2 + (Δz)^2 )"""
        dth = self.th1 - self.th0
        dz  = self.z1 - self.z0
        return 0.5 * math.hypot(R * dth, dz)

    def split(self) -> List['Cell']:
        """沿度量更长的一侧二分，保持子胞元形状适度方正"""
        dth = self.th1 - self.th0
        dz  = self.z1 - self.z0
        Lth = R * dth
        Lz  = dz
        if Lth >= Lz:
            thm = 0.5*(self.th0 + self.th1)
            return [Cell(self.th0, thm, self.z0, self.z1, self.depth+1),
                    Cell(thm, self.th1, self.z0, self.z1, self.depth+1)]
        else:
            zm = 0.5*(self.z0 + self.z1)
            return [Cell(self.th0, self.th1, self.z0, zm, self.depth+1),
                    Cell(self.th0, self.th1, zm, self.z1, self.depth+1)]

def point_from_theta_z(theta: float, z: float) -> np.ndarray:
    return np.array([R * math.cos(theta), 200.0 + R * math.sin(theta), z])

def certify_cell_L3(M: np.ndarray, C: np.ndarray, cell: Cell, dTmin: float, ths: float) -> Tuple[int, float, float]:
    """
    认证单个胞元：
    返回 (status, α_center, Δα_bound)：
      status = +1 安全（整个胞元被遮蔽）
             = -1 违反（整个胞元未被遮蔽）
             =  0 不确定（需要细化）
    其中 Δα_bound = 2*arcsin( s_cell / (2*dTmin) ) 为角度变化上界。
    """
    th_c, z_c = cell.center()
    P_c = point_from_theta_z(th_c, z_c).reshape(1,3)
    a_c = float(alpha_at(M, C, P_c)[0])
    s_cell = cell.metric_radius()
    delta = 2.0 * math.asin( min(1.0, 0.5 * s_cell / max(dTmin, 1e-12)) )

    if a_c + delta <= ths:
        return +1, a_c, delta
    if a_c - delta >  ths:
        return -1, a_c, delta
    return 0, a_c, delta

# ========= 时间边界二分 =========
def refine_time_edge(tl: float, tr: float, l3_func, maxit: int = 60) -> float:
    fl = l3_func(tl)
    fr = l3_func(tr)
    if fl == fr:
        return 0.5*(tl+tr)
    for _ in range(maxit):
        tm = 0.5*(tl+tr)
        fm = l3_func(tm)
        if fm == fl:
            tl, fl = tm, fm
        else:
            tr, fr = tm, fm
        if tr - tl < 1e-12:
            break
    return 0.5*(tl+tr)

# ========= 在单个时刻 t 进行 L3 判定（带空间自适应） =========
def L3_at_time(t: float,
               ntheta0: int = 64, nz0: int = 3,
               max_depth: int = 8,
               cell_budget: int = 50000) -> Tuple[bool, float, int]:
    """
    返回 (is_L3, min_margin, cells_examined)：
      is_L3     ：该时刻是否满足 L3；
      min_margin：遍历认证安全的所有胞元的全局“安全余量”最小值（θ_s - (α_c + Δα_bound)），
                  若出现违反/预算耗尽，返回非正值；
      cells_examined：已检查胞元数（衡量开销）。
    预算/层数不足时采用“保守失败”（未能认证 → 判不满足）。
    """
    M = M_pos(t); C = cloud_center(t)
    ths = theta_s_from_MC(M, C)        # 角度阈值（云内时为 π）
    dmc = float(np.linalg.norm(C - M))
    dTmin = dist_point_capped_cylinder(M)

    # 深度次序先验检查：若烟幕不在目标之前，直接失败
    if (dmc - r) > dTmin:
        return False, -(dmc - r - dTmin), 0

    # 若导弹在云内：角度条件自动满足（且上式已保证深度条件）
    if dmc <= r:
        return True, +0.5, 0  # 给出一个正的占位余量

    # 初始粗网格
    th_edges = np.linspace(0.0, 2.0*np.pi, ntheta0, endpoint=False).tolist()
    th_edges.append(2.0*np.pi)
    z_edges = np.linspace(0.0, H, nz0).tolist()

    cells: List[Cell] = []
    for i in range(len(th_edges)-1):
        for j in range(len(z_edges)-1):
            cells.append(Cell(th_edges[i], th_edges[i+1], z_edges[j], z_edges[j+1], depth=0))

    min_margin = float('inf')
    examined = 0
    stack = cells

    while stack:
        cell = stack.pop()
        examined += 1
        if examined > cell_budget:
            return False, -0.0, examined
        status, a_c, delta = certify_cell_L3(M, C, cell, dTmin, ths)
        if status == +1:
            margin = ths - (a_c + delta)
            if margin < min_margin:
                min_margin = margin
            continue
        elif status == -1:
            margin = ths - (a_c - delta)
            return False, margin, examined
        else:
            if cell.depth >= max_depth:
                margin = ths - a_c
                return False, margin, examined
            stack.extend(cell.split())

    # 全部胞元均被认证为安全
    if math.isinf(min_margin):
        min_margin = +0.0
    return True, min_margin, examined

# ========= 顶层驱动：粗时间网格 + 边界二分 =========
def main():
    # —— 可调参数（按机器性能/精度需要调整） ——
    N_t0 = 401           # 初始时间采样数
    ntheta0, nz0 = 64, 3 # 初始空间网格（θ×z）
    max_depth = 8        # 最大空间细化层数
    cell_budget = 80000  # 单时刻最大胞元检查数（防止过慢）

    ts = np.linspace(T_MIN, T_MAX, N_t0)
    mask = np.zeros_like(ts, dtype=int)
    margins = np.zeros_like(ts, dtype=float)
    cells_used = np.zeros_like(ts, dtype=int)

    for i, t in enumerate(ts):
        ok, margin, used = L3_at_time(t, ntheta0, nz0, max_depth, cell_budget)
        mask[i] = 1 if ok else 0
        margins[i] = margin
        cells_used[i] = used

    # 时间边界检测与二分细化
    edges = np.diff(mask.astype(int))
    starts = list(np.where(edges == 1)[0] + 1)
    ends   = list(np.where(edges == -1)[0] + 1)
    if mask[0]:  starts = [0] + starts
    if mask[-1]: ends   = ends + [len(mask)]

    intervals = []
    def l3_func(t):
        ok, _, _ = L3_at_time(t, ntheta0, nz0, max_depth, cell_budget)
        return ok
    for s_idx, e_idx in zip(starts, ends):
        if s_idx == e_idx:
            continue
        tL = ts[0] if s_idx==0 else refine_time_edge(ts[s_idx-1], ts[s_idx], l3_func)
        tR = ts[-1] if e_idx==len(ts) else refine_time_edge(ts[e_idx-1], ts[e_idx], l3_func)
        tm = 0.5*(tL + tR)
        if l3_func(tm):
            intervals.append((tL, tR))

    # 导出 CSV
    pd.DataFrame({
        "t": ts,
        "L3_mask": mask,
        "margin(rad)": margins,
        "cells_used": cells_used
    }).to_csv("L3_adaptive_timeseries.csv", index=False)
    pd.DataFrame([{"t_start": a, "t_end": b, "duration": b-a} for a,b in intervals])\
      .to_csv("L3_adaptive_intervals.csv", index=False)

    # 打印区间
    print("=== L3 (adaptive) intervals ===")
    if not intervals:
        print(f"None in [{T_MIN:.3f}, {T_MAX:.3f}] s")
    else:
        for a,b in intervals:
            print(f"[{a:.12f}, {b:.12f}]  Δt = {b-a:.12f} s")

    # 可选绘图
    try:
        import matplotlib.pyplot as plt
        plt.figure()
        plt.plot(ts, margins, label="safety margin θ_s-(α_c+Δα_bound)")
        plt.axhline(0.0, linestyle="--")
        for a,b in intervals: plt.axvspan(a,b, alpha=0.2)
        plt.xlabel("t (s)"); plt.ylabel("radian"); plt.title("Adaptive L3 safety margin over time")
        plt.legend(); plt.tight_layout()
        plt.savefig("L3_adaptive_margin.png", dpi=160, bbox_inches="tight")
        print("Saved plot: L3_adaptive_margin.png")
    except Exception as e:
        print("Matplotlib not available (plot skipped).")

if __name__ == "__main__":
    main()
