%% MATLAB 脚本：指标提升比较折线图

% 目的：绘制折线图，比较单侧指标和双侧指标从初始值到最优解的提升。

clear; clc; close all;

%% 1. 定义数据

% 初始指标值
single_sided_initial = 0.8273;
double_sided_initial = 0.8825;

% 最优解指标值
single_sided_optimal = 0.8934;
double_sided_optimal = 0.9209;

% 将数据组织成矩阵，方便绘图
% 第一行：初始值
% 第二行：优化值
data_matrix = [single_sided_initial, double_sided_initial;
               single_sided_optimal, double_sided_optimal];

% X轴的标签，表示不同的状态
x_labels = {'初始值', '优化后'};

fprintf('数据已定义。\n');
fprintf('单侧指标：初始 %.4f -> 优化 %.4f\n', single_sided_initial, single_sided_optimal);
fprintf('双侧指标：初始 %.4f -> 优化 %.4f\n', double_sided_initial, double_sided_optimal);


%% 2. 绘制折线图

figure('Name', '指标提升对比', 'NumberTitle', 'off', 'Color', 'w', 'Position', [100 100 700 500]);
hold on; % 允许在同一图上绘制多条线

% 绘制单侧指标的折线
plot(1:length(x_labels), data_matrix(:, 1), '-o', ...
     'LineWidth', 2, ...
     'MarkerSize', 8, ...
     'MarkerFaceColor', [0.8500 0.3250 0.0980], ... % 橙色填充标记
     'Color', [0.8500 0.3250 0.0980], ...          % 橙色线条
     'DisplayName', '单侧指标');

% 绘制双侧指标的折线
plot(1:length(x_labels), data_matrix(:, 2), '--s', ... % 使用虚线和方形标记
     'LineWidth', 2, ...
     'MarkerSize', 8, ...
     'MarkerFaceColor', [0 0.4470 0.7410], ... % 蓝色填充标记
     'Color', [0 0.4470 0.7410], ...          % 蓝色线条
     'DisplayName', '双侧指标');

% 添加数据点上的数值标签
text(1, single_sided_initial, sprintf(' %.4f', single_sided_initial), ...
     'VerticalAlignment', 'bottom', 'HorizontalAlignment', 'right', 'FontSize', 10, 'Color', [0.8500 0.3250 0.0980]);
text(2, single_sided_optimal, sprintf(' %.4f', single_sided_optimal), ...
     'VerticalAlignment', 'bottom', 'HorizontalAlignment', 'left', 'FontSize', 10, 'Color', [0.8500 0.3250 0.0980]);

text(1, double_sided_initial, sprintf(' %.4f', double_sided_initial), ...
     'VerticalAlignment', 'top', 'HorizontalAlignment', 'right', 'FontSize', 10, 'Color', [0 0.4470 0.7410]);
text(2, double_sided_optimal, sprintf(' %.4f', double_sided_optimal), ...
     'VerticalAlignment', 'top', 'HorizontalAlignment', 'left', 'FontSize', 10, 'Color', [0 0.4470 0.7410]);


% 设置图表标题和轴标签
title('单侧与双侧指标的提升比较', 'FontSize', 14, 'FontWeight', 'bold');
xlabel('状态', 'FontSize', 12, 'FontWeight', 'bold');
ylabel('指标值', 'FontSize', 12, 'FontWeight', 'bold');

% 设置X轴刻度及标签
xticks(1:length(x_labels));
xticklabels(x_labels);
xlim([0.5, length(x_labels) + 0.5]); % 稍微扩展X轴范围，使标记居中

% 设置Y轴范围，使其更清晰地显示变化
min_val = min([single_sided_initial, double_sided_initial, single_sided_optimal, double_sided_optimal]);
max_val = max([single_sided_initial, double_sided_initial, single_sided_optimal, double_sided_optimal]);
ylim([floor(min_val * 10) / 10 - 0.05, ceil(max_val * 10) / 10 + 0.05]); % 自动调整Y轴范围，留出一些边距

grid on; % 添加网格
legend('Location', 'northwest', 'FontSize', 10); % 添加图例
box on; % 显示图框

% 美化坐标轴
set(gca, 'FontSize', 10, 'FontWeight', 'bold', 'LineWidth', 1);

fprintf('折线图绘制完成！\n');
