% -------------------------------------------------------------------------
% 求解 问题 A - 问题1 (包含所有计算与绘图)
% -------------------------------------------------------------------------

clear; clc; close all; % 清理环境并关闭所有旧窗口

%% 1. 定义系统参数和初始条件
M = 2000.0;     % 车体质量 (kg)
c = 3600.0;     % 等效阻尼 (N·s/m)
k = 7225200.0;  % 等效刚度 (N/m)
m = 100.0;      % 偏心块质量 (kg)
r = 0.2;        % 偏心块半径 (m)
C_act = 2 * r * m; % 作动器力常数 (2rm = 40.0)

% 初始条件 [y(0); y_dot(0)]
Y0 = [0.01; 0]; 
% 求解时间范围
t_span = [0, 10];
T_total = 10; % 总时间 (s)

%% 2. 加载和准备场景1数据 (从 D:\A.xlsx 读取)

filename = 'D:\A.xlsx';
sheet_name = '场景1'; % !!! 如果工作表名不同, 请在此修改 !!!

fprintf('正在从 %s 的 "%s" 工作表加载数据...\n', filename, sheet_name);

try
    % 使用 readtable 读取 Excel，并指定跳过2行表头
    T = readtable(filename, 'Sheet', sheet_name, 'HeaderLines', 2);
    
    % 将 table 转换为 matrix
    data = table2array(T);
    
    if isempty(data)
        error('读取的数据为空，请检查工作表名称和表头设置。');
    end
    
catch ME
    fprintf('--- 错误! 无法读取 Excel 文件! ---\n');
    fprintf('错误信息: %s\n', ME.message);
    error('读取失败。请检查：\n1. 文件是否在 D:\A.xlsx？\n2. 工作表名是否为 "场景1"？\n3. 文件是否被Excel锁定？');
end

% 2.1. 提取输入数据
t_data   = data(:, 1); % 时间 (s)
F_d1     = data(:, 2); % 扰动力 (N)
theta11  = data(:, 3); % 作动器1, 组1 角度 (rad)
theta12  = data(:, 4); % 作动器1, 组2 角度 (rad)
theta21  = data(:, 5); % 作动器2, 组1 角度 (rad)
theta22  = data(:, 6); % 作动器2, 组2 角度 (rad)

fprintf('数据加载成功，共 %d 个时间点。\n', length(t_data));

%% 3. 中间计算 (为求解和绘图做准备)

% 3.1. 数值计算角速度 (omega = d(theta)/dt)
dt = t_data(2) - t_data(1); % 时间步长
omega11 = gradient(theta11, dt);
omega12 = gradient(theta12, dt);
omega21 = gradient(theta21, dt);
omega22 = gradient(theta22, dt);

% 3.2. 计算原始数据点的总控制力 (用于绘图)
F_control_data = C_act * ( ...
    omega11.^2 .* sin(theta11) - ...
    omega12.^2 .* sin(theta12) + ...
    omega21.^2 .* sin(theta21) - ...
    omega22.^2 .* sin(theta22) ...
);

% 3.3. 创建所有插值函数
F_d1_interp    = @(t) interp1(t_data, F_d1, t, 'linear', 'extrap');
theta11_interp = @(t) interp1(t_data, theta11, t, 'linear', 'extrap');
theta12_interp = @(t) interp1(t_data, theta12, t, 'linear', 'extrap');
theta21_interp = @(t) interp1(t_data, theta21, t, 'linear', 'extrap');
theta22_interp = @(t) interp1(t_data, theta22, t, 'linear', 'extrap');
omega11_interp = @(t) interp1(t_data, omega11, t, 'linear', 'extrap');
omega12_interp = @(t) interp1(t_data, omega12, t, 'linear', 'extrap');
omega21_interp = @(t) interp1(t_data, omega21, t, 'linear', 'extrap');
omega22_interp = @(t) interp1(t_data, omega22, t, 'linear', 'extrap');

% 3.4. 创建总控制力插值函数
F_control_interp = @(t) C_act * ( ...
    omega11_interp(t).^2 .* sin(theta11_interp(t)) - ...
    omega12_interp(t).^2 .* sin(theta12_interp(t)) + ...
    omega21_interp(t).^2 .* sin(theta21_interp(t)) - ...
    omega22_interp(t).^2 .* sin(theta22_interp(t)) ...
);

