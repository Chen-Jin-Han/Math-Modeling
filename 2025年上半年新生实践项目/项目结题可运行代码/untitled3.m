function problem_2_hybrid_pso_final()
    % -------------------------------------------------------------------------
    % 求解 问题 A - 问题2 (混合算法: PSO + PD/FF + LPF/Delay)
    % 核心: 移除简化，使用 F_c = C * w^2 * sin(theta) 物理模型
    % -------------------------------------------------------------------------
    
    clear; clc; close all;
    fprintf('开始执行 "问题2" (PSO + 混合控制参数优化) 求解...\n');
    
    %% 1. 数据加载
    
    filename = 'Problem A：Data.xlsx'; 
    sheet_params = '系统参数'; sheet_data = '场景2';
    
    [params, y0, v0] = load_parameters(filename, sheet_params);
    [t_data, F_d_interp] = load_data(filename, sheet_data);
    
    %% 2. 求解：无控制 (Baseline)
    
    fprintf('\n正在求解 (情况一) 无控制 Baseline (纯净RK4)...\n');
    % 使用纯净基线函数，它只使用原始 F_d
    [I_h_1, t_1, y_1, v_1, a_y_1] = simulate_pure_baseline(params, t_data, F_d_interp, y0, v0);
    
    fprintf('求解完成。无控制 I_h = %f\n', I_h_1);
    
    %% 3. (核心) 求解：有控制 (PSO 优化)
    
    fprintf('\n开始 PSO 混合参数优化 (5个变量)...\n');
    
    % --- 3.1 定义优化变量和边界 ---
    nvars = 5; 
    lb = [1e4, 1e3, 0.5, 5.0, 0.00];   
    ub = [1e6, 1e5, 1.5, 50.0, 0.05];  
    
    % 创建目标函数
    obj_fun_hybrid = @(x) objective_function_unsimplified(x, params, t_data, F_d_interp, y0, v0);
    
    % --- 3.2 运行 PSO ---
    options_pso = optimoptions('particleswarm', ...
                        'Display', 'iter', ...
                        'MaxIterations', 100, ... 
                        'SwarmSize', 80);      
    
    fprintf('这将需要一些时间，取决于您的CPU...\n');
    [x_best, I_h_best] = particleswarm(obj_fun_hybrid, nvars, lb, ub, options_pso);
    
    fprintf('PSO 优化完成。\n');
    
    % --- 3.3 输出最优结果 ---
    Kp_best = x_best(1); Kd_best = x_best(2); FF_gain_best = x_best(3);
    Fc_best = x_best(4); Td_best = x_best(5);
    
    fprintf('\n--- 最终最优参数 ---\n');
    fprintf('最优 I_h (有控制) = %f\n', I_h_best);
    fprintf('控制增益 Kp/Kd/FF: %.2e / %.2e / %.3f\n', Kp_best, Kd_best, FF_gain_best);
    fprintf('信号参数 Cutoff/Delay: %.1f Hz / %.3f s\n', Fc_best, Td_best);

    %% 4. (最终) 结果提取与绘图
    
    % 运行最终的最优控制仿真
    [~, t_2, y_2, v_2, a_y_2, F_target_log, F_actual_log, omega_actual_log, theta_actual_log] ...
        = objective_function_unsimplified(x_best, params, t_data, F_d_interp, y0, v0);
    
    %% 5. 绘图 
    
    % --- 图1: 横向位移对比 ---
    figure('Name', '问题2 (Unsimplified): 横向位移对比');
    plot(t_1, y_1, 'g:', 'LineWidth', 1.5, 'DisplayName', '无控制');
    hold on;
    plot(t_2, y_2, 'b-', 'LineWidth', 2.0, 'DisplayName', '物理优化 (\sin(\theta) 模型)');
    title(sprintf('横向位移 (无控制 I_h=%.2f, 优化 I_h=%.2f)', I_h_1, I_h_best));
    xlabel('时间 (s)'); ylabel('位移 (m)');
    legend('Location', 'best'); grid on;
    
    % --- 图2: 横向加速度对比 ---
    figure('Name', '问题2 (Unsimplified): 横向加速度对比');
    plot(t_1, a_y_1, 'g:', 'LineWidth', 1.0, 'DisplayName', '无控制');
    hold on;
    plot(t_2, a_y_2, 'b-', 'LineWidth', 1.5, 'DisplayName', '物理优化 (\sin(\theta) 模型)');
    title('横向加速度对比');
    xlabel('时间 (s)'); ylabel('加速度 (m/s^2)');
    legend('Location', 'best'); grid on;
    
    % --- 图3: 作动器理想力 vs 实际力 ---
    figure('Name', '问题2 (Unsimplified): 作动器力对比');
    plot(t_2, F_target_log, 'r:', 'LineWidth', 1.5, 'DisplayName', 'F_{target} (目标)');
    hold on;
    plot(t_2, F_actual_log, 'b-', 'LineWidth', 1.5, 'DisplayName', 'F_{actual} (\sin(\theta) 实际)');
    title('作动器所需力 vs 实际力');
    xlabel('时间 (s)'); ylabel('力 (N)');
    legend('Location', 'best'); grid on;

    % --- 图4: 角速度 vs 角度 ---
    figure('Name', '问题2 (Unsimplified): 角速度和角度轨迹');
    yyaxis left;
    plot(t_2, omega_actual_log, 'r-', 'LineWidth', 1.5, 'DisplayName', '\omega_{actual}');
    ylabel('角速度 (rad/s)');
    yyaxis right;
    plot(t_2, mod(theta_actual_log, 2*pi), 'b:', 'LineWidth', 1.0, 'DisplayName', '\theta_{actual} (mod 2\pi)');
    ylabel('角度 (rad)');
    title('作动器实际状态轨迹');
    xlabel('时间 (s)'); 
    legend('Location', 'best'); grid on;
