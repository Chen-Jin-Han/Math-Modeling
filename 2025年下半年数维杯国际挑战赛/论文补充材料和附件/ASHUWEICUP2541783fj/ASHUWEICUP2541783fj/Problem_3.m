function Problem_3()
    clear; clc; close all;
    fprintf('Starting "Problem 3" (multi-harmonic UKF + PSO, fixed alpha, 10-D joint optimization)...\n');

    try
        nc = feature('numcores');
        maxNumCompThreads(nc);
        fprintf('maxNumCompThreads set to %d.\n', nc);
    catch ME
        warning('Failed to set maxNumCompThreads: %s', ME.message);
    end

    useParallelFlag = false;
    if license('test', 'Distrib_Computing_Toolbox')
        useParallelFlag = true;
        pool = gcp('nocreate');
        if isempty(pool)
            fprintf('No parallel pool detected, attempting to create thread pool...\n');
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

    filename     = 'Problem A：Data.xlsx';
    sheet_params = '系统参数';
    sheet_data   = '场景2';

    [params, y0, v0]     = load_parameters(filename, sheet_params);
    [t_data, F_d_interp] = load_data(filename, sheet_data);

    params.ukf_alpha = 0.0005;

    fprintf('\n[Baseline] Solving uncontrolled baseline (pure RK4)...\n');
    [I_h_1, t_1, y_1, v_1, a_y_1] = simulate_pure_baseline(params, t_data, F_d_interp, y0, v0);
    fprintf('Baseline solved. Uncontrolled I_h = %f\n', I_h_1);

    nvars = 10;

    lb = [ ...
        3.0e4,   ...
        1.1e4,   ...
        1.0,     ...
        1.2e4,   ...
        5.3e4,   ...
        2.5,     ...
       -8.0,     ...
       -3.5,     ...
        1.2,     ...
        0.08     ...
    ];

    ub = [ ...
        5.0e4,   ...
        3.5e4,   ...
        3.0,     ...
        3.0e4,   ...
        1.3e5,   ...
        5.0,     ...
       -6.0,     ...
       -1.5,     ...
        2.5,     ...
        0.12     ...
    ];

    pso_max_iter   = 100;
    pso_swarm_size = 100;

    fprintf('\n[PSO-10D] Alpha fixed at 0.001, starting optimization of 10 hyperparameters...\n');

    h_wait_pso = waitbar(0, 'Running 10-D PSO optimization...', 'Name', 'PSO (Multi-UKF global hyperparameters)');
    my_pso_output_fcn = @(ov, state) pso_output_function(ov, state, h_wait_pso, pso_max_iter);

    options_pso = optimoptions('particleswarm', ...
                           'Display', 'iter', ...
                           'MaxIterations', pso_max_iter, ...
                           'SwarmSize', pso_swarm_size, ...
                           'OutputFcn', my_pso_output_fcn, ...
                           'UseParallel', useParallelFlag, ...
                           'UseVectorized', false);

    obj_fun = @(x) objective_function_wrapper(x, params, t_data, F_d_interp, y0, v0);

    [x_best, I_h_best] = particleswarm(obj_fun, nvars, lb, ub, options_pso);

    if ishandle(h_wait_pso), close(h_wait_pso); end
    fprintf('\n[PSO-10D] Optimization finished.\n');

    Kp1_best        = x_best(1);
    Kd1_best        = x_best(2);
    FF_gain_best    = x_best(3);
    Kp2_best        = x_best(4);
    Kd2_best        = x_best(5);
    omega_init_best = x_best(6);
    log_Q_w_best    = x_best(7);
    log_R_best      = x_best(8);
    log_q_fd_best   = x_best(9);
    T_delay_best    = x_best(10);

    fprintf('\n--- Final optimal hyperparameters (multi-harmonic UKF, alpha=0.001 fixed, 10-D joint optimization) ---\n');
    fprintf('Optimal I_h      = %f\n', I_h_best);
    fprintf('UKF alpha        : %.4g (fixed)\n', params.ukf_alpha);
    fprintf('PD (Set 1)       : Kp1=%.2e, Kd1=%.2e\n', Kp1_best, Kd1_best);
    fprintf('PD (Set 2)       : Kp2=%.2e, Kd2=%.2e\n', Kp2_best, Kd2_best);
    fprintf('FF Gain          : %.3f\n', FF_gain_best);
    fprintf('UKF (w_init)     : %.4f rad/s\n', omega_init_best);
    fprintf('UKF Q_omega      : log10(Q_w) = %.3f -> Q_w = %.3e\n', log_Q_w_best, 10^log_Q_w_best);
    fprintf('UKF R            : log10(R)   = %.3f -> R   = %.3e\n', log_R_best,      10^log_R_best);
    fprintf('Disturbance proc : log10(q_fd)= %.3f -> q_fd= %.3e\n', log_q_fd_best,   10^log_q_fd_best);
    fprintf('Prediction lead  : T_delay    = %.4f s\n', T_delay_best);

    fprintf('\nRunning final simulation with optimal hyperparameters (for plotting)...\n');

    [~, logs] = run_online_simulation_MultiEKF(x_best, params, t_data, F_d_interp, y0, v0);

    t_2   = logs.t_data;
    y_2   = logs.y_real_log;
    a_y_2 = logs.a_real_log;

    figure('Name', 'Problem 3 (Multi-UKF): Disturbance force estimation');
    plot(t_2, logs.Fd_real_log, 'r-', 'LineWidth', 1.5, 'DisplayName', 'F_{d} actual (unmeasured)');
    hold on;
    plot(t_2, logs.Fd_hat_log,  'g:', 'LineWidth', 2.0, 'DisplayName', 'F_{d} estimated (Fd1+Fd2)');
    plot(t_2, logs.Fd1_hat_log, 'c--','LineWidth', 1.0, 'DisplayName', 'F_{d1} estimated (fundamental)');
    title('Multi-harmonic UKF disturbance force estimation vs actual');
    xlabel('Time (s)'); ylabel('Force (N)');
    legend('Location', 'best'); grid on;
    xlim([t_2(1), t_2(end)]);

    figure('Name', 'Problem 3 (Multi-UKF): Disturbance force prediction');
    plot(t_2, logs.Fd_real_log, 'r-', 'LineWidth', 1.5, 'DisplayName', 'F_{d} actual (unmeasured)');
    hold on;
    plot(t_2, logs.Fd_pred_log, 'm:', 'LineWidth', 2.0, ...
        'DisplayName', sprintf('F_{d} prediction (lead %.2fs)', logs.T_delay));
    title('Multi-harmonic UKF prediction vs actual (no delay)');
    xlabel('Time (s)'); ylabel('Force (N)');
    legend('Location', 'best'); grid on;
    xlim([t_2(1), t_2(end)]);

    figure('Name', 'Problem 3 (Multi-UKF): Frequency estimation');
    plot(t_2, logs.omega_hat_log, 'b-', 'LineWidth', 2.0);
    title('Fundamental frequency \omega_1 estimated by UKF');
    xlabel('Time (s)'); ylabel('Angular frequency (rad/s)');
    grid on;

    figure('Name', 'Problem 3 (Multi-UKF): Lateral displacement');
    plot(t_1, y_1, 'g:', 'LineWidth', 1.5, 'DisplayName', 'Uncontrolled');
    hold on;
    plot(t_2, y_2, 'b-', 'LineWidth', 2.0, 'DisplayName', 'Online (Multi-UKF) control');
    title(sprintf('Lateral displacement (uncontrolled I_h=%.2f, optimized I_h=%.2f)', I_h_1, I_h_best));
    xlabel('Time (s)'); ylabel('Displacement (m)');
    legend('Location', 'best'); grid on;
