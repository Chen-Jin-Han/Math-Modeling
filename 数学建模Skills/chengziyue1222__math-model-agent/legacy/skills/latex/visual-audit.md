# /visual-audit

## 用途
对幻灯片进行视觉布局审计

## 用法
```bash
/visual-audit Lecture01.qmd
```

## 审计项目
1. **溢出检查** - 内容超出幻灯片边界
2. **字体一致性** - 字体大小、类型统一
3. **间距问题** - 元素间距是否合理
4. **对齐问题** - 元素对齐是否准确
5. **颜色对比** - 文字与背景对比度
6. **图片质量** - 图片分辨率和清晰度

## 参数
- `filename`: 幻灯片文件名

## 示例
```bash
/visual-audit Lecture01.qmd
/visual-audit presentation.tex
```

## 输出
生成视觉审计报告，标注问题位置和建议修复方案