%% 4. 定义ODE的状态空间函数
% y'' = (F_RHS(t) - c*y' - k*y) / M
ode_func_1_1 = @(t, Y) [ Y(2); (F_d1_interp(t) - c*Y(2) - k*Y(1)) / M ];
ode_func_1_2 = @(t, Y) [ Y(2); (F_d1_interp(t) + F_control_interp(t) - c*Y(2) - k*Y(1)) / M ];

%% 5. 求解 ODE
fprintf('正在求解 问题 1.1 (无控制)...\n');
[t_sol_1, Y_sol_1] = ode45(ode_func_1_1, t_span, Y0);
fprintf('求解完成。\n');

fprintf('正在求解 问题 1.2 (有控制)...\n');
[t_sol_2, Y_sol_2] = ode45(ode_func_1_2, t_span, Y0);
fprintf('求解完成。\n');

%% 6. 后处理：计算加速度和振动指数
% 提取位移和速度
y_1 = Y_sol_1(:, 1);
ydot_1 = Y_sol_1(:, 2);
y_2 = Y_sol_2(:, 1);
ydot_2 = Y_sol_2(:, 2);

% 计算加速度
F_d1_sol_1 = F_d1_interp(t_sol_1);
a_y_1 = (F_d1_sol_1 - c*ydot_1 - k*y_1) / M;

F_d1_sol_2 = F_d1_interp(t_sol_2);
F_ctrl_sol_2 = F_control_interp(t_sol_2);
a_y_2 = (F_d1_sol_2 + F_ctrl_sol_2 - c*ydot_2 - k*y_2) / M;

% 计算振动指数
I_h_1 = (1 / T_total) * trapz(t_sol_1, a_y_1.^2);
I_h_2 = (1 / T_total) * trapz(t_sol_2, a_y_2.^2);

fprintf('\n--- 结果 ---\n');
fprintf('问题 1.1 (无控制) 振动指数 I_h: %f\n', I_h_1);
fprintf('问题 1.2 (有控制) 振动指数 I_h: %f\n', I_h_2);


%% 7. 绘制所有图像
fprintf('\n正在生成所有图像...\n');

% --- 输入数据图 ---
figure('Name', '输入数据 (1): 扰动力');
plot(t_data, F_d1, 'k-');
title('输入: 横向扰动力 (F_{d1})');
xlabel('时间 (s)');
ylabel('力 (N)');
grid on;

figure('Name', '输入数据 (2): 作动器角度 (Theta)');
subplot(2, 2, 1);
plot(t_data, theta11, 'r-');
title('Act 1, Grp 1 角度 (\theta_{11})');
xlabel('时间 (s)'); ylabel('角度 (rad)'); grid on;
subplot(2, 2, 2);
plot(t_data, theta12, 'b-');
title('Act 1, Grp 2 角度 (\theta_{12})');
xlabel('时间 (s)'); ylabel('角度 (rad)'); grid on;
subplot(2, 2, 3);
plot(t_data, theta21, 'r-');
title('Act 2, Grp 1 角度 (\theta_{21})');
xlabel('时间 (s)'); ylabel('角度 (rad)'); grid on;
subplot(2, 2, 4);
plot(t_data, theta22, 'b-');
title('Act 2, Grp 2 角度 (\theta_{22})');
xlabel('时间 (s)'); ylabel('角度 (rad)'); grid on;
sgtitle('输入: 4个作动器角度'); % Super Title

% --- 中间计算图 ---
figure('Name', '中间计算 (1): 角速度 (Omega)');
subplot(2, 2, 1);
plot(t_data, omega11, 'r-');
title('Act 1, Grp 1 角速度 (\omega_{11})');
xlabel('时间 (s)'); ylabel('角速度 (rad/s)'); grid on;
subplot(2, 2, 2);
plot(t_data, omega12, 'b-');
title('Act 1, Grp 2 角速度 (\omega_{12})');
xlabel('时间 (s)'); ylabel('角速度 (rad/s)'); grid on;
subplot(2, 2, 3);
plot(t_data, omega21, 'r-');
title('Act 2, Grp 1 角速度 (\omega_{21})');
xlabel('时间 (s)'); ylabel('角速度 (rad/s)'); grid on;
subplot(2, 2, 4);
plot(t_data, omega22, 'b-');
title('Act 2, Grp 2 角速度 (\omega_{22})');
xlabel('时间 (s)'); ylabel('角速度 (rad/s)'); grid on;
sgtitle('中间计算: 4个作动器角速度');

figure('Name', '中间计算 (2): 总控制力');
plot(t_data, F_control_data, 'm-');
title('中间计算: 总控制力 (F_{control})');
xlabel('时间 (s)');
ylabel('力 (N)');
grid on;

% --- 结果图 (无控制) ---
figure('Name', '结果 (1.1): 无控制');
subplot(2, 1, 1);
plot(t_sol_1, y_1, 'b-');
title('1.1) 横向位移 (无控制)');
xlabel('时间 (s)'); ylabel('位移 (m)'); grid on;
subplot(2, 1, 2);
plot(t_sol_1, a_y_1, 'r-');
title('1.1) 横向加速度 (无控制)');
xlabel('时间 (s)'); ylabel('加速度 (m/s^2)'); grid on;

% --- 结果图 (有控制) ---
figure('Name', '结果 (1.2): 有控制');
subplot(2, 1, 1);
plot(t_sol_2, y_2, 'b-');
title('1.2) 横向位移 (有控制)');
xlabel('时间 (s)'); ylabel('位移 (m)'); grid on;
subplot(2, 1, 2);
plot(t_sol_2, a_y_2, 'r-');
title('1.2) 横向加速度 (有控制)');
xlabel('时间 (s)'); ylabel('加速度 (m/s^2)'); grid on;

% --- 结果对比图 ---
figure('Name', '结果 (对比): 位移');
plot(t_sol_1, y_1, 'g:', 'LineWidth', 1.5);
hold on;
plot(t_sol_2, y_2, 'b-', 'LineWidth', 1.5);
title('结果对比: 横向位移');
xlabel('时间 (s)');
ylabel('位移 (m)');
legend('无控制 (1.1)', '有控制 (1.2)', 'Location', 'best');
grid on;
hold off;

figure('Name', '结果 (对比): 加速度');
plot(t_sol_1, a_y_1, 'g:', 'LineWidth', 1);
hold on;
plot(t_sol_2, a_y_2, 'r-', 'LineWidth', 1);
title('结果对比: 横向加速度');
xlabel('时间 (s)');
ylabel('加速度 (m/s^2)');
legend('无控制 (1.1)', '有控制 (1.2)', 'Location', 'best');
grid on;
hold off;

fprintf('所有图像绘制完成。\n');