end

function I_h = objective_function_wrapper(x, params, t_data, F_d_interp, y0, v0)
    [I_h, ~] = run_online_simulation_MultiEKF(x, params, t_data, F_d_interp, y0, v0);
end

function [I_h, logs] = run_online_simulation_MultiEKF(x, params, t_data, F_d_interp, y0, v0)

    Kp1           = x(1);
    Kd1           = x(2);
    FF_gain       = x(3);
    Kp2           = x(4);
    Kd2           = x(5);
    omega_initial = x(6);
    log_Q_omega   = x(7);
    log_R         = x(8);
    log_q_fd      = x(9);
    T_delay       = x(10);

    q_fd        = 10^log_q_fd;
    dt          = t_data(2) - t_data(1);
    n           = length(t_data);

    M = params.M; c = params.c; k = params.k;
    H = [-k/M, -c/M, 1/M, 0, 1/M, 0, 0];
    D = 1/M;

    Q = diag([1e-10, 1e-8, q_fd, q_fd, q_fd, q_fd, 10^log_Q_omega]);
    R = 10^log_R;

    x_hat = [y0; v0; 0; 0; 0; 0; omega_initial];

    P = diag([1e-6, 1e-6, 1e2, 1e2, 1e2, 1e2, 1e0]);

    omega_min = 10.0;
    omega_max = 30.0;

    y_real   = y0;
    v_real   = v0;

    theta0_1 = 0;
    theta0_2 = 0;
    omega_actual_1 = 0.0; theta_actual_1 = theta0_1;
    omega_actual_2 = 0.0; theta_actual_2 = theta0_2;

    y_real_log         = zeros(n, 1);
    a_real_log         = zeros(n, 1);
    Fd1_hat_log        = zeros(n, 1);
    Fd_hat_log         = zeros(n, 1);
    Fd_pred_log        = zeros(n, 1);
    Fd_real_log        = zeros(n, 1);
    omega_hat_log      = zeros(n, 1);
    F_actual_1_log     = zeros(n, 1);
    F_actual_2_log     = zeros(n, 1);
    theta_actual_1_log = zeros(n, 1);
    theta_actual_2_log = zeros(n, 1);
    omega_actual_1_log = zeros(n, 1);
    omega_actual_2_log = zeros(n, 1);

    for i = 1:n
        t_i = t_data(i);

        F_act_prev = 0;
        if i > 1
            F_act_prev = F_actual_1_log(i-1) + F_actual_2_log(i-1);
        end

        [x_pred_k, P_pred_k, X_sigma_pred, Wm, Wc] = ...
            ukf_predict_step_multi(x_hat, P, F_act_prev, Q, params, dt);

        Fd1_hat     = x_pred_k(3);
        Fd1_dot_hat = x_pred_k(4);
        Fd2_hat     = x_pred_k(5);
        Fd2_dot_hat = x_pred_k(6);
        omega1_hat  = max(omega_min, min(omega_max, x_pred_k(7)));
        omega2_hat  = 2 * omega1_hat;

        w1_T     = omega1_hat * T_delay;
        Fd1_pred = Fd1_hat * cos(w1_T) + (Fd1_dot_hat / omega1_hat) * sin(w1_T);

        w2_T     = omega2_hat * T_delay;
        Fd2_pred = Fd2_hat * cos(w2_T) + (Fd2_dot_hat / omega2_hat) * sin(w2_T);

        F_d_compensated = Fd1_pred + Fd2_pred;

        y_hat = x_pred_k(1);
        v_hat = x_pred_k(2);

        F_target_1 = (FF_gain * F_d_compensated) - (Kp1 * y_hat + Kd1 * v_hat);
        F_target_2 = -(Kp2 * y_hat + Kd2 * v_hat);

        [omega_1_next, theta_1_next] = actuator_constrained_motion( ...
            F_target_1, omega_actual_1, theta_actual_1, dt, params);
        [omega_2_next, theta_2_next] = actuator_constrained_motion( ...
            F_target_2, omega_actual_2, theta_actual_2, dt, params);

        F_actual_1 = params.actuator_const * (omega_1_next^2) * sin(theta_1_next);
        F_actual_2 = params.actuator_const * (omega_2_next^2) * sin(theta_2_next);
        F_act_current = F_actual_1 + F_actual_2;

        F_d_real = F_d_interp(t_i);
        F_total  = F_d_real + F_act_current;

        [y_next, v_next] = rk4_step(y_real, v_real, F_total, params, dt);
        a_real = (F_total - c * v_real - k * y_real) / M;

        z_k = a_real;
        u_k = F_act_current;

        [x_hat, P] = ukf_update_step_multi( ...
            x_pred_k, P_pred_k, X_sigma_pred, Wm, Wc, ...
            z_k, u_k, H, D, R);

        x_hat(7) = max(omega_min, min(omega_max, x_hat(7)));

        y_real_log(i)         = y_real;
        a_real_log(i)         = a_real;
        Fd1_hat_log(i)        = x_hat(3);
        Fd_hat_log(i)         = x_hat(3) + x_hat(5);
        omega_hat_log(i)      = x_hat(7);
        Fd_real_log(i)        = F_d_real;
        Fd_pred_log(i)        = F_d_compensated;
        F_actual_1_log(i)     = F_actual_1;
        F_actual_2_log(i)     = F_actual_2;
        omega_actual_1_log(i) = omega_1_next;
        omega_actual_2_log(i) = omega_2_next;
        theta_actual_1_log(i) = theta_1_next;
        theta_actual_2_log(i) = theta_2_next;

        y_real         = y_next;
        v_real         = v_next;
        omega_actual_1 = omega_1_next;
        theta_actual_1 = theta_1_next;
        omega_actual_2 = omega_2_next;
        theta_actual_2 = theta_2_next;
    end

    I_h = trapz(t_data, a_real_log.^2) / (t_data(end) - t_data(1));

    if isnan(I_h) || isinf(I_h)
        I_h = 1e10;
    end

    logs = struct();
    logs.t_data             = t_data;
    logs.y_real_log         = y_real_log;
    logs.a_real_log         = a_real_log;
    logs.Fd1_hat_log        = Fd1_hat_log;
    logs.Fd_hat_log         = Fd_hat_log;
    logs.Fd_real_log        = Fd_real_log;
    logs.Fd_pred_log        = Fd_pred_log;
    logs.omega_hat_log      = omega_hat_log;
    logs.F_actual_1_log     = F_actual_1_log;
    logs.F_actual_2_log     = F_actual_2_log;
    logs.omega_actual_1_log = omega_actual_1_log;
    logs.omega_actual_2_log = omega_actual_2_log;
    logs.theta_actual_1_log = theta_actual_1_log;
    logs.theta_actual_2_log = theta_actual_2_log;
    logs.T_delay            = T_delay;
