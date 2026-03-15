# Manager Layer

## 目标

经理层的职责不是替代 kernel，也不是让员工自由聊天。

它当前只做一件事：

> 根据老板目标，顺序调用若干员工，并把整条链路落成可追踪的 plan、work order、deliverable 和 result。

## 当前支持的 job 类型

- `literature-brief`
- `paper-outline`
- `project-brief`

## 当前 manager 如何工作

### 1. 创建 `CompanyJob`

记录：

- 老板目标
- 项目
- 输入材料
- 可选修订稿

### 2. 创建 `ManagerPlan`

记录：

- 选中了哪些员工
- 按什么顺序执行
- 预期交付物是什么
- 最终结果如何汇总

### 3. 派发 `WorkOrder`

当前是严格顺序执行，不做并发。

每个 `WorkOrder` 会记录：

- 指派给哪个员工
- 当前任务目标
- 输入上下文引用
- 预期产出
- 执行状态

### 4. 收集 `Deliverable`

每个员工执行后都会产出 `Deliverable`，并保留：

- employee role
- 来源 task / work order
- 标题
- 摘要
- 输出路径

### 5. 生成 `JobResult`

最终结果会说明：

- 哪些员工参与了
- 各自产出了什么
- 最终结果如何汇总出来

## 当前的顺序化编排

### `literature-brief`

默认链路：

- `literature_analyst`
- `project_manager`
- `draft_writer`
- 如果提供修订稿，再加 `review_editor`

### `paper-outline`

默认链路：

- `project_manager`
- `literature_analyst`
- `draft_writer`
- 如果提供修订稿，再加 `review_editor`

### `project-brief`

当前采用：

- `literature_analyst`
- `project_manager`
- `draft_writer`

## 为什么这一版先做顺序 orchestrator

因为当前真正需要的是：

- 可解释
- 可回放
- 可追踪
- 基于已有员工真实能力

而不是复杂协作 runtime。

所以这层更像：

> 一个最小经理层，而不是一个 swarm 系统。
