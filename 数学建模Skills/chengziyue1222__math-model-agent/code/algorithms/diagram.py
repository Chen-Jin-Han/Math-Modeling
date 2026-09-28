"""
图表绘制工具 (Diagram)
=======================
数学建模论文中的流程图、ER图、系统模块图、学术三线表等自动生成。

包含类:
- FlowchartLayout: 流程图自动布局（Sugiyama 算法）
- ERDiagramLayout: ER 图布局（实体-关系图）
- SystemModuleLayout: 系统模块图布局
- AcademicTable: 学术三线表生成
- SQLParser: SQL 建表语句解析 → ER 图

竞赛场景:
- 论文中的系统架构图、算法流程图
- 数据库设计 ER 图
- 三线表自动生成（LaTeX/HTML/Markdown）

参考: https://github.com/kanerel/diagram-tools
"""

import math
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque


# ============================================================
# 1. 流程图自动布局 (FlowChart Auto-Layout)
# ============================================================

@dataclass
class FlowNode:
    """流程图节点"""
    id: str
    label: str
    node_type: str = 'process'  # start, end, process, decision, io
    x: float = 0
    y: float = 0
    w: float = 120
    h: float = 44


class FlowEdge:
    """流程图连线"""
    def __init__(self, from_id: str = '', to_id: str = '', label: str = '',
                 source: str = '', target: str = ''):
        self.from_id = from_id or source
        self.to_id = to_id or target
        self.label = label


