# -*- coding: utf-8 -*-
"""
Q3: 单机三弹，最大化 L3 完整遮蔽时长 —— 轻量创新版
- 判据：严格 L3（角度包含 + 深度先后，带 Δα 上界）
- 输出：控制台打印最佳航迹 + 三枚弹参数 + 遮蔽并集区间
依赖：numpy
"""

import math, sys, time
import numpy as np
from typing import List, Tuple

# ================= 常量定义 =================
g = 9.8

# 导弹
V_M = 300.0
M0 = np.array([20000.0, 0.0, 2000.0])
DM = -M0 / np.linalg.norm(M0)
T_IMPACT = float(np.linalg.norm(M0) / V_M)

# 无人机初始位置（题面 FY1）
F0 = np.array([17800.0, 0.0, 1800.0])

# 烟幕球
R_S = 10.0
SINK_V = 3.0
EFFECT_T = 20.0

# 目标圆柱
R_T, H_T = 7.0, 10.0
TARGET_BASE = np.array([0.0, 200.0, 0.0])

# 参数范围
V_MIN, V_MAX = 70.0, 140.0
TD_MIN, TD_MAX = 0.1, 60.0
TF_MIN, TF_MAX = 0.1, 15.0
DEPLOY_GAP = 1.0

# 判定精度
EPS_ANG = 1e-3
TIME_COARSE = 301
TOL_T = 1e-3

# ================ 基本几何与轨迹 ================
def missile_pos(t: float) -> np.ndarray:
    return M0 + V_M * DM * t

def drone_vel(v: float, theta: float) -> np.ndarray:
    return np.array([v*math.cos(theta), v*math.sin(theta), 0.0])

def cloud_center(t: float, td: float, tf: float, vvec: np.ndarray) -> np.ndarray:
    p_deploy = F0 + vvec * td
    p_detonate = p_deploy + vvec * tf + 0.5*np.array([0.0,0.0,-g])*(tf**2)
    t0 = td + tf
    p = p_detonate + np.array([0.0,0.0,-SINK_V*(t - t0)])
    if p[2] < 0: p[2] = 0.0
    return p

def dist_point_to_capped_cylinder(p: np.ndarray) -> float:
    x,y,z = (p - TARGET_BASE).tolist()
    rho = math.hypot(x,y)
    dr = max(rho - R_T, 0.0)
    if z<0: dz=-z
    elif z>H_T: dz=z-H_T
    else: dz=0.0
    return math.hypot(dr,dz)

def theta_s_from_MC(M: np.ndarray, C: np.ndarray) -> float:
    d = np.linalg.norm(C-M)
    if d <= R_S: return math.pi
    return math.asin(min(1.0,R_S/d))

# ================ 角度上界（αmax+Δα） ================
_grid_cache = {}
def boundary_grid(nth: int, nz: int):
    key=(nth,nz)
    if key in _grid_cache: return _grid_cache[key]
    thetas=np.linspace(0,2*math.pi,nth,endpoint=False)
    zs=np.linspace(0,H_T,nz)
    X=TARGET_BASE[0]+R_T*np.cos(thetas)
    Y=TARGET_BASE[1]+R_T*np.sin(thetas)
    Xg=np.repeat(X,nz); Yg=np.repeat(Y,nz); Zg=np.tile(zs,nth)
    P=np.stack([Xg,Yg,Zg],axis=1)
    _grid_cache[key]=P
    return P

def alpha_max_with_delta(M,C,eps_ang=EPS_ANG,nth0=64,nz0=3):
    dmin=max(1e-9,dist_point_to_capped_cylinder(M))
    nth=nth0; nz=nz0
    P=boundary_grid(nth,nz)
    w=C-M; d=np.linalg.norm(w)
    V=P-M; Vn=np.linalg.norm(V,axis=1)
    cos_a=np.clip((V@w)/(np.maximum(Vn,1e-15)*max(d,1e-15)),-1,1)
    amax=np.max(np.arccos(cos_a))
    dth=2*math.pi/nth; dz=H_T/max(nz-1,1)
    ds=math.hypot(R_T*dth,dz)
    delta=2*math.asin(min(1,ds/(2*dmin)))
    return amax,delta

