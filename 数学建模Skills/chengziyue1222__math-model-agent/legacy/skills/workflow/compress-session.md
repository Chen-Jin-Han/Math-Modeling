# /compress-session

## 用途
自动压缩前将当前对话提炼为结构化笔记

## 用法
```bash
/compress-session topic-slug
```

## 压缩内容
1. **决策** - 已做出的决策
2. **开放问题** - 待解决的问题
3. **文件指针** - 相关文件路径
4. **丢弃噪音** - 过滤无关信息

## 参数
- `slug`: 主题标识符

## 示例
```bash
/compress-session 项目讨论
/compress-session 技术方案
```

## 输出
生成结构化的会话笔记