class FlowchartLayout:
    """
    流程图自动布局引擎

    使用拓扑排序确定层级，自上而下布局
    支持5种节点类型: start(开始), end(结束), process(处理), decision(判断), io(输入/输出)

    算法:
    1. BFS拓扑排序确定节点层级
    2. 每层节点水平均匀分布
    3. 正交折线连接(垂直-水平-垂直)
    """

    NODE_H = 44
    NODE_MIN_W = 120
    NODE_PAD_X = 28
    CHAR_W = 14
    H_GAP = 60
    V_GAP = 80
    DIAMOND_SIZE = 36
    IO_SKEW = 14

    def __init__(self, nodes: Optional[List[FlowNode]] = None,
                 edges: Optional[List[FlowEdge]] = None):
        self.nodes: List[FlowNode] = list(nodes) if nodes else []
        self.edges: List[FlowEdge] = list(edges) if edges else []
        self.positions: Dict[str, Dict] = {}

    def add_node(self, node_id: str, label: str, node_type: str = 'process'):
        self.nodes.append(FlowNode(id=node_id, label=label, node_type=node_type))

    def add_edge(self, from_id: str, to_id: str, label: str = ''):
        self.edges.append(FlowEdge(from_id=from_id, to_id=to_id, label=label))

    def get_node_width(self, node: FlowNode) -> float:
        text_len = len(node.label)
        return max(text_len * self.CHAR_W + self.NODE_PAD_X * 2, self.NODE_MIN_W)

    def get_node_height(self, node: FlowNode) -> float:
        if node.node_type == 'decision':
            return self.DIAMOND_SIZE * 2
        return self.NODE_H

    def auto_layout(self):
        """拓扑排序自动布局"""
        valid_nodes = [n for n in self.nodes if n.label.strip()]
        if not valid_nodes:
            return

        self.positions = {}
        node_map = {n.id: n for n in valid_nodes}

        # 构建邻接表
        out_edges = defaultdict(list)
        in_degree = defaultdict(int)
        for n in valid_nodes:
            in_degree[n.id] = 0

        for edge in self.edges:
            if edge.from_id in node_map and edge.to_id in node_map:
                out_edges[edge.from_id].append(edge.to_id)
                in_degree[edge.to_id] += 1

        # BFS拓扑排序确定层级
        layers = []
        visited = set()
        queue = deque([n.id for n in valid_nodes if in_degree[n.id] == 0])

        if not queue:
            queue = deque([n.id for n in valid_nodes])

        while queue:
            layer = list(queue)
            layers.append(layer)
            visited.update(layer)
            next_queue = []
            for nid in queue:
                for target in out_edges[nid]:
                    if target not in visited:
                        next_queue.append(target)
            queue = deque(dict.fromkeys(next_queue))

            if not queue:
                remaining = [n.id for n in valid_nodes if n.id not in visited]
                if remaining:
                    layers.append(remaining)
                    visited.update(remaining)

        # 布局每层节点
        current_y = 60
        for layer in layers:
            layer_nodes = [node_map[nid] for nid in layer if nid in node_map]
            if not layer_nodes:
                continue
            total_w = sum(self.get_node_width(n) for n in layer_nodes) + \
                      (len(layer_nodes) - 1) * self.H_GAP
            current_x = -total_w / 2

            for node in layer_nodes:
                w = self.get_node_width(node)
                h = self.get_node_height(node)
                cx = current_x + w / 2
                cy = current_y
                self.positions[node.id] = {'x': cx, 'y': cy, 'w': w, 'h': h}
                current_x += w + self.H_GAP

            max_h = max(self.get_node_height(n) for n in layer_nodes)
            current_y += max_h + self.V_GAP

    def layout(self):
        """执行布局并将坐标写回节点对象。"""
        self.auto_layout()
        node_map = {n.id: n for n in self.nodes}
        for nid, pos in self.positions.items():
            if nid in node_map:
                node_map[nid].x = pos['x']
                node_map[nid].y = pos['y']

    def to_svg(self) -> str:
        """生成SVG字符串"""
        if not self.positions:
            self.auto_layout()

        valid_nodes = [n for n in self.nodes if n.label.strip() and n.id in self.positions]
        if not valid_nodes:
            return ''

        node_map = {n.id: n for n in valid_nodes}

        # 计算viewBox
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        for nid, pos in self.positions.items():
            node = node_map.get(nid)
            if not node:
                continue
            if node.node_type == 'decision':
                min_x = min(min_x, pos['x'] - pos['w'] / 2)
                max_x = max(max_x, pos['x'] + pos['w'] / 2)
                min_y = min(min_y, pos['y'] - self.DIAMOND_SIZE)
                max_y = max(max_y, pos['y'] + self.DIAMOND_SIZE)
            else:
                min_x = min(min_x, pos['x'] - pos['w'] / 2)
                max_x = max(max_x, pos['x'] + pos['w'] / 2)
                min_y = min(min_y, pos['y'] - pos['h'] / 2)
                max_y = max(max_y, pos['y'] + pos['h'] / 2)

        pad_x, pad_y = 80, 60
        vb_w = max(max_x - min_x + pad_x * 2, 400)
        vb_h = max(max_y - min_y + pad_y * 2, 300)
        vb_x = (min_x + max_x) / 2 - vb_w / 2
        vb_y = (min_y + max_y) / 2 - vb_h / 2

        def esc(s):
            return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

        parts = []
        parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" '
                     f'viewBox="{vb_x} {vb_y} {vb_w} {vb_h}" '
                     f'preserveAspectRatio="xMidYMid meet" '
                     f'style="background:#ffffff;font-family:sans-serif">')

        # 箭头标记
        parts.append('<defs>')
        parts.append('<marker id="arrow" markerWidth="12" markerHeight="8" refX="11" refY="4" '
                     'orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
                     '<path d="M 0 0 L 12 4 L 0 8 L 3 4 Z" fill="#555"/></marker>')
        parts.append('</defs>')

        # 连线
        parts.append('<g class="links">')
        for edge in self.edges:
            if edge.from_id not in self.positions or edge.to_id not in self.positions:
                continue
            fp = self.positions[edge.from_id]
            tp = self.positions[edge.to_id]
            fn = node_map.get(edge.from_id)
            tn = node_map.get(edge.to_id)
            if not fn or not tn:
                continue

            x1 = fp['x']
            y1 = fp['y'] + (self.DIAMOND_SIZE if fn.node_type == 'decision' else fp['h'] / 2)
            x2 = tp['x']
            y2 = tp['y'] - (self.DIAMOND_SIZE if tn.node_type == 'decision' else tp['h'] / 2)

            mid_y = (y1 + y2) / 2
            path_d = f'M {x1} {y1} L {x1} {mid_y} L {x2} {mid_y} L {x2} {y2}'

            parts.append(f'<path stroke="#555" stroke-width="1.5" fill="none" d="{path_d}" '
                         f'marker-end="url(#arrow)"/>')

            if edge.label.strip():
                label_x = (x1 + x2) / 2
                text_w = len(edge.label.strip()) * 8 + 16
                parts.append(f'<g transform="translate({label_x},{mid_y})">')
                parts.append(f'<rect x="{-text_w/2}" y="-10" width="{text_w}" height="20" '
                             f'fill="#ffffff" rx="3"/>')
                parts.append(f'<text text-anchor="middle" dominant-baseline="central" '
                             f'fill="#555" font-size="11">{esc(edge.label)}</text>')
                parts.append('</g>')
        parts.append('</g>')

        # 节点
        parts.append('<g class="nodes">')
        for node in valid_nodes:
            pos = self.positions[node.id]
            w, h = pos['w'], pos['h']
            label = esc(node.label.strip())

            parts.append(f'<g transform="translate({pos["x"]},{pos["y"]})">')

            if node.node_type in ('start', 'end'):
                rx = h / 2
                parts.append(f'<rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" '
                             f'rx="{rx}" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>')
            elif node.node_type == 'process':
                parts.append(f'<rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" '
                             f'fill="#ffffff" stroke="#000000" stroke-width="1.5"/>')
            elif node.node_type == 'decision':
                dw, dh = w / 2, self.DIAMOND_SIZE
                parts.append(f'<polygon points="0,{-dh} {dw},0 0,{dh} {-dw},0" '
                             f'fill="#ffffff" stroke="#000000" stroke-width="1.5"/>')
            elif node.node_type == 'io':
                sk = self.IO_SKEW
                parts.append(f'<polygon points="{-w/2+sk},{-h/2} {w/2+sk},{-h/2} '
                             f'{w/2-sk},{h/2} {-w/2-sk},{h/2}" '
                             f'fill="#ffffff" stroke="#000000" stroke-width="1.5"/>')

            parts.append(f'<text text-anchor="middle" fill="#000000" font-size="13">'
                         f'<tspan x="0" dy="0.35em">{label}</tspan></text>')
            parts.append('</g>')
        parts.append('</g>')
        parts.append('</svg>')

        return '\n'.join(parts)


