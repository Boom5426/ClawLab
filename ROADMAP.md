# ClawLab Roadmap

## v0.1 已完成

- Python-first CLI 主线建立
- `init / ingest-cv / project create / task run / learn / status` 闭环跑通
- txt / md / pdf 输入支持
- 无 API key 的本地规则版可运行

## v0.2 当前阶段

- `MaterialSummary` 材料理解层
- `Asset Retrieval` 经验检索层
- `TaskPlan` 任务规划层
- draft 显式依赖 materials / assets / planning
- learn 结果写回 JSON 与 markdown 资产
- local base / LLM enhanced 双模式共存

## v0.3 下一步

- 提升规则版材料压缩质量
- 提升资产检索相关性排序
- 让 literature-outline 与 paper-outline 的 planning / drafting 差异更明显
- 强化 learn 对结构调整、背景补充、去空话的识别
- 增加更多真实研究样例和回归测试

## 长期方向

- 更强的研究材料结构化解析
- 更稳定的可选 LLM 增强
- 从任务与项目中逐步长出 SOP、模板和 workflow 种子
- 让仓库逐步成为研究人员自己的长期研究协作操作层
