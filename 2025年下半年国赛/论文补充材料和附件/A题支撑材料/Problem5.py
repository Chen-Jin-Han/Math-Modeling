# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution, linear_sum_assignment

# =============== 0) 全局参数与复现控制 =================
GLOBAL_DE_SEED = 20250709
DE_STRATEGY    = "best1bin"
DE_WORKERS     = 1
EPS_GAIN       = 1e-9             # 提交增益阈值
PSO_MIN_EFFECT = 0.10             # PSO 非零门槛
PSO_RESTARTS_PER_MISSILE = 4
PSO_MAX_CYCLES = 3

# ============================ 1) 场景参数 =================
TRUE_TARGET = {
    "r": 7,
    "h": 10,
    "center": np.array([0, 200, 0]),
    "sample_points": None
}

MISSILES = {
    "M1": {"init_pos": np.array([20000,     0, 2000]), "dir": None, "flight_time": None},
    "M2": {"init_pos": np.array([19000,   600, 2100]), "dir": None, "flight_time": None},
    "M3": {"init_pos": np.array([18000,  -600, 1900]), "dir": None, "flight_time": None}
}
MISSILE_SPEED = 300  # m/s

G = 9.8
SMOKE_RADIUS = 10
SMOKE_SINK_SPEED = 3
SMOKE_EFFECTIVE_TIME = 20

DRONES = {
    "FY1": {"init_pos": np.array([17800,     0, 1800]), "max_smoke": 3, "speed_range": [70, 140],
            "smokes": [], "speed": None, "direction": None, "optimized": False},
    "FY2": {"init_pos": np.array([12000,  1400, 1400]), "max_smoke": 3, "speed_range": [70, 140],
            "smokes": [], "speed": None, "direction": None, "optimized": False},
    "FY3": {"init_pos": np.array([ 6000, -3000,  700]), "max_smoke": 3, "speed_range": [70, 140],
            "smokes": [], "speed": None, "direction": None, "optimized": False},
    "FY4": {"init_pos": np.array([11000,  2000, 1800]), "max_smoke": 3, "speed_range": [70, 140],
            "smokes": [], "speed": None, "direction": None, "optimized": False},
    "FY5": {"init_pos": np.array([13000, -2000, 1300]), "max_smoke": 3, "speed_range": [70, 140],
            "smokes": [], "speed": None, "direction": None, "optimized": False}
}
DROP_INTERVAL = 1.0
TIME_STEP = 0.1

# ============================ 1.1) 采样与导弹初始化 =========
def generate_true_target_samples():
    samples = []
    r, h, center = TRUE_TARGET["r"], TRUE_TARGET["h"], TRUE_TARGET["center"]

    # bottom
    samples.append(center)
    for theta in np.linspace(0, 2*np.pi, 15):
        x = center[0] + r*np.cos(theta)
        y = center[1] + r*np.sin(theta)
        samples.append(np.array([x, y, center[2]]))

    # top
    top_center = center + np.array([0, 0, h])
    samples.append(top_center)
    for theta in np.linspace(0, 2*np.pi, 15):
        x = top_center[0] + r*np.cos(theta)
        y = top_center[1] + r*np.sin(theta)
        samples.append(np.array([x, y, top_center[2]]))

    # side
    for z in np.linspace(center[2], top_center[2], 5):
        for theta in np.linspace(0, 2*np.pi, 12):
            x = center[0] + r*np.cos(theta)
            y = center[1] + r*np.sin(theta)
            samples.append(np.array([x, y, z]))

    TRUE_TARGET["sample_points"] = np.array(samples, dtype=float)

def init_missiles():
    for m_name, m_data in MISSILES.items():
        init_pos = m_data["init_pos"]
        dir_vec = -init_pos / np.linalg.norm(init_pos)
        m_data["dir"] = dir_vec * MISSILE_SPEED
        m_data["flight_time"] = float(np.linalg.norm(init_pos) / MISSILE_SPEED)

generate_true_target_samples()
init_missiles()

# ============================ 2) 运动学/几何 =========
def get_missile_pos(m_name, t):
    m_data = MISSILES[m_name]
    if t > m_data["flight_time"]:
        return m_data["init_pos"] + m_data["dir"] * m_data["flight_time"]
    return m_data["init_pos"] + m_data["dir"] * t

def get_drone_pos(drone_name, t):
    drone = DRONES[drone_name]
    if drone["speed"] is None or drone["direction"] is None:
        return drone["init_pos"]
    v_vec = np.array([
        drone["speed"] * np.cos(drone["direction"]),
        drone["speed"] * np.sin(drone["direction"]),
        0.0
    ])
    return drone["init_pos"] + v_vec * t