# ============================================================
# 2. ER图圆形布局 (ER Diagram Circular Layout)
# ============================================================

class ERDiagramLayout:
    """
    ER图圆形布局引擎

    中心矩形(表名)，椭圆节点(字段)围绕中心均匀分布

    算法:
    - 半径 = 180 + N * 24 (N = 字段数)
    - 起始角度 = 180°(左侧)，顺时针均匀分布
    - 角度间隔 = 360° / N
    """

    RECT_W = 180
    RECT_H = 50
    ELLIPSE_W = 140
    ELLIPSE_H = 60

    def __init__(self, table_name: Optional[str] = None, fields: Optional[List[str]] = None,
                 tables: Optional[Dict[str, List[str]]] = None):
        if isinstance(table_name, dict):
            tables = table_name
            table_name = None
        if tables:
            self.tables = tables
            self.table_name = next(iter(tables))
            self.fields = list(tables[self.table_name])
        else:
            self.table_name = table_name or ''
            self.fields = fields or []
            self.tables = {self.table_name: self.fields}

    def layout(self):
        """计算布局（兼容测试接口）。"""
        self.calculate_positions()

    def calculate_positions(self) -> Dict[str, Any]:
        """计算圆形布局位置"""
        n = len(self.fields)
        if n == 0:
            return {'center': (0, 0), 'fields': []}

        radius = 180 + n * 24
        cx, cy = self.RECT_W / 2, self.RECT_H / 2

        field_positions = []
        for i in range(n):
            angle_deg = 180 + (360 / n) * i
            angle_rad = math.radians(angle_deg)
            ecx = cx + radius * math.cos(angle_rad)
            ecy = cy - radius * math.sin(angle_rad)
            field_positions.append({
                'x': ecx - self.ELLIPSE_W / 2,
                'y': ecy - self.ELLIPSE_H / 2,
                'cx': ecx,
                'cy': ecy,
                'field': self.fields[i]
            })

        return {
            'center': (cx, cy),
            'radius': radius,
            'fields': field_positions
        }

    def to_svg(self) -> str:
        """生成SVG字符串"""
        layout = self.calculate_positions()
        if not layout['fields']:
            return ''

        # 计算边界
        min_x = min(f['x'] for f in layout['fields'])
        min_y = min(f['y'] for f in layout['fields'])
        max_x = max(f['x'] + self.ELLIPSE_W for f in layout['fields'])
        max_y = max(f['y'] + self.ELLIPSE_H for f in layout['fields'])

        pad = 20
        min_x = min(min_x, 0) - pad
        min_y = min(min_y, 0) - pad
        max_x = max(max_x, self.RECT_W) + pad
        max_y = max(max_y, self.RECT_H) + pad

        group_w = max_x - min_x
        group_h = max_y - min_y
        off_x, off_y = -min_x, -min_y

        def esc(s):
            return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        parts = []
        parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{group_w}" height="{group_h}" '
                     f'viewBox="0 0 {group_w} {group_h}" style="font-family:SimSun,serif">')

        # 连线
        for f in layout['fields']:
            parts.append(f'<line x1="{self.RECT_W/2 + off_x}" y1="{self.RECT_H/2 + off_y}" '
                         f'x2="{f["cx"] + off_x}" y2="{f["cy"] + off_y}" '
                         f'stroke="#000" stroke-width="1"/>')

        # 椭圆节点
        for f in layout['fields']:
            parts.append(f'<ellipse cx="{f["cx"] + off_x}" cy="{f["cy"] + off_y}" '
                         f'rx="{self.ELLIPSE_W/2}" ry="{self.ELLIPSE_H/2}" '
                         f'fill="#ffffff" stroke="#000" stroke-width="1"/>')
            parts.append(f'<text x="{f["cx"] + off_x}" y="{f["cy"] + off_y}" '
                         f'text-anchor="middle" dominant-baseline="central" '
                         f'font-size="14">{esc(f["field"])}</text>')

        # 中心矩形
        parts.append(f'<rect x="{off_x}" y="{off_y}" width="{self.RECT_W}" height="{self.RECT_H}" '
                     f'fill="#ffffff" stroke="#000" stroke-width="1.5" rx="2"/>')
        parts.append(f'<text x="{self.RECT_W/2 + off_x}" y="{self.RECT_H/2 + off_y}" '
                     f'text-anchor="middle" dominant-baseline="central" '
                     f'font-size="16" font-weight="bold">{esc(self.table_name)}</text>')

        parts.append('</svg>')
        return '\n'.join(parts)

    def to_drawio_xml(self) -> str:
        """生成 draw.io XML"""
        layout = self.calculate_positions()
        n = len(self.fields)
        def esc(s):
            return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

        # 计算group边界
        min_x = min(f['x'] for f in layout['fields'])
        min_y = min(f['y'] for f in layout['fields'])
        max_x = max(f['x'] + self.ELLIPSE_W for f in layout['fields'])
        max_y = max(f['y'] + self.ELLIPSE_H for f in layout['fields'])
        pad = 20
        min_x = min(min_x, 0) - pad
        min_y = min(min_y, 0) - pad
        max_x = max(max_x, self.RECT_W) + pad
        max_y = max(max_y, self.RECT_H) + pad

        group_w = max_x - min_x
        group_h = max_y - min_y
        off_x, off_y = -min_x, -min_y

        xml = '<mxfile><diagram id="ER-Diagram" name="ER Diagram"><mxGraphModel><root>'
        xml += '<mxCell id="0"/><mxCell id="1" parent="0"/>'

        # 连线
        for i in range(n):
            edge_id = str(n + 4 + i)
            target_id = str(3 + i)
            xml += (f'<mxCell id="{edge_id}" parent="1" edge="1" source="2" target="{target_id}" '
                    f'style="endArrow=none;html=1;strokeColor=#000000;strokeWidth=1;fontSize=14;'
                    f'fontFamily=SimSun,serif;fontColor=#000000;">'
                    f'<mxGeometry relative="1" as="geometry"/></mxCell>')

        # Group容器
        group_id = str(n + 3)
        xml += (f'<mxCell id="{group_id}" parent="1" vertex="1" connectable="0" '
                f'style="group;dropTarget=0;pointerEvents=0;">'
                f'<mxGeometry x="360" y="250" width="{group_w}" height="{group_h}" as="geometry"/></mxCell>')

        # 椭圆节点
        for i, f in enumerate(layout['fields']):
            cell_id = str(3 + i)
            xml += (f'<mxCell id="{cell_id}" parent="{group_id}" vertex="1" '
                    f'style="ellipse;whiteSpace=wrap;html=1;fillColor=#ffffff;fontColor=#000000;'
                    f'fontSize=14;fontFamily=SimSun,serif;" '
                    f'value="{esc(f["field"])}">'
                    f'<mxGeometry x="{f["x"] + off_x}" y="{f["y"] + off_y}" '
                    f'width="{self.ELLIPSE_W}" height="{self.ELLIPSE_H}" as="geometry"/></mxCell>')

        # 中心矩形
        xml += (f'<mxCell id="2" parent="{group_id}" vertex="1" '
                f'style="rounded=1;arcSize=0;whiteSpace=wrap;html=1;fillColor=#ffffff;'
                f'fontColor=#000000;fontSize=16;fontFamily=SimSun,serif;" '
                f'value="{esc(self.table_name)}">'
                f'<mxGeometry x="{off_x}" y="{off_y}" width="{self.RECT_W}" height="{self.RECT_H}" '
                f'as="geometry"/></mxCell>')

        xml += '</root></mxGraphModel></diagram></mxfile>'
        return xml


