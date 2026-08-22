%% 参数设置
clear; % 清除所有变量
clc;   % 清除命令窗口
close all; % 关闭所有图形窗口

num_lanes = 8;          % 车道总数
lane_width = 4;         % 单车道宽度（米）
road_length = 100;      % 道路总长度（米）
lane_endpoints = [40, 53, 66, 80, 100, 100, 100, 100];  % 各车道终点位置
simulation_time = 6000;  % 总仿真时间（秒）
dt = 0.2;               % 仿真时间步长（秒）
time_ratio = 10;       % 仿真速度控制参数
speed_limit = 15;       % 最高车速（米/秒）
min_gap = 4;            % 最小安全间距（米）
lc_duration = 1;        % 变道持续时间（秒）
off_center_threshold = lane_width / 4;  % 横向偏离阈值（米）
off_center_duration = 10 * dt;          % 最大偏离持续时间（秒）
density_threshold = 6;  % 5-8车道允许变道的车辆密度阈值
count = 0 ; % 计数器
passing_time = [];      % 记录每辆车通过时间
elapsed_real_time =0 
%% 初始化图形窗口
figure;
set(gcf, 'Position', [100 100 1000 400]);  % 设置窗口尺寸
axis([0 road_length 0 (num_lanes+1)*lane_width]);
daspect([1 1 1]);       % 等比例坐标轴
set(gca, 'Box', 'on');  % 显示坐标轴边框
hold on;

% 绘制车道分隔线
for lane = 1:num_lanes
    y = (lane)*lane_width;
    line([0 road_length], [y y], 'Color', [0.5 0.5 0.5], 'LineWidth', 1);
    
    % 绘制短道终点标识
    if lane <= 4
        lane_end = lane_endpoints(lane);
        rectangle('Position', [lane_end-0.5, (lane-1)*lane_width, 1, lane_width],...
                 'FaceColor', [1 0.8 0.8], 'EdgeColor', 'r');
    end
end

% 绘制收费站入口
rectangle('Position', [0 0 5 num_lanes*lane_width],...
         'FaceColor', [0.8 1 0.8], 'EdgeColor', 'g');
xlabel('道路位置（米）');
title('改进版变道决策模型仿真');
hold off;

%% 车辆结构体
vehicles = struct(...
    'position', {},...   % 车辆位置 [x,y]
    'speed', {},  ...     % 当前速度（米/秒）
    'length', {},  ...    % 车辆长度（米）
    'width', {},  ...     % 车辆宽度（米）
    'lane', {},  ...     % 当前所在车道
    'target_lane', {}, ...% 目标车道
    'lc_progress', {},... % 变道进度 (0~1)
    'color', {},  ...     % 车辆颜色
    'handle', {},  ...    % 图形句柄
    'waiting', {},  ...   % 是否在终点等待
    'lane_center', {}, ...% 车道中央y坐标
    'emergency_stop', {},... % 紧急制动状态
    'off_center_time', {},... % 偏离车道计时
    'is_first_vehicle', {}, ...% 是否为首车
    'can_change_lane', {}, ...% 是否允许变道
    'spawn_time', {});% 车辆生成时间
