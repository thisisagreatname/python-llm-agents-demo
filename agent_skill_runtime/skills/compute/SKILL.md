---
name: "compute"
description: "Executes numeric computation with a local toolchain. Invoke when the task is arithmetic evaluation, operator selection, or local skill-runtime execution."
---

# Compute Skill

## 功能概述

提供一个面向数值计算场景的本地技能，用于在 AI Agent 技能系统中完成技能发现、按需披露、脚本执行、事件记录、结果回传与错误处理。

适用场景：
- 调度器需要从多个技能中快速匹配“可做数值计算”的能力
- 执行器需要加载完整技能说明并调用本地脚本完成任务
- 需要使用标准 Skill 目录、脚本编排、日志与结果协议

## 核心能力

- 根据输入参数执行基础算术计算
- 通过独立脚本完成工具调用与结果处理
- 输出结构化事件，便于上层系统逐步观察执行状态
- 在脚本层提供日志、异常捕获、退出码和结果协议

## 适用边界

- 适合本地计算任务、技能系统集成与运行时校验
- 默认使用本地脚本，不依赖在线模型
- 当前默认运算为减法，可通过配置扩展为加减乘除等更多模式

## 工具列表

### tool_compute.py

主要用途：
- 负责实际数值计算
- 提供统一的 `compute` 函数
- 根据配置文件决定运算类型

### run_skill.py

主要用途：
- 作为技能执行入口
- 解析输入参数
- 调用工具脚本
- 输出 EVENT / RESULT 协议
- 记录日志并处理异常

## 调用方法

### 入口脚本

```bash
python run_skill.py --input-json "{\"a\": 1, \"b\": 2}"
```

### 输入参数

- `a`: number，第一个数字
- `b`: number，第二个数字

### 输出协议

- `EVENT <json>`：逐步披露执行信息
- `RESULT <json>`：最终结果

## scripts 目录说明

- `run_skill.py`：技能主执行脚本
- `tool_compute.py`：数值计算工具脚本
- `skill_config.json`：技能配置
- `example_input.json`：输入文件

## 结果处理逻辑

- 脚本执行成功时输出 `RESULT` JSON
- 参数异常时返回非 0 退出码并输出错误日志
- 上层运行时从标准输出中抽取 `EVENT` 和 `RESULT`，形成执行记录

