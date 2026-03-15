# Architecture Diagram

```text
Current Kernel
  - ResearcherProfile
  - ProjectCard
  - TaskCard
  - ReusableAsset
  - MaterialSummary
  - TaskPlan
  - CLI workflow: init -> ingest-cv -> project create -> task run -> learn -> status

        |
        v

Company Layer
  - Founder / Boss context
  - Active mission
  - Work orders
  - Handbook / SOP memory
  - Manager planning metaphor

        |
        v

Future Multi-Agent Company
  - COO / PM agent
  - Specialist worker agents
  - Shared company memory
  - Coordinated execution on the same kernel state
```
