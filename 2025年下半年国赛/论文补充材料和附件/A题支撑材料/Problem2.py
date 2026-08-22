# -*- coding: utf-8 -*-
"""
l3_global_opt_ultimate.py
-------------------------
严格 L3 判据 + 局部 ε 自适应边界采样 + 事件驱动时间细化
全局：DIRECT（确定性） + 差分进化 DE（随机）；局部：Pattern Search

"""

import math, time, sys, random
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

# ========================= 题面常量=========================
g = 9.8
V_M_SPEED = 300.0
M0_POS = np.array([20000.0, 0.0, 2000.0], dtype=float)
DM_VEC = -M0_POS / np.linalg.norm(M0_POS)

F0_POS = np.array([17800.0, 0.0, 1800.0], dtype=float)

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

# ========================= 基础几何/轨迹 =========================
def get_missile_pos(t: float) -> np.ndarray:
    return M0_POS + V_M_SPEED * DM_VEC * t

def get_cloud_center_pos(t: float, t_deploy: float, t_fuse: float, v_drone: np.ndarray) -> np.ndarray:
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
    """
    几何严格推导：
      若 d = ||C - M|| <= r，则任意方向视线均与球相交 ⇒ 遮蔽半角取 π；
      若 d > r，则遮蔽半角为 asin(r/d)。
    """
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
    """
    返回 (alpha_max, delta_alpha_upper)
    先用局部 dmin 生成网格，若误差上界仍偏大（> guard_deg），在 argmax 附近加密（翻倍 nθ,nz），最多 refine_cap 次。
    """
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
        # 当前网格的角度误差上界
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

# ========================= L3 判据 + 事件驱动时长 =========================
def L3_margins_at_time(t: float, t_deploy: float, t_fuse: float, v_vec: np.ndarray,
                       eps_ang: float) -> Tuple[bool, float, float]:
    """
    返回 (ok, phi1, phi2)
      phi1 = θs - αmax；phi2 = dist(M,T) - (||C-M|| - r)
    云内短路：若 ||C-M|| ≤ r，则角度条件恒真，深度裕度 ≥ dist(M,T) ≥ 0，直接 True。
    """
    M = get_missile_pos(t)
    C = get_cloud_center_pos(t, t_deploy, t_fuse, v_vec)
    dmc = float(np.linalg.norm(C - M))

    # --- 云内短路 ---
    if dmc <= SMOKE_RADIUS:
        dT = dist_point_to_capped_cylinder(M)
        phi1 = math.pi
        phi2 = dT - (dmc - SMOKE_RADIUS)  # ≥ dT ≥ 0
        return True, phi1, phi2

    # --- 常规分支 (dmc > r) ---
    dT  = dist_point_to_capped_cylinder(M)
    phi2 = dT - (dmc - SMOKE_RADIUS)
    if phi2 < 0.0:
        return False, float('-inf'), phi2
    ths = theta_s_from_MC(M, C)       # 此时 ths = asin(r/dmc)
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

def duration_adaptive_strict(v_vec: np.ndarray, t_deploy: float, t_fuse: float,
                             eps_ang: float = 1e-3, N_time_coarse: int = 401,
                             tol_t: float = 1e-3) -> float:
    t0 = t_deploy + t_fuse
    t1 = t0 + OBSCURATION_DURATION
    ts = np.linspace(t0, t1, max(3, N_time_coarse))
    pred = lambda tt: L3_margins_at_time(tt, t_deploy, t_fuse, v_vec, eps_ang)[0]
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

def quick_phi2_max(v_vec: np.ndarray, t_deploy: float, t_fuse: float, N:int=121) -> float:
    t0 = t_deploy + t_fuse
    t1 = t0 + OBSCURATION_DURATION
    ts = np.linspace(t0, t1, N)
    vals = []
    for t in ts:
        M = get_missile_pos(t)
        C = get_cloud_center_pos(t, t_deploy, t_fuse, v_vec)
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

_eval_cache: Dict[Tuple[float,float,float,float], float] = {}
EVAL_COUNT = 0

def round_key(x: np.ndarray, nd: int = 12) -> tuple:
    arr = np.asarray(x, dtype=np.float64).reshape(-1)
    if arr.size != 4:
        raise ValueError(f"round_key expects 4-d vector, got shape={arr.shape}")
    arr = np.round(arr, nd)
    return tuple(arr.tolist())

