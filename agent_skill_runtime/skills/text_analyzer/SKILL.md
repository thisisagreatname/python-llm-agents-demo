---
name: "text_analyzer"
description: "Analyzes text length, structure, and keyword signals. Invoke when the task needs lightweight text inspection, summaries of text metrics, or local NLP-style preprocessing."
---

# Text Analyzer Skill

## 功能概述

提供一个面向文本分析场景的本地技能，用于在 AI Agent 技能系统中通过 `SKILL.md + scripts` 结构组织文本处理能力，并向调度器与执行器分层披露信息。

适用场景：
- 调度器需要快速匹配“文本分析”“文本预处理”“内容统计”相关技能
- 执行器需要读取完整技能说明并运行本地脚本完成文本分析
- 需要使用技能脚本的日志、错误处理、结构化事件与结果输出

## 核心能力

- 统计字符数、单词数、行数与句子数
- 提取高频关键词候选
- 检测文本是否为空、是否超过建议长度
- 输出统一的 `EVENT` / `RESULT` 协议，便于上层系统消费

## 适用边界

- 适合本地文本检查、轻量预处理与集成场景
- 不依赖外部模型或第三方 NLP 库
- 当前关键词提取基于简单分词与停用词过滤，不替代专业语义分析

## 工具列表

### tool_text_stats.py

主要用途：
- 执行核心文本分析逻辑
- 提供文本规范化、基础统计和关键词提取能力
- 返回结构化分析结果

### run_skill.py

主要用途：
- 作为技能执行入口
- 解析输入文本
- 加载配置并调用工具脚本
- 输出结构化事件、结果和日志

## 调用方法

### 入口脚本

```bash
python run_skill.py --input-json "{\"text\": \"请对这段文本进行统计分析。\"}"
```

### 输入参数

- `text`: string，待分析文本

### 输出协议

- `EVENT <json>`：逐步披露执行信息
- `RESULT <json>`：最终结构化分析结果

## scripts 目录说明

- `run_skill.py`：技能主执行入口
- `tool_text_stats.py`：文本分析工具
- `skill_config.json`：技能配置
- `example_input.json`：输入文件

## 结果处理逻辑

- 成功时输出文本统计与关键词结果
- 输入非法或文本为空时输出错误事件并返回非 0 退出码
- 上层运行时负责抽取事件与结果，形成统一执行记录

