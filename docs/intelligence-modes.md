# Intelligence Modes

ClawLab 当前坚持两条原则：

- 默认范式应当面向 API 工作
- 智能增强必须建立在现有公司协议之上

因此，当前系统分成两种模式：

## 1. Local Base Mode

这是兜底模式。

特点：

- 不需要 API key
- materials / planning / drafts / learning 全部走规则版
- 整个公司主流程仍然完整可运行

保留规则版的原因很现实：

- 它保证仓库在没有外部依赖时仍然可用
- 它让 handbook / playbook / protocol 的结构先稳定下来
- 它让 LLM 失败时有可回退的底座

## 2. Hybrid Intelligent Mode

这是推荐主模式。

特点：

- 需要在配置中开启 `mode=hybrid`
- 需要 `provider=openai`
- 需要设置 `OPENAI_API_KEY`
- 任一步骤失败都会 fallback 回规则版

当前只增强关键岗位：

- `literature_analyst`
- `project_manager`
- `draft_writer`
- `review_editor`

不会增强这些层：

- workspace / storage
- handoff / review / retry / reassign 的协议执行
- 经理层的状态落盘和 trace

原因是这些层更应该保持稳定、可解释、可调试。

## 每一层增强分别做什么

### Materials

`literature_analyst` 的增强会在生成 `MaterialSummary` 时显式参考：

- company handbook
- literature_analyst playbook
- relevant assets
- recent review / handoff / reassignment context

目标是让材料压缩更像研究简报，而不是简单摘要。

### Planning

`project_manager` 和 manager planning 的增强会显式参考：

- company handbook
- project_manager playbook
- relevant assets
- recent `issue_type`
- recent `intervention_policy`
- blockers / constraints

目标是让计划更像“按公司规矩制定工作策略”，而不是只按 task type 套模板。

### Drafts

`draft_writer` 的增强会显式参考：

- material summaries
- selected assets
- task plan / manager plan
- company handbook
- draft_writer playbook
- recent review issue history

目标是让 draft 更贴近项目、更少空话、更能吸收历史反馈。

### Learning

`review_editor` 的增强会显式参考：

- company handbook
- review_editor playbook
- 历史 review decisions
- `issue_type` taxonomy
- manager intervention history

目标是让 learn 产物更稳地映射到：

- company memory
- employee memory
- project memory
- task trace

## handbook / playbook / issue_type / intervention_policy 如何发挥作用

这几层不是摆设，它们会作为 prompt 上下文显式进入增强链路：

- handbook：提供公司级规则和 SOP
- playbook：提供岗位级默认做法
- issue_type：提供问题分类语言
- intervention_policy：提供经理补救策略语言

这样，增强后的岗位不是“自由发挥”，而是“在公司规则之内更聪明地工作”。

## 当前仍不支持什么

当前仍然不做：

- 多 provider 扩展
- embedding 检索
- 联网检索
- OCR
- 复杂 agent runtime
- 员工自由聊天
- 自动训练模型

ClawLab 当前的重点仍然是：

在 API-first 的前提下，把关键岗位做成“可增强、可解释、可回退”的智能协作系统。
