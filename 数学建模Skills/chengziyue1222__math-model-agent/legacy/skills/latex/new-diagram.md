# /new-diagram

## 用途
从8种模板生成TikZ图表，最多5轮迭代修改

## 用法
```bash
/new-diagram [模板名] [输出文件名]
```

## 支持的模板类型
1. **DAG** - 有向无环图
2. **DiD** - 双重差分图
3. **事件研究** - 事件研究图
4. **时间线** - 时间线图
5. **流程图** - 流程示意图
6. **架构图** - 系统架构图
7. **对比图** - 对比分析图
8. **模型图** - 模型结构图

## 参数
- `template`: 模板名称
- `output`: 输出文件名

## 示例
```bash
/new-diagram DAG research_design
/new-diagram DiD treatment_effect
/new-diagram 事件研究 event_study
```

## 迭代修改
支持最多5轮迭代修改，每轮可调整：
- 节点位置
- 连接线样式
- 标签内容
- 颜色方案
