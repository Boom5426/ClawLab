# Collaboration Protocol

ClawLab 当前的协作层不是复杂的多 Agent 自由通信，而是一套最小、顺序化、可追踪的团队协议。

它的目标很明确：

- 让员工之间的交接有清晰契约
- 让复核结果可以被记录和解释
- 让经理在发现问题时有一次受控的补救动作

## 当前员工协作链

第一版默认链路围绕这 4 个岗位展开：

- `literature_analyst`
- `project_manager`
- `draft_writer`
- `review_editor`

典型执行顺序例如：

1. `literature_analyst` 先把原始材料压缩成 `MaterialSummary`
2. `project_manager` 根据项目上下文、资产和材料摘要生成 `TaskPlan`
3. `draft_writer` 基于摘要、计划和资产生成 draft
4. `review_editor` 对 draft 做最小复核，给出 `accept / revise / escalate`

## Handoff Contract 是什么

`Handoff` 是一份最小交接单。它不只是说明“上一步做完了”，还要说明“下一个岗位应该拿什么继续做”。

当前每条 handoff 至少会包含：

- `contract_type`
- `handoff_summary`
- `payload`
- `expected_use`
- `status`

其中 `status` 会从 `created` 变成 `consumed`，表示下一位员工已经接手了这份交接单。

当前明确支持的交接包括：

### literature_analyst -> project_manager

交接内容：

- material summary
- key topics
- relevant snippets
- relevance note

下一步用途：

- 用这些信息做任务聚焦和结构规划

### project_manager -> draft_writer

交接内容：

- task focus
- recommended structure
- selected assets
- project constraints

下一步用途：

- 用这些信息组织输出结构，避免 draft 空泛发散

### draft_writer -> review_editor

交接内容：

- produced draft
- outline summary
- open weaknesses / uncertain sections

下一步用途：

- 判断当前 draft 是否可接受，还是需要修订或升级处理

## Review Protocol 是什么

第一版 review 只做最小协议，不做复杂 loop。

`review_editor` 当前只会给出 3 种决定：

- `accept`
- `revise`
- `escalate`

含义如下：

- `accept`：当前交付物可以进入最终汇总
- `revise`：当前交付物还可以由原岗位再改一次
- `escalate`：问题已经超出简单修订范围，需要经理介入补救

每次 review 都会落成 `ReviewDecision`，并写入 job 目录，便于老板回看。

每个 review 决定还会携带一份最小 rubric：

- `risk_level`
- `issue_type`
- `review_checks.material_grounding`
- `review_checks.structure_clarity`
- `review_checks.gap_explicitness`

这样老板看到的就不只是“通过/返工/升级”，而是“为什么这样判定”。

## Manager 如何 retry / reassign

经理层当前支持两种最小补救动作：

### retry

如果 review 结果是 `revise`：

- 经理会把任务重新派回原 `draft_writer`
- 最多只允许一次 retry
- retry 后再次 review
- 如果仍然不通过，不再无限循环，而是直接进入风险输出

### reassign

如果 review 结果是 `escalate`：

- 经理会记录一条 `ReassignmentAction`
- 如果 `issue_type = material_insufficiency`，优先回派给 `literature_analyst`
- 如果 `issue_type = structure_problem`，优先回派给 `project_manager`
- 如果 `issue_type = project_context_gap`，也优先回派给 `project_manager`
- 第一版最多只允许一次 reassign

每条 reassignment 还会记录：

- `intervention_policy`
- `resolution_note`

这样做的目的不是把系统做成流程引擎，而是让团队第一次具备“发现问题 -> 补救一次 -> 明确收口”的能力。

## 为什么第一版只做最小协作

当前阶段不做这些事情：

- 员工自由聊天
- 多轮并发协作
- 复杂消息总线
- 无限 review loop
- 树状 workflow engine

原因很简单：

- 当前更需要稳定、可解释、可调试的协作痕迹
- 不是更花哨的 agent 互动

只要 handoff、review、retry、reassign 能稳定落盘并被老板看见，ClawLab 的团队层就已经从“脚本串联”迈进到了“最小真实协作”。
