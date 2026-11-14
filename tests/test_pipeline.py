from app.pipeline import normalize_doi, parse_paper, build_evidence, baseline_report

def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"

def test_metadata_does_not_imply_findings():
    paper = parse_paper({"DOI": "10.1234/example", "title": ["Example study"], "issued": {"date-parts": [[2024]]}})
    assert paper.evidence_status == "metadata_only"
    evidence = build_evidence([paper])
    assert "do not infer study findings" in evidence[0]["text"]
    assert "No full-text screening" in baseline_report("Example question", [paper], evidence)

def test_abstract_is_labeled():
    paper = parse_paper({"DOI": "10.1234/example", "title": ["Example study"], "abstract": "<jats:p>Observed effect.</jats:p>"})
    assert paper.abstract == "Observed effect."
    assert paper.evidence_status == "abstract_available"
