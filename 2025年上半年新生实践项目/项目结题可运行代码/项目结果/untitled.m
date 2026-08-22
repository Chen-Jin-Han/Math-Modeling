%% 参数设置
num_lanes = 8;          % 车道总数
lane_width = 4;         % 单车道宽度（米）
road_length = 100;      % 道路总长度（米）
lane_endpoints = [40, 53, 66, 80, 100, 100, 100, 100];  % 各车道终点位置
simulation_time = 600;  % 总仿真时间（秒）
dt = 0.2;               % 仿真时间步长（秒）
time_ratio = 10;        % 仿真速度控制参数，用于调整仿真显示的速度
speed_limit = 15;       % 最高车速（米/秒）
min_gap = 4;            % 最小安全间距（米）
lc_duration = 1;        % 变道持续时间（秒）
off_center_threshold = lane_width / 4;  % 横向偏离阈值（米）
off_center_duration = 10 * dt;          % 最大偏离持续时间（秒）
density_threshold = 6;  % 5-8车道允许变道的车辆密度阈值
count = 0;              % 计数器，用于统计通过车辆数
passing_time = [];      % 记录每辆车通过时间
elapsed_real_time = 0;  % 用于记录实际运行时间

%% 初始化图形窗口
figure; % 创建一个新的图形窗口
set(gcf, 'Position', [100 100 1000 400]);  % 设置窗口尺寸
axis([0 road_length 0 (num_lanes+1)*lane_width]); % 设置坐标轴的范围
daspect([1 1 1]);       % 等比例坐标轴
set(gca, 'Box', 'on');  % 显示坐标轴边框
hold on; % 保持当前图形，以便在上面绘制更多的内容

% 绘制车道分隔线
for lane = 1:num_lanes
    y = (lane)*lane_width; % 计算每条车道的y坐标
    line([0 road_length], [y y], 'Color', [0.5 0.5 0.5], 'LineWidth', 1); % 绘制车道分隔线，颜色为灰色
    
    % 绘制短道终点标识
    if lane <= 4
        lane_end = lane_endpoints(lane); % 获取短道的终点位置
        rectangle('Position', [lane_end-0.5, (lane-1)*lane_width, 1, lane_width],...
                 'FaceColor', [1 0.8 0.8], 'EdgeColor', 'r'); % 绘制短道终点的红色矩形标识
    end
end

% 绘制收费站入口
rectangle('Position', [0 0 5 num_lanes*lane_width],...
         'FaceColor', [0.8 1 0.8], 'EdgeColor', 'g'); % 绘制收费站入口，位置在x=0处，宽度为5米，高度为所有车道的总宽度，颜色为绿色
xlabel('道路位置（米）'); % 设置x轴标签
title('改进版变道决策模型仿真'); % 设置图形的标题
hold off; % 释放图形，结束绘图

%% 车辆结构体
vehicles = struct(... % 定义车辆的结构体，用于存储每辆车的状态信息
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
    'spawn_time', {}); % 车辆生成时间
flag_some = 1; % 标志变量，用于控制仿真速度