# ============================================================
# 3. 系统模块图树形布局 (System Module Tree Layout)
# ============================================================

@dataclass
class ModuleNode:
    """模块节点"""
    name: str
    node_type: str = 'module'  # module, function
    children: List = field(default_factory=list)


class SystemModuleLayout:
    """
    系统模块图树形布局引擎

    递归计算子树宽度，自上而下布局
    支持模块和功能两种节点类型，功能节点纵向排列文字

    算法:
    1. 递归计算每个子树所需宽度
    2. 子节点水平居中排列在父节点下方
    3. 折线连接(垂直-水平-垂直)
    """

    MOD_MIN_W = 150
    MOD_H = 70
    MOD_PAD_X = 30
    FUNC_W = 70
    FUNC_MIN_H = 120
    FUNC_CHAR_H = 30
    FUNC_PAD = 30
    H_GAP = 40
    V_GAP = 75

    def __init__(self, system_name: str):
        self.system_name = system_name
        self.modules: List[ModuleNode] = []
        self.positions: Dict[str, Dict] = {}
        self.connections: List[Tuple[str, str]] = []

    def add_module(self, name: str, children: Optional[List[ModuleNode]] = None):
        self.modules.append(ModuleNode(name=name, children=children or []))

    def calc_subtree_width(self, node: ModuleNode) -> float:
        """递归计算子树宽度"""
        is_func = node.node_type == 'function'
        node_w = self.FUNC_W if is_func else max(len(node.name) * 30 + self.MOD_PAD_X * 2, self.MOD_MIN_W)

        if not node.children:
            return node_w

        children_total_w = sum(self.calc_subtree_width(c) for c in node.children) + \
                           (len(node.children) - 1) * self.H_GAP
        return max(node_w, children_total_w)

    def _layout_subtree(self, node: ModuleNode, cx: float, y: float, parent_max_func_h: float = 0):
        """递归布局子树"""
        is_func = node.node_type == 'function'
        node_w = self.FUNC_W if is_func else max(len(node.name) * 30 + self.MOD_PAD_X * 2, self.MOD_MIN_W)

        if not node.children:
            node_h = parent_max_func_h if is_func and parent_max_func_h > 0 else \
                (max(len(node.name) * self.FUNC_CHAR_H + self.FUNC_PAD * 2, self.FUNC_MIN_H) if is_func else self.MOD_H)
            self.positions[node.name] = {'x': cx, 'y': y, 'w': node_w, 'h': node_h, 'is_func': is_func}
            return

        # 计算子节点最大功能节点高度
        max_func_h = 0
        for child in node.children:
            if child.node_type == 'function':
                h = len(child.name) * self.FUNC_CHAR_H + self.FUNC_PAD * 2
                max_func_h = max(max_func_h, h)
        max_func_h = max(max_func_h, self.FUNC_MIN_H, parent_max_func_h)

        node_h = max_func_h if is_func else self.MOD_H
        self.positions[node.name] = {'x': cx, 'y': y, 'w': node_w, 'h': node_h, 'is_func': is_func}

        child_widths = [self.calc_subtree_width(c) for c in node.children]
        total_child_w = sum(child_widths) + (len(node.children) - 1) * self.H_GAP

        start_x = cx - total_child_w / 2
        child_y = y + node_h / 2 + self.V_GAP

        for i, child in enumerate(node.children):
            child_cx = start_x + child_widths[i] / 2
            self.connections.append((node.name, child.name))
            self._layout_subtree(child, child_cx, child_y, max_func_h)
            start_x += child_widths[i] + self.H_GAP

    def auto_layout(self):
        """自动布局"""
        self.positions = {}
        self.connections = []

        root_w = max(len(self.system_name) * 30 + 80, 200)
        self.positions['__root__'] = {'x': 0, 'y': 0, 'w': root_w, 'h': 70, 'is_func': False}

        if not self.modules:
            return

        mod_widths = [self.calc_subtree_width(m) for m in self.modules]
        total_mod_w = sum(mod_widths) + (len(self.modules) - 1) * self.H_GAP

        start_x = -total_mod_w / 2
        mod_y = 70 / 2 + self.V_GAP

        for i, mod in enumerate(self.modules):
            mod_cx = start_x + mod_widths[i] / 2
            self.connections.append(('__root__', mod.name))
            self._layout_subtree(mod, mod_cx, mod_y)
            start_x += mod_widths[i] + self.H_GAP

    def to_svg(self) -> str:
        """生成SVG字符串"""
        if not self.positions:
            self.auto_layout()

        if not self.positions:
            return ''

        def esc(s):
            return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # 计算viewBox
        min_x = min(p['x'] - p['w'] / 2 for p in self.positions.values())
        max_x = max(p['x'] + p['w'] / 2 for p in self.positions.values())
        min_y = min(p['y'] - p['h'] / 2 for p in self.positions.values())
        max_y = max(p['y'] + p['h'] / 2 for p in self.positions.values())

        pad_x, pad_y = 80, 60
        vb_x = min_x - pad_x
        vb_y = min_y - pad_y
        vb_w = max(max_x - min_x + pad_x * 2, 400)
        vb_h = max(max_y - min_y + pad_y * 2, 200)

        parts = []
        parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" '
                     f'viewBox="{vb_x} {vb_y} {vb_w} {vb_h}" '
                     f'preserveAspectRatio="xMidYMid meet" '
                     f'style="background:#ffffff;font-family:sans-serif">')

        # 连线
        parts.append('<g class="links">')
        for from_id, to_id in self.connections:
            fp = self.positions.get(from_id)
            tp = self.positions.get(to_id)
            if not fp or not tp:
                continue

            x1 = fp['x']
            y1 = fp['y'] + (fp['h'] if fp['is_func'] else fp['h'] / 2)
            x2 = tp['x']
            y2 = tp['y'] if tp['is_func'] else tp['y'] - tp['h'] / 2
            mid_y = (y1 + y2) / 2

            parts.append(f'<path stroke="#000" stroke-width="2" fill="none" '
                         f'd="M {x1} {y1} L {x1} {mid_y} L {x2} {mid_y} L {x2} {y2}"/>')
        parts.append('</g>')

        # 节点
        parts.append('<g class="nodes">')
        for nid, pos in self.positions.items():
            label = self.system_name if nid == '__root__' else nid
            if pos['is_func']:
                chars = list(label)
                total_text_h = len(chars) * self.FUNC_CHAR_H
                node_h = pos['h']
                parts.append(f'<g transform="translate({pos["x"]},{pos["y"]})">')
                parts.append(f'<rect x="{-self.FUNC_W/2}" y="0" width="{self.FUNC_W}" height="{node_h}" '
                             f'fill="#ffffff" stroke="#000" stroke-width="2"/>')
                for i, ch in enumerate(chars):
                    char_y = (node_h - total_text_h) / 2 + self.FUNC_CHAR_H / 2 + i * self.FUNC_CHAR_H
                    parts.append(f'<text x="0" y="{char_y}" text-anchor="middle" '
                                 f'dominant-baseline="middle" font-size="16">{esc(ch)}</text>')
                parts.append('</g>')
            else:
                parts.append(f'<g transform="translate({pos["x"]},{pos["y"]})">')
                parts.append(f'<rect x="{-pos["w"]/2}" y="{-pos["h"]/2}" width="{pos["w"]}" height="{pos["h"]}" '
                             f'fill="#ffffff" stroke="#000" stroke-width="2"/>')
                parts.append(f'<text text-anchor="middle" font-size="16">'
                             f'<tspan x="0" dy="0.35em">{esc(label)}</tspan></text>')
                parts.append('</g>')
        parts.append('</g>')
        parts.append('</svg>')

        return '\n'.join(parts)


