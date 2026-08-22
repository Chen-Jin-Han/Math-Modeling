% -------------------------------------------------------------------------
% 求解 问题 A - 问题1
% -------------------------------------------------------------------------

clear; clc; close all;

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

%% 2. 加载和准备场景1数据
% 注意：假设CSV文件的前两行是表头（中文和英文）
% 我们使用 dlmread 从第3行（索引为2）开始读取
filename = 'Problem A：Data.xlsx - 场景1.csv';
try
    % dlmread(filename, delimiter, R_offset, C_offset)
    % 从第2行（跳过2行表头），第0列开始读
    data = dlmread(filename, ',', 2, 0); 
catch
    error('无法读取CSV文件。请确保文件与脚本在同一目录，并且表头为2行。');
end

% 提取数据列
t_data   = data(:, 1); % 时间 (s)
F_d1     = data(:, 2); % 扰动力 (N)
theta11  = data(:, 3); % 作动器1, 组1 角度 (rad)
theta12  = data(:, 4); % 作动器1, 组2 角度 (rad)
theta21  = data(:, 5); % 作动器2, 组1 角度 (rad)
theta22  = data(:, 6); % 作动器2, 组2 角度 (rad)

% 2.1. 数值计算角速度 (omega = d(theta)/dt)
% 我们使用 gradient 函数进行中心差分，更平滑
dt = t_data(2) - t_data(1); % 时间步长
omega11 = gradient(theta11, dt);
omega12 = gradient(theta12, dt);
omega21 = gradient(theta21, dt);
omega22 = gradient(theta22, dt);

% 2.2. 创建插值函数
% 'linear' 线性插值, 'extrap' 允许求解器在 t=10 附近轻微外推
F_d1_interp    = @(t) interp1(t_data, F_d1, t, 'linear', 'extrap');
theta11_interp = @(t) interp1(t_data, theta11, t, 'linear', 'extrap');
theta12_interp = @(t) interp1(t_data, theta12, t, 'linear', 'extrap');
theta21_interp = @(t) interp1(t_data, theta21, t, 'linear', 'extrap');
theta22_interp = @(t) interp1(t_data, theta22, t, 'linear', 'extrap');
omega11_interp = @(t) interp1(t_data, omega11, t, 'linear', 'extrap');
omega12_interp = @(t) interp1(t_data, omega12, t, 'linear', 'extrap');
omega21_interp = @(t) interp1(t_data, omega21, t, 'linear', 'extrap');
omega22_interp = @(t) interp1(t_data, omega22, t, 'linear', 'extrap');


%% 3. 定义ODE的状态空间函数
% 状态向量 Y = [y; y'] = [Y(1); Y(2)]
% 输出 dYdt = [y'; y''] = [Y(2); y'']
% M*y'' + c*y' + k*y = F_RHS(t)
% y'' = (F_RHS(t) - c*y' - k*y) / M
% y'' = (F_RHS(t) - c*Y(2) - k*Y(1)) / M

% 3.1. 问题 1.1) 的ODE函数 (无控制)
% F_RHS(t) = F_d1(t)
ode_func_1_1 = @(t, Y) [ Y(2); 
                       (F_d1_interp(t) - c*Y(2) - k*Y(1)) / M ];

% 3.2. 问题 1.2) 的ODE函数 (有控制)
% F_RHS(t) = F_d1(t) + F_control(t)
F_control_interp = @(t) C_act * ( ...
    omega11_interp(t).^2 .* sin(theta11_interp(t)) - ...
    omega12_interp(t).^2 .* sin(theta12_interp(t)) + ...
    omega21_interp(t).^2 .* sin(theta21_interp(t)) - ...
    omega22_interp(t).^2 .* sin(theta22_interp(t)) ...
);
ode_func_1_2 = @(t, Y) [ Y(2);
                       (F_d1_interp(t) + F_control_interp(t) - c*Y(2) - k*Y(1)) / M ];


%% 4. 求解 ODE
fprintf('正在求解 问题 1.1 (无控制)...\n');
[t_sol_1, Y_sol_1] = ode45(ode_func_1_1, t_span, Y0);
fprintf('求解完成。\n');

fprintf('正在求解 问题 1.2 (有控制)...\n');
[t_sol_2, Y_sol_2] = ode45(ode_func_1_2, t_span, Y0);
fprintf('求解完成。\n');

%% 5. 后处理：计算加速度和振动指数
% 提取位移 y(t)
y_1 = Y_sol_1(:, 1);
y_2 = Y_sol_2(:, 1);

% 提取速度 y_dot(t)
ydot_1 = Y_sol_1(:, 2);
ydot_2 = Y_sol_2(:, 2);

% 5.1. 计算加速度 a_y = y_ddot
% a_y = y'' = (F_RHS(t) - c*y' - k*y) / M
% 我们需要在求解器返回的时间点 t_sol_1 和 t_sol_2 上计算 F_RHS
F_d1_sol_1 = F_d1_interp(t_sol_1);
a_y_1 = (F_d1_sol_1 - c*ydot_1 - k*y_1) / M;

F_d1_sol_2 = F_d1_interp(t_sol_2);
F_ctrl_sol_2 = F_control_interp(t_sol_2);
a_y_2 = (F_d1_sol_2 + F_ctrl_sol_2 - c*ydot_2 - k*y_2) / M;

% 5.2. 计算振动指数 I_h = (1/T) * integral(a_y^2 dt)
% 使用 trapz (梯形法则) 进行数值积分
I_h_1 = (1 / T_total) * trapz(t_sol_1, a_y_1.^2);
I_h_2 = (1 / T_total) * trapz(t_sol_2, a_y_2.^2);

fprintf('\n--- 结果 ---\n');
fprintf('问题 1.1 (无控制) 振动指数 I_h: %f\n', I_h_1);
fprintf('问题 1.2 (有控制) 振动指数 I_h: %f\n', I_h_2);


%% 6. 绘图
% 问题 1.1 的结果
figure('Name', '问题 1.1 结果 (无控制)');
subplot(2, 1, 1);
plot(t_sol_1, y_1, 'b-');
title('1.1) 横向位移 (无控制)');
xlabel('时间 (s)');
ylabel('位移 (m)');
grid on;

subplot(2, 1, 2);
plot(t_sol_1, a_y_1, 'r-');
title('1.1) 横向加速度 (无控制)');
xlabel('时间 (s)');
ylabel('加速度 (m/s^2)');
grid on;

% 问题 1.2 的结果
figure('Name', '问题 1.2 结果 (有控制)');
subplot(2, 1, 1);
plot(t_sol_2, y_2, 'b-');
title('1.2) 横向位移 (有控制)');
xlabel('时间 (s)');
ylabel('位移 (m)');
grid on;

subplot(2, 1, 2);
plot(t_sol_2, a_y_2, 'r-');
title('1.2) 横向加速度 (有控制)');
xlabel('时间 (s)');
ylabel('加速度 (m/s^2)');
grid on;