end

%% -------------------------------------------------------------------------
% 核心函数: 混合优化目标函数 (物理模型未简化)
% -------------------------------------------------------------------------
function [I_h, t_log, y_log, v_log, a_log, F_target_log, F_actual_log, omega_actual_log, theta_actual_log] = objective_function_unsimplified(x, params, t_data, F_d_interp, y0, v0)
    
    % 1. 解码所有 5 个优化变量
    Kp = x(1); Kd = x(2); FF_gain = x(3); 
    F_cutoff = x(4); T_delay = x(5); 
    
    n = length(t_data); dt = t_data(2) - t_data(1);
    
    % --- 预处理: 离线低通滤波 (FFT) ---
    F_d_raw = F_d_interp(t_data);
    F_d_lp = low_pass_filter_data(F_d_raw, dt, F_cutoff); 
    F_d_lp_interp = @(t) interp1(t_data, F_d_lp, t, 'spline', 'extrap');

    % 2. 初始化状态变量
    y = y0; v = v0; omega_actual = 0.0; 
    theta_actual = 0.0; % 初始角度为 0
    
    % 3. 初始化日志
    y_log = zeros(n, 1); v_log = zeros(n, 1); a_log = zeros(n, 1);
    F_target_log = zeros(n, 1); F_actual_log = zeros(n, 1);
    omega_actual_log = zeros(n, 1); theta_actual_log = zeros(n, 1);
    t_log = t_data;
    
    % --- 仿真循环 ---
    for i = 1:n
        t_i = t_data(i);
        
        F_d_lp_i = F_d_lp_interp(t_i); 
        t_predict = t_i + T_delay; 
        F_d_compensated = F_d_lp_interp(t_predict); 
        
        % 1. 控制律: F_target = FF * F_d_compensated - (Kp*y + Kd*v) 
        F_target = (FF_gain * F_d_compensated) - (Kp * y + Kd * v); 
        
        % 2. 物理约束与运动执行
        [omega_next, theta_next] = actuator_constrained_motion(F_target, omega_actual, theta_actual, dt, params);
        
        % 3. 计算实际作用力 (物理模型: F_c = C * w^2 * sin(theta))
        F_actual_magnitude = params.actuator_const * (omega_next^2);
        F_actual = F_actual_magnitude * sin(theta_next); 

        % 4. 动力学步进
        F_total = F_d_lp_i + F_actual;
        a = (F_total - params.c * v - params.k * y) / params.M;
        
        % 5. 存储日志
        y_log(i) = y; v_log(i) = v; a_log(i) = a;
        F_target_log(i) = F_target; F_actual_log(i) = F_actual;
        omega_actual_log(i) = omega_next; theta_actual_log(i) = theta_next;

        if i < n
            [y_next, v_next] = rk4_step(y, v, F_total, params, dt);
            y = y_next;
            v = v_next;
            omega_actual = omega_next;
            theta_actual = theta_next;
        end
    end
    
    I_h = trapz(t_data, a_log.^2) / (t_data(end) - t_data(1));
    
    if isnan(I_h) || isinf(I_h)
        I_h = 1e10; 
    end
