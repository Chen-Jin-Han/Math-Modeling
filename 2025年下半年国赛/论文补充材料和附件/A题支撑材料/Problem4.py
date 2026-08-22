# -*- coding: utf-8 -*-
"""
l3_q4_pso.py
------------
第四问：三架无人机（FY1、FY2、FY3）各投放 1 枚烟幕干扰弹，联合最大化 M1 的有效遮蔽时间。
步骤：
  1) 对每架无人机各自单独使用第二问的求解器 (DIRECT+DE+PS) 得到最优解（热启动）；
  2) 以这三组解为三簇热启动，使用 PSO 在 12 维联合空间做严格的联合最优化；
  3) 保存结果到 result2.xlsx。
仅依赖：numpy, pandas
"""

import math, time, sys
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import numpy as np
import pandas as pd

# ========================= 进度条工具 =========================
def update_bar(current: int, total: int, prefix: str = "", length: int = 40):
    total = max(1, int(total))
    ratio = max(0.0, min(1.0, current / total))
    filled = int(length * ratio + 0.5)
    bar = "█" * filled + "-" * (length - filled)
    sys.stdout.write(f"\r{prefix} |{bar}| {ratio*100:6.2f}% ({current}/{total})")
    sys.stdout.flush()

def finish_bar(prefix: str = "", length: int = 40):
    bar = "█" * length
    sys.stdout.write(f"\r{prefix} |{bar}| 100.00% \n")
    sys.stdout.flush()

# ========================= 题面常量（严格按题） =========================
g = 9.8
V_M_SPEED = 300.0
M1_POS = np.array([20000.0, 0.0, 2000.0], dtype=float)           # M1
DM_VEC = -M1_POS / np.linalg.norm(M1_POS)                        # 指向假目标的单位向量

FY1 = np.array([17800.0,   0.0, 1800.0], dtype=float)
FY2 = np.array([12000.0, 1400.0, 1400.0], dtype=float)
FY3 = np.array([ 6000.0,-3000.0,  700.0], dtype=float)

SMOKE_RADIUS = 10.0
SINK_VELOCITY = 3.0
OBSCURATION_DURATION = 20.0  # s

TARGET_RADIUS, TARGET_HEIGHT = 7.0, 10.0
TARGET_BASE_CENTER = np.array([0.0, 200.0, 0.0], dtype=float)

# 决策变量边界：[v, theta, t_deploy, t_fuse]
BOUNDS = np.array([
    [70.0, 140.0],       # v_drone
    [0.0, 2.0*math.pi],  # theta_drone
    [0.1, 40.0],         # t_deploy
    [0.1, 15.0],         # t_fuse
], dtype=float)

# ========================= 基础几何/轨迹（参数化 F0） =========================
def get_missile_pos(t: float) -> np.ndarray:
    return M1_POS + V_M_SPEED * DM_VEC * t

def get_cloud_center_pos(t: float, F0_POS: np.ndarray, t_deploy: float, t_fuse: float, v_drone: np.ndarray) -> np.ndarray:
    p_deploy = F0_POS + v_drone * t_deploy
    p_detonate = p_deploy + v_drone * t_fuse + 0.5 * np.array([0, 0, -g]) * (t_fuse ** 2)
    t_detonate = t_deploy + t_fuse
    return p_detonate + np.array([0.0, 0.0, -SINK_VELOCITY * (t - t_detonate)])

def dist_point_to_capped_cylinder(p: np.ndarray) -> float:
    px, py, pz = p - TARGET_BASE_CENTER
    rho = math.hypot(px, py)
    dr = max(rho - TARGET_RADIUS, 0.0)
    if pz < 0.0: dz = -pz
    elif pz > TARGET_HEIGHT: dz = pz - TARGET_HEIGHT
    else: dz = 0.0
    return math.hypot(dr, dz)

def theta_s_from_MC(M: np.ndarray, C: np.ndarray) -> float:
    d = np.linalg.norm(C - M)
    return math.pi if d <= SMOKE_RADIUS else math.asin(SMOKE_RADIUS / d)

# ========================= ε 自适应边界采样（严格、可控） =========================
_P_grid_cache: Dict[Tuple[int,int], np.ndarray] = {}