# ============================================================
# 4. 学术三线表生成 (Academic Three-Line Table)
# ============================================================

class AcademicTable:
    """
    学术三线表生成器

    生成符合论文规范的三线表:
    - 顶线和底线: 粗线(1.5pt)
    - 标题行下方: 细线(0.75pt)
    - 无竖线
    """

    def __init__(self, title: str = '', headers: Optional[List[str]] = None,
                 data: Optional[List[List[str]]] = None, caption: str = ''):
        self.title = caption or title
        self.headers = headers or []
        self.data = data or []

    def to_latex(self) -> str:
        """生成LaTeX三线表代码"""
        n_cols = len(self.headers)
        col_spec = 'l' * n_cols

        lines = []
        lines.append('\\begin{table}[htbp]')
        lines.append('  \\centering')
        lines.append(f'  \\caption{{{self.title}}}')
        lines.append(f'  \\begin{{tabular}}{{{col_spec}}}')
        lines.append('    \\toprule')

        # 表头
        header_line = ' & '.join(f'\\textbf{{{h}}}' for h in self.headers) + ' \\\\'
        lines.append(f'    {header_line}')
        lines.append('    \\midrule')

        # 数据行
        for row in self.data:
            row_line = ' & '.join(str(cell) for cell in row) + ' \\\\'
            lines.append(f'    {row_line}')

        lines.append('    \\bottomrule')
        lines.append('  \\end{tabular}')
        lines.append('\\end{table}')

        return '\n'.join(lines)

    def to_markdown(self) -> str:
        """生成Markdown表格"""
        lines = []
        lines.append(f'**{self.title}**')
        lines.append('')

        # 表头
        lines.append('| ' + ' | '.join(self.headers) + ' |')
        lines.append('| ' + ' | '.join(['---'] * len(self.headers)) + ' |')

        # 数据行
        for row in self.data:
            lines.append('| ' + ' | '.join(str(cell) for cell in row) + ' |')

        return '\n'.join(lines)

    def to_html(self) -> str:
        """生成HTML三线表"""
        def esc(s):
            return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        lines = []
        lines.append('<style>')
        lines.append('.three-line-table { border-collapse: collapse; margin: 20px auto; font-family: SimSun, serif; }')
        lines.append('.three-line-table th, .three-line-table td { padding: 8px 16px; text-align: center; }')
        lines.append('.three-line-table thead tr:first-child th { border-top: 2px solid #000; border-bottom: 1px solid #000; }')
        lines.append('.three-line-table tbody tr:last-child td { border-bottom: 2px solid #000; }')
        lines.append('.three-line-table caption { font-size: 14px; font-weight: bold; margin-bottom: 8px; }')
        lines.append('</style>')
        lines.append('<table class="three-line-table">')
        lines.append(f'  <caption>{esc(self.title)}</caption>')
        lines.append('  <thead><tr>')
        for h in self.headers:
            lines.append(f'    <th>{esc(h)}</th>')
        lines.append('  </tr></thead>')
        lines.append('  <tbody>')
        for row in self.data:
            lines.append('    <tr>')
            for cell in row:
                lines.append(f'      <td>{esc(cell)}</td>')
            lines.append('    </tr>')
        lines.append('  </tbody>')
        lines.append('</table>')

        return '\n'.join(lines)