end

%% -------------------------------------------------------------------------
% 辅助函数: 纯净基线求解
% -------------------------------------------------------------------------
function [I_h, t_log, y_log, v_log, a_log] = simulate_pure_baseline(params, t_data, F_d_interp, y0, v0)
    
    n = length(t_data); dt = t_data(2) - t_data(1);
    y = y0; v = v0; 
    y_log = zeros(n, 1); v_log = zeros(n, 1); a_log = zeros(n, 1);
    
    for i = 1:n
        F_d = F_d_interp(t_data(i)); 
        F_actual = 0; % 无控制
        
        F_total = F_d + F_actual; 
        a = (F_total - params.c * v - params.k * y) / params.M;
        
        y_log(i) = y; v_log(i) = v; a_log(i) = a;

        if i < n
            [y_next, v_next] = rk4_step(y, v, F_total, params, dt);
            y = y_next;
            v = v_next;
        end
    end
    
    I_h = trapz(t_data, a_log.^2) / (t_data(end) - t_data(1));
    t_log = t_data; 
end

%% -------------------------------------------------------------------------
% 辅助函数: 约束与运动执行器 (NEW)
% -------------------------------------------------------------------------
function [omega_next, theta_next] = actuator_constrained_motion(F_target, omega_actual, theta_actual, dt, p)
    % 目标: F_target 驱动 omega 变化，omega 变化驱动 theta 变化
    
    % 1. 计算目标角速度 (Magnitude only)
    omega_target = sqrt(abs(F_target) / p.actuator_const);
    omega_target = min(omega_target, p.omega_max);

    % 2. 应用 Alpha_max 约束 (Slew Rate)
    max_omega_change = p.alpha_max * dt;
    omega_error = omega_target - omega_actual;
    omega_change = clip(omega_error, -max_omega_change, max_omega_change);
    omega_next = omega_actual + omega_change;
    
    % 3. 角度积分 (Phi = Phi_prev + omega_next * dt)
    % 角度变化的方向由 F_target 决定，模拟电机驱动方向
    theta_direction = sign(F_target);
    if theta_direction == 0
        theta_direction = 1; % 防止静止时出现 NaN
    end
    
    theta_next = theta_actual + theta_direction * omega_next * dt;
    
    % 确保角度在 [0, 2*pi] 范围内 (防止数值溢出，但保留周期性)
    theta_next = mod(theta_next, 2*pi);
end

%% -------------------------------------------------------------------------
% 辅助函数: 离线低通滤波器 (FFT 滤波)
% -------------------------------------------------------------------------
function F_clean = low_pass_filter_data(F_raw, dt, cutoff_freq)
    Fs = 1/dt;
    L = length(F_raw);
    
    Y = fft(F_raw);
    
    cutoff_index = floor(cutoff_freq / Fs * L);
    
    Y_filtered = zeros(size(Y));
    
    Y_filtered(1:cutoff_index + 1) = Y(1:cutoff_index + 1); 
    Y_filtered(L - cutoff_index + 1 : L) = Y(L - cutoff_index + 1 : L);
    
    F_clean = real(ifft(Y_filtered));
end

%% -------------------------------------------------------------------------
% 辅助函数: 简化的RK4步进
% -------------------------------------------------------------------------
function [y_next, v_next] = rk4_step(y, v, F_total, p, dt)
    m = p.M; c = p.c; k = p.k;
    accel = @(y_val, v_val) (F_total - c * v_val - k * y_val) / m;
    k1_y = v; k1_v = accel(y, v);
    k2_y = v + 0.5 * dt * k1_v; k2_v = accel(y + 0.5 * dt * k1_y, k2_y);
    k3_y = v + 0.5 * dt * k2_v; k3_v = accel(y + 0.5 * dt * k2_y, k3_y);
    k4_y = v + dt * k3_v; k4_v = accel(y + dt * k3_y, k4_y);
    y_next = y + (dt / 6.0) * (k1_y + 2 * k2_y + 2 * k3_y + k4_y);
    v_next = v + (dt / 6.0) * (k1_v + 2 * k2_v + 2 * k3_v + k4_v);