def get_smoke_pos(drone_name, drop_time, det_delay, t):
    drone = DRONES[drone_name]
    if t < drop_time:
        return None
    drop_pos = get_drone_pos(drone_name, drop_time)

    if t < drop_time + det_delay:
        dt = t - drop_time
        vx = drone["speed"] * np.cos(drone["direction"])
        vy = drone["speed"] * np.sin(drone["direction"])
        x = drop_pos[0] + vx * dt
        y = drop_pos[1] + vy * dt
        z = drop_pos[2] - 0.5 * G * dt*dt
        return np.array([x, y, max(z, 0.1)])

    det_time = drop_time + det_delay
    if t > det_time + SMOKE_EFFECTIVE_TIME:
        return None

    vx = drone["speed"] * np.cos(drone["direction"])
    vy = drone["speed"] * np.sin(drone["direction"])
    det_x = drop_pos[0] + vx * det_delay
    det_y = drop_pos[1] + vy * det_delay
    det_z = drop_pos[2] - 0.5 * G * det_delay*det_delay
    if det_z < 0:
        det_z = 0.1

    z = det_z - SMOKE_SINK_SPEED * (t - det_time)
    return np.array([det_x, det_y, max(z, 0.1)])

def segment_sphere_intersect(p1, p2, center, radius):
    vec_p = p2 - p1
    vec_c = center - p1
    denom = np.dot(vec_p, vec_p) + 1e-8
    t = float(np.dot(vec_c, vec_p) / denom)
    if 0.0 <= t <= 1.0:
        nearest = p1 + t * vec_p
    else:
        nearest = p1 if t < 0.0 else p2
    return np.linalg.norm(nearest - center) <= (radius + 1e-8)

# ============================ 3) 评分 =========
def calc_smoke_effective_time(drone_name, m_name, drop_time, det_delay):
    drone = DRONES[drone_name]
    v, theta = drone["speed"], drone["direction"]
    if v is None or theta is None:
        return -1000.0
    if not (drone["speed_range"][0] - 1e-3 <= v <= drone["speed_range"][1] + 1e-3):
        return -1000.0

    det_time = drop_time + det_delay
    drop_pos = get_drone_pos(drone_name, drop_time)
    det_z = drop_pos[2] - 0.5 * G * det_delay*det_delay
    if det_z < -0.5:
        return -1000.0

    for s in drone["smokes"]:
        if abs(drop_time - s["drop_time"]) < (DROP_INTERVAL - 0.1):
            return -1000.0

    max_t = min(det_time + SMOKE_EFFECTIVE_TIME, MISSILES[m_name]["flight_time"] + 1.0)
    min_t = max(det_time, 0.0)
    if min_t >= max_t - 1e-3:
        return 0.0

    eff = 0.0
    for t in np.arange(min_t, max_t, TIME_STEP):
        m_pos = get_missile_pos(m_name, t)
        smoke_pos = get_smoke_pos(drone_name, drop_time, det_delay, t)
        if smoke_pos is None:
            continue
        blocked = True
        for sample in TRUE_TARGET["sample_points"]:
            if not segment_sphere_intersect(m_pos, sample, smoke_pos, SMOKE_RADIUS):
                blocked = False
                break
        if blocked:
            eff += TIME_STEP
    return eff

# ============= 3.1) 总和/快照/提交 ============
def total_effective_time_drone(d_name):
    return float(sum(s["effective_time"] for s in DRONES[d_name]["smokes"]))

def total_effective_time_all():
    return float(sum(total_effective_time_drone(d) for d in DRONES))

def snapshot_drone(d_name):
    d = DRONES[d_name]
    return {"speed": d["speed"], "direction": d["direction"], "smokes": [dict(s) for s in d["smokes"]]}

def restore_drone(d_name, snap):
    DRONES[d_name]["speed"] = snap["speed"]
    DRONES[d_name]["direction"] = snap["direction"]
    DRONES[d_name]["smokes"] = snap["smokes"]

def commit_append_if_gain(drone_name, cand):
    """追加一枚；增益>0才提交"""
    d = DRONES[drone_name]
    snap = snapshot_drone(drone_name)
    before = total_effective_time_drone(drone_name)

    # 若是首枚，设置速度与方向
    first = (len(d["smokes"]) == 0)
    if first:
        d["speed"] = float(cand["v"])
        d["direction"] = float(cand["theta"])

    rec = dict(cand)
    rec["det_pos"] = get_smoke_pos(drone_name, rec["drop_time"], rec["det_delay"], rec["det_time"])
    d["smokes"].append(rec)

    after = total_effective_time_drone(drone_name)
    gain = after - before
    if gain > EPS_GAIN:
        return True, gain
    else:
        restore_drone(drone_name, snap)
        return False, 0.0

