clear; clc; 
%% 1. 定义用于优化的目标函数
% 'simulannealbnd' 旨在最小化函数，因此我们最小化负的SPS得分，等同于最大化SPS得分。
objective_function = @(d) -runSimulation(d);

%% 2. 设置并运行模拟退火算法
% 'd' 是要优化的变量，其取值范围在0到50之间。
d0 = 25;  % 'd' 的初始猜测值
lb = 0;   % 下界
ub = 50;  % 上界

options = optimoptions('simulannealbnd');
% 运行优化
[optimal_d, neg_max_sps_score] = simulannealbnd(objective_function, d0, lb, ub, options);
% 将结果转回正值
max_sps_score = -neg_max_sps_score;

%% 3. 输出最终结果
fprintf(' 优化结果 \n');
fprintf('找到的最优d值为: %.2f 米\n', optimal_d);
fprintf('在该d值下找到的最高平均SPS得分为: %.4f\n', max_sps_score);

%  主仿真函数 
% 该函数将被优化算法多次调用
function avg_sps_score = runSimulation(d)

    %% 定义固定的Lambda值和仿真次数
    current_lambda = 0.30;
    num_simulations = 1;

    % 初始化存储器，用于批量仿真结果
    all_counts = zeros(1, num_simulations);
    all_avg_passing_times = zeros(1, num_simulations);
    all_missed_vehicles = zeros(1, num_simulations);
    all_missed_vehicle_ratios = zeros(1, num_simulations);
    all_avg_congestion_times_for_congested = zeros(1, num_simulations);
    all_sps_scores = zeros(1, num_simulations);

    % 开始内层批量仿真主循环
    for sim_run = 1:num_simulations

        %% 参数设置
        num_lanes = 8;
        lane_width = 4;
        road_length = 100;

        % [修改] 根据 'd' 动态设置车道终点
        lane_endpoints = [100-2*d, 100-d, 100, 100, 100, 100, 100-d, 100-2*d];

        simulation_time = 600;
        dt = 0.2;
        speed_limit = 15;
        min_gap = 4;
        lc_duration = 1;
        off_center_threshold = lane_width / 4;
        off_center_duration = 10 * dt;
        density_threshold = 6;
        count = 0;
        passing_time = [];
        passing_congestion_time = [];
        passing_satisfaction = [];
        missed_vehicle_count = 0;
        mean_arrival_rate = ones(1, num_lanes) * current_lambda;

        %% 车辆结构体
        vehicles = struct(...
            'position', {}, 'speed', {}, 'length', {}, 'width', {}, ...
            'lane', {}, 'target_lane', {}, 'lc_progress', {}, 'color', {}, ...
            'handle', {}, 'timer_handle', {}, 'waiting', {}, 'lane_center', {}, ...
            'emergency_stop', {}, 'off_center_time', {}, 'is_first_vehicle', {}, ...
            'can_change_lane', {}, 'spawn_time', {}, 'congestion_time', {}, ...
            'satisfaction', {});

        %% 头车预生成模块
        short_lanes = [1, 2, 7, 8];
        for lane = short_lanes
            lane_end = lane_endpoints(lane);
            vehicle_len = 1;
            initial_x = lane_end - vehicle_len;
            speed_init = 0;
            vehicle_wid = 1.5;
            lane_center = (lane-1)*lane_width + lane_width/2 - vehicle_wid/2;
            vehicles(end+1) = struct(...
                'position', [initial_x, lane_center], 'speed', speed_init,...
                'length', vehicle_len, 'width', vehicle_wid, 'lane', lane,...
                'target_lane', lane, 'lc_progress', 0, 'color', [0 0 0], 'handle', [],...
                'timer_handle', [], 'waiting', true, 'lane_center', lane_center, ...
                'emergency_stop', true, 'off_center_time', 0, 'is_first_vehicle', true, ...
                'can_change_lane', false, 'spawn_time', 0, 'congestion_time', inf, 'satisfaction', 0);
        end

        %% 单次仿真主循环
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

        fprintf('  [仿真 %d/%d] 进度: ', sim_run, num_simulations);
        last_progress_percent = -1;

        while true
            current_sim_time = current_sim_time + dt;
            if current_sim_time >= simulation_time, break; end

            % [新增] 实时进度条显示
            progress_percent = round((current_sim_time / simulation_time) * 100);
            if progress_percent > last_progress_percent
                fprintf('\b%s', repmat(' ', 1, numel(num2str(last_progress_percent)) + 2));
                fprintf('\b%s', repmat(' ', 1, numel(num2str(last_progress_percent)) + 2));
                fprintf('%d%% ', progress_percent);
                last_progress_percent = progress_percent;
            end

            %% 生成新车辆
            for lane = 1:num_lanes
                if current_sim_time >= next_spawn_times(lane)

                    % 检查短道前方是否有静止车辆
                    is_blocked = false;
                    if ismember(lane, [1, 2, 7, 8])
                        lane_vehs = vehicles(arrayfun(@(v) v.lane == lane, vehicles));
                        for v_idx = 1:length(lane_vehs)
                            veh = lane_vehs(v_idx);
                            if veh.speed < 0.1 && veh.position(1) < 5
                                is_blocked = true;
                                break;
                            end
                        end
                    end

                    if is_blocked
                        missed_vehicle_count = missed_vehicle_count + 1;
                        if mean_arrival_rate(lane) > 0
                             mean_headway = 1 / mean_arrival_rate(lane);
                             time_gap = exprnd(mean_headway);
                             next_spawn_times(lane) = current_sim_time + time_gap;
                         else
                             next_spawn_times(lane) = inf;
                         end
                        continue; % 跳过本次生成
                    end

                    % 车辆数量限制逻辑
                    if ismember(lane, [1, 8]), max_vehicles = 8;
                    elseif ismember(lane, [2, 7]), max_vehicles = 12;
                    else, max_vehicles = inf;
                    end
                    lane_vehs = vehicles(arrayfun(@(v) v.lane == lane, vehicles));
                    if length(lane_vehs) >= max_vehicles
                        missed_vehicle_count = missed_vehicle_count + 1;
                    else
                        is_first_vehicle = false;
                        vehicle_len = 3 + 2*rand();
                        initial_x = 0;
                        speed_init = 4 + rand();
                        vehicle_wid = 1.5 + 0.7*rand();
                        color = rand(1,3);
                        lane_center = (lane-1)*lane_width + lane_width/2 - vehicle_wid/2;
                        vehicles(end+1) = struct(...
                            'position', [initial_x, lane_center], 'speed', speed_init,...
                            'length', vehicle_len, 'width', vehicle_wid, 'lane', lane,...
                            'target_lane', lane, 'lc_progress', 0, 'color', color, 'handle', [],...
                            'timer_handle', [], 'waiting', false, 'lane_center', lane_center, ...
                            'emergency_stop', false, 'off_center_time', 0, 'is_first_vehicle', is_first_vehicle, ...
                            'can_change_lane', false, 'spawn_time', current_sim_time, 'congestion_time', 0, 'satisfaction', 1);
                    end
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
                % 变道权限控制
                if ismember(lane_idx, [3,4,5,6]) % 中央车道
                    same_lane_vehs = vehicles(arrayfun(@(v) v.lane == lane_idx, vehicles));
                    vehicles(v_idx).can_change_lane = (length(same_lane_vehs) > density_threshold);
                else % 两侧车道
                    vehicles(v_idx).can_change_lane = (current.position(1) >= 5);
                end
                % 普通车辆在短道终点停止
                if ismember(lane_idx, short_lanes) && ~current.is_first_vehicle
                    lane_end = lane_endpoints(lane_idx);
                    if current.position(1) >= lane_end - current.length
                        if ~current.waiting
                            vehicles(v_idx).waiting = true;
                            vehicles(v_idx).speed = 0;
                        end
                        if vehicles(v_idx).speed == 0
                            vehicles(v_idx).congestion_time = vehicles(v_idx).congestion_time + dt;
                            k = 1/30;
                            vehicles(v_idx).satisfaction = exp(-k * vehicles(v_idx).congestion_time);
                        end
                        continue;
                    end
                end
                if current.is_first_vehicle, continue; end
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
                    if current.can_change_lane && ~current.is_first_vehicle
                        wants_to_change = false;
                        if ~ismember(current.lane, [4,5])
                            wants_to_change = true;
                        end
                        if wants_to_change
                            [can_change, target_lane_cand] = checkLaneChange(v_idx, vehicles, lane_width, min_gap, speed_limit, num_lanes);
                            if can_change
                                vehicles(v_idx).target_lane = target_lane_cand;
                                vehicles(v_idx).lc_progress = dt/lc_duration;
                            end
                        end
                    end
                end
                target_lane = current.target_lane;
                logical_indices = arrayfun(@(v) v.target_lane == target_lane, vehicles);
                same_lane_vehs = vehicles(logical_indices);
                [front_veh, distance] = findFrontVehicle(current, same_lane_vehs);
                if ~isempty(front_veh) && front_veh.speed == 0 && distance < 6
                    vehicles(v_idx).speed = 0; vehicles(v_idx).emergency_stop = true;
                else
                    if isempty(front_veh)
                        acc = (speed_limit - current.speed)/2;
                    else
                        if ismember(current.lane, [3,4,5,6])
                            s0 = 2.0 *1.0;
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
                end
                if vehicles(v_idx).speed == 0
                    vehicles(v_idx).congestion_time = vehicles(v_idx).congestion_time + dt;
                    k = 1/30;
                    vehicles(v_idx).satisfaction = exp(-k * vehicles(v_idx).congestion_time);
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
                    passing_satisfaction(end+1) = vehicles(idx_to_del).satisfaction;
                    vehicles(idx_to_del) = [];
                    count = count + 1;
                end
            end
        end

        fprintf('100%%. 仿真完成。            \n');

        %% 处理仿真结束时仍在路上的车辆
        for v_idx = 1:length(vehicles)
            if vehicles(v_idx).is_first_vehicle
                continue;
            end
            passing_congestion_time(end+1) = vehicles(v_idx).congestion_time;
        end

        %% 数据存储与单轮评估体系计算
        all_counts(sim_run) = count;
        if ~isempty(passing_time), all_avg_passing_times(sim_run) = mean(passing_time);
        else, all_avg_passing_times(sim_run) = NaN; end
        if ~isempty(passing_congestion_time)
            total_travel_time = sum(passing_time);
            total_congestion_time = sum(passing_congestion_time);
            congested_times = passing_congestion_time(passing_congestion_time > 0);
            if ~isempty(congested_times)
                all_avg_congestion_times_for_congested(sim_run) = mean(congested_times);
            else
                all_avg_congestion_times_for_congested(sim_run) = 0;
            end
        else
            all_avg_congestion_times_for_congested(sim_run) = 0;
        end
        num_congested_vehs = sum(passing_congestion_time > 0);
        num_remaining_vehs = length(vehicles) - sum(arrayfun(@(v)v.is_first_vehicle, vehicles));
        total_vehicles_in_stat = count + num_remaining_vehs;
        if total_vehicles_in_stat > 0
            all_congested_vehicle_ratios(sim_run) = (num_congested_vehs / total_vehicles_in_stat) * 100;
        else
            all_congested_vehicle_ratios(sim_run) = 0;
        end
        all_missed_vehicles(sim_run) = missed_vehicle_count;
        total_potential_vehicles = count + missed_vehicle_count;
        if total_potential_vehicles > 0
            all_missed_vehicle_ratios(sim_run) = (missed_vehicle_count / total_potential_vehicles) * 100;
        else
            all_missed_vehicle_ratios(sim_run) = 0;
        end
        % 计算本轮评估体系 (SPS)
        if ~isempty(passing_satisfaction)
            N_sat = mean(passing_satisfaction);
        else
            N_sat = 0;
        end
        all_avg_satisfactions(sim_run) = N_sat;
        N_pass_rate = 1 - (all_missed_vehicle_ratios(sim_run) / 100);
        T_cong = all_avg_congestion_times_for_congested(sim_run);
        T_cong_max = simulation_time;
        N_cong = max(0, 1 - (T_cong / T_cong_max));
        T_pass = all_avg_passing_times(sim_run);
        if isnan(T_pass)
            N_efficiency = 0;
        else
            T_max = simulation_time;
            T_ideal = road_length / speed_limit;
            N_efficiency = max(0, (T_max - T_pass) / (T_max - T_ideal));
        end
        sps_score = N_sat * N_pass_rate * N_cong * N_efficiency;
        all_sps_scores(sim_run) = sps_score;
    end

    % 返回5次仿真平均SPS得分
    avg_sps_score = nanmean(all_sps_scores);
    
    % 在每次 simulannealbnd 迭代后输出结果
    global iteration_counter;
    if isempty(iteration_counter)
        iteration_counter = 1;
    else
        iteration_counter = iteration_counter + 1;
    end
    
    fprintf('--- 迭代 %d 结果 ---\n', iteration_counter);
    fprintf('当前 d = %.2f, 平均 SPS 得分 = %.4f\n\n', d, avg_sps_score);
end

%% 函数区
% 车辆变道判断函数
function [can_change, target_lane] = checkLaneChange(v_idx, vehicles, lane_width, min_gap, speed_limit, num_lanes)
    current = vehicles(v_idx);
    can_change = false;
    target_lane = current.lane;
    if current.lane <= 4
        candidate_lanes = current.lane + 1;
    else
        candidate_lanes = current.lane - 1;
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

% 寻找前方车辆函数
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

% 寻找后方车辆函数
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

