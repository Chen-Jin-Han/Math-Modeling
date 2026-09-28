---
name: diagram-tools
description: 图表绘制工具集 - 流程图、ER图、系统模块图、学术三线表生成
version: "1.0.0"
---

# 图表绘制工具集

从 [diagram-tools](https://github.com/kanerel/diagram-tools) 项目提取的核心图表算法，用于数学建模论文中的图表自动生成。

## 📦 功能模块

### 1. 流程图 (FlowchartLayout)

**适用场景**: 算法流程图、决策流程、数据处理流程

**节点类型**:
- `start` - 开始（圆角矩形）
- `end` - 结束（圆角矩形）
- `process` - 处理（矩形）
- `decision` - 判断（菱形）
- `io` - 输入/输出（平行四边形）

**核心方法**:
```python
from algorithms.diagram import FlowchartLayout, save_svg

layout = FlowchartLayout()
layout.add_node('id', '标签', 'process')  # 添加节点
layout.add_edge('from_id', 'to_id', '标签')  # 添加连线
layout.auto_layout()  # 自动布局（拓扑排序）
svg = layout.to_svg()  # 生成SVG
save_svg(svg, 'flowchart.svg')
```

**算法**:
- BFS拓扑排序确定节点层级
- 每层节点水平均匀分布
- 正交折线连接（垂直→水平→垂直）

---

### 2. ER图 (ERDiagramLayout)

**适用场景**: 数据库ER图、实体关系图

**核心方法**:
```python
from algorithms.diagram import ERDiagramLayout, save_svg, save_drawio

er = ERDiagramLayout('表名', ['字段1', '字段2', '字段3'])
svg = er.to_svg()  # SVG格式
xml = er.to_drawio_xml()  # Draw.io格式
save_svg(svg, 'er.svg')
save_drawio(xml, 'er.drawio')
```

**算法**:
- 圆形布局：中心矩形（表名），椭圆节点（字段）围绕中心均匀分布
- 半径 = 180 + N × 24（N = 字段数）
- 起始角度 180°，顺时针均匀分布

---

### 3. 系统模块图 (SystemModuleLayout)

**适用场景**: 系统功能模块图、软件架构图

**节点类型**:
- `module` - 模块（矩形，水平文字）
- `function` - 功能（矩形，垂直文字）

**核心方法**:
```python
from algorithms.diagram import SystemModuleLayout, ModuleNode, save_svg

layout = SystemModuleLayout('系统名称')
layout.add_module('模块名', [
    ModuleNode('功能1', node_type='function'),
    ModuleNode('功能2', node_type='function'),
])
layout.auto_layout()
svg = layout.to_svg()
save_svg(svg, 'system.svg')
```

**算法**:
- 递归计算子树宽度
- 子节点水平居中排列在父节点下方
- 折线连接（垂直→水平→垂直）

---

### 4. 学术三线表 (AcademicTable)

**适用场景**: 论文中的数据对比表、实验结果表

**核心方法**:
```python
from algorithms.diagram import AcademicTable, save_html

table = AcademicTable(
    title='表1 算法性能对比',
    headers=['算法', '最优值', '运行时间'],
    data=[['GA', '0.023', '12.3s'], ['PSO', '0.024', '8.7s']]
)

latex = table.to_latex()   # LaTeX格式
md = table.to_markdown()   # Markdown格式
html = table.to_html()     # HTML格式（带样式）
```

**输出格式**:
- **LaTeX**: 使用 `booktabs` 宏包的 `\toprule`, `\midrule`, `\bottomrule`
- **Markdown**: 标准 Markdown 表格语法
- **HTML**: 带 CSS 样式的三线表（顶线底线粗，标题行下细线）

---

### 5. SQL解析器 (SQLParser)

**适用场景**: 从 SQL DDL 自动提取表结构，配合 ER 图使用

**核心方法**:
```python
from algorithms.diagram import SQLParser

sql = """
CREATE TABLE student (
    id INT PRIMARY KEY COMMENT '学号',
    name VARCHAR(50) NOT NULL COMMENT '姓名',
    age INT COMMENT '年龄'
) ENGINE=InnoDB COMMENT='学生表';
"""

result = SQLParser.parse_create_table(sql)
# result = {
#     'table_name': 'student',
#     'table_comment': '学生表',
#     'columns': [
#         {'name': 'id', 'display': '学号', 'type': 'INT', ...},
#         ...
#     ]
# }
```

---

## 🎯 使用决策

```
IF 需要画算法流程图:
    → FlowchartLayout

IF 需要画ER图/实体关系图:
    → ERDiagramLayout
    IF 有SQL DDL → 先用SQLParser解析，再生成ER图

IF 需要画系统功能模块图:
    → SystemModuleLayout

IF 需要生成论文表格:
    → AcademicTable
    IF 需要LaTeX → to_latex()
    IF 需要Word/网页 → to_html()
    IF 需要Markdown → to_markdown()
```

## 📐 快速参考

| 需求 | 类 | 输出格式 |
|------|-----|---------|
| 算法流程图 | `FlowchartLayout` | SVG |
| 数据库ER图 | `ERDiagramLayout` | SVG / Draw.io XML |
| 系统模块图 | `SystemModuleLayout` | SVG |
| 论文三线表 | `AcademicTable` | LaTeX / HTML / Markdown |
| SQL解析 | `SQLParser` | Python字典 |

## 💡 数学建模常用场景

### 场景1: 论文中的算法流程图
```python
layout = FlowchartLayout()
layout.add_node('s', '开始', 'start')
layout.add_node('input', '读取数据', 'io')
layout.add_node('init', '初始化种群', 'process')
layout.add_node('eval', '计算适应度', 'process')
layout.add_node('check', '满足终止条件?', 'decision')
layout.add_node('select', '选择/交叉/变异', 'process')
layout.add_node('output', '输出最优解', 'io')
layout.add_node('e', '结束', 'end')
# ... 添加连线
```

### 场景2: 数据建模的ER图
```python
er = ERDiagramLayout('订单表', ['订单号', '客户ID', '商品ID', '数量', '金额', '日期'])
svg = er.to_svg()
```

### 场景3: 论文中的算法对比表
```python
table = AcademicTable(
    '表2 不同算法求解结果对比',
    ['算法', '最优解', '最差解', '平均解', '标准差'],
    [['GA', '123.45', '130.22', '126.78', '2.34'],
     ['PSO', '122.89', '128.56', '125.34', '1.89'],
     ['SA', '124.01', '131.45', '127.56', '2.67']]
)
```