def commit_replace_if_gain(drone_name, idx, cand):
    """替换第 idx 枚（就地精修）；增益>0才提交"""
    d = DRONES[drone_name]
    snap = snapshot_drone(drone_name)
    before = total_effective_time_drone(drone_name)

    rec = dict(cand)
    rec["det_pos"] = get_smoke_pos(drone_name, rec["drop_time"], rec["det_delay"], rec["det_time"])
    d["smokes"][idx] = rec

    after = total_effective_time_drone(drone_name)
    gain = after - before
    if gain > EPS_GAIN:
        return True, gain
    else:
        restore_drone(drone_name, snap)
        return False, 0.0

# ============================ 4) 任务分配 ===========
def assign_tasks(drones_list):
    missile_list = list(MISSILES.keys())
    if not drones_list:
        return {m: [] for m in missile_list}

    n_d = len(drones_list)
    n_m = len(missile_list)
    cost = np.zeros((n_d, n_m))
    for i, d_name in enumerate(drones_list):
        d_init = DRONES[d_name]["init_pos"]
        d_avg_v = sum(DRONES[d_name]["speed_range"]) / 2.0
        for j, m_name in enumerate(missile_list):
            m_init = MISSILES[m_name]["init_pos"]
            tf = MISSILES[m_name]["flight_time"]
            dist = np.linalg.norm(d_init - m_init)
            c1 = dist / d_avg_v
            c2 = 1000.0 / (tf + 1.0)
            c3 = abs(d_avg_v - MISSILE_SPEED) / 100.0
            cost[i, j] = c1 + c2 + c3
    r, c = linear_sum_assignment(cost)
    assign = {m: [] for m in missile_list}
    for i, j in zip(r, c):
        assign[missile_list[j]].append(drones_list[i])
    assigned_rows = set(r)
    for i in range(n_d):
        if i not in assigned_rows:
            j = int(np.argmin(cost[i]))
            assign[missile_list[j]].append(drones_list[i])
    return assign

def missile_order_for_drone(preferred):
    others = [m for m in ["M1", "M2", "M3"] if m != preferred]
    return [preferred] + others

# ============================ 5) DE 求解器 ==========
def _de(obj, bounds, seed_bump=0, maxiter=80, popsize=60, mutation=0.8, recombination=0.9):
    return differential_evolution(
        func=obj,
        bounds=bounds,
        strategy=DE_STRATEGY,
        maxiter=maxiter,
        popsize=popsize,
        mutation=mutation,
        recombination=recombination,
        tol=1e-3,
        polish=True,
        seed=int(GLOBAL_DE_SEED + seed_bump),
        workers=DE_WORKERS,
        updating="deferred" if DE_WORKERS != 1 else "immediate"
    )

def de_first_smoke(drone_name, m_name, seed_bump=0):
    d = DRONES[drone_name]
    vmin, vmax = d["speed_range"]
    tf = MISSILES[m_name]["flight_time"]

    def objective(x):
        v, th, tdrop, ddel = x
        bak_v, bak_th = d["speed"], d["direction"]
        d["speed"], d["direction"] = float(v), float(th)
        val = -calc_smoke_effective_time(drone_name, m_name, float(tdrop), float(ddel))
        d["speed"], d["direction"] = bak_v, bak_th
        return val

    bounds = [
        (vmin*0.8, vmax*1.2),
        (0.0, 2*np.pi),
        (0.0, max(0.0, tf - 0.1)),
        (0.10, 20.0),
    ]
    res = _de(objective, bounds, seed_bump=seed_bump)
    v, th, tdrop, ddel = res.x
    eff = -float(res.fun)
    return {
        "v": float(np.clip(v, vmin, vmax)),
        "theta": float(th),
        "drop_time": float(tdrop),
        "det_delay": float(ddel),
        "det_time": float(tdrop + ddel),
        "det_pos": None,
        "effective_time": float(eff),
        "missile": m_name
    }

def de_next_smoke(drone_name, m_name, min_drop_time, seed_bump=0):
    d = DRONES[drone_name]
    if d["speed"] is None or d["direction"] is None:
        return None
    tf = MISSILES[m_name]["flight_time"]
    low = float(min_drop_time)
    high = float(max(0.0, tf - 0.1))
    if low >= high - 1e-9:
        return None

    def objective(x):
        tdrop, ddel = x
        return -calc_smoke_effective_time(drone_name, m_name, float(tdrop), float(ddel))

    bounds = [(low, high), (0.10, 20.0)]
    res = _de(objective, bounds, seed_bump=seed_bump, maxiter=60, popsize=50, mutation=0.7, recombination=0.8)
    tdrop, ddel = res.x
    eff = -float(res.fun)
    return {
        "v": float(d["speed"]),
        "theta": float(d["direction"]),
        "drop_time": float(tdrop),
        "det_delay": float(ddel),
        "det_time": float(tdrop + ddel),
        "det_pos": None,
        "effective_time": float(eff),
        "missile": m_name
    }

