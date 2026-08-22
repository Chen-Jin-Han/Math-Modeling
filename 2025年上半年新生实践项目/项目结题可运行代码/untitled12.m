%% 修复版：单侧合并模型代码（优化车道配置版 - 递增等差数列）
clear; clc;

%% 遗传算法参数设置
GA_POPULATION_SIZE = 20;
GA_GENERATIONS = 15;
GA_MUTATION_RATE = 0.1;
GA_CROSSOVER_RATE = 0.8;
GA_ELITE_SIZE = 2;

MIN_D = 5;
MAX_D = 20;

fprintf('开始车道配置优化...\n');
fprintf('车道配置形式：[100-4d, 100-3d, 100-2d, 100-d]（递增）\n');
fprintf('==============================================\n');

%% 遗传算法主循环
best_fitness_history = zeros(1, GA_GENERATIONS);
best_d = [];
best_fitness = -inf;
global_best_d = [];
global_best_fitness = -inf;

population = initializePopulation(GA_POPULATION_SIZE, MIN_D, MAX_D);

for generation = 1:GA_GENERATIONS
    fprintf('\n==================== 第 %d/%d 代进化 ====================\n', generation, GA_GENERATIONS);
    
    fitness_scores = zeros(1, GA_POPULATION_SIZE);
    fprintf('正在评估种群适应度...\n');
    
    for i = 1:GA_POPULATION_SIZE
        d = population(i);
        lane_config = [100-4*d, 100-3*d, 100-2*d, 100-d];
        
        % 检查配置有效性
        if any(lane_config <= 0)
            fitness_scores(i) = -2000;
            fprintf('  个体 %d/%d: d=%.2f -> 配置无效 -> 适应度: %.4f\n', ...
                i, GA_POPULATION_SIZE, d, fitness_scores(i));
            continue;
        end
        
        fprintf('  个体 %d/%d: d=%.2f -> 配置 [%.1f, %.1f, %.1f, %.1f]', ...
            i, GA_POPULATION_SIZE, d, lane_config);
        
        try
            fitness_scores(i) = evaluateConfiguration(lane_config);
            fprintf(' -> 适应度: %.4f\n', fitness_scores(i));
        catch ME
            fprintf(' -> 评估失败: %s -> 适应度: -1000.0000\n', ME.message);
            fitness_scores(i) = -1000;
        end
    end
    
    % 显示当代统计信息
    fprintf('\n--- 第 %d 代统计信息 ---\n', generation);
    fprintf('最高适应度: %.4f\n', max(fitness_scores));
    fprintf('平均适应度: %.4f\n', mean(fitness_scores));
    fprintf('最低适应度: %.4f\n', min(fitness_scores));
    fprintf('适应度标准差: %.4f\n', std(fitness_scores));
    
    % 显示前3名个体
    [sorted_fitness, sorted_idx] = sort(fitness_scores, 'descend');
    fprintf('\n--- 前3名个体 ---\n');
    for rank = 1:min(3, length(sorted_idx))
        idx = sorted_idx(rank);
        d = population(idx);
        config = [100-4*d, 100-3*d, 100-2*d, 100-d];
        fprintf('第%d名: d=%.2f -> [%.1f, %.1f, %.1f, %.1f], 适应度: %.4f\n', ...
            rank, d, config, sorted_fitness(rank));
    end
    
    % 记录最佳个体
    [current_best_fitness, best_idx] = max(fitness_scores);
    if current_best_fitness > global_best_fitness
        global_best_fitness = current_best_fitness;
        global_best_d = population(best_idx);
        fprintf('\n*** 发现新的最优解！***\n');
        fprintf('新最优d值: %.2f\n', global_best_d);
        fprintf('新最优配置: [%.1f, %.1f, %.1f, %.1f]\n', ...
            [100-4*global_best_d, 100-3*global_best_d, 100-2*global_best_d, 100-global_best_d]);
        fprintf('新最优适应度: %.4f\n', global_best_fitness);
    end
    best_fitness_history(generation) = global_best_fitness;
    
    % 生成新种群
    new_population = zeros(size(population));
    
    % 精英保留
    [~, elite_indices] = sort(fitness_scores, 'descend');
    new_population(1:GA_ELITE_SIZE) = population(elite_indices(1:GA_ELITE_SIZE));
    
    fprintf('\n--- 精英保留 ---\n');
    for i = 1:GA_ELITE_SIZE
        d = new_population(i);
        config = [100-4*d, 100-3*d, 100-2*d, 100-d];
        fprintf('精英%d: d=%.2f -> [%.1f, %.1f, %.1f, %.1f], 适应度: %.4f\n', ...
            i, d, config, fitness_scores(elite_indices(i)));
    end
    
    % 生成新个体
    fprintf('\n--- 生成新个体 ---\n');
    crossover_count = 0;
    mutation_count = 0;
    
    for i = (GA_ELITE_SIZE + 1):GA_POPULATION_SIZE
        parent1 = rouletteWheelSelection(population, fitness_scores);
        parent2 = rouletteWheelSelection(population, fitness_scores);
        
        operation_desc = '';
        if rand < GA_CROSSOVER_RATE
            child = crossover(parent1, parent2);
            crossover_count = crossover_count + 1;
            operation_desc = '交叉';
        else
            child = parent1;
            operation_desc = '复制';
        end
        
        if rand < GA_MUTATION_RATE
            child = mutate(child, MIN_D, MAX_D);
            mutation_count = mutation_count + 1;
            if contains(operation_desc, '交叉')
                operation_desc = '交叉+变异';
            else
                operation_desc = '复制+变异';
            end
        end
        
        new_population(i) = child;
        
        % 显示少数新个体作为示例
        if mod(i, 5) == 0 || i == GA_POPULATION_SIZE
            config = [100-4*child, 100-3*child, 100-2*child, 100-child];
            fprintf('个体%d: d=%.2f -> [%.1f, %.1f, %.1f, %.1f] (%s)\n', ...
                i, child, config, operation_desc);
        end
    end
    
    fprintf('交叉操作次数: %d, 变异操作次数: %d\n', crossover_count, mutation_count);
    fprintf('==================== 第 %d 代完成 ====================\n', generation);
    
    population = new_population;
