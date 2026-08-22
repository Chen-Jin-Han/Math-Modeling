function Problem_2()
    clear; clc; close all;
    fprintf('Starting execution of "Problem 2" (PSO + fmincon sequential optimization)...\n');
    
    useParallelFlag = false;
if license('test', 'Distrib_Computing_Toolbox')
    useParallelFlag = true;
    pool = gcp('nocreate');
    if isempty(pool)
        fprintf('No parallel pool detected, attempting to create a thread pool...\n');
        try
   
            pool = parpool('threads');
            fprintf('Thread pool started (workers = %d).\n', pool.NumWorkers);
        catch
            warning('Failed to create thread pool, trying local process pool...');
            try
                c = parcluster('local');
                if c.NumWorkers > 0
                    pool = parpool(c, c.NumWorkers);
                    fprintf('Local process pool started (workers = %d).\n', pool.NumWorkers);
                else
                    warning('Local cluster NumWorkers = 0, falling back to serial mode.');
                    useParallelFlag = false;
                end
            catch ME2
                warning('Failed to create local process pool: %s\nFalling back to serial mode.', ME2.message);
                useParallelFlag = false;
            end
        end
    else
        fprintf('Existing parallel pool detected (workers = %d), reusing it.\n', pool.NumWorkers);
    end
else
    warning('Parallel Computing Toolbox not detected, PSO will run in serial mode.');