def de_refine_existing(drone_name, idx, seed_bump=0):
    """就地精修第 idx 枚：仅优化 drop_time / det_delay，速度与方向不变，且受相邻边界约束。"""
    d = DRONES[drone_name]
    k = idx
    s = d["smokes"][k]
    m = s["missile"]

    # 左右邻的时间边界
    left_min = 0.0 if k == 0 else d["smokes"][k-1]["drop_time"] + DROP_INTERVAL
    right_max_by_neighbor = (MISSILES[m]["flight_time"] - 0.1) if k == len(d["smokes"])-1 else (d["smokes"][k+1]["drop_time"] - DROP_INTERVAL)
    low = max(0.0, left_min)
    high = min(MISSILES[m]["flight_time"] - 0.1, right_max_by_neighbor)
    if low >= high - 1e-9:
        return None  # 无可行时间窗

    def objective(x):
        tdrop, ddel = x
        return -calc_smoke_effective_time(drone_name, m, float(tdrop), float(ddel))

    # 以当前值为中心，允许在合法窗内自由搜索
    bounds = [(low, high), (0.10, 20.0)]
    res = _de(objective, bounds, seed_bump=seed_bump, maxiter=40, popsize=50, mutation=0.6, recombination=0.85)
    tdrop, ddel = res.x
    eff = -float(res.fun)
    return {
        "v": float(d["speed"]),
        "theta": float(d["direction"]),
        "drop_time": float(tdrop),
        "det_delay": float(ddel),
        "det_time": float(tdrop + ddel),
        "det_pos": None,
        "effective_time": float(eff),
        "missile": m
    }

# ============================ 6) PSO 回填（仅首枚） ==========
STRICT_SAMPLES = None
STRICT_CENTER = None

def generate_strict_samples():
    global STRICT_SAMPLES, STRICT_CENTER
    pts = []
    r, h = float(TRUE_TARGET["r"]), float(TRUE_TARGET["h"])
    cx, cy, z0 = map(float, TRUE_TARGET["center"])
    bottom_center = np.array([cx, cy, z0], dtype=float)
    top_center    = np.array([cx, cy, z0 + h], dtype=float)
    STRICT_CENTER = 0.5 * (bottom_center + top_center)
    pts.append(bottom_center); pts.append(top_center)
    for th in np.linspace(0, 2*np.pi, 32, endpoint=False):
        pts.append(np.array([cx + r*np.cos(th), cy + r*np.sin(th), z0], dtype=float))
        pts.append(np.array([cx + r*np.cos(th), cy + r*np.sin(th), z0 + h], dtype=float))
    for z in np.linspace(z0, z0 + h, 9):
        for th in np.linspace(0, 2*np.pi, 24, endpoint=False):
            pts.append(np.array([cx + r*np.cos(th), cy + r*np.sin(th), z], dtype=float))
    for z in np.linspace(z0, z0 + h, 5):
        for rho in np.linspace(0.0, r*0.95, 5):
            for th in np.linspace(0, 2*np.pi, 24, endpoint=False):
                pts.append(np.array([cx + rho*np.cos(th), cy + rho*np.sin(th), z], dtype=float))
    STRICT_SAMPLES = np.array(pts, dtype=float)

generate_strict_samples()

def analytic_segment_sphere_intersect(p1, p2, center, radius):
    u = p2 - p1
    oc = p1 - center
    a = float(np.dot(u, u)) + 1e-18
    b = 2.0 * float(np.dot(u, oc))
    c = float(np.dot(oc, oc)) - radius * radius
    disc = b*b - 4*a*c
    if disc < 0.0:
        return False
    sq = np.sqrt(disc)
    t1 = (-b - sq) / (2*a)
    t2 = (-b + sq) / (2*a)
    t_enter = min(t1, t2); t_exit = max(t1, t2)
    return (t_exit >= -1e-12) and (t_enter <= 1.0 + 1e-12)

def strict_center_quick(m_pos, smoke_pos):
    return analytic_segment_sphere_intersect(m_pos, STRICT_CENTER, smoke_pos, SMOKE_RADIUS)

def strict_is_blocked_all(m_pos, smoke_pos):
    if smoke_pos is None: return False
    if smoke_pos[2] <= 2.0: return False
    if not strict_center_quick(m_pos, smoke_pos): return False
    for p in STRICT_SAMPLES:
        if not analytic_segment_sphere_intersect(m_pos, p, smoke_pos, SMOKE_RADIUS):
            return False
    return True