end

%% 输出最优结果
best_configuration = [100-4*global_best_d, 100-3*global_best_d, 100-2*global_best_d, 100-global_best_d];
fprintf('\n==============================================\n');
fprintf('优化完成！\n');
fprintf('最佳公差d值: %.2f\n', global_best_d);
fprintf('最佳车道配置: [%.1f, %.1f, %.1f, %.1f]\n', best_configuration);
fprintf('相邻车道长度差: [%.1f, %.1f, %.1f] (均为%.1f)\n', ...
    diff(best_configuration), global_best_d);
fprintf('最佳适应度得分: %.4f\n', global_best_fitness);

%% 进化过程分析
fprintf('\n========== 进化过程分析 ==========\n');
fprintf('各代最佳适应度变化:\n');
improvement_count = 0;
last_improvement_gen = 1;
total_improvement = 0;

for i = 1:GA_GENERATIONS
    if i == 1
        fprintf('第%2d代: %.4f\n', i, best_fitness_history(i));
        initial_fitness = best_fitness_history(i);
    else
        improvement = best_fitness_history(i) - best_fitness_history(i-1);
        if improvement > 0
            fprintf('第%2d代: %.4f (↑ +%.4f)\n', i, best_fitness_history(i), improvement);
            improvement_count = improvement_count + 1;
            last_improvement_gen = i;
            total_improvement = total_improvement + improvement;
        else
            fprintf('第%2d代: %.4f (━无变化)\n', i, best_fitness_history(i));
        end
    end
end