end


    % 1. Data loading
    filename     = 'Problem A：Data.xlsx'; 
    sheet_params = '系统参数'; 
    sheet_data   = '场景2';
    
    [params, y0, v0]     = load_parameters(filename, sheet_params);
    [t_data, F_d_interp] = load_data(filename, sheet_data);
    
    % 2. Baseline (no control)
    fprintf('\nSolving Case 1: uncontrolled baseline (pure RK4)...\n');
    [I_h_1, t_1, y_1, v_1, a_y_1] = simulate_pure_baseline(params, t_data, F_d_interp, y0, v0);
    
    fprintf('Computation finished. Uncontrolled I_h = %f\n', I_h_1);
    

    
    % Step 1: PSO (Set 1)
    nvars_pso = 6; 
    % [Kp1, Kd1, FF, Fc, Td, theta0_1]
    lb_pso = [1e4, 1e3, 0.5, 5.0, 0.00, 0];  
    ub_pso = [1e6, 1e5, 1.5, 50.0, 0.05, 2*pi]; 
    
    % Step 2: fmincon (Set 2)
    nvars_fmincon = 3;
    % [Kp2, Kd2, theta0_2]
    lb_fmincon = [1e4, 1e3, 0];
    ub_fmincon = [1e6, 1e5, 2*pi];
    
    pso_iters = 40;
    pso_swarm = 40;
    fmincon_iters = 20;
    
    fprintf('\n--- Step 1: Run PSO to optimize 6 variables (Set 1) ---\n');
    fprintf(' (Set 2 is disabled at this stage)\n');
    
    x2_inactive = [0, 0, 0]; 
    
    obj_fun_pso = @(x1) objective_function_unsimplified([x1, x2_inactive], ...
                             params, t_data, F_d_interp, y0, v0);
    
    h_wait_pso = waitbar(0, 'PSO starting...', 'Name', 'Step 1: PSO (Set 1) optimization');
    my_pso_output_fcn = @(ov, state) pso_output_function(ov, state, h_wait_pso, pso_iters);
    
    options_pso = optimoptions('particleswarm', ...
                       'Display', 'iter', ... 
                       'MaxIterations', pso_iters, ...
                       'SwarmSize', pso_swarm, ...
                       'OutputFcn', my_pso_output_fcn); 

    [x1_best, I_h_step1] = particleswarm(obj_fun_pso, nvars_pso, lb_pso, ub_pso, options_pso);
    
    if ishandle(h_wait_pso), close(h_wait_pso); end
    fprintf('--- Step 1 completed. Best I_h (Set 1 only) = %f ---\n', I_h_step1);
    
    fprintf('\n--- Step 2: Run fmincon to optimize 3 variables (Set 2) ---\n');
    fprintf(' (Fixing optimal parameters of Set 1)\n');
    
    obj_fun_fmincon = @(x2) objective_function_unsimplified([x1_best, x2], ...
                                 params, t_data, F_d_interp, y0, v0);
    
    h_wait_fmincon = waitbar(0, 'fmincon starting...', 'Name', 'Step 2: fmincon (Set 2) fine tuning');
    my_fmincon_output_fcn = @(x, ov, state) fmincon_output_function(x, ov, state, h_wait_fmincon, fmincon_iters);
    
    options_fmincon = optimoptions('fmincon', ...
        'Algorithm', 'interior-point', ... 
        'Display', 'none', ...          
        'MaxIterations', fmincon_iters, ...
        'SpecifyObjectiveGradient', false, ... 
        'OutputFcn', my_fmincon_output_fcn);
    
    x2_start = (lb_fmincon + ub_fmincon) / 2.0; 
    
    [x2_best, I_h_final_check] = fmincon(obj_fun_fmincon, ...
        x2_start, ...
        [], [], [], [], ...
        lb_fmincon, ub_fmincon, ...
        [], options_fmincon);
    
    if ishandle(h_wait_fmincon), close(h_wait_fmincon); end
    fprintf('--- Step 2 completed. Final I_h (Set 1 + Set 2) = %f ---\n', I_h_final_check);

    x_best = [x1_best, x2_best];
    
    Kp1_best      = x_best(1); 
    Kd1_best      = x_best(2); 
    FF_gain_best  = x_best(3);
    Fc_best       = x_best(4); 
    Td_best       = x_best(5);
    theta0_1_best = x_best(6);
    
    Kp2_best      = x_best(7); 
    Kd2_best      = x_best(8);
    theta0_2_best = x_best(9);
    
    fprintf('\n--- Final optimal parameters ---\n');
    fprintf('Optimal I_h (sequential optimization) = %f\n', I_h_final_check);
    fprintf('Set 1 (PD+FF): Kp/Kd/FF: %.2e / %.2e / %.3f\n', Kp1_best, Kd1_best, FF_gain_best);
    fprintf('Set 1 (Phase): theta0_1: %.3f rad (%.1f deg)\n', theta0_1_best, rad2deg(theta0_1_best));
    fprintf('Set 2 (PD)   : Kp/Kd   : %.2e / %.2e\n', Kp2_best, Kd2_best);
    fprintf('Set 2 (Phase): theta0_2: %.3f rad (%.1f deg)\n', theta0_2_best, rad2deg(theta0_2_best));
    fprintf('Signal parameters Cutoff/Delay : %.1f Hz / %.3f s\n', Fc_best, Td_best);

    [~, t_2, y_2, v_2, a_y_2, ...
     F_target_1_log, F_actual_1_log, omega_actual_1_log, theta_actual_1_log, ...
     F_target_2_log, F_actual_2_log, omega_actual_2_log, theta_actual_2_log] ...
        = objective_function_unsimplified(x_best, params, t_data, F_d_interp, y0, v0);
    
    figure('Name', 'Problem 2 (Sequential Optimization): Lateral Displacement Comparison');
    plot(t_1, y_1, 'g:', 'LineWidth', 1.5, 'DisplayName', 'Uncontrolled');
    hold on;
    plot(t_2, y_2, 'b-', 'LineWidth', 2.0, 'DisplayName', 'Sequential optimization (PSO+fmincon)');
    title(sprintf('Lateral displacement (Uncontrolled I_h=%.2f, Optimized I_h=%.2f)', I_h_1, I_h_final_check));
    xlabel('Time (s)'); ylabel('Displacement (m)');
    legend('Location', 'best'); grid on;
    
    figure('Name', 'Problem 2 (Sequential Optimization): Lateral Acceleration Comparison');
    plot(t_1, a_y_1, 'g:', 'LineWidth', 1.0, 'DisplayName', 'Uncontrolled');
    hold on;
    plot(t_2, a_y_2, 'b-', 'LineWidth', 1.5, 'DisplayName', 'Sequential optimization (PSO+fmincon)');
    title('Lateral acceleration comparison');
    xlabel('Time (s)'); ylabel('Acceleration (m/s^2)');
    legend('Location', 'best'); grid on;
    
    figure('Name', 'Problem 2 (Sequential Optimization): Actual Actuating Force');
    plot(t_2, F_actual_1_log, 'r-', 'LineWidth', 1.5, 'DisplayName', 'F_{actual, 1} (Set 1)');
    hold on;
    plot(t_2, F_actual_2_log, 'm-', 'LineWidth', 1.5, 'DisplayName', 'F_{actual, 2} (Set 2)');
    plot(t_2, F_actual_1_log + F_actual_2_log, 'b:', 'LineWidth', 2.0, 'DisplayName', 'F_{actual, Total}');
    title('Actual actuator output force');
    xlabel('Time (s)'); ylabel('Force (N)');
    legend('Location', 'best'); grid on;

    figure('Name', 'Problem 2 (Sequential Optimization): Angular Velocity and Angle Trajectories');
    subplot(2, 1, 1);
    plot(t_2, omega_actual_1_log, 'r-', 'LineWidth', 1.5, 'DisplayName', '\omega_1 (Set 1)');
    hold on;
    plot(t_2, omega_actual_2_log, 'm-', 'LineWidth', 1.5, 'DisplayName', '\omega_2 (Set 2)');
    ylabel('Angular velocity (rad/s)');
    title('Actual actuator state trajectories');
    legend('Location', 'best'); grid on;
    subplot(2, 1, 2);
    plot(t_2, mod(theta_actual_1_log, 2*pi), 'r:', 'LineWidth', 1.0, 'DisplayName', '\theta_1 (Set 1, mod 2\pi)');
    hold on;
    plot(t_2, mod(theta_actual_2_log, 2*pi), 'm:', 'LineWidth', 1.0, 'DisplayName', '\theta_2 (Set 2, mod 2\pi)');
    ylabel('Angle (rad)');
    xlabel('Time (s)'); 
    legend('Location', 'best'); grid on;
