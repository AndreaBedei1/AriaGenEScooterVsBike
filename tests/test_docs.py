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
        "docs/study_overview.md",
        "docs/literature/literature_review.md",
        "docs/literature/paper_matrix.csv",
        "docs/literature/replication_plan.md",
        "docs/literature/research_gaps.md",
        "docs/literature/references.bib",
        "docs/literature/kegalle_replication.md",
        "docs/methodology/metrics_catalog.md",
        "docs/methodology/metrics_feasibility.csv",
        "docs/methodology/statistical_analysis_plan.md",
        "docs/research/scientific_contribution.md",
        "docs/route/cesena_route_map.html",
        "docs/route/cesena_route.geojson",
        "docs/route/cesena_route.gpx",
        "docs/route/route_description.md",
        "docs/route/route_segments.csv",
        "docs/route/route_validation_checklist.md",
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


def test_relative_markdown_links_resolve(project_root: Path) -> None:
    """Every relative link in the Markdown documentation points to an existing file."""
    import re

    files = [*project_root.joinpath("docs").rglob("*.md"), project_root / "README.md"]
    broken = []
    for md in files:
        for match in re.finditer(r"\]\(([^)#\s]+)(#[^)]*)?\)", md.read_text(encoding="utf-8")):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (md.parent / target).exists():
                broken.append(f"{md.relative_to(project_root).as_posix()}: {target}")
    assert not broken, "broken links:\n" + "\n".join(broken)


def test_bibliography_keys_unique_and_matrix_keys_present(project_root: Path) -> None:
    import csv
    import re

    bib = (project_root / "docs" / "literature" / "references.bib").read_text(encoding="utf-8")
    keys = re.findall(r"@\w+\{([^,]+),", bib)
    assert len(keys) == len(set(keys))
    with (project_root / "docs" / "literature" / "paper_matrix.csv").open(encoding="utf-8") as handle:
        matrix_keys = {row["key"] for row in csv.DictReader(handle)}
    assert matrix_keys <= set(keys), sorted(matrix_keys - set(keys))
