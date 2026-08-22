%% 双侧合并模型代码（高级功能集成版）
% 版本：最终集成版
% 规则:
% 1. [移植] 1,2,7,8号道的隐形头车在仿真开始前确定性地预生成。
% 2. [移植] 仿真过程中生成的车辆均为普通车辆，到达过程服从泊松分布。
% 3. [移植] 所有非首车都有100%意愿向道路中心变道，无冷却。
% 4. [移植] 3-6号中央车道直行，最小安全跟车距离缩短40%。
% 5. [移植] 判断变道时，对后车的安全距离要求也缩短40%。
% 6. [移植] 变道轨迹采用平滑的五次多项式模型。
% 7. [移植] 增加了拥堵计时器和可视化。

%% 参数设置
num_lanes = 8;          % 车道总数
lane_width = 4;         % 单车道宽度（米）
road_length = 100;      % 道路总长度（米）
lane_endpoints = [45, 80, 100, 100, 100, 100, 80, 45];  % [双侧] 各车道终点位置
simulation_time = 600;  % 总仿真时间（秒）
dt = 0.2;               % 仿真时间步长（秒）
time_ratio = 5;       % 仿真速度控制参数
speed_limit = 15;       % 最高车速（米/秒）
min_gap = 4;            % [移植] 最小安全间距（米）
lc_duration = 1;      % [移植] 变道持续时间（秒）
off_center_threshold = lane_width / 4;
off_center_duration = 10 * dt;
density_threshold = 6;
count = 0;
passing_time = [];
passing_congestion_time = []; % [移植]

% [移植] 定义每条车道的平均车辆到达率 (lambda, 单位: 辆/秒)
mean_arrival_rate = [0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35]; 

%% 初始化图形窗口
figure; 
set(gcf, 'Position', [100 100 1000 400]);
axis([0 road_length 0 (num_lanes+1)*lane_width]);
daspect([1 1 1]);
set(gca, 'Box', 'on');
hold on;

for lane = 1:num_lanes
    y = (lane)*lane_width;
    line([0 road_length], [y y], 'Color', [0.5 0.5 0.5], 'LineWidth', 1);
    
    % [双侧] 绘制短道终点标识
    if ismember(lane, [1,2,7,8])
        lane_end = lane_endpoints(lane);
        rectangle('Position', [lane_end-0.5, (lane-1)*lane_width, 1, lane_width],...
                 'FaceColor', [1 0.8 0.8], 'EdgeColor', 'r');
    end
end

rectangle('Position', [0 0 5 num_lanes*lane_width], 'FaceColor', [0.8 1 0.8], 'EdgeColor', 'g');
xlabel('道路位置（米）');
title('双侧合并仿真（高级功能集成版）');
hold off;

%% 车辆结构体
vehicles = struct(...
    'position', {},...
    'speed', {},...
    'length', {},...
    'width', {},...
    'lane', {},...
    'target_lane', {},...
    'lc_progress', {},...
    'color', {},...
    'handle', {},...
    'timer_handle', {},... % [移植]
    'waiting', {},...
    'lane_center', {},...
    'emergency_stop', {},...
    'off_center_time', {},...
    'is_first_vehicle', {},...
    'can_change_lane', {},...
    'spawn_time', {},...
    'congestion_time', {}); % [移植]

%% [移植] 头车预生成模块
short_lanes = [1, 2, 7, 8]; % [双侧] 定义短车道
for lane = short_lanes
    lane_end = lane_endpoints(lane);
    vehicle_len = 1;
    initial_x = lane_end - vehicle_len;
    speed_init = 0;
    vehicle_wid = 1.5;
    lane_center = (lane-1)*lane_width + lane_width/2 - vehicle_wid/2;
    
    h = rectangle('Position', [initial_x, lane_center, vehicle_len, vehicle_wid], 'Visible', 'off');
    timer_h = text(initial_x + vehicle_len/2, lane_center + vehicle_wid/2, '', 'Visible', 'off');
    
    vehicles(end+1) = struct(...
        'position', [initial_x, lane_center], 'speed', speed_init,...
        'length', vehicle_len, 'width', vehicle_wid, 'lane', lane,...
        'target_lane', lane, 'lc_progress', 0, 'color', [0 0 0], 'handle', h,...
        'timer_handle', timer_h, ...
        'waiting', true, 'lane_center', lane_center, 'emergency_stop', true,...
        'off_center_time', 0, 'is_first_vehicle', true, 'can_change_lane', false,...
        'spawn_time', 0, 'congestion_time', inf);