end

function stop = pso_output_function(optimValues, state, h_waitbar, max_iter)
    stop = false; 
    
    if strcmp(state, 'iter')
        current_iter = optimValues.iteration;
        if ishandle(h_waitbar)
            progress = current_iter / max_iter;
            waitbar(progress, h_waitbar, ...
                sprintf('PSO iteration: %d / %d (best I_h: %.2f)', ...
                        current_iter, max_iter, optimValues.bestfval));
            drawnow;
        else
            fprintf('User canceled PSO optimization.\n');
            stop = true;
        end
    end
end

function stop = fmincon_output_function(x, optimValues, state, h_waitbar, max_iter)
    stop = false;

    if strcmp(state, 'iter')
        current_iter = optimValues.iteration;
        if ishandle(h_waitbar)
            progress = current_iter / max_iter;
            waitbar(progress, h_waitbar, ...
                sprintf('fmincon iteration: %d / %d (I_h: %.2f)', ...
                        current_iter, max_iter, optimValues.fval));
            drawnow;
        else
            fprintf('User canceled fmincon optimization.\n');
            stop = true;
        end
    end
end

function [I_h, t_log, y_log, v_log, a_log, ...
          F_target_1_log, F_actual_1_log, omega_actual_1_log, theta_actual_1_log, ...
          F_target_2_log, F_actual_2_log, omega_actual_2_log, theta_actual_2_log] = ...
    objective_function_unsimplified(x, params, t_data, F_d_interp, y0, v0)
    
    Kp1      = x(1); 
    Kd1      = x(2); 
    FF_gain  = x(3); 
    F_cutoff = x(4); 
    T_delay  = x(5); 
    theta0_1 = x(6); 
    Kp2      = x(7); 
    Kd2      = x(8);
    theta0_2 = x(9); 
    
    n  = length(t_data); 
    dt = t_data(2) - t_data(1);
    
    F_d_raw = F_d_interp(t_data);
    F_d_lp  = low_pass_filter_data(F_d_raw, dt, F_cutoff); 
    F_d_lp_interp = @(t) spline(t_data, F_d_lp, t);

    y = y0; 
    v = v0; 
    omega_actual_1 = 0.0;
    theta_actual_1 = theta0_1;
    omega_actual_2 = 0.0;
    theta_actual_2 = theta0_2;
    
    y_log              = zeros(n, 1); 
    v_log              = zeros(n, 1); 
    a_log              = zeros(n, 1);
    t_log              = t_data;
    F_target_1_log     = zeros(n, 1); 
    F_actual_1_log     = zeros(n, 1);
    omega_actual_1_log = zeros(n, 1); 
    theta_actual_1_log = zeros(n, 1);
    F_target_2_log     = zeros(n, 1); 
    F_actual_2_log     = zeros(n, 1);
    omega_actual_2_log = zeros(n, 1); 
    theta_actual_2_log = zeros(n, 1);
    
    for i = 1:n
        t_i = t_data(i);
        
        F_d_lp_i        = F_d_lp_interp(t_i); 
        t_predict       = t_i + T_delay; 
        F_d_compensated = F_d_lp_interp(t_predict); 
        
        F_target_1 = (FF_gain * F_d_compensated) - (Kp1 * y + Kd1 * v); 
        F_target_2 = -(Kp2 * y + Kd2 * v);
        
        [omega_1_next, theta_1_next] = actuator_constrained_motion(F_target_1, omega_actual_1, theta_actual_1, dt, params);
        [omega_2_next, theta_2_next] = actuator_constrained_motion(F_target_2, omega_actual_2, theta_actual_2, dt, params);
        
        F_actual_1 = params.actuator_const * (omega_1_next^2) * sin(theta_1_next); 
        F_actual_2 = params.actuator_const * (omega_2_next^2) * sin(theta_2_next); 

        F_total = F_d_lp_i + F_actual_1 + F_actual_2;
        a       = (F_total - params.c * v - params.k * y) / params.M;
        
        y_log(i)              = y; 
        v_log(i)              = v; 
        a_log(i)              = a;
        F_target_1_log(i)     = F_target_1; 
        F_actual_1_log(i)     = F_actual_1;
        omega_actual_1_log(i) = omega_1_next; 
        theta_actual_1_log(i) = theta_1_next;
        F_target_2_log(i)     = F_target_2; 
        F_actual_2_log(i)     = F_actual_2;
        omega_actual_2_log(i) = omega_2_next; 
        theta_actual_2_log(i) = theta_2_next;
        
        if i < n
            [y_next, v_next] = rk4_step(y, v, F_total, params, dt);
            y = y_next;
            v = v_next;
            omega_actual_1 = omega_1_next;
            theta_actual_1 = theta_1_next;
            omega_actual_2 = omega_2_next;
            theta_actual_2 = theta_2_next;
        end
    end
    
    I_h = trapz(t_data, a_log.^2) / (t_data(end) - t_data(1));
    
    if isnan(I_h) || isinf(I_h)
        I_h = 1e10; 
    end