%% 主仿真循环
next_spawn_times = 3 + 2*rand(1, num_lanes); % 初始生成时间，随机生成每条车道下一辆车的生成时间
start_time = tic; % 记录仿真开始时间
current_sim_time = 0; % 当前仿真时间初始化为0
while true
    %elapsed_real_time = toc(start_time); % 计算实际运行时间
    %elapsed_real_time = dt; % 仿真时间步长
    %current_sim_time = elapsed_real_time * time_ratio; % 计算当前仿真时间
    current_sim_time = current_sim_time + dt; % 更新当前仿真时间
    if current_sim_time >= simulation_time
        break; % 如果仿真时间超过总仿真时间，退出循环
    end

    %% 生成新车辆
    for lane = 1:num_lanes
        lane_end = lane_endpoints(lane); % 获取当前车道的终点位置
        
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
            max_vehicles = inf; % 无限制
        end
        
        % 检查当前车道车辆数
        lane_vehs = vehicles(arrayfun(@(v) v.lane == lane, vehicles)); % 获取当前车道的所有车辆
        if length(lane_vehs) >= max_vehicles
            continue; % 如果车辆数达到限制，跳过当前车道
        end
        
        if current_sim_time >= next_spawn_times(lane)
            % 生成车辆参数
            speed_init = 4 + rand(); % 初始速度，随机生成
            vehicle_len = 3 + 2*rand(); % 车辆长度，随机生成
            vehicle_wid = 1.5 + 0.7*rand(); % 车辆宽度，随机生成
            
            % 短道首车特殊处理
            if lane <= 4 && isempty(lane_vehs)
                vehicle_len = 1;  % 缩短首车长度
            end
            
            color = rand(1,3); % 随机生成车辆颜色
            lane_center = (lane-1)*lane_width + lane_width/2 - vehicle_wid/2; % 计算车道中心的y坐标
            is_first_vehicle = isempty(lane_vehs); % 判断是否为首车
            
            % 绘制车辆图形
            h = rectangle('Position', [0, lane_center, vehicle_len, vehicle_wid],...
                'FaceColor', color, 'EdgeColor', 'k'); % 绘制车辆矩形
            
            % 短道首车隐身
            if is_first_vehicle && lane <=4
                set(h, 'Visible', 'off'); % 首车不显示
            end
            
            % 记录车辆信息
            vehicles(end+1) = struct(... % 将新车辆添加到车辆列表
                'position', [0, lane_center], 'speed', speed_init,...
                'length', vehicle_len, 'width', vehicle_wid, 'lane', lane,...
                'target_lane', lane, 'lc_progress', 0, 'color', color, 'handle', h,...
                'waiting', false, 'lane_center', lane_center, 'emergency_stop', false,...
                'off_center_time', 0, 'is_first_vehicle', is_first_vehicle, 'can_change_lane', false,'spawn_time', current_sim_time);
            
            next_spawn_times(lane) = current_sim_time + 3 + 2*rand(); % 更新下一辆车的生成时间
        end
    end

    %% 更新车辆状态
    to_delete = []; % 初始化需要删除的车辆列表
    for v_idx = 1:length(vehicles)
        current = vehicles(v_idx); % 获取当前车辆的信息
        lane_idx = current.lane; % 获取当前车辆所在的车道
        
        % ==== 变道权限控制 ====
        if lane_idx >= 6
            % 统计当前车道车辆数
            same_lane_vehs = vehicles(arrayfun(@(v) v.lane == lane_idx, vehicles)); % 获取当前车道的所有车辆
            vehicles(v_idx).can_change_lane = (length(same_lane_vehs) > density_threshold); % 根据车辆密度判断是否允许变道
        else
            % 1-4车道原逻辑：驶过5米后允许变道
            vehicles(v_idx).can_change_lane = (current.position(1) >= 5); % 如果车辆行驶超过5米，允许变道
        end

        % 到达短道终点的处理
        if lane_idx <= 4
            lane_end = lane_endpoints(lane_idx); % 获取短道的终点位置
            if current.position(1) >= lane_end - current.length
                if ~current.waiting
                    vehicles(v_idx).waiting = true; % 标记车辆为等待状态
                    vehicles(v_idx).speed = 0; % 停止车辆
                end
                continue; % 跳过当前车辆的后续处理
            end
        end

        % 首车逻辑
        if current.is_first_vehicle
            new_x = current.position(1) + current.speed * dt; % 更新首车的位置
            vehicles(v_idx).position = [new_x, current.position(2)]; % 更新车辆位置
            set(current.handle, 'Position', [new_x, current.position(2), current.length, current.width]); % 更新车辆图形位置
            continue; % 跳过当前车辆的后续处理
        end

        % 变道控制
        if current.lc_progress > 0
            new_lc_progress = current.lc_progress + dt/lc_duration; % 更新变道进度
            if new_lc_progress >= 1
                vehicles(v_idx).lane = current.target_lane; % 完成变道，更新车道
                vehicles(v_idx).lc_progress = 0; % 重置变道进度
                new_lane_center = (current.target_lane-1)*lane_width + lane_width/2 - current.width/2; % 计算新车道中心的y坐标
                vehicles(v_idx).lane_center = new_lane_center; % 更新车道中心
                vehicles(v_idx).emergency_stop = false; % 重置紧急制动状态
            else
                vehicles(v_idx).lc_progress = new_lc_progress; % 更新变道进度
            end
        else
            % 变道触发决策
            if current.can_change_lane
                % 按车道类型使用不同决策规则
                if current.lane >= 6 && current.lane <= 8
                    % 6-8车道固定概率
                    if rand() < 0.03
                        [can_change, target_lane] = checkLaneChange(v_idx, vehicles,...
                            lane_width, min_gap, speed_limit, num_lanes); % 检查是否可以变道
                        if can_change
                            vehicles(v_idx).target_lane = target_lane; % 更新目标车道
                            vehicles(v_idx).lc_progress = dt/lc_duration; % 开始变道
                        end
                    end
                else
                    % 1-5车道风险系数决策
                    same_lane_vehs = vehicles(arrayfun(@(v) v.lane == current.lane, vehicles)); % 获取当前车道的所有车辆
                    [front_veh, front_dist] = findFrontVehicle(current, same_lane_vehs); % 查找前车
                    [rear_veh, rear_dist] = findRearVehicle(current, same_lane_vehs); % 查找后车
                    
                    % 处理无穷大距离
                    if isinf(front_dist), front_dist = 1000; end
                    if isinf(rear_dist), rear_dist = 1000; end
                    
                    % 计算风险系数
                    s = 1/(front_dist + rear_dist + eps);  % 防止除以零
                    f = 0.6 + 2*s + 15*s^2;
                    
                    if 0 > f-rand() % 如果随机数大于风险系数，尝试变道
                        [can_change, target_lane] = checkLaneChange(v_idx, vehicles,...
                            lane_width, min_gap, speed_limit, num_lanes); % 检查是否可以变道
                        if can_change
                            vehicles(v_idx).target_lane = target_lane; % 更新目标车道
                            vehicles(v_idx).lc_progress = dt/lc_duration; % 开始变道
                        end
                    end
                end
            end
        end

        % 跟车与加速度计算
        target_lane = current.target_lane; % 获取目标车道
        same_lane_vehs = vehicles(arrayfun(@(v) v.target_lane, vehicles) == target_lane); % 获取目标车道的所有车辆
        [front_veh, distance] = findFrontVehicle(current, same_lane_vehs); % 查找前车

        if ~isempty(front_veh) && front_veh.speed == 0 && distance < 6  %急停情况
            vehicles(v_idx).speed = 0; % 前车紧急停车且距离小于6米，当前车也紧急停车
            vehicles(v_idx).emergency_stop = true; % 标记紧急制动状态
        else
            if isempty(front_veh)
                acc = (speed_limit - current.speed)/2; % 如果没有前车，加速到最高车速
            else
                delta_v = current.speed - front_veh.speed; % 速度差
                acc = 10*(1 - (current.speed/speed_limit)^4 - ((2 + 1.5*current.speed + current.speed*delta_v/8)/distance)^2); % 计算加速度
                acc = max(-5, min(acc, 3)); % 限制加速度范围
            end

            new_speed = current.speed + acc*dt; % 更新速度
            new_speed = max(0.1, min(new_speed, speed_limit)); % 限制速度范围
            new_x = current.position(1) + new_speed*dt; % 更新位置

            % 横向位置更新
            if current.lc_progress > 0
                start_y = current.lane_center; % 当前车道中心
                target_lane_center = (current.target_lane-1)*lane_width + lane_width/2 - current.width/2; % 目标车道中心
                new_y = start_y + (target_lane_center - start_y)*current.lc_progress; % 更新横向位置
            else
                new_y = current.lane_center; % 如果没有变道，保持当前车道中心
            end

            vehicles(v_idx).speed = new_speed; % 更新车辆速度
            vehicles(v_idx).position = [new_x, new_y]; % 更新车辆位置
            set(current.handle, 'Position', [new_x, new_y, current.length, current.width]); % 更新车辆图形位置
        end

        % 超出道路检测
        if current.position(1) > road_length
            to_delete = [to_delete, v_idx]; % 如果车辆超出道路范围，记录需要删除的车辆
        end
    end

    % 横向偏离检测
    for v_idx = 1:length(vehicles)
        current = vehicles(v_idx); % 获取当前车辆的信息
        lane_center = (current.lane-1)*lane_width + lane_width/2 - current.width/2; % 计算车道中心的y坐标
        deviation = abs(current.position(2) - lane_center); % 计算横向偏离距离
        
        if deviation > off_center_threshold
            vehicles(v_idx).off_center_time = vehicles(v_idx).off_center_time + dt; % 更新偏离时间
            if vehicles(v_idx).off_center_time > off_center_duration
                to_delete = [to_delete, v_idx]; % 如果偏离时间超过最大允许时间，记录需要删除的车辆
            end
        else
            vehicles(v_idx).off_center_time = 0; % 如果没有偏离，重置偏离时间
        end
    end

    % 删除出界车辆
    for i = length(to_delete):-1:1
        passing_time(end+1) = current_sim_time - vehicles(to_delete(i)).spawn_time; % 记录车辆通过时间
        delete(vehicles(to_delete(i)).handle); % 删除车辆图形
        vehicles(to_delete(i)) = []; % 从车辆列表中移除车辆
        count = count + 1; % 更新通过车辆计数
    end

    % 实时性控制
    if flag_some
        pause_time = (dt/time_ratio) - (toc(start_time) - elapsed_real_time); % 计算暂停时间
        if pause_time > 0
            %pause(max(pause_time, 0.001)); % 暂停仿真
            %pause(0.001)
        end
        drawnow limitrate; % 更新图形
    end
