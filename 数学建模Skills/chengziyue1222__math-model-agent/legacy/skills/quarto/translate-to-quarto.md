# /translate-to-quarto

## 用途
LaTeX to Quarto RevealJS翻译（多阶段：环境审计→逐页翻译→引用转换→图表集成→部署）

## 用法
```bash
/translate-to-quarto Lecture1_Topic.tex
```

## 翻译阶段
1. **环境审计** - 分析LaTeX文件结构
2. **逐页翻译** - 逐页转换为Quarto格式
3. **引用转换** - 转换引用和参考文献
4. **图表集成** - 集成TikZ图表
5. **部署配置** - 配置RevealJS输出

## 参数
- `filename`: LaTeX文件名

## 示例
```bash
/translate-to-quarto Lecture01_Intro.tex
/translate-to-quarto Chapter02_Methods.tex
```

## 输出
生成.qmd文件，可直接用Quarto渲染为RevealJS幻灯片