def _get_smoke_pos_strict(drone_name, drop_time, det_delay, t, v, th):
    d0 = DRONES[drone_name]["init_pos"]
    if t < drop_time: return None
    vx, vy = v*np.cos(th), v*np.sin(th)
    drop_pos = d0 + np.array([vx*drop_time, vy*drop_time, 0.0])
    if t < drop_time + det_delay:
        dt = t - drop_time
        x = drop_pos[0] + vx*dt; y = drop_pos[1] + vy*dt
        z = drop_pos[2] - 0.5*G*dt*dt
        return np.array([x, y, max(z, 1e-6)])
    det_t = drop_time + det_delay
    if t > det_t + SMOKE_EFFECTIVE_TIME: return None
    det_x = drop_pos[0] + vx*det_delay
    det_y = drop_pos[1] + vy*det_delay
    det_z = drop_pos[2] - 0.5*G*det_delay*det_delay
    if det_z < 0.0: det_z = 1e-6
    z = det_z - SMOKE_SINK_SPEED*(t-det_t)
    return np.array([det_x, det_y, max(z, 1e-6)])

def calc_effect_strict_pso(drone_name, m_name, v, th, tdrop, ddel):
    vmin, vmax = DRONES[drone_name]["speed_range"]
    if not (vmin*0.8 <= v <= vmax*1.2): return -1e6
    d0 = DRONES[drone_name]["init_pos"]
    vx, vy = v*np.cos(th), v*np.sin(th)
    drop_pos = d0 + np.array([vx*tdrop, vy*tdrop, 0.0])
    det_z = drop_pos[2] - 0.5*G*ddel*ddel
    if det_z < 5.0: return 0.0
    det_t = tdrop + ddel
    t0 = max(det_t, 0.0); t1 = min(det_t + SMOKE_EFFECTIVE_TIME, MISSILES[m_name]["flight_time"] + 1.0)
    if t1 <= t0: return 0.0
    dt1, dt2 = 0.02, 0.1
    split = min(t0 + 2.0, t1)
    eff = 0.0
    t = t0
    while t < split - 1e-12:
        m_pos = get_missile_pos(m_name, t)
        s_pos = _get_smoke_pos_strict(drone_name, tdrop, ddel, t, v, th)
        if strict_is_blocked_all(m_pos, s_pos): eff += dt1
        t += dt1
    t = split
    while t < t1 - 1e-12:
        m_pos = get_missile_pos(m_name, t)
        s_pos = _get_smoke_pos_strict(drone_name, tdrop, ddel, t, v, th)
        if strict_is_blocked_all(m_pos, s_pos): eff += dt2
        t += dt2
    return eff

def pso_first_smoke_once(drone_name, m_name, seed_base):
    vmin, vmax = DRONES[drone_name]["speed_range"]
    tf = MISSILES[m_name]["flight_time"]
    bounds = np.array([
        [0.0, 2*np.pi],
        [vmin*0.8, vmax*1.2],
        [0.0, max(0.0, tf - 0.1)],
        [0.10, 10.0],
    ], dtype=float)
    rng = np.random.default_rng(seed_base)
    n_particles, iters = 40, 50
    w, c1, c2 = 0.72, 1.49, 1.49
    pos = bounds[:,0] + (bounds[:,1] - bounds[:,0]) * rng.random((n_particles, 4))
    vel = np.zeros_like(pos)

    def fit(x):
        th, v, tdrop, ddel = x
        return -calc_effect_strict_pso(drone_name, m_name, float(v), float(th), float(tdrop), float(ddel))

    pbest = pos.copy()
    pbest_val = np.array([fit(p) for p in pos])
    gidx = int(np.argmin(pbest_val))
    gbest = pbest[gidx].copy(); gbest_val = pbest_val[gidx]

    for _ in range(iters):
        r1 = rng.random(pos.shape); r2 = rng.random(pos.shape)
        vel = w*vel + c1*r1*(pbest - pos) + c2*r2*(gbest - pos)
        pos = pos + vel
        pos = np.maximum(pos, bounds[:,0]); pos = np.minimum(pos, bounds[:,1])
        vals = np.array([fit(p) for p in pos])
        improved = vals < pbest_val
        pbest[improved] = pos[improved]; pbest_val[improved] = vals[improved]
        gidx = int(np.argmin(pbest_val))
        if pbest_val[gidx] < gbest_val - 1e-12:
            gbest = pbest[gidx].copy(); gbest_val = pbest_val[gidx]

    th, v, tdrop, ddel = gbest[0], gbest[1], gbest[2], gbest[3]
    eff = -gbest_val
    if eff <= PSO_MIN_EFFECT: return False
    cand = {
        "v": float(np.clip(v, vmin, vmax)), "theta": float(th),
        "drop_time": float(tdrop), "det_delay": float(ddel),
        "det_time": float(tdrop + ddel), "det_pos": None,
        "effective_time": float(eff), "missile": m_name
    }
    ok, _ = commit_append_if_gain(drone_name, cand)
    return ok

