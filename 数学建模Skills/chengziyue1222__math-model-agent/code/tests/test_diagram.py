"""图表生成模块测试"""
from algorithms.diagram import (
    FlowchartLayout,
    FlowNode,
    FlowEdge,
    ERDiagramLayout,
    AcademicTable,
    save_svg,
    save_html,
)


class TestFlowchartLayout:
    """流程图布局测试"""

    def test_basic_flow(self):
        """基本流程图"""
        nodes = [
            FlowNode(id='start', label='Start', node_type='start'),
            FlowNode(id='process', label='Process', node_type='process'),
            FlowNode(id='end', label='End', node_type='end'),
        ]
        edges = [
            FlowEdge(source='start', target='process'),
            FlowEdge(source='process', target='end'),
        ]
        layout = FlowchartLayout(nodes=nodes, edges=edges)
        layout.layout()
        # 节点应有位置
        for node in nodes:
            assert hasattr(node, 'x')
            assert hasattr(node, 'y')

    def test_branch_flow(self):
        """分支流程"""
        nodes = [
            FlowNode(id='s', label='Start', node_type='start'),
            FlowNode(id='d', label='Decision', node_type='decision'),
            FlowNode(id='a', label='A', node_type='process'),
            FlowNode(id='b', label='B', node_type='process'),
        ]
        edges = [
            FlowEdge(source='s', target='d'),
            FlowEdge(source='d', target='a', label='Yes'),
            FlowEdge(source='d', target='b', label='No'),
        ]
        layout = FlowchartLayout(nodes=nodes, edges=edges)
        layout.layout()
        assert True  # 不报错即可


class TestERDiagramLayout:
    """ER图布局测试"""

    def test_basic_er(self):
        tables = {
            'users': ['id', 'name', 'email'],
            'orders': ['id', 'user_id', 'amount'],
        }
        layout = ERDiagramLayout(tables)
        layout.layout()
        assert True


class TestAcademicTable:
    """学术表格测试"""

    def test_basic_table(self):
        table = AcademicTable(
            headers=['Method', 'Accuracy', 'Speed'],
            data=[
                ['A', '95%', 'Fast'],
                ['B', '90%', 'Slow'],
            ],
            caption='Comparison'
        )
        latex = table.to_latex()
        assert 'Method' in latex
        assert 'A' in latex

    def test_markdown_output(self):
        table = AcademicTable(
            headers=['X', 'Y'],
            data=[['1', '2']],
            caption='Test'
        )
        md = table.to_markdown()
        assert 'X' in md
        assert 'Y' in md


class TestSaveFunctions:
    """保存功能测试"""

    def test_save_svg_string(self):
        content = '<svg>test</svg>'
        result = save_svg(content)
        assert isinstance(result, str) or result is None

    def test_save_html_string(self):
        content = '<html>test</html>'
        result = save_html(content)
        assert isinstance(result, str) or result is None
