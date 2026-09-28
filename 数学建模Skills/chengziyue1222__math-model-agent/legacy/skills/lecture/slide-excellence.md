# /slide-excellence

## 用途
3代理综合幻灯片审查：视觉审计+教学审查+校对

## 用法
```bash
/slide-excellence Lecture1.tex
```

## 审查维度
1. **视觉审计** - 布局、字体、间距
2. **教学审查** - 教学效果和清晰度
3. **校对** - 语法、拼写、格式
4. **（可选）TikZ/R/内容审查** - 图表和代码质量

## 检查项目
1. **视觉质量** - 幻灯片视觉效果
2. **教学效果** - 教学内容清晰度
3. **语言质量** - 语言表达质量
4. **技术准确性** - 技术内容准确性

## 参数
- `filename`: 幻灯片文件名

## 示例
```bash
/slide-excellence Lecture01.tex
/slide-excellence presentation.tex
```

## 输出
生成综合评分报告，标注各维度得分
