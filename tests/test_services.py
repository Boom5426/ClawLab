import unittest
from pathlib import Path
from unittest.mock import patch

from clawlab.core.models import LlmSettings, MaterialSummary, ProjectCard, ReusableAsset, TaskCard, TaskPlan
from clawlab.services.asset_service import group_assets_by_scope, retrieve_assets_for_task, select_top_assets
from clawlab.services.draft_service import generate_draft
from clawlab.services.employee_service import get_employee_spec, list_employee_specs, run_employee_task
from clawlab.services.ingest_service import read_cv_text
from clawlab.services.learning_service import derive_assets_from_revision
from clawlab.services.llm_service import get_llm_runtime_status
from clawlab.services.manager_service import create_manager_plan, dispatch_work_orders, synthesize_job_result
from clawlab.services.material_service import condense_material, detect_material_type, extract_text, read_material
from clawlab.services.planning_service import create_task_plan
from clawlab.services.profile_service import parse_cv_to_profile
from clawlab.services.project_service import create_project_from_answers, create_project_from_intake
from clawlab.services.workspace_service import save_asset, save_project, save_project_asset


class ProfileServiceTests(unittest.TestCase):
    def test_parse_cv_to_profile_extracts_basic_fields(self) -> None:
        cv_text = """Li Wei
PhD Candidate in Computational Biology
Methods: differential expression, literature synthesis
Tools: Python, R, Git
"""
        profile = parse_cv_to_profile(cv_text)

        self.assertEqual(profile.name, "Li Wei")
        self.assertEqual(profile.role, "PhD Candidate")
        self.assertEqual(profile.discipline, "Computational Biology")
        self.assertIn("Python", profile.tools)

    def test_ingest_service_reads_text_files(self) -> None:
        text = read_cv_text(Path("examples/cv.txt"))
        self.assertIn("Li Wei", text)

    def test_detect_material_type_supports_txt_md_pdf(self) -> None:
        self.assertEqual(detect_material_type(Path("notes.txt")), "txt")
        self.assertEqual(detect_material_type(Path("notes.md")), "md")
        self.assertEqual(detect_material_type(Path("notes.pdf")), "pdf")

    def test_read_material_supports_pdf(self) -> None:
        material = read_material(Path("examples/material_sample.pdf"))
        self.assertEqual(material.material_type, "pdf")
        self.assertTrue(material.extracted_text.strip())

    def test_extract_text_supports_md(self) -> None:
        text = extract_text(Path("examples/project_brief.md"))
        self.assertIn("Project Brief", text)

    def test_read_cv_text_supports_pdf(self) -> None:
        text = read_cv_text(Path("examples/cv_sample.pdf"))
        self.assertTrue(text.strip())

    def test_condense_material_returns_summary_for_pdf(self) -> None:
        project = ProjectCard(
            id="project_demo",
            researcher_profile_id="profile_demo",
            title="Glioma resistance project",
            research_question="How do resistant glioma states emerge?",
            current_goal="Prepare a literature-backed outline",
            current_stage="Evidence consolidation",
            blockers=["Need tighter storyline"],
            materials=["material sample pdf"],
            next_step="Outline the evidence buckets",
        )
        summary = condense_material(Path("examples/material_sample.pdf"), project=project)
        self.assertEqual(summary.source_type, "pdf")
        self.assertTrue(summary.short_summary)
        self.assertTrue(summary.useful_snippets)
        self.assertTrue(summary.raw_text_excerpt)
        self.assertTrue(summary.relevance_to_project)
        self.assertIn("project", summary.short_summary.lower())

    def test_condensed_summary_prefers_informative_excerpt(self) -> None:
        project = ProjectCard(
            id="project_demo",
            researcher_profile_id="profile_demo",
            title="Glioma resistance project",
            research_question="How do resistant glioma states emerge?",
            current_goal="Prepare a literature-backed outline",
            current_stage="Evidence consolidation",
            blockers=["Need tighter storyline"],
            materials=["notes"],
            next_step="Outline the evidence buckets",
        )
        summary = condense_material(Path("examples/task_input.txt"), project=project)
        self.assertTrue(summary.raw_text_excerpt.strip())
        self.assertTrue(any(topic in summary.short_summary.lower() for topic in summary.key_topics[:2]))

    def test_local_mode_does_not_require_api_key(self) -> None:
        enabled, reason = get_llm_runtime_status(LlmSettings(), "materials")
        self.assertFalse(enabled)
        self.assertEqual(reason, "local mode enabled")

    def test_hybrid_mode_without_key_falls_back_cleanly(self) -> None:
        settings = LlmSettings(mode="hybrid", provider="openai", use_llm_for_materials=True)
        with patch.dict("os.environ", {}, clear=False):
            enabled, reason = get_llm_runtime_status(settings, "materials")
            self.assertFalse(enabled)
            self.assertIn("OPENAI_API_KEY", reason)
            summary = condense_material(Path("examples/material_sample.pdf"), llm_settings=settings)
            self.assertTrue(summary.short_summary)

    @patch("clawlab.services.material_service.is_llm_enabled", return_value=True)
    @patch("clawlab.services.material_service.call_llm")
    def test_materials_llm_branch_can_return_structured_summary(self, mock_call_llm, _mock_enabled) -> None:
        mock_call_llm.return_value = """{
          "title": "LLM Material Title",
          "short_summary": "LLM summary.",
          "key_topics": ["glioma", "resistance"],
          "methods_or_entities": ["trajectory", "single-cell"],
          "useful_snippets": ["snippet 1", "snippet 2"],
          "relevance_to_project": "Highly relevant.",
          "raw_text_excerpt": "Excerpt"
        }"""
        settings = LlmSettings(mode="hybrid", provider="openai", use_llm_for_materials=True)
        summary = condense_material(Path("examples/material_sample.pdf"), llm_settings=settings)
        self.assertEqual(summary.title, "LLM Material Title")
        self.assertEqual(summary.key_topics, ["glioma", "resistance"])

    @patch("clawlab.services.material_service.call_llm", side_effect=AssertionError("LLM should not be called"))
    def test_materials_config_off_stays_rule_based(self, _mock_call_llm) -> None:
        settings = LlmSettings(mode="local", provider="none", use_llm_for_materials=False)
        summary = condense_material(Path("examples/material_sample.pdf"), llm_settings=settings)
        self.assertTrue(summary.short_summary)