def sample_boundary_side(n_theta: int, n_z: int) -> np.ndarray:
    thetas = np.linspace(0.0, 2.0*np.pi, num=n_theta, endpoint=False)
    zs = np.linspace(0.0, TARGET_HEIGHT, num=n_z)
    X = TARGET_BASE_CENTER[0] + TARGET_RADIUS*np.cos(thetas)
    Y = TARGET_BASE_CENTER[1] + TARGET_RADIUS*np.sin(thetas)
    Xg = np.repeat(X, n_z); Yg = np.repeat(Y, n_z); Zg = np.tile(zs, n_theta)
    return np.stack([Xg, Yg, Zg], axis=1)

def get_boundary_grid(n_theta: int, n_z: int) -> np.ndarray:
    key = (int(n_theta), int(n_z))
    P = _P_grid_cache.get(key)
    if P is None:
        P = sample_boundary_side(n_theta, n_z)
        _P_grid_cache[key] = P
    return P

def mesh_sizes_from_epsilon_local(eps_ang: float, dmin_local: float) -> Tuple[int,int]:
    ds_max = 2.0 * dmin_local * math.sin(0.5 * eps_ang)
    dtheta_max = ds_max / TARGET_RADIUS
    n_theta = int(math.ceil(2.0*math.pi / max(dtheta_max, 1e-12)))
    dz_max = ds_max
    n_z = int(math.ceil(TARGET_HEIGHT / max(dz_max, 1e-12))) + 1
    return max(n_theta, 64), max(n_z, 3)

def alpha_max_with_delta(M: np.ndarray, C: np.ndarray,
                         eps_ang: float, refine_cap: int = 2,
                         guard_deg: float = 0.5) -> Tuple[float, float]:
    dmin_local = max(1e-9, dist_point_to_capped_cylinder(M))
    def eval_on(n_theta:int, n_z:int):
        P = get_boundary_grid(n_theta, n_z)
        w = C - M
        d = np.linalg.norm(w)
        V = P - M
        Vn = np.linalg.norm(V, axis=1)
        cos_a = np.clip((V @ w) / (Vn * d), -1.0, 1.0)
        a = np.arccos(cos_a)
        a_max = float(np.max(a))
        dtheta = 2.0 * math.pi / n_theta
        dz = TARGET_HEIGHT / max(n_z - 1, 1)
        ds = math.hypot(TARGET_RADIUS * dtheta, dz)
        delta = 2.0 * math.asin(min(1.0, ds / (2.0 * dmin_local)))
        return a_max, delta
    n_theta, n_z = mesh_sizes_from_epsilon_local(eps_ang, dmin_local)
    amax, delta = eval_on(n_theta, n_z)
    for _ in range(refine_cap):
        if delta <= math.radians(guard_deg):
            break
        n_theta *= 2
        n_z = min(2*n_z - 1, n_z + 64)
        amax, delta = eval_on(n_theta, n_z)
    return amax, delta

# ========================= L3 判据 + 事件驱动时长（参数化 F0） =========================
def L3_margins_at_time(t: float, F0_POS: np.ndarray, t_deploy: float, t_fuse: float, v_vec: np.ndarray,
                       eps_ang: float) -> Tuple[bool, float, float]:
    M = get_missile_pos(t)
    C = get_cloud_center_pos(t, F0_POS, t_deploy, t_fuse, v_vec)
    dmc = float(np.linalg.norm(C - M))

    if dmc <= SMOKE_RADIUS:  # 云内短路
        dT = dist_point_to_capped_cylinder(M)
        phi1 = math.pi
        phi2 = dT - (dmc - SMOKE_RADIUS)
        return True, phi1, phi2

    dT  = dist_point_to_capped_cylinder(M)
    phi2 = dT - (dmc - SMOKE_RADIUS)
    if phi2 < 0.0:
        return False, float('-inf'), phi2
    ths = theta_s_from_MC(M, C)
    amax, dalpha = alpha_max_with_delta(M, C, eps_ang=eps_ang, refine_cap=1)
    phi1 = ths - amax
    if phi1 <= dalpha:
        amax, dalpha = alpha_max_with_delta(M, C, eps_ang=0.5*eps_ang, refine_cap=2)
        phi1 = ths - amax
    ok = (phi1 >= 0.0) and (phi2 >= 0.0)
    return ok, phi1, phi2