flag_some = 1
%% 主仿真循环
next_spawn_times = 3 + 2*rand(1, num_lanes); % 初始生成时间
start_time = tic;%true clock
current_sim_time = 0
while true
    %elapsed_real_time = toc(start_time);%运行时间
    %elapsed_real_time = dt;
    %current_sim_time = elapsed_real_time * time_ratio %世界时间,时钟
    current_sim_time = current_sim_time + dt
    if current_sim_time >= simulation_time
        break;
    end

    %% 生成新车辆
    for lane = 1:num_lanes
        lane_end = lane_endpoints(lane);
        
        % 短道车辆数量限制
        if lane_end == 50
            max_vehicles = 9;
        elseif lane_end == 60
            max_vehicles = 11;
        elseif lane_end == 70
            max_vehicles = 12;
        elseif lane_end == 80
            max_vehicles = 15;
        else
            max_vehicles = inf;
        end
        
        % 检查当前车道车辆数
        lane_vehs = vehicles(arrayfun(@(v) v.lane == lane, vehicles));
        if length(lane_vehs) >= max_vehicles
            continue;
        end
        
        if current_sim_time >= next_spawn_times(lane)
            % 生成车辆参数
            speed_init = 4 + rand();
            vehicle_len = 3 + 2*rand();
            vehicle_wid = 1.5 + 0.7*rand();
            
            % 短道首车特殊处理
            if lane <= 4 && isempty(lane_vehs)
                vehicle_len = 1;  % 缩短首车长度
            end
            
            color = rand(1,3);
            lane_center = (lane-1)*lane_width + lane_width/2 - vehicle_wid/2;
            is_first_vehicle = isempty(lane_vehs);
            
            % 绘制车辆图形
            h = rectangle('Position', [0, lane_center, vehicle_len, vehicle_wid],...
                'FaceColor', color, 'EdgeColor', 'k');
            
            % 短道首车隐身
            if is_first_vehicle && lane <=4
                set(h, 'Visible', 'off');
            end
            
            % 记录车辆信息
            vehicles(end+1) = struct(...
                'position', [0, lane_center], 'speed', speed_init,...
                'length', vehicle_len, 'width', vehicle_wid, 'lane', lane,...
                'target_lane', lane, 'lc_progress', 0, 'color', color, 'handle', h,...
                'waiting', false, 'lane_center', lane_center, 'emergency_stop', false,...
                'off_center_time', 0, 'is_first_vehicle', is_first_vehicle, 'can_change_lane', false,'spawn_time', current_sim_time);
            
            next_spawn_times(lane) = current_sim_time + 3 + 2*rand();
        end
    end

    %% 更新车辆状态
    to_delete = [];
    for v_idx = 1:length(vehicles)
        current = vehicles(v_idx);
        lane_idx = current.lane;
        
        % ==== 变道权限控制 ====
        if lane_idx >= 6
            % 统计当前车道车辆数
            same_lane_vehs = vehicles(arrayfun(@(v) v.lane == lane_idx, vehicles));
            vehicles(v_idx).can_change_lane = (length(same_lane_vehs) > density_threshold);
        else
            % 1-4车道原逻辑：驶过5米后允许变道
            vehicles(v_idx).can_change_lane = (current.position(1) >= 5);
        end

        % 到达短道终点的处理
        if lane_idx <= 4
            lane_end = lane_endpoints(lane_idx);
            if current.position(1) >= lane_end - current.length
                if ~current.waiting
                    vehicles(v_idx).waiting = true;
                    vehicles(v_idx).speed = 0;
                end
                continue;
            end
        end

        % 首车逻辑
        if current.is_first_vehicle
            new_x = current.position(1) + current.speed * dt;
            vehicles(v_idx).position = [new_x, current.position(2)];
            set(current.handle, 'Position', [new_x, current.position(2), current.length, current.width]);
            continue;
        end

        % 变道控制
        if current.lc_progress > 0
            new_lc_progress = current.lc_progress + dt/lc_duration;
            if new_lc_progress >= 1
                vehicles(v_idx).lane = current.target_lane;
                vehicles(v_idx).lc_progress = 0;
                new_lane_center = (current.target_lane-1)*lane_width + lane_width/2 - current.width/2;
                vehicles(v_idx).lane_center = new_lane_center;
                vehicles(v_idx).emergency_stop = false;
            else
                vehicles(v_idx).lc_progress = new_lc_progress;
            end
        else
            % 变道触发决策
            if current.can_change_lane
                % 按车道类型使用不同决策规则
                if current.lane >= 6 && current.lane <= 8
                    % 6-8车道固定概率
                    if rand() < 0.03
                        [can_change, target_lane] = checkLaneChange(v_idx, vehicles,...
                            lane_width, min_gap, speed_limit, num_lanes);
                        if can_change
                            vehicles(v_idx).target_lane = target_lane;
                            vehicles(v_idx).lc_progress = dt/lc_duration;
                        end
                    end
                else
                    % 1-5车道风险系数决策
                    same_lane_vehs = vehicles(arrayfun(@(v) v.lane == current.lane, vehicles));
                    [front_veh, front_dist] = findFrontVehicle(current, same_lane_vehs);
                    [rear_veh, rear_dist] = findRearVehicle(current, same_lane_vehs);
                    
                    % 处理无穷大距离
                    if isinf(front_dist), front_dist = 1000; end
                    if isinf(rear_dist), rear_dist = 1000; end
                    
                    % 计算风险系数
                    s = 1/(front_dist + rear_dist + eps);  % 防止除以零
                    f = 0.6 + 2*s + 15*s^2;
                    
                    if 0 > f-rand()
                        [can_change, target_lane] = checkLaneChange(v_idx, vehicles,...
                            lane_width, min_gap, speed_limit, num_lanes);
                        if can_change
                            vehicles(v_idx).target_lane = target_lane;
                            vehicles(v_idx).lc_progress = dt/lc_duration;
                        end
                    end
                end
            end
        end

        % 跟车与加速度计算
        target_lane = current.target_lane;
        same_lane_vehs = vehicles(arrayfun(@(v) v.target_lane, vehicles) == target_lane);
        [front_veh, distance] = findFrontVehicle(current, same_lane_vehs);

        if ~isempty(front_veh) && front_veh.speed == 0 && distance < 6  %急停情况
            vehicles(v_idx).speed = 0; 
            vehicles(v_idx).emergency_stop = true;
        else
            if isempty(front_veh)
                acc = (speed_limit - current.speed)/2;
            else
                delta_v = current.speed - front_veh.speed;
                acc = 10*(1 - (current.speed/speed_limit)^4 - ((2 + 1.5*current.speed + current.speed*delta_v/8)/distance)^2);
                acc = max(-5, min(acc, 3));
            end

            new_speed = current.speed + acc*dt;
            new_speed = max(0.1, min(new_speed, speed_limit));
            new_x = current.position(1) + new_speed*dt;

            % 横向位置更新
            if current.lc_progress > 0
                start_y = current.lane_center;
                target_lane_center = (current.target_lane-1)*lane_width + lane_width/2 - current.width/2;
                new_y = start_y + (target_lane_center - start_y)*current.lc_progress;
            else
                new_y = current.lane_center;
            end

            vehicles(v_idx).speed = new_speed;
            vehicles(v_idx).position = [new_x, new_y];
            set(current.handle, 'Position', [new_x, new_y, current.length, current.width]);
        end

        % 超出道路检测
        if current.position(1) > road_length
            to_delete = [to_delete, v_idx];
        end
    end

    % 横向偏离检测
    for v_idx = 1:length(vehicles)
        current = vehicles(v_idx);
        lane_center = (current.lane-1)*lane_width + lane_width/2 - current.width/2;
        deviation = abs(current.position(2) - lane_center);
        
        if deviation > off_center_threshold
            vehicles(v_idx).off_center_time = vehicles(v_idx).off_center_time + dt;
            if vehicles(v_idx).off_center_time > off_center_duration
                to_delete = [to_delete, v_idx];
            end
        else
            vehicles(v_idx).off_center_time = 0;
        end
    end

    % 删除出界车辆
    for i = length(to_delete):-1:1
        passing_time(end+1) = current_sim_time - vehicles(to_delete(i)).spawn_time;
        delete(vehicles(to_delete(i)).handle);
        vehicles(to_delete(i)) = [];
        count = count + 1;
    end

    % 实时性控制
    if flag_some
        pause_time = (dt/time_ratio) - (toc(start_time) - elapsed_real_time);
        if pause_time > 0
            %pause(max(pause_time, 0.001));
            %pause(0.001)
        end
        drawnow limitrate;
    end