end

function [I_h, t_log, y_log, v_log, a_log] = simulate_pure_baseline(params, t_data, F_d_interp, y0, v0)
    n  = length(t_data); 
    dt = t_data(2) - t_data(1);
    y  = y0; 
    v  = v0; 
    y_log = zeros(n, 1); 
    v_log = zeros(n, 1); 
    a_log = zeros(n, 1);
    for i = 1:n
        F_d      = F_d_interp(t_data(i)); 
        F_actual = 0;
        F_total = F_d + F_actual; 
        a       = (F_total - params.c * v - params.k * y) / params.M;
        y_log(i) = y; 
        v_log(i) = v; 
        a_log(i) = a;
        if i < n
            [y_next, v_next] = rk4_step(y, v, F_total, params, dt);
            y = y_next;
            v = v_next;
        end
    end
    I_h   = trapz(t_data, a_log.^2) / (t_data(end) - t_data(1));
    t_log = t_data; 
end

function [omega_next, theta_next] = actuator_constrained_motion(F_target, omega_actual, theta_actual, dt, p)
    omega_target = sqrt(abs(F_target) / p.actuator_const);
    omega_target = min(omega_target, p.omega_max);
    max_omega_change = p.alpha_max * dt;
    omega_error      = omega_target - omega_actual;
    omega_change     = clip(omega_error, -max_omega_change, max_omega_change);
    omega_next       = omega_actual + omega_change;
    theta_direction = sign(F_target);
    if theta_direction == 0, theta_direction = 1; end
    theta_next = mod(theta_actual + theta_direction * omega_next * dt, 2*pi);
end

