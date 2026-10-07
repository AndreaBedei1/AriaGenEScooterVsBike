"""Documentation stays consistent with the code and the repository."""

from __future__ import annotations

from pathlib import Path

from ariagen_escooter.streams import ANNOTATION_SPECS, STREAM_SPECS


def test_data_schema_doc_lists_every_column(project_root: Path) -> None:
    text = (project_root / "docs" / "data_schema.md").read_text(encoding="utf-8")
    for spec in list(STREAM_SPECS.values()) + list(ANNOTATION_SPECS.values()):
        assert f"`{spec.filename_stem}.csv`" in text
        for column in spec.columns:
            assert f"`{column.name}`" in text, f"{spec.name}.{column.name} missing from docs/data_schema.md"


def test_required_documents_exist(project_root: Path) -> None:
    for rel in (
        "README.md",
        "docs/methodology.md",
        "docs/data_schema.md",
        "docs/privacy_pipeline.md",
        "docs/research_questions.md",
        "docs/aria_gen2_integration.md",
        "docs/ethics/ethics_study_overview.md",
        "docs/ethics/ethics_one_page.md",
        "docs/presentation/AriaGenEScooter_overview.pptx",
    ):
        path = project_root / rel
        assert path.is_file() and path.stat().st_size > 1000, rel


def test_ethics_documents_keep_open_decisions_explicit(project_root: Path) -> None:
    text = (project_root / "docs" / "ethics" / "ethics_study_overview.md").read_text(encoding="utf-8")
    assert text.count("TBD") >= 5
    for word in ("hazard", "near miss", "near-miss"):
        # neutral vocabulary: the words may appear only to say they are NOT used
        for line in text.lower().splitlines():
            if word in line:
                assert "non " in line or "not " in line, line