end

%% 主仿真循环
% [移植] 根据到达率为每条车道生成初始的下一辆车到达时间
next_spawn_times = zeros(1, num_lanes);
for i = 1:num_lanes
    if mean_arrival_rate(i) > 0
        mean_headway = 1 / mean_arrival_rate(i);
        next_spawn_times(i) = exprnd(mean_headway);
    else
        next_spawn_times(i) = inf;
    end
end

current_sim_time = 0;

while true
    current_sim_time = current_sim_time + dt;
    if current_sim_time >= simulation_time, break; end

    %% 生成新车辆
    for lane = 1:num_lanes
        % [双侧] 车辆数量限制逻辑
        if ismember(lane, [1, 8]), max_vehicles = 9;
        elseif ismember(lane, [2, 7]), max_vehicles = 12;
        else, max_vehicles = inf;
        end
        
        lane_vehs = vehicles(arrayfun(@(v) v.lane == lane, vehicles));
        if length(lane_vehs) >= max_vehicles, continue; end
        
        if current_sim_time >= next_spawn_times(lane)
            % [移植] 所有仿真中生成的都是普通车辆
            is_first_vehicle = false;
            vehicle_len = 3 + 2*rand();
            initial_x = 0;
            speed_init = 4 + rand();

            vehicle_wid = 1.5 + 0.7*rand();
            color = rand(1,3);
            lane_center = (lane-1)*lane_width + lane_width/2 - vehicle_wid/2;
            
            h = rectangle('Position', [initial_x, lane_center, vehicle_len, vehicle_wid], 'FaceColor', color, 'EdgeColor', 'k');
            
            timer_h = text(initial_x + vehicle_len/2, lane_center + vehicle_wid/2, '0.0s', ...
                'Color', 'k', 'FontSize', 8, 'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle', 'Visible', 'off');

            vehicles(end+1) = struct(...
                'position', [initial_x, lane_center], 'speed', speed_init,...
                'length', vehicle_len, 'width', vehicle_wid, 'lane', lane,...
                'target_lane', lane, 'lc_progress', 0, 'color', color, 'handle', h,...
                'timer_handle', timer_h, ...
                'waiting', false, 'lane_center', lane_center, 'emergency_stop', false,...
                'off_center_time', 0, 'is_first_vehicle', is_first_vehicle, 'can_change_lane', false,...
                'spawn_time', current_sim_time, 'congestion_time', 0);
             
            if mean_arrival_rate(lane) > 0
                mean_headway = 1 / mean_arrival_rate(lane);
                time_gap = exprnd(mean_headway);
                next_spawn_times(lane) = current_sim_time + time_gap;
            else
                next_spawn_times(lane) = inf;
            end
        end
    end

    %% 更新车辆状态
    to_delete = [];
    for v_idx = 1:length(vehicles)
        
        current = vehicles(v_idx);
        lane_idx = current.lane;
        
        % [双侧] 变道权限控制
        if ismember(lane_idx, [3,4,5,6]) % 中央车道
            same_lane_vehs = vehicles(arrayfun(@(v) v.lane == lane_idx, vehicles));
            vehicles(v_idx).can_change_lane = (length(same_lane_vehs) > density_threshold);
        else % 两侧车道
            vehicles(v_idx).can_change_lane = (current.position(1) >= 5);
        end

        % [双侧] 普通车辆在短道终点停止
        if ismember(lane_idx, short_lanes) && ~current.is_first_vehicle
            lane_end = lane_endpoints(lane_idx);
            if current.position(1) >= lane_end - current.length
                if ~current.waiting
                    vehicles(v_idx).waiting = true;
                    vehicles(v_idx).speed = 0;
                end
                if vehicles(v_idx).speed == 0, vehicles(v_idx).congestion_time = vehicles(v_idx).congestion_time + dt; end
                continue;
            end
        end
        
        % [移植] 预生成的头车保持静止
        if current.is_first_vehicle
            continue;
        end

        if current.lc_progress > 0
            new_lc_progress = current.lc_progress + dt/lc_duration;
            if new_lc_progress >= 1
                vehicles(v_idx).lane = current.target_lane; 
                vehicles(v_idx).lc_progress = 0;
                new_lane_center = (current.target_lane-1)*lane_width + lane_width/2 - current.width/2;
                vehicles(v_idx).lane_center = new_lane_center; 
                vehicles(v_idx).emergency_stop = false;
            else, vehicles(v_idx).lc_progress = new_lc_progress; end
        else
            % [移植] 激进的变道意愿
            if current.can_change_lane && ~current.is_first_vehicle
                wants_to_change = false; 
                % 只要不在中间目标车道(4,5)，就想向中间变道
                if ~ismember(current.lane, [4,5])
                    wants_to_change = true;
                end
                if wants_to_change
                    [can_change, target_lane] = checkLaneChange(v_idx, vehicles, lane_width, min_gap, speed_limit, num_lanes);
                    if can_change
                        vehicles(v_idx).target_lane = target_lane;
                        vehicles(v_idx).lc_progress = dt/lc_duration;
                    end
                end
            end
        end

        target_lane = current.target_lane;
        same_lane_vehs = vehicles(arrayfun(@(v) v.lane == target_lane & v.handle ~= current.handle, vehicles));
        [front_veh, distance] = findFrontVehicle(current, same_lane_vehs);
        if ~isempty(front_veh) && front_veh.speed == 0 && distance < 6
            vehicles(v_idx).speed = 0; vehicles(v_idx).emergency_stop = true;
        else
            if isempty(front_veh)
                acc = (speed_limit - current.speed)/2;
            else
                % [移植] 中央车道紧凑跟驰
                if ismember(current.lane, [3,4,5,6])
                    s0 = 2.0 * 0.6; 
                else
                    s0 = 2.0; 
                end
                delta_v = current.speed - front_veh.speed;
                acc = 10*(1 - (current.speed/speed_limit)^4 - ((s0 + 1.5*current.speed + current.speed*delta_v/8)/distance)^2);
                acc = max(-5, min(acc, 3));
            end
            new_speed = current.speed + acc*dt; new_speed = max(0.1, min(new_speed, speed_limit));
            if current.emergency_stop, new_speed = max(0, new_speed); end
            new_x = current.position(1) + new_speed*dt;
            
            % [移植] 五次多项式轨迹
            if current.lc_progress > 0
                start_y = current.lane_center;
                target_lane_center = (current.target_lane-1)*lane_width + lane_width/2 - current.width/2;
                tau = current.lc_progress;
                polynomial_scaler = 6*tau^5 - 15*tau^4 + 10*tau^3;
                total_lateral_shift = target_lane_center - start_y;
                current_lateral_shift = total_lateral_shift * polynomial_scaler;
                new_y = start_y + current_lateral_shift;
            else
                new_y = current.lane_center;
            end
            vehicles(v_idx).speed = new_speed;
            vehicles(v_idx).position = [new_x, new_y];
            set(current.handle, 'Position', [new_x, new_y, current.length, current.width]);
        end
        
        if vehicles(v_idx).speed == 0, vehicles(v_idx).congestion_time = vehicles(v_idx).congestion_time + dt; end

        timer_h = vehicles(v_idx).timer_handle;
        new_timer_pos = [vehicles(v_idx).position(1) + vehicles(v_idx).length/2, ...
                         vehicles(v_idx).position(2) + vehicles(v_idx).width/2, 0]; 
        set(timer_h, 'Position', new_timer_pos);

        if vehicles(v_idx).congestion_time > 0
            set(timer_h, 'String', sprintf('%.1fs', vehicles(v_idx).congestion_time), 'Visible', 'on');
        else
            set(timer_h, 'Visible', 'off');
        end

        if current.position(1) > road_length, to_delete = [to_delete, v_idx]; end
    end

    for v_idx = 1:length(vehicles)
        current = vehicles(v_idx);
        lane_center = (current.lane-1)*lane_width + lane_width/2 - current.width/2;
        deviation = abs(current.position(2) - lane_center);
        if deviation > off_center_threshold
            vehicles(v_idx).off_center_time = vehicles(v_idx).off_center_time + dt;
            if vehicles(v_idx).off_center_time > off_center_duration, to_delete = [to_delete, v_idx]; end
        else, vehicles(v_idx).off_center_time = 0; end
    end

    to_delete = unique(to_delete);
    for i = length(to_delete):-1:1
        idx_to_del = to_delete(i);
        if idx_to_del <= length(vehicles)
            if vehicles(idx_to_del).is_first_vehicle, continue; end
            
            passing_time(end+1) = current_sim_time - vehicles(idx_to_del).spawn_time;
            passing_congestion_time(end+1) = vehicles(idx_to_del).congestion_time;
            delete(vehicles(idx_to_del).handle);
            delete(vehicles(idx_to_del).timer_handle);
            vehicles(idx_to_del) = [];
            count = count + 1;
        end
    end

    pause(dt / time_ratio);
    drawnow limitrate;