end

function x_next = ekf_state_transition_multi(x_prev, u_prev, params, dt)
    y       = x_prev(1);
    v       = x_prev(2);
    Fd1     = x_prev(3);
    Fd1_dot = x_prev(4);
    Fd2     = x_prev(5);
    Fd2_dot = x_prev(6);
    omega1  = max(1e-3, x_prev(7));
    omega2  = 2 * omega1;

    M = params.M; c = params.c; k = params.k;

    x_next = zeros(7, 1);

    x_next(1) = y + v * dt;

    Fd_total = Fd1 + Fd2;
    a_prev   = (Fd_total + u_prev - c * v - k * y) / M;
    x_next(2) = v + a_prev * dt;

    w1_dt     = omega1 * dt;
    x_next(3) = Fd1 * cos(w1_dt) + (Fd1_dot / omega1) * sin(w1_dt);
    x_next(4) = -Fd1 * omega1 * sin(w1_dt) + Fd1_dot * cos(w1_dt);

    w2_dt     = omega2 * dt;
    x_next(5) = Fd2 * cos(w2_dt) + (Fd2_dot / omega2) * sin(w2_dt);
    x_next(6) = -Fd2 * omega2 * sin(w2_dt) + Fd2_dot * cos(w2_dt);

    x_next(7) = omega1;