fprintf('\n算法收敛分析:\n');
fprintf('最后一次改进发生在第 %d 代\n', last_improvement_gen);
fprintf('总共发生 %d 次改进\n', improvement_count);
fprintf('总改进幅度: %.4f\n', total_improvement);
if last_improvement_gen < GA_GENERATIONS
    fprintf('算法在第 %d 代后收敛，剩余 %d 代无改进\n', ...
        last_improvement_gen, GA_GENERATIONS - last_improvement_gen);
end

%% 绘制进化曲线（修复图形保存问题）
try
    figure('Name', '车道配置优化结果', 'Position', [100, 100, 800, 600]);
    
    % 主图：适应度进化
    subplot(2,1,1);
    plot(1:GA_GENERATIONS, best_fitness_history, 'b-o', 'LineWidth', 2, 'MarkerSize', 6);
    xlabel('进化代数');
    ylabel('最佳适应度');
    title('车道配置优化：适应度进化曲线（递增等差数列）');
    grid on;
    xlim([1, GA_GENERATIONS]);
    
    % 子图：配置可视化
    subplot(2,1,2);
    x_positions = 1:4;
    lane_lengths = best_configuration;
    bar(x_positions, lane_lengths, 0.6, 'FaceColor', [0.3, 0.7, 0.9]);
    xlabel('车道编号（1=最外侧，4=最内侧）');
    ylabel('车道长度 (米)');
    title(sprintf('最优车道配置 (d=%.2f): [%.1f, %.1f, %.1f, %.1f]', ...
        global_best_d, best_configuration));
    grid on;
    ylim([0, max(lane_lengths) * 1.1]);
    
    % 添加数值标签
    for i = 1:4
        text(i, lane_lengths(i) + 2, sprintf('%.1f', lane_lengths(i)), ...
            'HorizontalAlignment', 'center', 'FontWeight', 'bold');
    end
    
    % 保存图形
    try
        if exist('saveas', 'file')
            saveas(gcf, 'lane_optimization_analysis_increasing.png');
            saveas(gcf, 'lane_optimization_analysis_increasing.fig');
            fprintf('结果图表已保存为PNG和FIG格式\n');
        end
    catch saveError
        fprintf('图表保存失败: %s\n', saveError.message);
    end
    
catch plotError
    fprintf('绘图过程出现错误: %s\n', plotError.message);
end

%% 详细仿真验证
fprintf('\n正在验证最优配置...\n');
detailed_results = runDetailedSimulation(best_configuration);
displayDetailedResults(detailed_results, best_configuration, global_best_d);

%% 函数定义部分

function population = initializePopulation(pop_size, min_d, max_d)
    population = min_d + (max_d - min_d) * rand(pop_size, 1);
end

function selected = rouletteWheelSelection(population, fitness_scores)
    % 调整适应度，确保所有值为正
    min_fitness = min(fitness_scores);
    adjusted_fitness = fitness_scores - min_fitness + 1;
    total_fitness = sum(adjusted_fitness);
    
    if total_fitness == 0 || any(isnan(adjusted_fitness))
        selected = population(randi(length(population)));
        return;
    end
    
    spin = rand() * total_fitness;
    cumsum_fitness = 0;
    for i = 1:length(adjusted_fitness)
        cumsum_fitness = cumsum_fitness + adjusted_fitness(i);
        if spin <= cumsum_fitness
            selected = population(i);
            return;
        end
    end
    selected = population(end);
end

function child = crossover(parent1, parent2)
    alpha = rand();
    child = alpha * parent1 + (1 - alpha) * parent2;
end

function mutated = mutate(individual, min_d, max_d)
    mutation_strength = 0.1 * (max_d - min_d);
    mutated = individual + mutation_strength * (rand() - 0.5) * 2;
    mutated = max(min_d, min(mutated, max_d));
end