def pso_first_smoke_with_restarts(drone_name, m_name, base_seed):
    for r in range(PSO_RESTARTS_PER_MISSILE):
        seed = int(base_seed + r*97)
        if pso_first_smoke_once(drone_name, m_name, seed):
            return True
    return False

def fallback_with_pso_for_uncovered(uncovered):
    missiles = ["M1", "M2", "M3"]
    for d_name in uncovered:
        print(f"\n[PSO 严格回填] 处理 {d_name} ...")
        ok_any = False
        for cyc in range(1, PSO_MAX_CYCLES + 1):
            if ok_any: break
            print(f"  回填循环 {cyc}/{PSO_MAX_CYCLES}")
            base_seed = 2025 + cyc*1000
            for j, m in enumerate(missiles):
                if len(DRONES[d_name]["smokes"]) > 0:
                    ok_any = True; break
                cur_seed = base_seed + j*311
                ok = pso_first_smoke_with_restarts(d_name, m, cur_seed)
                if ok:
                    print(f"    + 接受 {d_name} 针对 {m} 的 1 枚（PSO，非零增益）")
                    ok_any = True; break
                else:
                    print(f"    - {d_name} 针对 {m} 未达到非零门槛，继续回填")
        if not ok_any:
            print(f"  ! {d_name} 回填失败（已达回填循环上限）")

# ============================ 7) 工具：时间顺序 ==========
def min_next_drop_time(drone_name):
    d = DRONES[drone_name]
    if not d["smokes"]:
        return 0.0
    last = max(s["drop_time"] for s in d["smokes"])
    return float(last + DROP_INTERVAL)

# ============================ 8) 每轮对单 UAV 的流程 ==========
def process_one_drone_in_iteration(drone_name, preferred_missile, seed_bump_iter):
    """
    返回 (是否有增益, 本轮对该 UAV 的增益, 成功追加的枚数)
    步骤：
      1) 先就地精修已提交弹（按序 0..k-1）。
      2) 再在末尾串行追加：成功就继续追加，直到达到配额或本轮该 UAV 无增益。
    """
    d = DRONES[drone_name]
    improved = False
    gain_total = 0.0
    appended_cnt = 0

    # 1) 已有弹就地精修（仅 drop_time / det_delay）
    for idx in range(len(d["smokes"])):
        cand = de_refine_existing(drone_name, idx, seed_bump=seed_bump_iter + idx)
        if cand is None:
            continue
        ok, g = commit_replace_if_gain(drone_name, idx, cand)
        if ok:
            improved = True
            gain_total += g
            print(f"  [{drone_name}] 精修第{idx+1}枚 +{g:.2f}s")
        else:
            print(f"  [{drone_name}] 精修第{idx+1}枚 无增益")

    # 2) 在末尾串行追加，直到达到配额或无增益为止
    while len(d["smokes"]) < d["max_smoke"]:
        seed_offset = seed_bump_iter + 100 + appended_cnt
        # 先用首选导弹，再按其他导弹
        for m in missile_order_for_drone(preferred_missile):
            if len(d["smokes"]) == 0:
                cand = de_first_smoke(drone_name, m, seed_bump=seed_offset)
            else:
                cand = de_next_smoke(drone_name, m, min_next_drop_time(drone_name), seed_bump=seed_offset)
            if cand is None:
                continue
            ok, g = commit_append_if_gain(drone_name, cand)
            if ok:
                improved = True
                gain_total += g
                appended_cnt += 1
                print(f"  [{drone_name}] 追加 1 枚（{m}）+{g:.2f}s，已投 {len(d['smokes'])}/{d['max_smoke']}")
                break
        else:
            # 所有导弹都未产生增益，停止对该 UAV 的追加
            break

    return improved, gain_total, appended_cnt

