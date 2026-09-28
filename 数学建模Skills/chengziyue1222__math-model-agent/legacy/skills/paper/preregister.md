# /preregister

## 用途
起草预注册文档，支持OSF、AsPredicted、AEARCT三种格式

## 用法
```bash
/preregister --style osf --input spec.md
```

## 支持格式
1. **OSF** - Open Science Framework
2. **AsPredicted** - AsPredicted.org格式
3. **AEARCT** - AEA RCT Registry格式

## 预注册内容
1. **研究问题** - 明确的研究问题
2. **假设** - 可检验的假设
3. **方法** - 详细的研究方法
4. **分析计划** - 预先指定的分析计划
5. **样本量** - 样本量确定依据

## 参数
- `--style`: 预注册格式
- `--input`: 研究规范文件

## 示例
```bash
/preregister --style osf --input spec.md
/preregister --style AsPredicted --input research_plan.md
/preregister --style AEARCT --input protocol.md
```

## 输出
生成符合指定格式的预注册文档