# ============================================================
# 5. SQL解析器 (SQL DDL Parser)
# ============================================================

class SQLParser:
    """
    SQL DDL解析器

    解析CREATE TABLE语句，提取表名、字段名、类型、约束等
    """

    @staticmethod
    def parse_create_table(sql: str) -> Dict[str, Any]:
        """解析单个CREATE TABLE语句"""
        import re

        # 提取表名
        name_match = re.search(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`([^`]+)`|"([^"]+)"|(\w+))',
            sql, re.IGNORECASE
        )
        table_name = name_match.group(1) or name_match.group(2) or name_match.group(3) if name_match else 'unknown'

        # 提取括号内的列定义
        paren_match = re.search(r'\(([\s\S]*)\)\s*(?:ENGINE|DEFAULT|CHARSET|COLLATE|$)', sql, re.IGNORECASE)
        columns_str = paren_match.group(1) if paren_match else ''

        # 提取表注释（在最后一个右括号之后）
        last_paren = sql.rfind(')')
        table_comment = ''
        if last_paren >= 0:
            after_paren = sql[last_paren + 1:]
            comment_match = re.search(r"COMMENT\s*=?\s*'([^']*)'", after_paren, re.IGNORECASE)
            if comment_match:
                table_comment = comment_match.group(1)

        # 解析列
        columns = []
        depth = 0
        current = ''
        for ch in columns_str:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            if ch == ',' and depth == 0:
                col = current.strip()
                if col:
                    parsed = SQLParser._parse_column(col)
                    if parsed:
                        columns.append(parsed)
                current = ''
            else:
                current += ch
        if current.strip():
            parsed = SQLParser._parse_column(current.strip())
            if parsed:
                columns.append(parsed)

        return {
            'table_name': table_name,
            'table_comment': table_comment,
            'columns': columns
        }

    @staticmethod
    def _parse_column(col_def: str) -> Optional[Dict[str, str]]:
        """解析单个列定义"""
        import re

        upper = col_def.upper().strip()
        if re.match(r'^(PRIMARY\s+KEY|UNIQUE\s+KEY|UNIQUE|KEY|INDEX|CONSTRAINT|CHECK|FOREIGN\s+KEY)', upper):
            return None

        name_match = re.match(r'^`([^`]+)`|"([^"]+)"|(\w+)', col_def)
        if not name_match:
            return None
        name = name_match.group(1) or name_match.group(2) or name_match.group(3)

        after_name = col_def[name_match.end():].strip()
        type_match = re.match(r'(\w+(?:\s*\(\s*\d+(?:\s*,\s*\d+)?\s*\))?)', after_name, re.IGNORECASE)
        col_type = type_match.group(1).upper() if type_match else ''

        nullable = 'YES'
        if re.search(r'\bNOT\s+NULL\b', col_def, re.IGNORECASE):
            nullable = 'NO'

        default_val = '—'
        default_match = re.search(r"DEFAULT\s+(?:'([^']*)'|(\S+))", col_def, re.IGNORECASE)
        if default_match:
            default_val = default_match.group(1) if default_match.group(1) is not None else default_match.group(2)

        comment_match = re.search(r"COMMENT\s+'([^']*)'", col_def, re.IGNORECASE)
        display = comment_match.group(1) if comment_match else name

        return {
            'name': name,
            'display': display,
            'type': col_type,
            'nullable': nullable,
            'default': default_val
        }

    @staticmethod
    def parse_multiple(sql: str) -> List[Dict[str, Any]]:
        """解析多个CREATE TABLE语句"""
        import re
        normalized = sql.strip()
        normalized = re.sub(r'--[^\n]*', '', normalized)
        normalized = re.sub(r'/\*[\s\S]*?\*/', '', normalized)

        positions = [m.start() for m in re.finditer(r'CREATE\s+TABLE\s', normalized, re.IGNORECASE)]
        results = []
        for i, pos in enumerate(positions):
            end = positions[i + 1] if i + 1 < len(positions) else len(normalized)
            stmt = normalized[pos:end].strip()
            results.append(SQLParser.parse_create_table(stmt))
        return results