end

% 输出仿真结果
disp(['总通行车辆数：', num2str(count)]); % 输出总通行车辆数
if ~isempty(passing_time)
    disp(['平均通过时间：', num2str(mean(passing_time)), ' 秒']); % 输出平均通过时间
else
    disp('没有车辆通过，无法计算平均时间'); % 如果没有车辆通过，提示无法计算平均时间
end

%% 变道检查函数（改进版）
function [can_change, target_lane] = checkLaneChange(v_idx, vehicles, lane_width, min_gap, speed_limit, num_lanes)
    current = vehicles(v_idx); % 获取当前车辆的信息
    can_change = false; % 初始化变道标志为false
    target_lane = current.lane; % 初始化目标车道为当前车道

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
    candidate_lanes = candidate_lanes(candidate_lanes >= 1 & candidate_lanes <= num_lanes); % 确保候选车道在有效范围内

    predict_dx = current.speed * 0.5;  % 预测插入位置
    predict_x = current.position(1) + predict_dx; % 计算预测插入位置

    % 检查每个候选车道
    for lane = candidate_lanes
        lane_vehs = vehicles(arrayfun(@(v) v.target_lane == lane, vehicles)); % 获取候选车道的所有车辆
        front_veh = []; % 初始化前车为空
        rear_veh = []; % 初始化后车为空
        front_dist = inf; % 初始化前车距离为无穷大
        rear_dist = inf; % 初始化后车距离为无穷大

        % 查找最近前车和后车
        for i = 1:length(lane_vehs)
            dx = lane_vehs(i).position(1) - predict_x; % 计算车辆与预测位置的相对距离
            if dx > 0 && dx < front_dist
                front_veh = lane_vehs(i); % 更新前车
                front_dist = dx; % 更新前车距离
            elseif dx < 0 && -dx < rear_dist
                rear_veh = lane_vehs(i); % 更新后车
                rear_dist = -dx; % 更新后车距离
            end
        end

        % 安全距离检查
        front_safe = front_dist > min_gap + 0.2*speed_limit;  % 前距>7米
        rear_safe = rear_dist > min_gap + 0.3*speed_limit;    % 后距>8.5米

        if front_safe && rear_safe
            target_lane = lane; % 更新目标车道
            can_change = true; % 允许变道
            return; % 返回变道结果
        end
    end