# ============================ 9) 主循环（新终止逻辑） ==========
def iterative_optimization(max_iterations=20, no_improve_stop_rounds=3):
    # 清零
    for d_name in DRONES:
        DRONES[d_name]["optimized"] = False
        DRONES[d_name]["smokes"]   = []
        DRONES[d_name]["speed"]    = None
        DRONES[d_name]["direction"]= None

    prev_total = 0.0
    stall_rounds = 0

    for it in range(1, max_iterations+1):
        print(f"\n===== 迭代 {it}/{max_iterations} =====")

        # 分配：对“未达配额”的 UAV 做调度
        drones_need_more = [d for d in DRONES if len(DRONES[d]["smokes"]) < DRONES[d]["max_smoke"]]
        assignments = assign_tasks(drones_need_more)

        improved_any = False
        iter_gain = 0.0
        iter_appended = 0

        for m_name, drones in assignments.items():
            for d_name in drones:
                improved, g, appended = process_one_drone_in_iteration(
                    d_name, preferred_missile=m_name, seed_bump_iter=it*1000
                )
                improved_any |= improved
                iter_gain += g
                iter_appended += appended

        total_now = total_effective_time_all()
        print(f"本轮增益: {iter_gain:.2f}s | 当前总遮蔽时长: {total_now:.2f}s | 本轮新增弹数: {iter_appended}")
        all_count = sum(len(DRONES[d]["smokes"]) for d in DRONES)
        print(f"累计投放进度: {all_count}/15")

        # 终止条件：仅当“全 15 枚已投完 且 连续 no_improve_stop_rounds 轮无增益”
        if improved_any:
            stall_rounds = 0
        else:
            stall_rounds += 1

        if all_count == sum(DRONES[d]["max_smoke"] for d in DRONES):
            if stall_rounds >= no_improve_stop_rounds:
                print(f"全部 15 枚已投完，且连续 {no_improve_stop_rounds} 轮无增益，停止迭代。")
                break

        prev_total = total_now

    # 20 轮后若仍有 0 枚的 UAV，触发 PSO 回填（非零门槛）
    remaining_zero = [d for d in DRONES if len(DRONES[d]["smokes"]) == 0]
    if remaining_zero:
        print("\n=== 触发 PSO 严格回填（仅 0 枚的 UAV；非零门槛） ===")
        fallback_with_pso_for_uncovered(remaining_zero)

    # 汇总
    all_smokes = []
    for d_name, d_data in DRONES.items():
        all_smokes.extend([{**s, "drone": d_name} for s in d_data["smokes"]])
    return all_smokes

# ============================ 10) 输出与可视化 ==========
def save_result(smokes, filename="result3.xlsx"):
    rows = []
    for idx, s in enumerate(smokes, 1):
        drop_pos = get_drone_pos(s["drone"], s["drop_time"])
        det_pos  = s["det_pos"] if s["det_pos"] is not None else np.array([0.0, 0.0, 0.0])
        rows.append({
            "无人机编号": s["drone"],
            "无人机运动方向": round(np.degrees(s["theta"]), 2),
            "无人机运动速度 (m/s)": round(s["v"], 2),
            "烟幕干扰弹编号": idx,
            "烟幕干扰弹投放点的x坐标 (m)": round(float(drop_pos[0]), 2),
            "烟幕干扰弹投放点的y坐标 (m)": round(float(drop_pos[1]), 2),
            "烟幕干扰弹投放点的z坐标 (m)": round(float(drop_pos[2]), 2),
            "烟幕干扰弹起爆点的x坐标 (m)": round(float(det_pos[0]), 2),
            "烟幕干扰弹起爆点的y坐标 (m)": round(float(det_pos[1]), 2),
            "烟幕干扰弹起爆点的z坐标 (m)": round(float(det_pos[2]), 2),
            "有效干扰时长 (s)": round(float(s["effective_time"]), 2),
            "干扰的导弹编号": s["missile"],
        })
    cols = [
        "无人机编号","无人机运动方向","无人机运动速度 (m/s)","烟幕干扰弹编号",
        "烟幕干扰弹投放点的x坐标 (m)","烟幕干扰弹投放点的y坐标 (m)","烟幕干扰弹投放点的z坐标 (m)",
        "烟幕干扰弹起爆点的x坐标 (m)","烟幕干扰弹起爆点的y坐标 (m)","烟幕干扰弹起爆点的z坐标 (m)",
        "有效干扰时长 (s)","干扰的导弹编号"
    ]
    df = pd.DataFrame(rows, columns=cols)
    df.to_excel(filename, index=False, engine="openpyxl")
    print(f"结果已保存到 {filename}")
    return df

