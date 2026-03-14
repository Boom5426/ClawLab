import unittest
from pathlib import Path

from clawlab.core.models import MaterialDocument, TaskCard
from clawlab.services.draft_service import generate_draft
from clawlab.services.ingest_service import detect_material_type, read_cv_text, read_material
from clawlab.services.learning_service import derive_assets_from_revision
from clawlab.services.profile_service import parse_cv_to_profile
from clawlab.services.project_service import create_project_from_answers
from clawlab.services.workspace_service import get_outputs_dir


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

    def test_read_cv_text_supports_pdf(self) -> None:
        text = read_cv_text(Path("examples/cv_sample.pdf"))
        self.assertTrue(text.strip())


class ProjectAndDraftTests(unittest.TestCase):
    def test_create_project_and_generate_task_card(self) -> None:
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
        material = MaterialDocument(
            path="examples/task_input.txt",
            material_type="txt",
            extracted_text=Path("examples/task_input.txt").read_text(encoding="utf-8"),
        )
        output_dir = Path("workspace/projects/test_project/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)

        task, draft_path = generate_draft(
            profile,
            project,
            task_type="literature-outline",
            material=material,
            output_dir=output_dir,
            workspace_root=Path("workspace"),
        )

        self.assertEqual(project.title, "Glioma resistance project")
        self.assertEqual(task.input_material_types, ["txt"])
        self.assertTrue(draft_path.exists())
        self.assertIn("Suggested Review Structure", draft_path.read_text(encoding="utf-8"))


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


if __name__ == "__main__":
    unittest.main()