def objective_duration(x: np.ndarray) -> float:
    global EVAL_COUNT
    key = round_key(x)
    if key in _eval_cache:
        return _eval_cache[key]
    v, th, td, tf = x
    v_vec = np.array([v*math.cos(th), v*math.sin(th), 0.0], dtype=float)
    if ECFG.fast_screen:
        if quick_phi2_max(v_vec, td, tf, N=121) < 0.0:
            _eval_cache[key] = 0.0
            EVAL_COUNT += 1
            return 0.0
    dur = duration_adaptive_strict(v_vec, td, tf,
                                   eps_ang=ECFG.eps_ang,
                                   N_time_coarse=ECFG.N_time_coarse,
                                   tol_t=ECFG.tol_t)
    _eval_cache[key] = float(dur)
    EVAL_COUNT += 1
    return float(dur)

def objective_neg(x: np.ndarray) -> float:
    return -objective_duration(x)

# ========================= DIRECT =========================
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

    def to_unit(self, x: np.ndarray) -> np.ndarray:
        return (x - self.bounds[:,0]) / (self.bounds[:,1] - self.bounds[:,0])

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
                uc = np.clip(c + sign*(delta/2.0)*e, 0.0, 1.0)  # 中间三分法的两侧中心
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

# ========================= 差分进化 =========================
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
            idxs = list(range(cfg.pop_size))
            idxs.remove(i)
            a, b, c = pop[rng.choice(idxs, 3, replace=False)]
            mutant = a + cfg.F*(b - c)
            cross = rng.random(dim) < cfg.CR
            jrand = rng.integers(0, dim)
            cross[jrand] = True
            trial = np.where(cross, mutant, pop[i])
            trial = clip_bounds(trial, bounds)
            ft = objfun(trial)
            if ft < f[i]:
                pop[i] = trial
                f[i] = ft
                if ft < fbest:
                    fbest = float(ft); best = trial.copy()
        if cfg.verbose and (time.time() - last_print > 0.1):
            update_bar(gen, cfg.max_gens, prefix="[DE] Progress")
            last_print = time.time()
    if cfg.verbose:
        finish_bar(prefix="[DE] Progress")
        print(f"[DE] done: best f={fbest:.6f} (duration={-fbest:.6f}s)")
    return best, fbest, pop, f

# ========================= Pattern Search =========================
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

# ========================= 顶层调度 =========================
@dataclass
class ULTConfig:
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

