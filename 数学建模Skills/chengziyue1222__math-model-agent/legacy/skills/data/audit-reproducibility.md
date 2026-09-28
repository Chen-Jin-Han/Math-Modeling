# /audit-reproducibility

## 用途
交叉验证手稿中每一项数值声明vs实际R/Stata/Python输出

## 用法
```bash
/audit-reproducibility paper.pdf scripts/R/ _outputs/
```

## 验证内容
1. **数值声明** - 论文中的数值声明
2. **实际输出** - 代码的实际输出
3. **交叉验证** - 两者是否一致

## 检查项目
1. **表格数据** - 表格数值是否一致
2. **图表数据** - 图表数据是否一致
3. **统计结果** - 统计检验结果是否一致
4. **回归系数** - 回归系数是否一致

## 参数
- `paper`: 论文文件
- `scripts`: 代码目录
- `outputs`: 输出目录

## 示例
```bash
/audit-reproducibility paper.pdf scripts/R/ _outputs/
/audit-reproducibility manuscript.pdf code/ results/
```

## 输出
生成PASS/FAIL报告，标注所有不一致之处