end


disp(['总通行车辆数：', num2str(count)]);
if ~isempty(passing_time)
    disp(['平均通过时间：', num2str(mean(passing_time)), ' 秒']);
else
    disp('没有车辆通过，无法计算平均时间');
end

%% 变道检查函数（改进版）
function [can_change, target_lane] = checkLaneChange(v_idx, vehicles, lane_width, min_gap, speed_limit, num_lanes)
    current = vehicles(v_idx);
    can_change = false;
    target_lane = current.lane;

    % ==== 生成候选车道 ====
    if current.lane == 5||current.lane==6
        candidate_lanes = current.lane + 1;  % 5\6道只能向上变道
    elseif  current.lane == 7
        candidate_lanes = [current.lane-1, current.lane+1];  % 7道可双向变道
    elseif current.lane == 8
        candidate_lanes = current.lane - 1;  % 8道只能向下变道
    else
        candidate_lanes = current.lane + 1;  % 1-4道原逻辑
    end
    candidate_lanes = candidate_lanes(candidate_lanes >= 1 & candidate_lanes <= num_lanes);

    predict_dx = current.speed * 0.5;  % 预测插入位置
    predict_x = current.position(1) + predict_dx;

    % 检查每个候选车道
    for lane = candidate_lanes
        lane_vehs = vehicles(arrayfun(@(v) v.target_lane == lane, vehicles));
        front_veh = [];
        rear_veh = [];
        front_dist = inf;
        rear_dist = inf;

        % 查找最近前车和后车
        for i = 1:length(lane_vehs)
            dx = lane_vehs(i).position(1) - predict_x;
            if dx > 0 && dx < front_dist
                front_veh = lane_vehs(i);
                front_dist = dx;
            elseif dx < 0 && -dx < rear_dist
                rear_veh = lane_vehs(i);
                rear_dist = -dx;
            end
        end

        % 安全距离检查
        front_safe = front_dist > min_gap + 0.2*speed_limit;  % 前距>7米
        rear_safe = rear_dist > min_gap + 0.3*speed_limit;    % 后距>8.5米

        if front_safe && rear_safe
            target_lane = lane;
            can_change = true;
            return;
        end
    end
end

%% 前车查找函数
function [front_veh, distance] = findFrontVehicle(current, candidates)
    if isempty(candidates)
        front_veh = [];
        distance = inf;
        return;
    end
    x_positions = arrayfun(@(v) v.position(1), candidates);
    front_indices = x_positions > current.position(1);
    if any(front_indices)
        front_vehs = candidates(front_indices);
        front_x = arrayfun(@(v) v.position(1), front_vehs);
        [min_distance, idx] = min(front_x - current.position(1));
        front_veh = front_vehs(idx);
        distance = min_distance;
    else
        front_veh = [];
        distance = inf;
    end
end

%% 后车查找函数
function [rear_veh, distance] = findRearVehicle(current, candidates)
    if isempty(candidates)
        rear_veh = [];
        distance = inf;
        return;
    end
    x_positions = arrayfun(@(v) v.position(1), candidates);
    rear_indices = x_positions < current.position(1);
    if any(rear_indices)
        rear_vehs = candidates(rear_indices);
        rear_x = arrayfun(@(v) v.position(1), rear_vehs);
        [max_distance, idx] = max(current.position(1) - rear_x);
        rear_veh = rear_vehs(idx);
        distance = max_distance;
    else
        rear_veh = [];
        distance = inf;
    end
end    



