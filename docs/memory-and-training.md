# Memory And Training

## 目标

ClawLab 的虚拟研究公司不应该只是一次次调用员工。

它还需要逐步形成：

- 公司级手册
- 员工级岗位手册
- 项目级记忆
- 任务级痕迹

这一层的重点不是复杂训练，而是：

> 可解释、可落盘、可检索的团队知识层。

## 四层记忆

### 1. Company memory

适合放：

- 全局写作规范
- 通用结构模板
- common mistakes
- SOP seeds

典型例子：

- “先写项目特定 claim，再给背景”
- “交付前检查 gap statement 和 evidence placement”

### 2. Employee memory

适合放：

- 某个员工角色的岗位打法
- 常见错误
- 推荐模板

典型例子：

- `draft_writer` 常犯的空泛开场
- `review_editor` 在修订时重点检查什么

### 3. Project memory

适合放：

- 某项目的术语
- 某项目当前 blocker
- 某项目的背景补充

典型例子：

- 某个项目里 “state transition” 指的具体是什么

### 4. Task memory

适合放：

- 一次任务的临时模板
- 某次交付中的特殊结构

它最短期，不应主导长期手册。

## 当前写回逻辑

当前 `learn` 会根据 revision signal 和资产类型，把内容写到不同层：

- `writing_rule` -> `company`
- `structure_template` -> `employee`
- `project_note` -> `project`
- `common_mistake` -> `employee`
- `sop_seed` -> `company`

## 当前检索逻辑

当前 retrieval 会统一从 `ReusableAsset` 中检索，但现在这些资产已经通过 `scope` 区分为：

- `company`
- `employee`
- `project`
- `task`

因此执行前的上下文，实际上已经开始包含：

- 公司手册
- 员工岗位手册
- 项目记忆
- 任务级经验

## 为什么现在不做向量库或训练模型

因为这一阶段真正需要的是：

- 知识层级清楚
- 写回逻辑清楚
- 检索逻辑可解释
- 文件可直接打开阅读

先把这四点做实，比过早上复杂 memory stack 更重要。
