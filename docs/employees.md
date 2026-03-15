# Employees

## 为什么先做员工层，而不是直接做经理层

ClawLab 当前已经有一条稳定的工作流内核：

`materials -> material summaries -> asset retrieval -> task plan -> draft -> learn -> asset writeback`

在这个阶段，最合理的做法不是直接引入复杂协作，而是先把这条链上的真实能力包装成岗位。

这样做的意义是：

- 未来经理层调度的是“真实能力”，不是角色扮演
- 员工层复用当前 kernel，而不是绕开 kernel 另起炉灶
- 每个员工都能产出明确的 `Deliverable`

## 第一批 4 个员工

### 1. `literature_analyst`

负责：

- 读取 txt / md / pdf 材料
- 生成 `MaterialSummary`
- 提供结构化 research brief

底层调用：

- `material_service`

为什么它是第一批合理角色：

- 材料理解是所有后续任务的入口
- 当前内核已经具备真实的材料压缩能力

### 2. `project_manager`

负责：

- 读取项目上下文
- 检索相关资产
- 生成 `TaskPlan`

底层调用：

- `asset_service`
- `planning_service`

为什么它是第一批合理角色：

- 当前内核已经有 task planning 层
- 这是未来经理层最直接的前置岗位原型

### 3. `draft_writer`

负责：

- 基于 profile / project / materials / assets / task plan 生成草稿
- 创建真实 `TaskCard`

底层调用：

- `draft_service`
- `planning_service`
- `asset_service`

为什么它是第一批合理角色：

- 这是当前内核里最直接的“生产岗位”
- 它已经有明确输出物：markdown draft

### 4. `review_editor`

负责：

- 读取生成稿和修订稿
- 提炼写作规则、结构模板、项目笔记
- 写回可检索资产层

底层调用：

- `learning_service`

为什么它是第一批合理角色：

- 没有 review / learn，系统就不会积累经验
- 它是 kernel 自我增强的关键岗位

## 员工层与内核的关系

员工层不是新内核。

它只是把已有能力包装成 4 类稳定岗位：

- `literature_analyst` -> 材料理解岗位
- `project_manager` -> 规划岗位
- `draft_writer` -> 产出岗位
- `review_editor` -> 学习岗位

当前员工执行接口是：

- `run_employee_task(employee_role, ...)`

每个员工：

- 接收结构化输入
- 调用已有 kernel service
- 产出 `Deliverable`

## 为什么现在不做更多角色

当前不适合继续扩很多员工角色，因为：

1. 现有内核真正稳定的能力只有这 4 类
2. 太早拆更多岗位，会让角色比能力多
3. 当前还没有 manager / orchestrator，先做小而真比做多而空更重要

所以第一批员工的目标不是“看起来像公司”，而是：

> 每个员工背后都已经有真实岗位能力可调用。
