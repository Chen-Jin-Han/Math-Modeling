% 数据定义：变化水平、性能变化百分比（带符号）
changes = {'+10%', '+5%', '-5%', '-10%'};
perf_changes = [-0.34, -1.66, 3.21, -0.53];  % 性能变化百分比
abs_sizes = abs(perf_changes);  % 绝对值用于扇区大小
total_abs = sum(abs_sizes);  % 总和，用于计算比例

% 颜色方案：蓝色、绿色、黄色、红色 (RGB 矩阵)
colors = [0 0 1; 0 1 0; 1 1 0; 1 0 0];  % 蓝色、绿色、黄色、红色

% 标签：包含变化水平和具体值
labels = cell(4,1);
for i = 1:4
    labels{i} = sprintf('%s: %.2f%%', changes{i}, perf_changes(i));
end

% 绘制饼状图
figure('Name', '完成一次变道所需时间参数系统性能变化分布', 'NumberTitle', 'off');
pie_handle = pie(abs_sizes, labels);  % 基本饼图：大小 + 标签

% 设置每个扇区的颜色和删除轮廓线条（针对 Patch 对象）
patch_idx = 1;  % 用于颜色索引
for i = 1:length(pie_handle)
    if strcmp(get(pie_handle(i), 'Type'), 'patch')  % 只针对 Patch 对象
        set(pie_handle(i), 'FaceColor', colors(patch_idx, :), 'EdgeColor', 'none');
        patch_idx = patch_idx + 1;
    end
end

title('完成一次变道所需时间参数系统性能变化分布', ...
      'FontSize', 14, 'FontWeight', 'bold');

% 美化：设置等轴比例、添加图例
legend(labels, 'Location', 'best', 'FontSize', 10);  % 图例
axis equal;  % 等轴比例

% 可选：保存图像
% saveas(gcf, 'lane_change_duration_pie_chart_bgyr_noedge.png');  % 保存为 PNG 文件

% 打印比例信息（控制台输出）
fprintf('饼状图扇区比例（基于绝对变化）:\n');
for i = 1:4
    pct = (abs_sizes(i) / total_abs) * 100;
    fprintf('%s: %.1f%% (性能变化: %.2f%%)\n', changes{i}, pct, perf_changes(i));
end