end

%% 输出仿真结果
disp(['总通行车辆数：', num2str(count)]);
if ~isempty(passing_time), disp(['平均通过时间：', num2str(mean(passing_time)), ' 秒']);
else, disp('没有车辆通过，无法计算平均时间'); end

if ~isempty(passing_congestion_time)
    disp(['平均拥堵时间：', num2str(mean(passing_congestion_time)), ' 秒']);
    disp(['最大拥堵时间：', num2str(max(passing_congestion_time)), ' 秒']);
    total_travel_time = sum(passing_time);
    total_congestion_time = sum(passing_congestion_time);
    if total_travel_time > 0
        congestion_ratio = total_congestion_time / total_travel_time * 100;
        disp(['总行程中拥堵时间占比：', num2str(congestion_ratio), ' %']);
    end
else, disp('没有车辆通过，无法计算拥堵时间统计。'); end


%% 函数区
function [can_change, target_lane] = checkLaneChange(v_idx, vehicles, lane_width, min_gap, speed_limit, num_lanes)
    current = vehicles(v_idx);
    can_change = false;
    target_lane = current.lane;
    
    % [双侧] 变道方向逻辑
    if current.lane <= 4
        candidate_lanes = current.lane + 1; % 下方车道向上变
    else % current.lane >= 5
        candidate_lanes = current.lane - 1; % 上方车道向下变
    end
    
    candidate_lanes = candidate_lanes(candidate_lanes >= 1 & candidate_lanes <= num_lanes);
    if isempty(candidate_lanes), return; end
    
    predict_dx = current.speed * 0.5;
    predict_x = current.position(1) + predict_dx;

    for lane = candidate_lanes
        lane_vehs = vehicles(arrayfun(@(v) v.target_lane == lane, vehicles));
        front_veh = []; rear_veh = [];
        front_dist = inf; rear_dist = inf;
        for i = 1:length(lane_vehs)
            dx = lane_vehs(i).position(1) - predict_x;
            if dx > 0 && dx < front_dist, front_veh = lane_vehs(i); front_dist = dx;
            elseif dx < 0 && -dx < rear_dist, rear_veh = lane_vehs(i); rear_dist = -dx; end
        end
        
        front_safe = front_dist > (current.length + min_gap);
        
        rear_safe = false;
        if isempty(rear_veh), rear_safe = true;
        else
            rear_veh_speed = rear_veh.speed;
            dynamic_safe_dist = rear_veh_speed * 1.5 + rear_veh.length + min_gap;
            reduced_safe_dist = dynamic_safe_dist * 0.6; 
            speed_diff = rear_veh_speed - current.speed;
            is_rear_approaching_fast = speed_diff > 5;
            
            if is_rear_approaching_fast
                if rear_dist > reduced_safe_dist * 1.8, rear_safe = true; end
            else
                if rear_dist > reduced_safe_dist, rear_safe = true; end
            end
        end
         
        if front_safe && rear_safe, target_lane = lane; can_change = true; return; end
    end
end

function [front_veh, distance] = findFrontVehicle(current, candidates)
    if isempty(candidates), front_veh = []; distance = inf; return; end
    x_positions = arrayfun(@(v) v.position(1), candidates);
    front_indices = x_positions > current.position(1);
    if any(front_indices)
        front_vehs = candidates(front_indices);
        front_x = arrayfun(@(v) v.position(1), front_vehs);
        [min_distance, idx] = min(front_x - current.position(1));
        front_veh = front_vehs(idx); distance = min_distance;
    else, front_veh = []; distance = inf; end
end

function [rear_veh, distance] = findRearVehicle(current, candidates)
    if isempty(candidates), rear_veh = []; distance = inf; return; end
    x_positions = arrayfun(@(v) v.position(1), candidates);
    rear_indices = x_positions < current.position(1);
    if any(rear_indices)
        rear_vehs = candidates(rear_indices);
        rear_x = arrayfun(@(v) v.position(1), rear_vehs);
        [max_pos, ~] = max(rear_x);
        idx = find(rear_x == max_pos, 1);
        rear_veh = rear_vehs(idx); distance = current.position(1) - max_pos;
    else, rear_veh = []; distance = inf; end
end