# ================ 严格 L3 判据（单云单时刻） ================
def L3_ok_at_time(t,td,tf,vvec):
    if t<0 or t>T_IMPACT: return False
    M=missile_pos(t); C=cloud_center(t,td,tf,vvec)
    dmc=np.linalg.norm(C-M)
    if dmc<=R_S: # 云内
        return dist_point_to_capped_cylinder(M)-(dmc-R_S)>=0
    dT=dist_point_to_capped_cylinder(M)
    if dT-(dmc-R_S)<0: return False
    ths=theta_s_from_MC(M,C)
    amax,dalpha=alpha_max_with_delta(M,C)
    return ths-(amax+dalpha)>=0

# ================ 单云区间（事件二分） ================
def single_cloud_intervals(td,tf,vvec):
    t0=td+tf; t1=min(t0+EFFECT_T,T_IMPACT)
    if t1<=t0: return []
    ts=np.linspace(t0,t1,TIME_COARSE)
    pred=lambda tt:L3_ok_at_time(tt,td,tf,vvec)
    mask=np.array([pred(t) for t in ts],dtype=bool)
    edges=np.nonzero(mask[1:]!=mask[:-1])[0]+1
    def refine(a,b):
        fa,fb=pred(a),pred(b)
        if fa==fb: return 0.5*(a+b)
        L,R=a,b
        for _ in range(50):
            m=0.5*(L+R); fm=pred(m)
            if fm==fa: L,fa=m,fm
            else: R,fb=m,fm
            if R-L<=TOL_T: break
        return 0.5*(L+R)
    cuts=[refine(ts[i-1],ts[i]) for i in edges]
    cuts.sort()
    segs=[]; cur=t0; state=mask[0]
    for c in cuts:
        if state: segs.append((cur,c))
        state=not state; cur=c
    if state: segs.append((cur,t1))
    return segs

# ================ 区间并集工具 ================
def union_intervals(intervals: List[Tuple[float,float]]) -> List[Tuple[float,float]]:
    if not intervals: return []
    segs=sorted(intervals)
    out=[list(segs[0])]
    for a,b in segs[1:]:
        if a<=out[-1][1]+1e-9: out[-1][1]=max(out[-1][1],b)
        else: out.append([a,b])
    return [(a,b) for a,b in out]
def total_length(intervals): return sum(b-a for a,b in intervals)

def greedy_three(v,theta,t0_scan,tf_scan):
    vvec=drone_vel(v,theta)
    U=[]; picks=[]
    deploy_times=[]
    for k in range(3):
        best_gain=-1; best=None
        for tf in tf_scan:
            tds=t0_scan-tf
            tds=tds[(tds>=TD_MIN)&(tds<=TD_MAX)]
            for td in tds:
                if any(abs(td-pt)<DEPLOY_GAP for pt in deploy_times): continue
                segs=single_cloud_intervals(td,tf,vvec)
                if not segs: continue
                newU=union_intervals(U+segs)
                gain=total_length(newU)-total_length(U)
                if gain>best_gain:
                    best_gain=gain; best=(td,tf,segs)
        if best:
            td,tf,segs=best
            deploy_times.append(td)
            U=union_intervals(U+segs)
            picks.append({'td':td,'tf':tf,'t0':td+tf})
    return total_length(U),picks,U

# ================ 顶层搜索 ================
def solve_q3():
    speeds=[80.0,110.0,140.0]
    thetas=np.linspace(math.pi-1.0,math.pi+1.0,9)  # 朝 -x 左右 ~114°
    t0_scan=np.linspace(2.0,70.0,101)
    tf_scan=np.linspace(0.5,8.0,30)

    best=-1; best_sol=None
    total=len(speeds)*len(thetas); done=0
    for v in speeds:
        for th in thetas:
            dur,picks,U=greedy_three(v,th,t0_scan,tf_scan)
            done+=1
            if dur>best:
                best=dur; best_sol=(v,th,picks,U)
            if done%5==0: sys.stdout.write(f"\r[Search] {done}/{total} best={best:.3f}s")
    sys.stdout.write("\n")

    v,th,picks,U=best_sol
    print("\n=== Q3 Best (single UAV, 3 bombs) ===")
    print(f"Total L3 duration: {best:.3f} s")
    print(f"v={v:.1f} m/s, theta={th:.3f} rad ({math.degrees(th):.1f} deg)")
    for i,d in enumerate(picks,1):
        print(f" Bomb-{i}: t_deploy={d['td']:.3f}, t_fuse={d['tf']:.3f}, t_detonate={d['t0']:.3f}")
    print("Union intervals:")
    for a,b in U: print(f" [{a:.3f}, {b:.3f}] Δ={b-a:.3f}")

if __name__=="__main__":
    solve_q3()