def refine_edge_time(tl: float, tr: float, pred, max_iter: int = 80, tol: float = 1e-3) -> float:
    fl, fr = pred(tl), pred(tr)
    if fl == fr:
        return 0.5*(tl+tr)
    for _ in range(max_iter):
        tm = 0.5*(tl+tr); fm = pred(tm)
        if fm == fl: tl, fl = tm, fm
        else: tr, fr = tm, fm
        if tr - tl <= tol: break
    return 0.5*(tl+tr)

# ===== 单机时长 =====
def duration_adaptive_strict(F0_POS: np.ndarray, v_vec: np.ndarray, t_deploy: float, t_fuse: float,
                             eps_ang: float = 1e-3, N_time_coarse: int = 401, tol_t: float = 1e-3) -> float:
    t0 = t_deploy + t_fuse
    t1 = t0 + OBSCURATION_DURATION
    ts = np.linspace(t0, t1, max(3, N_time_coarse))
    pred = lambda tt: L3_margins_at_time(tt, F0_POS, t_deploy, t_fuse, v_vec, eps_ang)[0]
    mask = np.array([pred(t) for t in ts], dtype=bool)
    edges = np.nonzero(mask[1:] != mask[:-1])[0] + 1
    cross = [refine_edge_time(ts[i-1], ts[i], pred, tol=tol_t) for i in edges]
    cross.sort()
    dur = 0.0; state = bool(mask[0]); cur = t0
    for tc in cross:
        if state: dur += (tc - cur)
        state = not state; cur = tc
    if state: dur += (t1 - cur)
    return float(max(0.0, dur))

def quick_phi2_max(F0_POS: np.ndarray, v_vec: np.ndarray, t_deploy: float, t_fuse: float, N:int=121) -> float:
    t0 = t_deploy + t_fuse
    t1 = t0 + OBSCURATION_DURATION
    ts = np.linspace(t0, t1, N)
    vals = []
    for t in ts:
        M = get_missile_pos(t)
        C = get_cloud_center_pos(t, F0_POS, t_deploy, t_fuse, v_vec)
        dmc = float(np.linalg.norm(C - M))
        dT  = dist_point_to_capped_cylinder(M)
        vals.append(dT - (dmc - SMOKE_RADIUS))
    return float(np.max(vals))

# ========================= 目标函数（带缓存、筛选、统计） =========================
@dataclass
class EngineConfig:
    eps_ang: float = 1e-3
    N_time_coarse: int = 401
    tol_t: float = 1e-3
    fast_screen: bool = True  # 先做 phi2 粗筛

ECFG = EngineConfig()
_eval_cache_single: Dict[Tuple[float,float,float,float,float,float,float], float] = {}  # (Fx,Fy,Fz,v,th,td,tf)->dur
EVAL_COUNT = 0

def round_key(arr: np.ndarray, nd: int = 12) -> tuple:
    a = np.asarray(arr, dtype=np.float64).reshape(-1)
    a = np.round(a, nd)
    return tuple(a.tolist())

def objective_duration_single(F0_POS: np.ndarray, x: np.ndarray) -> float:
    """ 单机时长 """
    global EVAL_COUNT
    key = round_key(np.concatenate([F0_POS, x]))
    if key in _eval_cache_single:
        return _eval_cache_single[key]
    v, th, td, tf = x
    v_vec = np.array([v*math.cos(th), v*math.sin(th), 0.0], dtype=float)
    if ECFG.fast_screen and quick_phi2_max(F0_POS, v_vec, td, tf, N=121) < 0.0:
        val = 0.0
    else:
        val = duration_adaptive_strict(F0_POS, v_vec, td, tf,
                                       eps_ang=ECFG.eps_ang,
                                       N_time_coarse=ECFG.N_time_coarse,
                                       tol_t=ECFG.tol_t)
    _eval_cache_single[key] = float(val)
    EVAL_COUNT += 1
    return float(val)