# ============================================================
# 6. 绘图辅助函数
# ============================================================

def save_svg(svg_content: str, filepath: Optional[str] = None) -> str:
    """保存 SVG 到文件；未指定路径时返回内容。"""
    if filepath is None:
        return svg_content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f"SVG已保存到: {filepath}")
    return svg_content


def save_drawio(xml_content: str, filepath: str):
    """保存draw.io XML到文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    print(f"Draw.io文件已保存到: {filepath}")


def save_html(html_content: str, filepath: Optional[str] = None) -> str:
    """保存 HTML 到文件；未指定路径时返回内容。"""
    if filepath is None:
        return html_content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"HTML已保存到: {filepath}")
    return html_content


# ============================================================
# 示例
# ============================================================

def example_flowchart():
    """流程图示例: 算法流程"""
    layout = FlowchartLayout()
    layout.add_node('start', '开始', 'start')
    layout.add_node('input', '输入数据', 'io')
    layout.add_node('init', '初始化参数', 'process')
    layout.add_node('calc', '计算目标函数', 'process')
    layout.add_node('check', '满足终止条件?', 'decision')
    layout.add_node('update', '更新解', 'process')
    layout.add_node('output', '输出结果', 'io')
    layout.add_node('end', '结束', 'end')

    layout.add_edge('start', 'input')
    layout.add_edge('input', 'init')
    layout.add_edge('init', 'calc')
    layout.add_edge('calc', 'check')
    layout.add_edge('check', 'output', '是')
    layout.add_edge('check', 'update', '否')
    layout.add_edge('update', 'calc')
    layout.add_edge('output', 'end')

    layout.auto_layout()
    return layout.to_svg()


def example_er_diagram():
    """ER图示例: 学生表"""
    er = ERDiagramLayout('学生表', ['学号', '姓名', '性别', '年龄', '班级', '联系电话'])
    return er.to_svg()


def example_system_module():
    """系统模块图示例: 数学建模系统"""
    layout = SystemModuleLayout('数学建模系统')

    data_module = ModuleNode('数据处理', [
        ModuleNode('数据清洗', node_type='function'),
        ModuleNode('特征工程', node_type='function'),
        ModuleNode('数据可视化', node_type='function'),
    ])
    model_module = ModuleNode('模型求解', [
        ModuleNode('优化算法', node_type='function'),
        ModuleNode('机器学习', node_type='function'),
        ModuleNode('统计分析', node_type='function'),
    ])
    result_module = ModuleNode('结果展示', [
        ModuleNode('图表生成', node_type='function'),
        ModuleNode('报告导出', node_type='function'),
    ])

    layout.add_module('数据处理', data_module.children)
    layout.add_module('模型求解', model_module.children)
    layout.add_module('结果展示', result_module.children)

    layout.auto_layout()
    return layout.to_svg()


def example_table():
    """三线表示例: 算法对比"""
    table = AcademicTable(
        title='表1 不同优化算法性能对比',
        headers=['算法', '最优值', '平均值', '标准差', '运行时间(s)'],
        data=[
            ['遗传算法', '0.0234', '0.0256', '0.0012', '12.3'],
            ['粒子群', '0.0241', '0.0268', '0.0015', '8.7'],
            ['模拟退火', '0.0238', '0.0271', '0.0018', '15.2'],
            ['蚁群算法', '0.0245', '0.0275', '0.0014', '18.9'],
        ]
    )
    return table.to_latex()


if __name__ == '__main__':
    # 测试所有功能
    print("=" * 60)
    print("流程图示例SVG已生成")
    print("=" * 60)

    svg = example_flowchart()
    save_svg(svg, 'example_flowchart.svg')

    print("\nER图示例SVG已生成")
    svg = example_er_diagram()
    save_svg(svg, 'example_er.svg')

    print("\n系统模块图示例SVG已生成")
    svg = example_system_module()
    save_svg(svg, 'example_system_module.svg')

    print("\n三线表LaTeX代码:")
    print(example_table())
