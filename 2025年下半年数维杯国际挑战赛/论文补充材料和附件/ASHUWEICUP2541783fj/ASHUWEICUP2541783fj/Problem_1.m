function Problem_1()
    clear; clc; close all;
    
    params = struct();
    params.M = 2000.0;
    params.c = 3600.0;
    params.k = 7225200.0;
    params.m_ecc = 100.0;
    params.r = 0.2;
    params.C_act = 2 * params.r * params.m_ecc;
    
    y0 = 0.01;
    v0 = 0;
    
    T_total = 10;
    
    filename = 'Problem A：Data.xlsx';
    sheet_name = '场景1';
    
    fprintf('Loading data from file %s, sheet "%s"...\n', filename, sheet_name);
    
    try
        T = readtable(filename, 'Sheet', sheet_name, 'HeaderLines', 2);
        data = table2array(T);
        if isempty(data)
            error('Read data is empty. Please check the sheet name and header settings.');
        end
    catch ME
        fprintf('--- Error! Failed to read Excel file! ---\n');
        fprintf('Error message: %s\n', ME.message);
        error('Read failed. Please check:\n1. Is the file at D:\\A.xlsx?\n2. Is the sheet name "场景1"?\n3. Is the file locked by Excel?');
    end
    
    t_data    = data(:, 1);
    F_d1      = data(:, 2);
    theta11   = data(:, 3);
    theta12   = data(:, 4);
    theta21   = data(:, 5);
    theta22   = data(:, 6);
    
    fprintf('Data loaded successfully, total %d time points.\n', length(t_data));
    
    omega11 = gradient(unwrap(theta11), t_data);
    omega12 = gradient(unwrap(theta12), t_data);
    omega21 = gradient(unwrap(theta21), t_data);
    omega22 = gradient(unwrap(theta22), t_data);
    
    F_d1_interp    = @(t) spline(t_data, F_d1, t);
    theta11_interp = @(t) spline(t_data, theta11, t);
    theta12_interp = @(t) spline(t_data, theta12, t);
    theta21_interp = @(t) spline(t_data, theta21, t);
    theta22_interp = @(t) spline(t_data, theta22, t);
    omega11_interp = @(t) spline(t_data, omega11, t);
    omega12_interp = @(t) spline(t_data, omega12, t);
    omega21_interp = @(t) spline(t_data, omega21, t);
    omega22_interp = @(t) spline(t_data, omega22, t);
    
    F_control_PYTHON_LOGIC = @(t) params.C_act * ( ...
        (omega11_interp(t).^2 .* sin(theta11_interp(t))) + ...
        (omega12_interp(t).^2 .* sin(theta12_interp(t))) + ...
        (omega21_interp(t).^2 .* sin(theta21_interp(t))) + ...
        (omega22_interp(t).^2 .* sin(theta22_interp(t))) ...
    );
    
    F_total_no_control   = @(t) F_d1_interp(t);
    F_total_with_control = @(t) F_d1_interp(t) + F_control_PYTHON_LOGIC(t);
    
    Y0 = [y0; v0];
    
    t_span = t_data;
    
    options = odeset('RelTol', 1e-6, 'AbsTol', 1e-9);
    
    fprintf('Solving Problem 1.1 (no control, ode45)...\n');
    ode_no_control = @(t, Y) vehicle_ode(t, Y, F_total_no_control, params);
    [t, Y_1] = ode45(ode_no_control, t_span, Y0, options);
    y_1 = Y_1(:, 1);
    v_1 = Y_1(:, 2);
    fprintf('Solving finished.\n');
    
    fprintf('Solving Problem 1.2 (with control, ode45, Python force model)...\n');
    ode_with_control = @(t, Y) vehicle_ode(t, Y, F_total_with_control, params);
    [~, Y_2] = ode45(ode_with_control, t_span, Y0, options);
    y_2 = Y_2(:, 1);
    v_2 = Y_2(:, 2);
    fprintf('Solving finished.\n');
    
    fprintf('Computing acceleration and vibration index...\n');
    
    F_d1_at_t = F_d1_interp(t);
    F_ctrl_at_t = F_control_PYTHON_LOGIC(t);
    
    a_y_1 = (F_d1_at_t - params.c * v_1 - params.k * y_1) / params.M;
    
    F_total_2_at_t = F_d1_at_t + F_ctrl_at_t;
    a_y_2 = (F_total_2_at_t - params.c * v_2 - params.k * y_2) / params.M;
    
    I_h_1 = trapz(t, a_y_1.^2) / (t(end) - t(1));
    I_h_2 = trapz(t, a_y_2.^2) / (t(end) - t(1));
    
    fprintf('\n--- Results (ode45 solver) ---\n');
    fprintf('Problem 1.1 (no control) vibration index I_h: %f\n', I_h_1);
    fprintf('Problem 1.2 (with control) vibration index I_h: %f\n', I_h_2);
    
    fprintf('\nGenerating all figures...\n');
    
    figure('Name', 'Results (1.1): No control (ode45)');
    subplot(2, 1, 1);
    plot(t, y_1, 'b-');
    title('1.1) Lateral displacement (no control)');
    xlabel('Time (s)'); ylabel('Displacement (m)'); grid on;
    subplot(2, 1, 2);
    plot(t, a_y_1, 'r-');
    title('1.1) Lateral acceleration (no control)');
    xlabel('Time (s)'); ylabel('Acceleration (m/s^2)'); grid on;
    
    figure('Name', 'Results (1.2): With control (ode45, Python force model)');
    subplot(2, 1, 1);
    plot(t, y_2, 'b-');
    title('1.2) Lateral displacement (with control)');
    xlabel('Time (s)'); ylabel('Displacement (m)'); grid on;
    subplot(2, 1, 2);
    plot(t, a_y_2, 'r-');
    title('1.2) Lateral acceleration (with control)');
    xlabel('Time (s)'); ylabel('Acceleration (m/s^2)'); grid on;
    
    figure('Name', 'Results (comparison): Displacement (ode45)');
    plot(t, y_1, 'g:', 'LineWidth', 1.5);
    hold on;
    plot(t, y_2, 'b-', 'LineWidth', 1.5);
    title('Comparison: Lateral displacement');
    xlabel('Time (s)');
    ylabel('Displacement (m)');
    legend('No control (1.1)', 'With control (1.2)', 'Location', 'best');
    grid on;
    hold off;
    
    figure('Name', 'Results (comparison): Acceleration (ode45)');
    plot(t, a_y_1, 'g:', 'LineWidth', 1);
    hold on;
    plot(t, a_y_2, 'r-', 'LineWidth', 1);
    title('Comparison: Lateral acceleration');
    xlabel('Time (s)');
    ylabel('Acceleration (m/s^2)');
    legend('No control (1.1)', 'With control (1.2)', 'Location', 'best');
    grid on;
    hold off;
    fprintf('All figures generated.\n');
end

function dYdt = vehicle_ode(t, Y, F_total_func, p)
    F_total = F_total_func(t);
    dYdt = zeros(2, 1);
    dYdt(1) = Y(2);
    dYdt(2) = (F_total - p.c * Y(2) - p.k * Y(1)) / p.M;
end