def objective_neg_single(F0_POS: np.ndarray, x: np.ndarray) -> float:
    return -objective_duration_single(F0_POS, x)

# ========================= DIRECT（确定性全局，单机） =========================
@dataclass
class DirectConfig:
    max_evals: int = 20000
    eps: float = 1e-4
    split_batch_cap: int = 400
    verbose: bool = True

class DirectOptimizer:
    def __init__(self, bounds: np.ndarray, cfg: DirectConfig, objfun):
        self.bounds = bounds.copy()
        self.cfg = cfg
        self.objfun = objfun
        self.dim = bounds.shape[0]
        self.centers: List[np.ndarray] = []
        self.half: List[np.ndarray] = []
        self.fvals: List[float] = []
        self.evals = 0

    def from_unit(self, u: np.ndarray) -> np.ndarray:
        return self.bounds[:,0] + u * (self.bounds[:,1] - self.bounds[:,0])

    def eval_center(self, u: np.ndarray) -> float:
        x = self.from_unit(u)
        f = self.objfun(x)
        self.evals += 1
        return f

    def init(self):
        c0 = np.full(self.dim, 0.5, dtype=float)
        h0 = np.full(self.dim, 0.5, dtype=float)
        f0 = self.eval_center(c0)
        self.centers = [c0]; self.half = [h0]; self.fvals = [f0]
        if self.cfg.verbose:
            print(f"[DIRECT] start: f0={f0:.6f}  (duration={-f0:.6f}s)")
            update_bar(self.evals, self.cfg.max_evals, prefix="[DIRECT] Progress")

    def potential_set(self):
        dlist = np.array([np.linalg.norm(h) for h in self.half], dtype=float)
        flist = np.array(self.fvals, dtype=float)
        fmin = float(np.min(flist))
        uniq_d = {}
        for i, d in enumerate(dlist):
            key = float(np.round(d, 12))
            uniq_d.setdefault(key, []).append(i)
        pts = []
        for key, idxs in uniq_d.items():
            fbest = float(np.min(flist[idxs]))
            pts.append((key, fbest, idxs))
        pts.sort(key=lambda z: z[0])
        hull = []
        for k,(d,f,idxs) in enumerate(pts):
            while len(hull) >= 2:
                d1,f1,_ = pts[hull[-2]]
                d2,f2,_ = pts[hull[-1]]
                slope1 = (f2 - f1) / (d2 - d1 + 1e-18)
                slope2 = (f - f2) / (d - d2 + 1e-18)
                if slope2 >= slope1:
                    hull.pop()
                else:
                    break
            hull.append(k)
        cand_set = set()
        for hidx in hull:
            _,_,idxs = pts[hidx]
            cand_set.update(idxs)
        eps = self.cfg.eps
        for i, f in enumerate(flist):
            if f <= fmin + eps*abs(fmin):
                cand_set.add(i)
        cand = list(cand_set)
        cand.sort(key=lambda i: self.fvals[i])
        return cand[:self.cfg.split_batch_cap]

    def split_rect(self, i: int):
        c = self.centers[i]; h = self.half[i]
        hmax = float(np.max(h))
        J = np.where(h >= hmax - 1e-15)[0]
        delta = hmax / 3.0
        # 预评估 c±δ e_j
        for j in J:
            e = np.zeros_like(c); e[j] = 1.0
            u1 = np.clip(c + delta*e, 0.0, 1.0)
            u2 = np.clip(c - delta*e, 0.0, 1.0)
            f1 = self.eval_center(u1); f2 = self.eval_center(u2)
            self.centers.append(u1); self.half.append(h.copy()); self.fvals.append(f1)
            self.centers.append(u2); self.half.append(h.copy()); self.fvals.append(f2)
        # 替换父矩形为中心处三分子矩形
        new_rects = []
        for j in J:
            e = np.zeros_like(c); e[j] = 1.0
            for sign in (-1.0, 1.0):
                uc = np.clip(c + sign*(delta/2.0)*e, 0.0, 1.0)
                hc = h.copy(); hc[j] = h[j] / 2.0
                new_rects.append((uc, hc, self.eval_center(uc)))
        # 删除原 i
        self.centers[i:i+1] = []
        self.half[i:i+1] = []
        self.fvals[i:i+1] = []
        for uc, hc, fc in new_rects:
            self.centers.append(uc); self.half.append(hc); self.fvals.append(fc)

    def run(self):
        self.init()
        last_print = time.time()
        while self.evals < self.cfg.max_evals:
            cand = self.potential_set()
            if not cand:
                break
            for i in sorted(cand, reverse=True):
                if self.evals >= self.cfg.max_evals:
                    break
                self.split_rect(i)
                if self.cfg.verbose and (time.time() - last_print > 0.1):
                    update_bar(self.evals, self.cfg.max_evals, prefix="[DIRECT] Progress")
                    last_print = time.time()
        if self.cfg.verbose:
            finish_bar(prefix="[DIRECT] Progress")
            fmin = float(np.min(self.fvals))
            print(f"[DIRECT] done: evals={self.evals}, best f={fmin:.6f} (duration={-fmin:.6f}s)")
        idx = int(np.argmin(self.fvals))
        x_best = self.from_unit(self.centers[idx])
        f_best = float(self.fvals[idx])
        centers = np.array([self.from_unit(u) for u in self.centers])
        fvals = np.array(self.fvals)
        return x_best, f_best, centers, fvals

