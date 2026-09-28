# /respond-to-referees

## 用途
生成回复审稿人文档，逐条交叉引用修改位置，分类为已解决/部分解决/推迟/有异议

## 用法
```bash
/respond-to-referees referees.pdf revised.pdf
```

## 回复分类
1. **已解决** - 完全按照审稿意见修改
2. **部分解决** - 部分采纳审稿意见
3. **推迟** - 计划在后续版本中修改
4. **有异议** - 不同意审稿意见并说明理由

## 参数
- `referees_file`: 审稿意见文件
- `revised_file`: 修改后的论文文件

## 示例
```bash
/respond-to-referees referees.pdf revised.pdf
/respond-to-referees review_comments.pdf paper_v2.pdf
```

## 输出
生成结构化的回复文档，包含审稿意见、回复和修改位置