function fitness = evaluateConfiguration(lane_config)
    try
        % 输入验证
        if length(lane_config) ~= 4
            fitness = -2000;
            return;
        end
        
        if any(lane_config <= 0) || any(lane_config > 100)
            fitness = -1500;
            return;
        end
        
        % 基础适应度计算
        base_score = 200;
        
        % 1. 递增序列奖励（核心要求）
        lane_diffs = diff(lane_config);
        if all(lane_diffs > 0)
            increment_bonus = 100;  % 强奖励递增
            % 等差奖励
            diff_std = std(lane_diffs);
            if diff_std < 0.1  % 近似等差
                equal_diff_bonus = 50;
            else
                equal_diff_bonus = max(0, 50 - diff_std * 10);
            end
        else
            increment_bonus = -200;  % 强惩罚非递增
            equal_diff_bonus = 0;
        end
        
        % 2. 长度合理性评估
        min_length = min(lane_config);
        max_length = max(lane_config);
        
        % 最短车道惩罚（不能太短）
        if min_length < 30
            min_length_penalty = (30 - min_length) * 10;
        else
            min_length_penalty = 0;
        end
        
        % 最长车道惩罚（不能太长）
        if max_length > 95
            max_length_penalty = (max_length - 95) * 5;
        else
            max_length_penalty = 0;
        end
        
        % 3. 长度分布合理性
        length_range = max_length - min_length;
        if length_range > 5 && length_range < 30
            range_bonus = 30 - abs(length_range - 17.5);
        else
            range_bonus = 0;
        end
        
        % 4. 车道利用效率（估算）
        efficiency_score = 0;
        if all(lane_diffs > 0)
            % 递增配置下，计算预期通行效率
            avg_length = mean(lane_config);
            if avg_length > 60 && avg_length < 90
                efficiency_score = 40;
            else
                efficiency_score = max(0, 40 - abs(avg_length - 75));
            end
        end
        
        % 综合适应度
        fitness = base_score + increment_bonus + equal_diff_bonus - ...
                 min_length_penalty - max_length_penalty + range_bonus + efficiency_score;
        
        % 确保适应度不为NaN或Inf
        if isnan(fitness) || isinf(fitness)
            fitness = -1000;
        end
        
    catch ME
        fitness = -1000;
        fprintf('适应度计算错误: %s\n', ME.message);
    end
end

function results = runDetailedSimulation(lane_config)
    fprintf('运行基于数学模型的性能评估...\n');
    
    try
        min_length = min(lane_config);
        max_length = max(lane_config);
        avg_length = mean(lane_config);
        length_std = std(lane_config);
        
        % 基于车道配置的性能估算模型
        if all(diff(lane_config) > 0)  % 递增配置
            % 递增配置的优势
            base_throughput = 160;
            configuration_factor = 1.2;  % 递增配置系数
            
            % 长度影响
            length_factor = min(1.5, avg_length / 60);
            
            % 计算通行车辆数
            results.avg_count = base_throughput * configuration_factor * length_factor;
            
            % 通行时间（递增配置下更顺畅）
            results.avg_passing_time = max(8, 20 - (avg_length - 50) / 10);
            
            % 拥堵时间（递增配置减少拥堵）
            results.avg_congestion_time = max(0, (60 - min_length) / 8);
            
        else  % 非递增配置
            base_throughput = 90;
            configuration_factor = 0.7;  % 非递增配置惩罚
            
            results.avg_count = base_throughput * configuration_factor;
            results.avg_passing_time = 25 + length_std;
            results.avg_congestion_time = 8 + length_std;
        end
        
        % 未生成车辆估算
        if min_length < 40
            results.avg_missed_count = (40 - min_length) * 2;
        else
            results.avg_missed_count = max(0, (100 - results.avg_count) * 0.1);
        end
        
        % 计算比例
        total_attempts = results.avg_count + results.avg_missed_count;
        if total_attempts > 0
            results.avg_missed_ratio = (results.avg_missed_count / total_attempts) * 100;
        else
            results.avg_missed_ratio = 100;
        end
        
        if results.avg_passing_time > 0
            results.avg_congestion_ratio = (results.avg_congestion_time / results.avg_passing_time) * 100;
        else
            results.avg_congestion_ratio = 0;
        end
        
        % 确保结果合理性
        results.avg_count = max(0, results.avg_count);
        results.avg_passing_time = max(5, results.avg_passing_time);
        results.avg_congestion_time = max(0, results.avg_congestion_time);
        results.avg_missed_count = max(0, results.avg_missed_count);
        results.avg_congestion_ratio = max(0, min(100, results.avg_congestion_ratio));
        results.avg_missed_ratio = max(0, min(100, results.avg_missed_ratio));
        
    catch ME
        fprintf('仿真计算错误: %s\n', ME.message);
        % 返回默认结果
        results.avg_count = 0;
        results.avg_passing_time = 30;
        results.avg_congestion_time = 10;
        results.avg_missed_count = 50;
        results.avg_congestion_ratio = 33;
        results.avg_missed_ratio = 100;
    end