end

function [x_pred, P_pred, X_sigma_pred, Wm, Wc] = ...
    ukf_predict_step_multi(x_hat_prev, P_prev, u_prev, Q, params, dt)

    n = length(x_hat_prev);

    if isfield(params, 'ukf_alpha') && ~isempty(params.ukf_alpha)
        alpha = params.ukf_alpha;
    else
        alpha = 5e-4;
    end
    kappa = 0;
    beta  = 2;

    lambda = alpha^2 * (n + kappa) - n;
    c      = n + lambda;

    Wm = zeros(2*n+1, 1);
    Wc = zeros(2*n+1, 1);
    Wm(1) = lambda / c;
    Wc(1) = Wm(1) + (1 - alpha^2 + beta);
    Wm(2:end) = 1 / (2*c);
    Wc(2:end) = Wm(2:end);

    P_prev = (P_prev + P_prev.')/2;
    jitter = 1e-12;
    [S, chol_flag] = chol(c * P_prev, 'lower');
    if chol_flag ~= 0
        S = chol(c * (P_prev + jitter*eye(n)), 'lower');
    end

    X_sigma = zeros(n, 2*n+1);
    X_sigma(:,1) = x_hat_prev;
    for i = 1:n
        X_sigma(:, i+1)   = x_hat_prev + S(:,i);
        X_sigma(:, i+1+n) = x_hat_prev - S(:,i);
    end

    X_sigma_pred = zeros(size(X_sigma));
    for j = 1:(2*n+1)
        X_sigma_pred(:,j) = ekf_state_transition_multi(X_sigma(:,j), u_prev, params, dt);
    end

    x_pred = X_sigma_pred * Wm;

    P_pred = Q;
    for j = 1:(2*n+1)
        dx = X_sigma_pred(:,j) - x_pred;
        P_pred = P_pred + Wc(j) * (dx * dx.');
    end
    P_pred = (P_pred + P_pred.')/2;
end

function [x_upd, P_upd] = ukf_update_step_multi( ...
    x_pred, P_pred, X_sigma_pred, Wm, Wc, z_k, u_k, H, D, R)

    n = length(x_pred);
    L = size(X_sigma_pred, 2);

    Z_sigma = zeros(1, L);
    for j = 1:L
        Z_sigma(j) = H * X_sigma_pred(:,j) + D * u_k;
    end

    z_pred = Z_sigma * Wm;

    S   = R;
    Pxz = zeros(n, 1);

    for j = 1:L
        dz = Z_sigma(j) - z_pred;
        dx = X_sigma_pred(:,j) - x_pred;
        S   = S   + Wc(j) * dz * dz';
        Pxz = Pxz + Wc(j) * dx * dz;
    end

    K = Pxz / S;

    x_upd = x_pred + K * (z_k - z_pred);
    P_upd = P_pred - K * S * K.';
    P_upd = (P_upd + P_upd.')/2;
end

function stop = pso_output_function(optimValues, state, h_waitbar, max_iter)
    stop = false;

    if strcmp(state, 'iter')
        current_iter = optimValues.iteration;
        if ishandle(h_waitbar)
            progress = current_iter / max_iter;
            waitbar(progress, h_waitbar, ...
                sprintf('PSO progress: iteration %d / %d (best I_h: %.2f)', ...
                        current_iter, max_iter, optimValues.bestfval));
            drawnow;
        else
            fprintf('User closed waitbar, stopping PSO.\n');
            stop = true;
        end
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
        F_total  = F_d + F_actual;
        a        = (F_total - params.c * v - params.k * y) / params.M;
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
    theta_direction  = sign(F_target);
    if theta_direction == 0, theta_direction = 1; end
    theta_next = mod(theta_actual + theta_direction * omega_next * dt, 2*pi);
end

function [y_next, v_next] = rk4_step(y, v, F_total, p, dt)
    m = p.M; c = p.c; k = p.k;

    accel = @(y_val, v_val) (F_total - c * v_val - k * y_val) / m;

    k1_y = v;                k1_v = accel(y, v);
    k2_y = v + 0.5*dt*k1_v;  k2_v = accel(y + 0.5*dt*k1_y, k2_y);
    k3_y = v + 0.5*dt*k2_v;  k3_v = accel(y + 0.5*dt*k2_y, k3_y);
    k4_y = v + dt*k3_v;      k4_v = accel(y + dt*k3_y, k4_y);

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
        fprintf('System parameters loaded successfully.\n');
    catch
        fprintf('--- Error! Failed to load system parameters from sheet "%s" in file "%s"! ---\n', sheet_params, filename);
        error('Failed to load parameters.');
    end
    y0 = 0.01; v0 = 0;
end

function [t_data, F_d_interp] = load_data(filename, sheet_data)
    fprintf('Loading data from sheet "%s" in file "%s"...\n', sheet_data, filename);
    try
        opts = detectImportOptions(filename, 'Sheet', sheet_data);
        opts.VariableNamingRule = 'preserve';
        T_data = readtable(filename, opts);
        col_names = T_data.Properties.VariableNames;
        if ismember('采样时刻', col_names), t_data = T_data.("采样时刻");
        else, t_data = T_data{:, 1}; end
        if ismember('横向扰动力(单位：N)', col_names), F_d_data = T_data.("横向扰动力(单位：N)");
        else, F_d_data = T_data{:, 2}; end
    catch
        fprintf('--- Error! Failed to load scenario 2 data from sheet "%s" in file "%s"! ---\n', sheet_data, filename);
        error('Failed to read data.');
    end
    invalid_rows = ~isfinite(t_data) | ~isfinite(F_d_data);
    if any(invalid_rows)
        fprintf('Warning: Detected %d invalid data row(s); removed.\n', sum(invalid_rows));
        t_data(invalid_rows)   = [];
        F_d_data(invalid_rows) = [];
    end
    fprintf('Scenario 2 data loaded successfully.\n');
    F_d_interp = @(t_query) spline(t_data, F_d_data, t_query);
end
