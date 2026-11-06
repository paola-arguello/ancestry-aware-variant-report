import check_inputs

EXPECTED = {"chr1": 248956422, "chr17": 83257441}

HEADER = [
    "##fileformat=VCFv4.2",
    "##contig=<ID=chr1,length=248956422>",
    "##contig=<ID=chr17,length=83257441>",
    "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG002",
]


def test_header_contigs_reads_names_and_lengths():
    contigs = check_inputs.header_contigs(HEADER)
    assert contigs == {"chr1": 248956422, "chr17": 83257441}


def test_header_contigs_allows_missing_length():
    assert check_inputs.header_contigs(["##contig=<ID=chr1>"]) == {"chr1": None}


def test_header_samples():
    assert check_inputs.header_samples(HEADER) == ["HG002"]


def test_matching_build_has_no_problems():
    found = check_inputs.header_contigs(HEADER)
    assert check_inputs.length_problems("vcf", found, EXPECTED) == []


def test_grch37_chr1_length_is_flagged():
    found = {"chr1": 249250621}
    problems = check_inputs.length_problems("vcf", found, EXPECTED)
    assert len(problems) == 1
    assert "wrong genome build" in problems[0]


def test_missing_chr_prefix_is_flagged():
    problems = check_inputs.name_problems("clinvar", ["1", "17"], EXPECTED)
    assert any("should be 'chr17'" in p for p in problems)


def test_header_without_contigs_means_build_unknown():
    problems = check_inputs.length_problems("vcf", {}, EXPECTED)
    assert problems == ["vcf: no expected contigs found, build unknown"]


def test_extra_contigs_are_ignored():
    found = {"chr1": 248956422, "chrUn_KI270302v1": 2274}
    assert check_inputs.length_problems("fasta", found, EXPECTED) == []


def test_wrong_sample_name():
    problems = check_inputs.sample_problems(["NA12878"], "HG002")
    assert problems == ["sample VCF: expected one sample 'HG002', found ['NA12878']"]


def test_main_returns_1_on_failure(tmp_path):
    header = tmp_path / "header.txt"
    header.write_text("\n".join(HEADER).replace("83257441", "81195210"))
    expected = tmp_path / "contigs.tsv"
    expected.write_text("chr1\t248956422\nchr17\t83257441\n")
    argv = ["--header", str(header), "--sample", "HG002", "--expected", str(expected)]
    assert check_inputs.main(argv) == 1


def test_main_returns_0_on_success(tmp_path):
    header = tmp_path / "header.txt"
    header.write_text("\n".join(HEADER))
    expected = tmp_path / "contigs.tsv"
    expected.write_text("# comment\nchr1\t248956422\nchr17\t83257441\n")
    names = tmp_path / "clinvar_contigs.txt"
    names.write_text("chr1\nchr17\n")
    argv = [
        "--header",
        str(header),
        "--sample",
        "HG002",
        "--expected",
        str(expected),
        "--names",
        str(names),
    ]
    assert check_inputs.main(argv) == 0