class ProjectAndDraftTests(unittest.TestCase):
    def _build_profile_project_material(self) -> tuple:
        profile = parse_cv_to_profile(
            """Li Wei
PhD Candidate in Computational Biology
Methods: differential expression, literature synthesis
Tools: Python, R, Git
"""
        )
        project = create_project_from_answers(
            profile,
            title="Glioma resistance project",
            desired_outcome="Prepare a tighter outline",
            blocker="Scattered notes",
            materials="Paper notes; memo",
        )
        material_summary = MaterialSummary(
            id="material_test",
            source_path="examples/task_input.txt",
            source_type="txt",
            title="Task input material",
            short_summary="This material summarizes resistance state transitions and points to the central evidence gap.",
            key_topics=["resistance", "state", "transition"],
            methods_or_entities=["single-cell", "trajectory"],
            useful_snippets=[
                "Treatment pressure may induce reversible state switching.",
                "Trajectory evidence is more useful than static cluster labels for this project.",
            ],
            relevance_to_project="Strongly relevant to the current project goal.",
            raw_text_excerpt="Need a literature outline for treatment-resistant glioma state transitions.",
        )
        return profile, project, material_summary

    def test_create_project_from_intake_uses_brief_and_goal(self) -> None:
        profile = parse_cv_to_profile(
            """Li Wei
PhD Candidate in Computational Biology
Methods: differential expression, literature synthesis
Tools: Python, R, Git
"""
        )
        project = create_project_from_intake(
            profile,
            project_brief=(
                "Single-cell trajectories of resistant glioma states\n"
                "We want to understand how treatment pressure induces reversible state switching.\n"
                "Current challenge: the storyline is scattered across notes."
            ),
            current_goal="Draft a paper-outline that tightens the storyline and surfaces the main claim.",
            source_label="examples/project_brief.md",
        )

        self.assertIn("glioma", project.title.lower())
        self.assertIn("understand", project.research_question.lower())
        self.assertTrue(project.materials)
        self.assertTrue(project.blockers)
        self.assertEqual(project.current_goal, "Draft a paper-outline that tightens the storyline and surfaces the main claim.")

    def test_create_project_and_generate_task_card(self) -> None:
        profile, project, material_summary = self._build_profile_project_material()
        output_dir = Path("workspace/projects/test_project/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)
        retrieved_assets = [
            ReusableAsset(
                id="asset_rule_demo",
                scope="global",
                asset_type="writing_rule",
                title="Claim-first writing",
                content="Open each section with a project-specific claim.",
                confidence=0.8,
                source_task_id="task_prev",
                project_card_id=project.id,
                task_type="literature-outline",
            )
        ]
        task_plan = TaskPlan(
            task_type="literature-outline",
            task_goal="Prepare a literature outline",
            output_strategy="background_review",
            key_points_to_cover=["Context", "Gap", "Evidence"],
            recommended_structure=["Context", "Grouped evidence", "Gap"],
            project_considerations=["Avoid generic background."],
            selected_assets=["writing_rule: Claim-first writing"],
        )

        task, draft_path = generate_draft(
            profile,
            project,
            task_type="literature-outline",
            material_summaries=[material_summary],
            retrieved_assets=retrieved_assets,
            task_plan=task_plan,
            output_dir=output_dir,
            workspace_root=Path("workspace"),
        )

        self.assertEqual(project.title, "Glioma resistance project")
        self.assertEqual(task.input_material_types, ["txt"])
        self.assertEqual(task.retrieved_asset_ids, ["asset_rule_demo"])
        self.assertTrue(draft_path.exists())
        draft_text = draft_path.read_text(encoding="utf-8")
        self.assertIn("Material summary", draft_text)
        self.assertIn("Trajectory evidence is more useful than static cluster labels", draft_text)
        self.assertIn("Claim-first writing", draft_text)

    @patch("clawlab.services.draft_service.is_llm_enabled", return_value=True)
    @patch("clawlab.services.draft_service.call_llm", return_value="# LLM Draft\n\n## Section\n- stronger draft")
    def test_draft_llm_branch_can_return_markdown(self, _mock_call_llm, _mock_enabled) -> None:
        profile, project, material_summary = self._build_profile_project_material()
        output_dir = Path("workspace/projects/test_project/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)
        _, draft_path = generate_draft(
            profile,
            project,
            task_type="paper-outline",
            material_summaries=[material_summary],
            retrieved_assets=[],
            task_plan=TaskPlan(
                task_type="paper-outline",
                task_goal="Prepare a paper outline",
                output_strategy="paper_storyline",
                key_points_to_cover=["Problem", "Gap"],
                recommended_structure=["Introduction", "Gap", "Evidence"],
                project_considerations=["Keep the story tight."],
                selected_assets=[],
            ),
            output_dir=output_dir,
            workspace_root=Path("workspace"),
            llm_settings=LlmSettings(mode="hybrid", provider="openai", use_llm_for_drafts=True),
        )
        self.assertIn("LLM Draft", draft_path.read_text(encoding="utf-8"))

    def test_asset_retrieval_and_grouping_returns_relevant_subset(self) -> None:
        profile, project, material_summary = self._build_profile_project_material()
        assets = [
            ReusableAsset(
                id="asset_global_rule",
                scope="global",
                asset_type="writing_rule",
                title="Glioma claim-first",
                content="State the glioma resistance claim before evidence.",
                confidence=0.8,
                source_task_id="task_prev",
                project_card_id=project.id,
                task_type="literature-outline",
            ),
            ReusableAsset(
                id="asset_project_note",
                scope="project",
                asset_type="project_note",
                title="Resistance storyline note",
                content="Emphasize reversible state switching.",
                confidence=0.82,
                source_task_id="task_prev",
                project_card_id=project.id,
                task_type="literature-outline",
            ),
            ReusableAsset(
                id="asset_unrelated",
                scope="global",
                asset_type="structure_template",
                title="Traffic forecasting template",
                content="Use temporal graph forecasting sections.",
                confidence=0.6,
                source_task_id="task_prev2",
                project_card_id="project_other",
                task_type="paper-outline",
            ),
        ]
        grouped = group_assets_by_scope(assets)
        self.assertEqual(len(grouped["global"]), 2)
        retrieved = retrieve_assets_for_task(
            task_type="literature-outline",
            project=project,
            profile=profile,
            material_summaries=[material_summary],
            assets=assets,
        )
        retrieved_ids = [asset.id for asset in retrieved]
        self.assertIn("asset_global_rule", retrieved_ids)
        self.assertIn("asset_project_note", retrieved_ids)
        self.assertNotEqual(retrieved_ids[0], "asset_unrelated")

    def test_select_top_assets_preserves_scope_and_type_diversity(self) -> None:
        assets = [
            ReusableAsset(
                id="a1",
                scope="project",
                asset_type="project_note",
                title="Project note",
                content="Current blocker is storyline.",
                confidence=0.9,
                source_task_id="task1",
                project_card_id="project_x",
                task_type="literature-outline",
            ),
            ReusableAsset(
                id="a2",
                scope="global",
                asset_type="writing_rule",
                title="Claim first",
                content="Lead with the claim.",
                confidence=0.8,
                source_task_id="task2",
            ),
            ReusableAsset(
                id="a3",
                scope="task",
                asset_type="structure_template",
                title="Outline template",
                content="Context, evidence, gap.",
                confidence=0.75,
                source_task_id="task3",
            ),
        ]
        selected = select_top_assets(assets, limit=3)
        self.assertEqual(selected[0].scope, "project")
        self.assertIn("writing_rule", {asset.asset_type for asset in selected})
        self.assertIn("structure_template", {asset.asset_type for asset in selected})

    def test_task_planning_differs_by_task_type(self) -> None:
        profile, project, material_summary = self._build_profile_project_material()
        literature_plan = create_task_plan(
            task_type="literature-outline",
            profile=profile,
            project=project,
            material_summaries=[material_summary],
            retrieved_assets=[],
        )
        paper_plan = create_task_plan(
            task_type="paper-outline",
            profile=profile,
            project=project,
            material_summaries=[material_summary],
            retrieved_assets=[],
        )
        self.assertEqual(literature_plan.output_strategy, "background_review")
        self.assertEqual(paper_plan.output_strategy, "paper_storyline")
        self.assertTrue(literature_plan.recommended_structure)
        self.assertTrue(paper_plan.recommended_structure)
        self.assertTrue(any("materials" in point.lower() for point in literature_plan.key_points_to_cover))


class LearningServiceTests(unittest.TestCase):
    def test_derive_assets_from_revision_returns_expected_asset_types(self) -> None:
        profile = parse_cv_to_profile(
            """Li Wei
PhD Candidate in Computational Biology
Tools: Python, LaTeX
"""
        )
        project = create_project_from_answers(
            profile,
            title="Test project",
            desired_outcome="Prepare an outline",
            blocker="Scattered notes",
            materials="Paper notes; memo",
        )
        task = TaskCard(
            id="task_demo",
            project_card_id=project.id,
            task_type="literature-outline",
            input_summary="Outline the literature",
            input_materials=["Paper notes", "Memo"],
            input_material_paths=["examples/task_input.txt"],
            input_material_types=["txt"],
            expected_output="Markdown outline",
            generated_draft_path="workspace/projects/test/outputs/demo.md",
        )

        updated_task, updated_project, assets = derive_assets_from_revision(
            task,
            project,
            generated_text="# Draft\n- broad framing\n",
            revised_text="# Draft\n## Evidence\n- tighter framing\n",
        )

        self.assertTrue(updated_task.feedback_summary)
        self.assertTrue(updated_project.next_step)
        self.assertEqual(
            {asset.asset_type for asset in assets},
            {"writing_rule", "structure_template", "project_note"},
        )
        self.assertIn("global", {asset.scope for asset in assets})
        self.assertIn("project", {asset.scope for asset in assets})
        self.assertIn("task", {asset.scope for asset in assets})
        self.assertIn("Signals:", updated_task.feedback_summary)
        self.assertIn("Observed revision signals", assets[-1].content)

    @patch("clawlab.services.learning_service.is_llm_enabled", return_value=True)
    @patch("clawlab.services.learning_service.call_llm")
    def test_learning_llm_branch_can_return_structured_assets(self, mock_call_llm, _mock_enabled) -> None:
        mock_call_llm.return_value = """{
          "writing_rules": ["Prefer explicit gap statements."],
          "structure_template": "Use context, gap, evidence, next move.",
          "project_note": "User prefers tighter logic around blocker resolution."
        }"""
        profile = parse_cv_to_profile("Li Wei\nPhD Candidate in Computational Biology")
        project = create_project_from_answers(
            profile,
            title="Test project",
            desired_outcome="Prepare an outline",
            blocker="Scattered notes",
            materials="Paper notes; memo",
        )
        task = TaskCard(
            id="task_demo",
            project_card_id=project.id,
            task_type="literature-outline",
            input_summary="Outline the literature",
            input_materials=["Paper notes", "Memo"],
            input_material_paths=["examples/task_input.txt"],
            input_material_types=["txt"],
            expected_output="Markdown outline",
            generated_draft_path="workspace/projects/test/outputs/demo.md",
        )
        _, _, assets = derive_assets_from_revision(
            task,
            project,
            generated_text="# Draft\n- broad framing\n",
            revised_text="# Draft\n## Evidence\n- tighter framing\n",
            llm_settings=LlmSettings(mode="hybrid", provider="openai", use_llm_for_learning=True),
        )
        self.assertEqual(assets[0].content, "Prefer explicit gap statements.")

    def test_task_plan_carries_selected_assets(self) -> None:
        profile = parse_cv_to_profile(
            """Li Wei
PhD Candidate in Computational Biology
Tools: Python, LaTeX
"""
        )
        project = create_project_from_answers(
            profile,
            title="Test project",
            desired_outcome="Prepare an outline",
            blocker="Scattered notes",
            materials="Paper notes; memo",
        )
        material_summary = MaterialSummary(
            id="material_test",
            source_path="examples/task_input.txt",
            source_type="txt",
            title="Task input material",
            short_summary="Evidence summary for resistant glioma states.",
            key_topics=["glioma", "resistance"],
            methods_or_entities=["single-cell"],
            useful_snippets=["Trajectory evidence sharpens the storyline."],
            relevance_to_project="Strongly relevant to the active goal.",
            raw_text_excerpt="Trajectory evidence sharpens the storyline.",
        )
        assets = [
            ReusableAsset(
                id="asset_rule_demo",
                scope="global",
                asset_type="writing_rule",
                title="Claim-first writing",
                content="Open each section with a project-specific claim.",
                confidence=0.8,
                source_task_id="task_prev",
                project_card_id=project.id,
                task_type="paper-outline",
            )
        ]
        plan = create_task_plan(
            task_type="paper-outline",
            profile=profile,
            project=project,
            material_summaries=[material_summary],
            retrieved_assets=assets,
        )
        self.assertTrue(plan.selected_assets)
        self.assertIn("Claim-first writing", plan.selected_assets[0])

    def test_assets_are_saved_as_json_and_markdown(self) -> None:
        profile = parse_cv_to_profile(
            """Li Wei
PhD Candidate in Computational Biology
Tools: Python, LaTeX
"""
        )
        project = create_project_from_answers(
            profile,
            title="Test project",
            desired_outcome="Prepare an outline",
            blocker="Scattered notes",
            materials="Paper notes; memo",
        )
        save_project(project)

        _, _, assets = derive_assets_from_revision(
            TaskCard(
                id="task_demo",
                project_card_id=project.id,
                task_type="literature-outline",
                input_summary="Outline the literature",
                input_materials=["Paper notes", "Memo"],
                input_material_paths=["examples/task_input.txt"],
                input_material_types=["txt"],
                expected_output="Markdown outline",
                generated_draft_path="workspace/projects/test/outputs/demo.md",
            ),
            project,
            generated_text="# Draft\n- broad framing\n",
            revised_text="# Draft\n## Evidence\n- tighter framing\n",
        )

        for asset in assets:
            json_path = save_asset(asset)
            project_json_path = save_project_asset(project.id, asset)
            self.assertTrue(json_path.exists())
            self.assertTrue(project_json_path.exists())

        self.assertTrue(Path(f"workspace/assets/writing-rules/{assets[0].id}.md").exists())
        self.assertTrue(Path(f"workspace/assets/templates/{assets[-2].id}.md").exists())
        self.assertTrue(Path(f"workspace/assets/project-notes/{assets[-1].id}.md").exists())
        self.assertTrue(Path(f"workspace/projects/{project.id}/notes/{assets[-1].id}.md").exists())


class EmployeeServiceTests(unittest.TestCase):
    def test_employee_registry_contains_expected_roles(self) -> None:
        roles = {spec.role_name for spec in list_employee_specs()}
        self.assertEqual(
            roles,
            {"literature_analyst", "project_manager", "draft_writer", "review_editor"},
        )
        spec = get_employee_spec("draft_writer")
        self.assertIn("markdown generation", spec.core_capabilities)

    def test_literature_analyst_creates_real_deliverable(self) -> None:
        profile = parse_cv_to_profile(
            """Li Wei
PhD Candidate in Computational Biology
Tools: Python, LaTeX
"""
        )
        project = create_project_from_answers(
            profile,
            title="Glioma resistance project",
            desired_outcome="Prepare an outline",
            blocker="Scattered notes",
            materials="Paper notes; memo",
        )
        save_project(project)
        deliverable = run_employee_task(
            "literature_analyst",
            project=project,
            input_path=Path("examples/task_input.txt"),
        )
        self.assertEqual(deliverable.employee_role, "literature_analyst")
        self.assertTrue(Path(deliverable.output_path).exists())

    def test_draft_writer_creates_task_backed_deliverable(self) -> None:
        profile = parse_cv_to_profile(
            """Li Wei
PhD Candidate in Computational Biology
Methods: differential expression, literature synthesis
Tools: Python, R, Git
"""
        )
        project = create_project_from_answers(
            profile,
            title="Glioma resistance project",
            desired_outcome="Prepare a tighter outline",
            blocker="Scattered notes",
            materials="Paper notes; memo",
        )
        save_project(project)
        material_summary = MaterialSummary(
            id="material_test",
            source_path="examples/task_input.txt",
            source_type="txt",
            title="Task input material",
            short_summary="This material summarizes resistance state transitions and points to the central evidence gap.",
            key_topics=["resistance", "state", "transition"],
            methods_or_entities=["single-cell", "trajectory"],
            useful_snippets=["Trajectory evidence is more useful than static cluster labels for this project."],
            relevance_to_project="Strongly relevant to the current project goal.",
            raw_text_excerpt="Need a literature outline for treatment-resistant glioma state transitions.",
        )
        deliverable = run_employee_task(
            "draft_writer",
            profile=profile,
            project=project,
            task_type="literature-outline",
            material_summaries=[material_summary],
        )
        self.assertEqual(deliverable.employee_role, "draft_writer")
        self.assertIsNotNone(deliverable.source_task_id)
        self.assertTrue(Path(deliverable.output_path).exists())


class ManagerServiceTests(unittest.TestCase):
    def _build_profile_and_project(self):
        profile = parse_cv_to_profile(
            """Li Wei
PhD Candidate in Computational Biology
Methods: differential expression, literature synthesis
Tools: Python, R, Git
"""
        )
        project = create_project_from_answers(
            profile,
            title="Glioma resistance project",
            desired_outcome="Prepare a tighter outline",
            blocker="Scattered notes",
            materials="Paper notes; memo",
        )
        save_project(project)
        return profile, project

    def test_create_manager_plan_builds_sequential_work_orders(self) -> None:
        _, project = self._build_profile_and_project()
        job, plan, work_orders = create_manager_plan(
            job_type="literature-brief",
            boss_goal="Produce a concise literature brief for the active project.",
            project=project,
            input_path=Path("examples/task_input.txt"),
        )
        self.assertEqual(job.job_type, "literature-brief")
        self.assertTrue(plan.selected_employees)
        self.assertEqual(plan.work_order_sequence, [work_order.id for work_order in work_orders])
        self.assertEqual(work_orders[0].employee_role, "literature_analyst")
        self.assertEqual(work_orders[-1].employee_role, "draft_writer")

    def test_manager_dispatch_and_result_produce_traceable_outputs(self) -> None:
        profile, project = self._build_profile_and_project()
        job, plan, work_orders = create_manager_plan(
            job_type="paper-outline",
            boss_goal="Produce a paper outline for the active project.",
            project=project,
            input_path=Path("examples/task_input.txt"),
        )
        deliverables = dispatch_work_orders(
            job=job,
            plan=plan,
            work_orders=work_orders,
            profile=profile,
            project=project,
        )
        result = synthesize_job_result(job=job, plan=plan, deliverables=deliverables)
        self.assertTrue(deliverables)
        self.assertTrue(Path(result.final_output_path).exists())
        self.assertIn("project_manager", result.participating_employees)
        self.assertEqual(len(result.deliverable_ids), len(deliverables))


if __name__ == "__main__":
    unittest.main()