def visualize_result(smokes):
    if not smokes:
        print("无有效数据可可视化"); return
    plt.rcParams["font.sans-serif"] = ["SimHei"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    theta = np.linspace(0, 2*np.pi, 100)
    x_circle = TRUE_TARGET["center"][0] + TRUE_TARGET["r"] * np.cos(theta)
    y_circle = TRUE_TARGET["center"][1] + TRUE_TARGET["r"] * np.sin(theta)
    ax1.plot(x_circle, y_circle, "r-", label="真目标投影")
    ax1.scatter(TRUE_TARGET["center"][0], TRUE_TARGET["center"][1], c="r", marker="*", s=200, label="真目标中心")

    colors = ["red", "green", "blue"]
    for i, (m_name, m_data) in enumerate(MISSILES.items()):
        t_range = np.linspace(0, m_data["flight_time"], 100)
        pos_list = [get_missile_pos(m_name, t)[:2] for t in t_range]
        pos_arr = np.array(pos_list)
        ax1.plot(pos_arr[:, 0], pos_arr[:, 1], f"{colors[i]}--", label=f"{m_name}轨迹")
        ax1.scatter(m_data["init_pos"][0], m_data["init_pos"][1], c=colors[i], s=100, label=f"{m_name}初始位置")

    drone_colors = ["orange", "purple", "cyan", "magenta", "brown"]
    for i, (d_name, d_data) in enumerate(DRONES.items()):
        if not d_data["smokes"]: continue
        last_smoke = d_data["smokes"][-1]
        t_range = np.linspace(0, last_smoke["drop_time"], 50)
        if d_data["speed"] is not None and d_data["direction"] is not None:
            v_vec = np.array([d_data["speed"]*np.cos(d_data["direction"]),
                              d_data["speed"]*np.sin(d_data["direction"]), 0.0])
        else:
            v_vec = np.array([0.0, 0.0, 0.0])
        pos_arr = np.array([d_data["init_pos"] + v_vec * t for t in t_range])
        ax1.plot(pos_arr[:, 0], pos_arr[:, 1], f"{drone_colors[i]}-", label=f"{d_name}轨迹")
        ax1.scatter(d_data["init_pos"][0], d_data["init_pos"][1], c=drone_colors[i], s=100, marker="^", label=f"{d_name}初始位置")
        for s in d_data["smokes"]:
            if s["det_pos"] is not None:
                ax1.scatter(s["det_pos"][0], s["det_pos"][1], c=drone_colors[i], s=50, alpha=0.7)
                circle = plt.Circle((s["det_pos"][0], s["det_pos"][1]), SMOKE_RADIUS, color=drone_colors[i], alpha=0.2)
                ax1.add_patch(circle)

    ax1.set_xlabel("X(m)"); ax1.set_ylabel("Y(m)")
    ax1.set_title("无人机、导弹轨迹及烟幕起爆点")
    ax1.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    ax1.grid(True, alpha=0.3)

    missile_effect = {m: 0.0 for m in MISSILES.keys()}
    for s in smokes:
        missile_effect[s["missile"]] += s["effective_time"]
    ax2.bar(missile_effect.keys(), missile_effect.values(), color=colors)
    ax2.set_xlabel("导弹编号"); ax2.set_ylabel("总遮蔽时长(s)")
    ax2.set_title("各导弹总遮蔽时长")
    for m, t in missile_effect.items():
        ax2.text(m, t + 0.5, f"{t:.1f}s", ha="center")

    drone_smoke_count = {d: len(DRONES[d]["smokes"]) for d in DRONES.keys()}
    ax3.bar(drone_smoke_count.keys(), drone_smoke_count.values(), color=drone_colors)
    ax3.set_xlabel("无人机编号"); ax3.set_ylabel("烟幕弹数量")
    ax3.set_title("各无人机烟幕弹投放数量")
    for d, cnt in drone_smoke_count.items():
        ax3.text(d, cnt + 0.05, str(cnt), ha="center")

    effect_times = [s["effective_time"] for s in smokes]
    ax4.hist(effect_times, bins=10, color="skyblue", edgecolor="black", alpha=0.7)
    ax4.set_xlabel("单烟幕弹遮蔽时长(s)"); ax4.set_ylabel("烟幕弹数量")
    ax4.set_title("单烟幕弹遮蔽时长分布")
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("smoke_optimization_visualization.png", dpi=300, bbox_inches="tight")
    plt.show()

# ============================ 11) main =======================
if __name__ == "__main__":
    all_smokes = iterative_optimization(max_iterations=50, no_improve_stop_rounds=3)

    if all_smokes:
        _df = save_result(all_smokes, filename="result3.xlsx")
        visualize_result(all_smokes)

        print("\n" + "="*50)
        print("最终结果汇总：")
        print(f"总烟幕弹数量：{len(all_smokes)}")
        print(f"总遮蔽时长：{sum([s['effective_time'] for s in all_smokes]):.2f}s")
        print("\n各无人机投放详情：")
        for d_name, d_data in DRONES.items():
            if d_data["smokes"]:
                total = sum([s["effective_time"] for s in d_data["smokes"]])
                print(f"{d_name}：{len(d_data['smokes'])}枚弹，总遮蔽时长{total:.2f}s")
            else:
                print(f"{d_name}：未找到有效投放方案")
        print("="*50)
    else:
        print("未找到有效的烟幕弹投放方案")