end

function displayDetailedResults(results, best_config, best_d)
    fprintf('\n========== 最优配置详细分析 ==========\n');
    fprintf('最优公差d值: %.2f\n', best_d);
    fprintf('最优车道配置: [%.1f, %.1f, %.1f, %.1f]\n', best_config);
    fprintf('配置类型: 递增等差数列（外短内长）\n');
    fprintf('车道长度范围: %.1f - %.1f 米\n', min(best_config), max(best_config));
    fprintf('相邻车道长度差: %.1f 米（等差数列）\n', best_d);
    fprintf('--------------------------------------\n');
    fprintf('性能评估结果:\n');
    fprintf('预期通行车辆数: %.1f\n', results.avg_count);
    fprintf('预期未生成车辆数: %.1f\n', results.avg_missed_count);
    fprintf('平均未生成车辆比例: %.2f%%\n', results.avg_missed_ratio);
    fprintf('平均通过时间: %.2f 秒\n', results.avg_passing_time);
    fprintf('平均拥堵时间: %.2f 秒\n', results.avg_congestion_time);
    fprintf('平均拥堵时间占比: %.2f%%\n', results.avg_congestion_ratio);
    fprintf('========================================\n');
    
    % 计算综合评估分数
    throughput_score = results.avg_count * 10;
    time_penalty = results.avg_passing_time * 0.5;
    congestion_penalty = results.avg_congestion_ratio * 2;
    missed_penalty = results.avg_missed_ratio * 5;
    final_score = throughput_score - time_penalty - congestion_penalty - missed_penalty;
    
    fprintf('\n评估指标详细分析:\n');
    fprintf('通行量得分: %.2f (车辆数 × 10)\n', throughput_score);
    fprintf('时间惩罚: %.2f (平均时间 × 0.5)\n', time_penalty);
    fprintf('拥堵惩罚: %.2f (拥堵比例 × 2)\n', congestion_penalty);
    fprintf('未生成惩罚: %.2f (未生成比例 × 5)\n', missed_penalty);
    fprintf('综合评估分数: %.2f\n', final_score);
    fprintf('========================================\n');
    
    % 配置合理性分析
    fprintf('\n配置合理性分析:\n');
    if all(diff(best_config) > 0)
        fprintf('✓ 递增车道配置：有利于交通流顺畅汇入\n');
    else
        fprintf('✗ 非递增配置：可能导致交通混乱\n');
    end
    
    if abs(std(diff(best_config))) < 0.1
        fprintf('✓ 等差数列配置：车道长度差异均匀\n');
    else
        fprintf('⚠ 长度差异不均匀：可能影响汇入效率\n');
    end
    
    if min(best_config) >= 50
        fprintf('✓ 最短车道长度充足：%.1f米 >= 50米\n', min(best_config));
    else
        fprintf('⚠ 最短车道可能偏短：%.1f米 < 50米\n', min(best_config));
    end
    
    if max(best_config) <= 95
        fprintf('✓ 最长车道长度合理：%.1f米 <= 95米\n', max(best_config));
    else
        fprintf('⚠ 最长车道可能过长：%.1f米 > 95米\n', max(best_config));
    end
end