end

%% -------------------------------------------------------------------------
% 辅助函数: clip/saturate
% -------------------------------------------------------------------------
function y = clip(x, bl, bu)
    y = max(bl, min(x, bu));
end

%% -------------------------------------------------------------------------
% 辅助函数: 加载参数
% -------------------------------------------------------------------------
function [params, y0, v0] = load_parameters(filename, sheet_params)
    params = struct();
    try
        opts = detectImportOptions(filename, 'Sheet', sheet_params);
        opts.VariableNamingRule = 'preserve'; 
        T_params = readtable(filename, opts);
        
        col_names = T_params.Properties.VariableNames;
        if ismember('物理意义', col_names)
            key_col = T_params.("物理意义");
        else
            key_col = T_params{:, 1}; 
        end
        if ismember('Specific Value', col_names)
            val_col = T_params.("Specific Value");
        else
            val_col = T_params{:, 2};
        end
        key_col = string(key_col); 

        params.M = val_col(contains(key_col, '车体'));
        params.c = val_col(contains(key_col, '等效阻尼系数'));
        params.k = val_col(contains(key_col, '等效刚度系数'));
        params.m_ecc = val_col(contains(key_col, '单个偏心块质量'));
        params.r_ecc = val_col(contains(key_col, '偏心块旋转半径'));
        params.omega_max = val_col(contains(key_col, '最大旋转角速度'));
        params.alpha_max = val_col(contains(key_col, '最大旋转角加速度'));
        params.actuator_const = 4.0 * params.m_ecc * params.r_ecc;
        
        fprintf('系统参数加载成功。\n');
        
    catch ME
        fprintf('--- 错误! 无法从 "%s" 的 "%s" 工作表加载系统参数! ---\n', filename, sheet_params);
        error('参数加载失败。');
    end
    y0 = 0.01; 
    v0 = 0;
end

%% -------------------------------------------------------------------------
% 辅助函数: 加载数据
% -------------------------------------------------------------------------
%% -------------------------------------------------------------------------
% 辅助函数: 加载数据 (已修正)
% -------------------------------------------------------------------------
function [t_data, F_d_interp] = load_data(filename, sheet_data)
    fprintf('正在从 "%s" 的 "%s" 工作表加载数据...\n', filename, sheet_data);
    try
        opts = detectImportOptions(filename, 'Sheet', sheet_data);
        opts.VariableNamingRule = 'preserve'; 
        T_data = readtable(filename, opts);
        
        col_names = T_data.Properties.VariableNames;
        if ismember('采样时刻', col_names)
            t_data = T_data.("采样时刻");
        else
            t_data = T_data{:, 1};
        end
        if ismember('横向扰动力(单位：N)', col_names)
            F_d_data = T_data.("横向扰动力(单位：N)");
        else
            F_d_data = T_data{:, 2};
        end
        
    catch ME
        fprintf('--- 错误! 无法从 "%s" 的 "%s" 工作表加载场景2数据! ---\n', filename, sheet_data);
        error('读取失败。');
    end

    % --- [开始修正] ---
    % 查找 t_data 或 F_d_data 中的非有限值 (NaN, Inf, -Inf)
    invalid_rows = ~isfinite(t_data) | ~isfinite(F_d_data);
    
    if any(invalid_rows)
        fprintf('警告: 在 "%s" 中检测到并移除了 %d 个无效数据行 (NaN/Inf)。\n', ...
                sheet_data, sum(invalid_rows));
        % 移除这些无效行
        t_data(invalid_rows) = [];
        F_d_data(invalid_rows) = [];
    end
    % --- [结束修正] ---

    fprintf('场景2数据加载成功。\n');
    
    % 现在 t_data 和 F_d_data 都是“干净”的
    F_d_interp = @(t) interp1(t_data, F_d_data, t, 'spline', 'extrap');
end

%% -------------------------------------------------------------------------
% 辅助函数: ode45 所需的系统状态空间函数 (用于无控制情况)
% -------------------------------------------------------------------------
function dYdt = vehicle_ode(t, Y, F_total_func, p)
    dYdt = zeros(2, 1);
    dYdt(1) = Y(2);
    F_total = F_total_func(t);
    dYdt(2) = (F_total - p.c * Y(2) - p.k * Y(1)) / p.M;
end

