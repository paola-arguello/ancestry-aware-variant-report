import io
import json
import urllib.error

import pytest

import make_panel_bed

BRCA1 = {
    "assembly_name": "GRCh38",
    "seq_region_name": "17",
    "start": 1001,
    "end": 2000,
}


def fake_opener(payload):
    def opener(request):
        return io.BytesIO(json.dumps(payload).encode())

    return opener


def test_read_genes_skips_comments_and_blanks(tmp_path):
    path = tmp_path / "genes.txt"
    path.write_text("# panel\nBRCA1\n\nTP53\n")
    assert make_panel_bed.read_genes(path) == ["BRCA1", "TP53"]


def test_bed_record_converts_to_zero_based_with_chr_prefix():
    assert make_panel_bed.bed_record(BRCA1, "BRCA1") == ("chr17", 1000, 2000, "BRCA1")


def test_bed_record_padding():
    assert make_panel_bed.bed_record(BRCA1, "BRCA1", pad=100)[1:3] == (900, 2100)


def test_bed_record_rejects_other_builds():
    with pytest.raises(ValueError, match="GRCh37"):
        make_panel_bed.bed_record(dict(BRCA1, assembly_name="GRCh37"), "BRCA1")


def test_merge_records_joins_overlaps_and_sorts():
    records = [
        ("chr2", 500, 900, "MSH2"),
        ("chr2", 100, 600, "EPCAM"),
        ("chr17", 10, 20, "TP53"),
    ]
    assert make_panel_bed.merge_records(records) == [
        ("chr17", 10, 20, "TP53"),
        ("chr2", 100, 900, "EPCAM;MSH2"),
    ]


def test_lookup_gene_uses_rest_payload():
    gene = make_panel_bed.lookup_gene("BRCA1", opener=fake_opener(BRCA1))
    assert gene["seq_region_name"] == "17"


def flaky_opener(failures, code=503):
    calls = {"n": 0}

    def opener(request):
        calls["n"] += 1
        if calls["n"] <= failures:
            raise urllib.error.HTTPError(request.full_url, code, "busy", {}, None)
        return io.BytesIO(json.dumps(BRCA1).encode())

    return opener, calls


def test_get_json_retries_when_server_is_busy():
    opener, calls = flaky_opener(failures=2)
    result = make_panel_bed.get_json(
        "https://example.org/x", opener, sleep=lambda s: None
    )
    assert result["seq_region_name"] == "17"
    assert calls["n"] == 3


def test_get_json_gives_up_after_last_try():
    opener, _ = flaky_opener(failures=10)
    with pytest.raises(urllib.error.HTTPError):
        make_panel_bed.get_json(
            "https://example.org/x", opener, tries=3, sleep=lambda s: None
        )


def test_get_json_does_not_retry_not_found():
    opener, calls = flaky_opener(failures=1, code=404)
    with pytest.raises(urllib.error.HTTPError):
        make_panel_bed.get_json("https://example.org/x", opener, sleep=lambda s: None)
    assert calls["n"] == 1
