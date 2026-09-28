# /review-paper

## 用途
7个并行子代理分别审查摘要/引言/方法/结果/稳健性/写作/引用，合成优先修改清单

## 用法
```bash
/review-paper paper.pdf adversarial
/review-paper paper.pdf -peer AER
```

## 审查维度
1. **摘要** - 摘要质量和完整性
2. **引言** - 引言逻辑和动机
3. **方法** - 方法描述和合理性
4. **结果** - 结果呈现和解释
5. **稳健性** - 稳健性检验充分性
6. **写作** - 写作质量和清晰度
7. **引用** - 引用完整性和规范性

## 参数
- `filename`: 论文文件名
- `mode`: 审查模式（adversarial/-peer AER等）

## 示例
```bash
/review-paper paper.pdf adversarial
/review-paper manuscript.pdf -peer AER
```

## 输出
生成优先修改清单，按重要性排序