function F_clean = low_pass_filter_data(F_raw, dt, cutoff_freq)
    Fs = 1/dt;
    L  = length(F_raw);
    Y = fft(F_raw);
    cutoff_index = floor(cutoff_freq / Fs * L);
    Y_filtered = zeros(size(Y));
    Y_filtered(1:cutoff_index + 1)        = Y(1:cutoff_index + 1); 
    Y_filtered(L - cutoff_index + 1 : L) = Y(L - cutoff_index + 1 : L);
    F_clean = real(ifft(Y_filtered));
end

function [y_next, v_next] = rk4_step(y, v, F_total, p, dt)
    m = p.M; c = p.c; k = p.k;
    accel = @(y_val, v_val) (F_total - c * v_val - k * y_val) / m;
    k1_y = v;               k1_v = accel(y, v);
    k2_y = v + 0.5*dt*k1_v; k2_v = accel(y + 0.5*dt*k1_y, k2_y);
    k3_y = v + 0.5*dt*k2_v; k3_v = accel(y + 0.5*dt*k2_y, k3_y);
    k4_y = v + dt*k3_v;     k4_v = accel(y + dt*k3_y, k4_y);
    y_next = y + (dt / 6.0) * (k1_y + 2*k2_y + 2*k3_y + k4_y);
    v_next = v + (dt / 6.0) * (k1_v + 2*k2_v + 2*k3_v + k4_v);
end

function y = clip(x, bl, bu)
    y = max(bl, min(x, bu));
end

function [params, y0, v0] = load_parameters(filename, sheet_params)
    params = struct();
    try
        opts = detectImportOptions(filename, 'Sheet', sheet_params);
        opts.VariableNamingRule = 'preserve'; 
        T_params = readtable(filename, opts);
        col_names = T_params.Properties.VariableNames;
        if ismember('物理意义', col_names), key_col = T_params.("物理意义");
        else, key_col = T_params{:, 1}; end
        if ismember('Specific Value', col_names), val_col = T_params.("Specific Value");
        else, val_col = T_params{:, 2}; end
        key_col = string(key_col); 
        params.M           = val_col(contains(key_col, '车体'));
        params.c           = val_col(contains(key_col, '等效阻尼系数'));
        params.k           = val_col(contains(key_col, '等效刚度系数'));
        params.m_ecc       = val_col(contains(key_col, '单个偏心块质量'));
        params.r_ecc       = val_col(contains(key_col, '偏心块旋转半径'));
        params.omega_max   = val_col(contains(key_col, '最大旋转角速度'));
        params.alpha_max   = val_col(contains(key_col, '最大旋转角加速度'));
        params.actuator_const = 4.0 * params.m_ecc * params.r_ecc;
        fprintf('Load successful!。\n');
    catch
        fprintf('--- Error! Can not load "%s" from "%s" ! ---\n', filename, sheet_params);
        error('Faild!');
    end
    y0 = 0.01; v0 = 0;
end

function [t_data, F_d_interp] = load_data(filename, sheet_data)
    fprintf('Loading data from sheet "%s" in "%s"...\n', sheet_data, filename);
    try
        opts = detectImportOptions(filename, 'Sheet', sheet_data);
        opts.VariableNamingRule = 'preserve'; 
        T_data = readtable(filename, opts);
        col_names = T_data.Properties.VariableNames;
        if ismember('Sampling Time', col_names), t_data = T_data.("Sampling Time");
        else, t_data = T_data{:, 1}; end
        if ismember('Lateral Disturbance Force (N)', col_names), F_d_data = T_data.("Lateral Disturbance Force (N)");
        else, F_d_data = T_data{:, 2}; end
    catch
        fprintf('--- Error! Unable to load Scenario 2 data from sheet "%s" in "%s"! ---\n', sheet_data, filename);
        error('Reading failed.');
    end
    invalid_rows = ~isfinite(t_data) | ~isfinite(F_d_data);
    if any(invalid_rows)
        fprintf('Warning: Detected %d invalid data rows, removed.\n', sum(invalid_rows));
        t_data(invalid_rows)   = [];
        F_d_data(invalid_rows) = [];
    end
    fprintf('Scenario 2 data loaded successfully.\n');
    F_d_interp = @(t_query) spline(t_data, F_d_data, t_query);
end
