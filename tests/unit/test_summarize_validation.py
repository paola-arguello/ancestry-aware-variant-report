import summarize_validation


def write_vcf(path, n_records):
    lines = ["##fileformat=VCFv4.2", "#CHROM\tPOS\tID\tREF\tALT"]
    lines += [f"chr17\t{100 + i}\t.\tA\tG" for i in range(n_records)]
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def test_count_records_ignores_header(tmp_path):
    assert summarize_validation.count_records(write_vcf(tmp_path / "a.vcf", 3)) == 3


def test_metrics_perfect_match():
    values = summarize_validation.metrics(tp=10, fp=0, fn=0)
    assert values["recall"] == 1.0
    assert values["precision"] == 1.0


def test_metrics_spiked_variants_lower_precision_only():
    # PatientA: 10 benchmark variants found, 4 spiked variants not in the truth set
    values = summarize_validation.metrics(tp=10, fp=4, fn=0)
    assert values["recall"] == 1.0
    assert values["precision"] == 0.7143


def test_ratio_with_nothing_to_divide_is_none():
    assert summarize_validation.ratio(0, 0) is None


def test_format_row_writes_na_for_missing():
    values = summarize_validation.metrics(tp=0, fp=0, fn=0)
    assert summarize_validation.format_row("S1", values) == "S1\t0\t0\t0\tNA\tNA"


def test_main_prints_table(tmp_path, capsys):
    argv = [
        "--sample", "HG002",
        "--shared", write_vcf(tmp_path / "tp.vcf", 8),
        "--query-only", write_vcf(tmp_path / "fp.vcf", 0),
        "--truth-only", write_vcf(tmp_path / "fn.vcf", 2),
    ]  # fmt: skip
    summarize_validation.main(argv)
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "sample\ttp\tfp\tfn\trecall\tprecision"
    assert out[1] == "HG002\t8\t0\t2\t0.8\t1.0"