end

%% 前车查找函数
function [front_veh, distance] = findFrontVehicle(current, candidates)
    if isempty(candidates)
        front_veh = []; % 如果候选车辆为空，返回空
        distance = inf; % 返回无穷大距离
        return;
    end
    x_positions = arrayfun(@(v) v.position(1), candidates); % 获取候选车辆的x位置
    front_indices = x_positions > current.position(1); % 找到在当前车辆前方的车辆
    if any(front_indices)
        front_vehs = candidates(front_indices); % 获取前方车辆
        front_x = arrayfun(@(v) v.position(1), front_vehs); % 获取前方车辆的x位置
        [min_distance, idx] = min(front_x - current.position(1)); % 找到最近的前方车辆
        front_veh = front_vehs(idx); % 返回最近的前方车辆
        distance = min_distance; % 返回最近前方车辆的距离
    else
        front_veh = []; % 如果没有前方车辆，返回空
        distance = inf; % 返回无穷大距离
    end
end

%% 后车查找函数
function [rear_veh, distance] = findRearVehicle(current, candidates)
    if isempty(candidates)
        rear_veh = []; % 如果候选车辆为空，返回空
        distance = inf; % 返回无穷大距离
        return;
    end
    x_positions = arrayfun(@(v) v.position(1), candidates); % 获取候选车辆的x位置
    rear_indices = x_positions < current.position(1); % 找到在当前车辆后方的车辆
    if any(rear_indices)
        rear_vehs = candidates(rear_indices); % 获取后方车辆
        rear_x = arrayfun(@(v) v.position(1), rear_vehs); % 获取后方车辆的x位置
        [max_distance, idx] = max(current.position(1) - rear_x); % 找到最近的后方车辆
        rear_veh = rear_vehs(idx); % 返回最近的后方车辆
        distance = max_distance; % 返回最近后方车辆的距离
    else
        rear_veh = []; % 如果没有后方车辆，返回空
        distance = inf; % 返回无穷大距离
    end
end