# ========================= DE（随机全局，单机） =========================
@dataclass
class DEConfig:
    pop_size: int = 64
    F: float = 0.7
    CR: float = 0.9
    max_gens: int = 200
    verbose: bool = True
    seed: int = 2025

def clip_bounds(x: np.ndarray, bounds: np.ndarray) -> np.ndarray:
    return np.minimum(np.maximum(x, bounds[:,0]), bounds[:,1])

def differential_evolution(bounds: np.ndarray, cfg: DEConfig, objfun):
    rng = np.random.default_rng(cfg.seed)
    dim = bounds.shape[0]
    pop = rng.random((cfg.pop_size, dim))
    pop = bounds[:,0] + pop*(bounds[:,1]-bounds[:,0])
    f = np.array([objfun(ind) for ind in pop], dtype=float)
    best_idx = int(np.argmin(f)); best = pop[best_idx].copy(); fbest = float(f[best_idx])
    if cfg.verbose:
        update_bar(0, cfg.max_gens, prefix="[DE] Progress")
    last_print = time.time()
    for gen in range(1, cfg.max_gens+1):
        for i in range(cfg.pop_size):
            idxs = list(range(cfg.pop_size)); idxs.remove(i)
            a, b, c = pop[rng.choice(idxs, 3, replace=False)]
            mutant = a + cfg.F*(b - c)
            cross = rng.random(dim) < cfg.CR
            jrand = rng.integers(0, dim); cross[jrand] = True
            trial = np.where(cross, mutant, pop[i])
            trial = clip_bounds(trial, bounds)
            ft = objfun(trial)
            if ft < f[i]:
                pop[i] = trial; f[i] = ft
                if ft < fbest:
                    fbest = float(ft); best = trial.copy()
        if cfg.verbose and (time.time() - last_print > 0.1):
            update_bar(gen, cfg.max_gens, prefix="[DE] Progress")
            last_print = time.time()
    if cfg.verbose:
        finish_bar(prefix="[DE] Progress")
        print(f"[DE] done: best f={fbest:.6f} (duration={-fbest:.6f}s)")
    return best, fbest, pop, f

# ========================= Pattern Search（局部，单机） =========================
@dataclass
class PSConfig:
    init_step: float = 0.05     # 归一化步长
    min_step: float = 5e-5
    shrink: float = 0.5
    max_poll: int = 20000
    verbose: bool = True

