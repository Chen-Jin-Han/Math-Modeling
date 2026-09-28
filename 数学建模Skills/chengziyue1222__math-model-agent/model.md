# 数学模型：波浪能最大输出功率

## 一、模型假设

1. 波浪为规则线性波（Airy 波），波形为正弦
2. 浮子做垂荡运动（一维上下运动）
3. 浮子为圆柱形，完全浸没部分为圆柱
4. 流体为不可压缩、无粘、无旋的理想流体
5. 运动为小振幅（线性化假设）
6. 能量输出系统为弹簧-阻尼器模型

## 二、符号说明

| 符号 | 含义 | 单位 |
|------|------|------|
| $H$ | 波高 | m |
| $T$ | 波浪周期 | s |
| $h$ | 水深 | m |
| $r$ | 浮子半径 | m |
| $d$ | 浮子吃水深度 | m |
| $\rho$ | 海水密度 (1025) | kg/m³ |
| $g$ | 重力加速度 (9.8) | m/s² |
| $m$ | 浮子质量 | kg |
| $m_a$ | 附加质量 | kg |
| $c_r$ | 辐射阻尼系数 | N·s/m |
| $k_s$ | 弹簧刚度 | N/m |
| $c_d$ | 阻尼器系数 | N·s/m |
| $z(t)$ | 浮子垂荡位移 | m |
| $z_w(t)$ | 波面位移 | m |
| $\omega$ | 波浪角频率 | rad/s |
| $k_w$ | 波数 | rad/m |
| $P$ | 平均输出功率 | W |

## 三、模型建立

### 3.1 波浪运动模型

波浪角频率：
$$\omega = \frac{2\pi}{T} \tag{1}$$

色散关系（深水近似）：
$$\omega^2 = g k_w \tanh(k_w h) \tag{2}$$

波面位移：
$$z_w(t) = \frac{H}{2} \cos(\omega t) \tag{3}$$

### 3.2 浮子受力分析

浮子受到以下力：
1. **重力**：$F_g = -mg$
2. **静水恢复力**：$F_s = -\rho g \pi r^2 z$
3. **入射波浪力**（F-K 力）：$F_{FK} = \rho g \pi r^2 \frac{H}{2} \frac{\sinh(k_w d)}{\cosh(k_w h)}$
4. **辐射力**：$F_r = -m_a \ddot{z} - c_r \dot{z}$
5. **弹簧力**：$F_{ks} = -k_s z$
6. **阻尼力**：$F_{cd} = -c_d \dot{z}$

### 3.3 垂荡运动方程

根据牛顿第二定律：
$$(m + m_a)\ddot{z} + (c_r + c_d)\dot{z} + (k_s + \rho g \pi r^2)z = F_{FK} \cos(\omega t) \tag{4}$$

设：
- $M = m + m_a$（总等效质量）
- $C = c_r + c_d$（总阻尼）
- $K = k_s + \rho g \pi r^2$（总刚度）
- $F_0 = \rho g \pi r^2 \frac{H}{2} \frac{\sinh(k_w d)}{\cosh(k_w h)}$（波浪激励力幅值）

简化为：
$$M\ddot{z} + C\dot{z} + Kz = F_0 \cos(\omega t) \tag{5}$$

### 3.4 稳态解

设稳态解为 $z(t) = A \cos(\omega t - \phi)$，其中：

振幅：
$$A = \frac{F_0}{\sqrt{(K - M\omega^2)^2 + (C\omega)^2}} \tag{6}$$

相位：
$$\phi = \arctan\left(\frac{C\omega}{K - M\omega^2}\right) \tag{7}$$

### 3.5 附加质量和辐射阻尼

圆柱形浮子的附加质量（半径为 $r$，吃水 $d$）：
$$m_a = \rho \pi r^2 d \cdot C_a \tag{8}$$

其中 $C_a$ 为附加质量系数，对圆柱约取 1.0。

辐射阻尼系数：
$$c_r = \frac{\rho g \pi r^2}{\omega} \cdot C_r \tag{9}$$

其中 $C_r$ 为辐射阻尼系数，与 $k_w r$ 相关。

### 3.6 输出功率模型

阻尼器吸收的瞬时功率：
$$P(t) = c_d \dot{z}^2(t) \tag{10}$$

平均输出功率：
$$\bar{P} = \frac{1}{T} \int_0^T c_d \dot{z}^2 dt = \frac{1}{2} c_d \omega^2 A^2 \tag{11}$$

### 3.7 最优阻尼

对 $c_d$ 求导令 $\frac{d\bar{P}}{dc_d} = 0$，得最优阻尼条件：

当 $K = M\omega^2$（共振）时：
$$c_{d,opt} = \sqrt{c_r^2 + \frac{F_0^2}{A_{max}^2}} - c_r \tag{12}$$

此时最大功率（Budal 上界）：
$$P_{max} = \frac{F_0^2}{8(c_r + c_{d,opt})} \tag{13}$$

## 四、优化模型

### 目标函数
$$\max_{r, d, k_s, c_d} \bar{P} = \frac{1}{2} c_d \omega^2 A^2(r, d, k_s, c_d) \tag{14}$$

### 约束条件
$$0.5 \leq r \leq 5.0 \quad \text{(浮子半径范围/m)} \tag{15}$$
$$0.5 \leq d \leq 10.0 \quad \text{(吃水深度范围/m)} \tag{16}$$
$$1000 \leq k_s \leq 10^6 \quad \text{(弹簧刚度范围/N/m)} \tag{17}$$
$$100 \leq c_d \leq 10^5 \quad \text{(阻尼系数范围/N·s/m)} \tag{18}$$