def run_ultimate(cfg: ULTConfig):
    global ECFG, EVAL_COUNT
    ECFG = EngineConfig(eps_ang=cfg.eps_ang, N_time_coarse=cfg.N_time, tol_t=cfg.tol_t, fast_screen=True)
    EVAL_COUNT = 0
    t0 = time.time()

    # 1) DIRECT（确定性全局）
    direct = DirectOptimizer(
        bounds=BOUNDS,
        cfg=DirectConfig(max_evals=cfg.direct_max_evals,
                         eps=cfg.direct_eps,
                         split_batch_cap=cfg.direct_split_cap,
                         verbose=cfg.verbose),
        objfun=objective_neg
    )
    xD, fD, poolD, fpoolD = direct.run()

    # 2) 差分进化（随机全局）
    de_cfg = DEConfig(pop_size=cfg.de_pop, F=cfg.de_F, CR=cfg.de_CR, max_gens=cfg.de_gens,
                      verbose=cfg.verbose, seed=cfg.seed)
    xE, fE, popE, fpopE = differential_evolution(BOUNDS, de_cfg, objective_neg)

    # 3) 组装候选种子并多启动 Pattern Search 精炼
    K = cfg.refine_topK
    idxD = np.argsort(fpoolD)[:max(2, K//2)]
    idxE = np.argsort(fpopE)[:max(2, K - len(idxD))]
    seeds = np.vstack([poolD[idxD,:], popE[idxE,:]])
    seeds = np.vstack([seeds, xD.reshape(1,-1), xE.reshape(1,-1)])
    # 去重
    uniq = []
    seen = set()
    for s in seeds:
        key = round_key(s)
        if key not in seen:
            seen.add(key); uniq.append(s)
    seeds = np.array(uniq, dtype=float)

    if cfg.verbose:
        print(f"[TOP] seeds into PS: {len(seeds)}")
        update_bar(0, len(seeds), prefix="[PS][Seeds] Overall")

    ps_cfg = PSConfig(init_step=cfg.ps_init_step, min_step=cfg.ps_min_step,
                      shrink=cfg.ps_shrink, max_poll=cfg.ps_max_poll, verbose=False)
    global_best_x = None
    global_best_f = float("inf")
    for k, s in enumerate(seeds, start=1):
        x_ref, f_ref = pattern_search(s, BOUNDS, ps_cfg, objective_neg)
        if f_ref < global_best_f:
            global_best_f, global_best_x = f_ref, x_ref.copy()
        update_bar(k, len(seeds), prefix="[PS][Seeds] Overall")
    finish_bar(prefix="[PS][Seeds] Overall")

    # 4) 输出与审计
    best_duration = float(-global_best_f)
    out = {
        "v_drone": global_best_x[0],
        "theta_drone (rad)": global_best_x[1],
        "theta_drone (deg)": float(np.rad2deg(global_best_x[1])),
        "t_deploy": global_best_x[2],
        "t_fuse": global_best_x[3],
        "duration_s": best_duration
    }
    print("\n=== ULTIMATE GLOBAL BEST ===")
    for k,v in out.items():
        print(f"{k}: {v:.9f}" if isinstance(v, float) else f"{k}: {v}")
    print(f"Evals used: {EVAL_COUNT}, Total time: {time.time()-t0:.1f}s")

    # 审计：输出遮蔽区间与中点裕度
    iv, mids_phi = audit_intervals(global_best_x, ECFG)
    total = sum(b-a for a,b in iv)
    print(f"\n[Audit] 遮蔽区间共 {len(iv)} 段，总时长 ≈ {total:.6f} s")
    for i,(ab,phi) in enumerate(zip(iv, mids_phi), start=1):
        a,b = ab; p1,p2 = phi
        print(f"  段{i}: [{a:.6f}, {b:.6f}]  中点裕度: phi1=θs-αmax={p1:.6e}, phi2={p2:.6e}")

    # 保存
    pd.DataFrame([out]).to_csv("ultimate_best.csv", index=False)
    pd.DataFrame(np.hstack([poolD, fpoolD.reshape(-1,1)]),
                 columns=["v","theta","t_deploy","t_fuse","f(-dur)"]).to_csv("direct_pool.csv", index=False)
    pd.DataFrame(np.hstack([popE, fpopE.reshape(-1,1)]),
                 columns=["v","theta","t_deploy","t_fuse","f(-dur)"]).to_csv("de_pool.csv", index=False)
    print("保存：ultimate_best.csv, direct_pool.csv, de_pool.csv")

# 审计工具
def audit_intervals(xbest: np.ndarray, ecfg: EngineConfig):
    v, th, td, tf = xbest
    v_vec = np.array([v*math.cos(th), v*math.sin(th), 0.0], dtype=float)
    t0 = td + tf; t1 = t0 + OBSCURATION_DURATION
    ts = np.linspace(t0, t1, max(3, ecfg.N_time_coarse))
    def pred(tt):
        return L3_margins_at_time(tt, td, tf, v_vec, ecfg.eps_ang)[0]
    mask = np.array([pred(t) for t in ts], dtype=bool)
    edges = np.nonzero(mask[1:] != mask[:-1])[0] + 1
    cross = [refine_edge_time(ts[i-1], ts[i], pred, tol=ecfg.tol_t) for i in edges]
    cross.sort()
    intervals = []
    state = bool(mask[0]); cur = t0
    for tc in cross:
        if state: intervals.append([cur, tc])
        state = not state; cur = tc
    if state: intervals.append([cur, t1])
    mids = [0.5*(a+b) for a,b in intervals]
    mids_phi = []
    for m in mids:
        ok, phi1, phi2 = L3_margins_at_time(m, td, tf, v_vec, ecfg.eps_ang)
        mids_phi.append((float(phi1), float(phi2)))
    return intervals, mids_phi

# ========================= 主入口 =========================
if __name__ == "__main__":
    cfg = ULTConfig(
        eps_ang=1e-3,
        N_time=601,
        tol_t=1e-3,
        direct_max_evals=20000,
        direct_eps=1e-4,
        direct_split_cap=400,
        de_pop=64,
        de_F=0.7,
        de_CR=0.9,
        de_gens=160,
        refine_topK=30,
        ps_init_step=0.05,
        ps_min_step=5e-5,
        ps_shrink=0.5,
        ps_max_poll=20000,
        verbose=True,
        seed=2025
    )
    run_ultimate(cfg)