def pattern_search(x0: np.ndarray, bounds: np.ndarray, cfg: PSConfig, objfun):
    x = x0.copy()
    f = objfun(x)
    step = cfg.init_step
    scale = (bounds[:,1] - bounds[:,0])
    polls = 0
    if cfg.verbose:
        print(f"[PS] start f={f:.6f}, x={x}")
        update_bar(0, cfg.max_poll, prefix="[PS] Progress")
    last_print = time.time()
    while step >= cfg.min_step and polls < cfg.max_poll:
        improved = False
        for j in range(bounds.shape[0]):
            for sgn in (+1.0, -1.0):
                xt = clip_bounds(x + (sgn*step)*scale*np.eye(1,4,j)[0], bounds)
                ft = objfun(xt)
                polls += 1
                if ft < f - 1e-12:
                    x, f = xt, ft
                    improved = True
                    break
            if improved: break
        if not improved:
            step *= cfg.shrink
        if cfg.verbose and (time.time() - last_print > 0.1):
            update_bar(polls, cfg.max_poll, prefix="[PS] Progress")
            last_print = time.time()
    if cfg.verbose:
        finish_bar(prefix="[PS] Progress")
        print(f"[PS] end   f={f:.6f}, polls={polls}")
    return x, f

# ========================= “第二问”求解器（单机封装） =========================
@dataclass
class ULTConfigSingle:
    eps_ang: float = 1e-3
    N_time: int = 601
    tol_t: float = 1e-3
    # DIRECT
    direct_max_evals: int = 20000
    direct_eps: float = 1e-4
    direct_split_cap: int = 400
    # DE
    de_pop: int = 64
    de_F: float = 0.7
    de_CR: float = 0.9
    de_gens: int = 160
    # 精炼
    refine_topK: int = 30
    # PS
    ps_init_step: float = 0.05
    ps_min_step: float = 5e-5
    ps_shrink: float = 0.5
    ps_max_poll: int = 20000
    # 日志
    verbose: bool = True
    seed: int = 2025

