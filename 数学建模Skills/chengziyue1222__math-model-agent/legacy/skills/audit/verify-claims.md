# /verify-claims

## 用途
链式验证：提取事实声明→生成验证问题→独立验证者→核对报告

## 用法
```bash
/verify-claims draft.pdf
```

## 验证流程
1. **提取声明** - 提取事实声明
2. **生成问题** - 生成验证问题
3. **独立验证** - 独立验证者验证
4. **核对报告** - 生成核对报告

## 验证结果
- **PASS** - 声明正确
- **PARTIAL** - 部分正确
- **FAIL** - 声明错误

## 参数
- `filename`: 文件名

## 示例
```bash
/verify-claims paper_draft.pdf
/verify-claims research_report.pdf
```

## 输出
生成验证报告，标注每个声明的验证结果
