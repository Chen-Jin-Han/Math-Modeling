# /stata-replication

## 用途
端到端Stata复现管道：生成.do文件通过stata-mcp执行抓取输出

## 用法
```bash
/stata-replication paper.pdf
```

## 复现流程
1. **解析论文** - 提取分析方法
2. **生成代码** - 生成Stata .do文件
3. **执行分析** - 通过stata-mcp执行
4. **抓取输出** - 抓取分析结果
5. **验证结果** - 与论文结果对比

## 输出内容
1. **.do文件** - Stata代码文件
2. **日志文件** - 执行日志
3. **输出表格** - 分析结果表格
4. **验证报告** - 复现验证报告

## 参数
- `paper`: 论文文件名

## 示例
```bash
/stata-replication empirical_paper.pdf
/stata-replication analysis.pdf
```

## 输出
生成完整的Stata复现文件和验证报告