def run_single_best(F0_POS: np.ndarray, cfg: ULTConfigSingle):
    """ 返回单机最优解 x* 与持续时间 """
    global ECFG, EVAL_COUNT
    ECFG = EngineConfig(eps_ang=cfg.eps_ang, N_time_coarse=cfg.N_time, tol_t=cfg.tol_t, fast_screen=True)
    # DIRECT
    dopt = DirectOptimizer(
        bounds=BOUNDS,
        cfg=DirectConfig(max_evals=cfg.direct_max_evals, eps=cfg.direct_eps,
                         split_batch_cap=cfg.direct_split_cap, verbose=cfg.verbose),
        objfun=lambda x: objective_neg_single(F0_POS, x)
    )
    xD, fD, poolD, fpoolD = dopt.run()
    # DE
    de_cfg = DEConfig(pop_size=cfg.de_pop, F=cfg.de_F, CR=cfg.de_CR, max_gens=cfg.de_gens,
                      verbose=cfg.verbose, seed=cfg.seed)
    xE, fE, popE, fpopE = differential_evolution(BOUNDS, de_cfg, lambda x: objective_neg_single(F0_POS, x))
    # 组装 PS 种子
    K = cfg.refine_topK
    idxD = np.argsort(fpoolD)[:max(2, K//2)]
    idxE = np.argsort(fpopE)[:max(2, K - len(idxD))]
    seeds = np.vstack([poolD[idxD,:], popE[idxE,:], xD.reshape(1,-1), xE.reshape(1,-1)])
    # 去重
    uniq = []; seen=set()
    for s in seeds:
        key = round_key(s)
        if key not in seen:
            seen.add(key); uniq.append(s)
    seeds = np.array(uniq, dtype=float)
    if cfg.verbose:
        print(f"[TOP-1UAV] seeds into PS: {len(seeds)}")
        update_bar(0, len(seeds), prefix="[PS][Seeds-1UAV]")

    ps_cfg = PSConfig(init_step=cfg.ps_init_step, min_step=cfg.ps_min_step,
                      shrink=cfg.ps_shrink, max_poll=cfg.ps_max_poll, verbose=False)
    gbest_x = None; gbest_f = float("inf")
    for k, s in enumerate(seeds, start=1):
        xr, fr = pattern_search(s, BOUNDS, ps_cfg, lambda x: objective_neg_single(F0_POS, x))
        if fr < gbest_f:
            gbest_f, gbest_x = fr, xr.copy()
        update_bar(k, len(seeds), prefix="[PS][Seeds-1UAV]")
    finish_bar(prefix="[PS][Seeds-1UAV]")
    return gbest_x, float(-gbest_f)

# ========================= 三机联合：并集遮蔽时长 =========================
def union_duration_three(x12: np.ndarray,
                         F_list: List[np.ndarray],
                         eps_ang: float = 1e-3,
                         N_time_coarse: int = 601,
                         tol_t: float = 1e-3) -> float:
    """
    x12: [v1,th1,td1,tf1, v2,th2,td2,tf2, v3,th3,td3,tf3]
    F_list: [FY1, FY2, FY3]
    """
    x12 = np.asarray(x12, dtype=float).reshape(12)
    xs = [x12[0:4], x12[4:8], x12[8:12]]
    ts0 = [xs[i][2] + xs[i][3] for i in range(3)]
    ts1 = [ts0[i] + OBSCURATION_DURATION for i in range(3)]
    T0 = float(min(ts0)); T1 = float(max(ts1))
    if T1 <= T0:  # 极小概率数值错误保护
        return 0.0

    # 预构造每架机的判定函数
    vvec = []
    for i in range(3):
        v, th, td, tf = xs[i]
        vvec.append(np.array([v*math.cos(th), v*math.sin(th), 0.0], dtype=float))

    def pred_i(i, t):
        v, th, td, tf = xs[i]
        ok, _, _ = L3_margins_at_time(t, F_list[i], td, tf, vvec[i], eps_ang)
        return ok

    def pred_union(t):
        return pred_i(0,t) or pred_i(1,t) or pred_i(2,t)

    ts = np.linspace(T0, T1, max(3, N_time_coarse))
    mask = np.array([pred_union(t) for t in ts], dtype=bool)
    edges = np.nonzero(mask[1:] != mask[:-1])[0] + 1
    # 二分细化
    cross = [refine_edge_time(ts[i-1], ts[i], pred_union, tol=tol_t) for i in edges]
    cross.sort()
    dur = 0.0; state = bool(mask[0]); cur = T0
    for tc in cross:
        if state: dur += (tc - cur)
        state = not state; cur = tc
    if state: dur += (T1 - cur)
    return float(max(0.0, dur))

# ========================= PSO（三簇热启动，12 维联合优化） =========================
@dataclass
class PSOConfig:
    swarm_size: int = 90      # 3 簇 * 30
    iters: int = 160
    w: float = 0.72
    c1: float = 1.49
    c2: float = 1.49
    verbose: bool = True
    hot_sigma_frac: float = 0.08  # 热启动簇的噪声尺度（相对边界跨度 8%）

def pso_three_uav(F_list: List[np.ndarray],
                  x1: np.ndarray, x2: np.ndarray, x3: np.ndarray,
                  cfg: PSOConfig,
                  eps_ang: float = 1e-3,
                  N_time_coarse: int = 601,
                  tol_t: float = 1e-3):
    rng = np.random.default_rng(2025)
    dim4 = 4
    dim = 12
    # 边界拼接
    B = np.vstack([BOUNDS, BOUNDS, BOUNDS])

    # 组成基准热启动解
    base = np.concatenate([x1, x2, x3]).astype(float)

    # 初始化群体（三簇围绕三个热启动）
    swarm = np.zeros((cfg.swarm_size, dim), dtype=float)
    vel   = np.zeros_like(swarm)
    span = (B[:,1]-B[:,0])
    sigma = cfg.hot_sigma_frac * span

    per = cfg.swarm_size // 3
    for k,(xhot,off) in enumerate([(x1,0),(x2,per),(x3,2*per)]):
        for i in range(per):
            z = np.concatenate([xhot if j==k else (x1 if j==0 else (x2 if j==1 else x3))
                                for j in range(3)]).copy()
            # 仅在所属簇的4维上加噪
            start = k*dim4; end = start+dim4
            z[start:end] += rng.normal(0.0, sigma[start:end])
            z = np.minimum(np.maximum(z, B[:,0]), B[:,1])
            swarm[off+i,:] = z
    # 如 swarm_size 不是 3 的倍数，补若干基准个体
    for i in range(3*per, cfg.swarm_size):
        swarm[i,:] = base.copy()

    # 适应度（越大越好），PSO内部使用负号做最小化
    def fit(x12):
        return -union_duration_three(x12, F_list, eps_ang, N_time_coarse, tol_t)

    f = np.array([fit(p) for p in swarm], dtype=float)
    pbest = swarm.copy(); fpbest = f.copy()
    gidx = int(np.argmin(f)); gbest = swarm[gidx].copy(); fgbest = float(f[gidx])

    if cfg.verbose:
        update_bar(0, cfg.iters, prefix="[PSO-3UAV] Progress")
    last_print = time.time()

    for it in range(1, cfg.iters+1):
        r1 = rng.random((cfg.swarm_size, dim))
        r2 = rng.random((cfg.swarm_size, dim))
        vel = (cfg.w*vel
               + cfg.c1*r1*(pbest - swarm)
               + cfg.c2*r2*(gbest - swarm))
        swarm = swarm + vel
        swarm = np.minimum(np.maximum(swarm, B[:,0]), B[:,1])
        f = np.array([fit(p) for p in swarm], dtype=float)
        better = f < fpbest
        pbest[better,:] = swarm[better,:]
        fpbest[better] = f[better]
        gidx = int(np.argmin(f))
        if f[gidx] < fgbest:
            fgbest = float(f[gidx]); gbest = swarm[gidx].copy()
        if cfg.verbose and (time.time() - last_print > 0.1):
            update_bar(it, cfg.iters, prefix="[PSO-3UAV] Progress")
            last_print = time.time()
    if cfg.verbose:
        finish_bar(prefix="[PSO-3UAV] Progress")
        print(f"[PSO-3UAV] done: best union duration = {-fgbest:.6f}s")

    return gbest, float(-fgbest)

# ========================= 顶层：跑单机最优 -> PSO 联合优化 =========================
@dataclass
class Q4Config:
    # 单机求解（沿用第二问参数）
    single: ULTConfigSingle = ULTConfigSingle()
    # PSO
    pso: PSOConfig = PSOConfig()
    # 栅格与误差
    eps_ang: float = 1e-3
    N_time: int = 601
    tol_t: float = 1e-3
    verbose: bool = True

def run_q4_and_save():
    print("=== Q4 | Step-1: 分别求 FY1/FY2/FY3 的单机最优（第二问求解器） ===")
    cfg1 = Q4Config()
    # 分别跑单机
    x1, d1 = run_single_best(FY1, cfg1.single)
    x2, d2 = run_single_best(FY2, cfg1.single)
    x3, d3 = run_single_best(FY3, cfg1.single)
    print("\n[Single Best] FY1:", x1, "duration:", d1)
    print("[Single Best] FY2:", x2, "duration:", d2)
    print("[Single Best] FY3:", x3, "duration:", d3)

    print("\n=== Q4 | Step-2: 以三组最优解为三簇热启动，PSO 做 12 维联合优化 ===")
    gbest, union_dur = pso_three_uav([FY1, FY2, FY3], x1, x2, x3,
                                     cfg1.pso, eps_ang=cfg1.eps_ang,
                                     N_time_coarse=cfg1.N_time, tol_t=cfg1.tol_t)

    # 解析联合最优
    sol1 = gbest[0:4]; sol2 = gbest[4:8]; sol3 = gbest[8:12]
    def row(FYname, x):
        v, th, td, tf = x
        return dict(UAV=FYname,
                    v=v,
                    theta_rad=th,
                    theta_deg=float(np.rad2deg(th)),
                    t_deploy=td,
                    t_fuse=tf)

    df = pd.DataFrame([row("FY1", sol1), row("FY2", sol2), row("FY3", sol3)])
    # 附加一个总览 sheet：联合遮蔽总时长
    summary = pd.DataFrame([{"union_duration_s": union_dur,
                             "FY1_single_best_s": d1,
                             "FY2_single_best_s": d2,
                             "FY3_single_best_s": d3}])

    with pd.ExcelWriter("result2.xlsx") as w:
        df.to_excel(w, index=False, sheet_name="strategy")
        summary.to_excel(w, index=False, sheet_name="summary")

    print("\n=== Q4 最终结果 ===")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.6f}"))
    print(f"\n[Union duration (three UAVs)] = {union_dur:.6f} s")
    print("结果已保存：result2.xlsx")

# ========================= 主入口 =========================
if __name__ == "__main__":
    run_q4_and_save()
