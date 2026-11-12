# jd-insight

从 V2EX 招聘版抓取岗位帖，用 LLM 抽取结构化字段，存入 PostgreSQL 并做聚合分析。

## 为什么做

招聘帖里写满了市场对技术栈的要求，但全是自然语言。想回答
「现在 AI 应用开发岗最常要求什么技术」，得先把文本变成能查的数据。

这个项目的重点不是"分析招聘市场"，而是**非结构化文本 → 结构化数据的完整管线**——
用招聘 JD 作为示例场景。

## 流程

`update.py` 把前两步串成一条命令，由 Windows 计划任务每天两次自动执行。

## 技术栈

Python 3.12 / requests / psycopg2 / PostgreSQL 16（JSONB）
DeepSeek API（结构化抽取）/ Docker / Windows 任务计划程序

## 设计要点

### 1. 幂等采集

`source_id` 建 UNIQUE 约束，插入用 `ON CONFLICT (source_id) DO NOTHING`。
重复运行不会重复入库。

### 2. 增量抽取

用 `extracted_at` 做处理标记：`NULL` 表示未抽取。
脚本只取 `WHERE extracted_at IS NULL` 的行，**失败时不写标记**，下次运行自动重试。

### 3. 两层防线：提示词 + 代码校验

LLM 输出不可直接信任，关键约束必须落在代码里。

- **提示词层**：约束模型尽量抽对
- **代码层**：`validate()` 检查返回结构与字段类型；`normalize_tech_stack()`
  统一大小写、去重、过滤过宽泛的词

实测中模型仍会违反提示词（返回数组代替字符串、混入公司名），
这两类问题分别由校验和过滤拦下。

### 4. 提示词迭代了 4 轮

| 轮次 | 做法 | 结果 |
|---|---|---|
| 1 | 只说"技术栈名称数组" | 抽出 `Meta`、`Google Ads`、`缓存` |
| 2 | 加反例：不要公司名/平台名/概念词 | 好一些，但 `AI`、`LLM` 仍在 |
| 3 | 改成白名单：只收语言/框架/库/数据库 | **矫枉过正**，`RAG`、`Agent` 被排除 |
| 4 | 换成判断标准："能不能写进简历的技能栏" | 正确 |

结论：**给标准比给清单有效**。清单永远列不全，而标准能让模型自己判断。

### 5. 原子写入

数据字段与 `extracted_at` 在同一条 `UPDATE` 中写入。
避免"写了数据但没打标记"导致下次重复抽取。

## 运行

```bash
# 1. 起数据库
docker run -d --name pg-jd \
  -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=jd \
  -p 5432:5432 postgres:16

# 2. 建表（见 schema.sql）

# 3. 装依赖
pip install requests psycopg2-binary

# 4. 跑
python update.py
```

需要自备 DeepSeek API key。

## 已知限制

- **技术同义词未归并**：`go`/`golang`、`agent`/`ai agent` 分别统计
- **城市未拆分**：多城市岗位（如"广州、天津"）作为单个值保存
- **样本量小**：当前仅 20 条，统计结论不具备代表性
- **无薪资分析**：约半数 JD 未标注薪资，样本不足以做分布
- **key 读取路径待改造**：目前写死本地绝对路径，应改为环境变量优先

## 数据来源

V2EX jobs 节点公开 API，仅用于技术学习与求职准备。