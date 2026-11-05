# ancestry-aware-variant-report

[![CI](https://github.com/paola-arguello/ancestry-aware-variant-report/actions/workflows/ci.yml/badge.svg)](https://github.com/paola-arguello/ancestry-aware-variant-report/actions/workflows/ci.yml)

> **Synthetic data. Not for clinical use.**

A Nextflow DSL2 pipeline that takes a germline VCF, restricts it to a hereditary cancer gene panel, annotates it with ClinVar and gnomAD, and writes a clinical-style variant report. The report shows allele frequencies for each gnomAD genetic ancestry group and states when the group that matches the patient has little or no data.

I built it to show how the frequency evidence behind a variant interpretation depends on who is in the reference data.

**Status:** in development toward v0.1.0.

- Written: the Nextflow modules for `CHECK_INPUTS`, `NORMALIZE`, `RESTRICT_PANEL`, `ANNOTATE` and `VALIDATE`, the data download script, and the Python helpers.
- Tested: the Python helpers have unit tests (pytest) that run in CI with ruff.
- Not yet done: the Nextflow modules have not been run end to end on real data. `TRIAGE`, `REPORT` and the bundled test dataset for `-profile test` are next.

## What it does

| Step | Tool | What it does |
|---|---|---|
| `CHECK_INPUTS` | Python | Stops if the VCF, FASTA or resources are not on GRCh38, use different contig names, or have the wrong sample |
| `NORMALIZE` | bcftools norm | Splits multiallelic records and left-aligns indels against the reference. Stops on a REF mismatch |
| `RESTRICT_PANEL` | bcftools view | Keeps variants inside the panel genes |
| `ANNOTATE` | bcftools annotate | Adds ClinVar classification, review status and condition, and gnomAD frequencies per genetic ancestry group |
| `TRIAGE` | Python | *(next)* Maps review status to stars, groups variants by classification, flags conflicts and missing frequency data |
| `REPORT` | Python, Jinja2 | *(next)* HTML report |
| `VALIDATE` | bcftools isec | Compares the pipeline output with the GIAB HG002 benchmark inside the panel |

## Quick start

```bash
# 1. Software: conda, or Docker
conda env create -f environment.yml && conda activate ancestry-aware-variant-report
# or
docker build -t ancestry-aware-variant-report:0.1.0 .

# 2. Data (about 4 GB, mostly the reference FASTA)
bash scripts/download_data.sh data

# 3. Run on GIAB HG002
nextflow run main.nf -profile conda \
    --sample HG002 \
    --vcf data/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz \
    --fasta data/GRCh38.fa \
    --panel_bed data/panel.bed \
    --clinvar data/clinvar_YYYYMMDD.chr.norm.vcf.gz \
    --gnomad data/gnomad_v4.1_genomes_panel.vcf.gz \
    --truth_vcf data/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz \
    --truth_bed data/HG002_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed
```

## Data

`scripts/download_data.sh` writes every source URL, download date and md5 to `data/MANIFEST.tsv`.

| Resource | Version | Notes |
|---|---|---|
| Reference | GRCh38 no-alt analysis set (NCBI) | UCSC-style names (`chr17`) |
| Panel | 14 genes, `assets/panel_genes.txt` | Gene spans from Ensembl REST. Release recorded in `panel.bed.provenance.txt` |
| ClinVar | weekly GRCh38 VCF, date in file name | Renamed from `17` to `chr17` and normalized with the same FASTA |
| gnomAD | v4.1 genomes | Sliced to the panel. Allele counts and frequencies only |
| Benchmark | GIAB HG002 v4.2.1, GRCh38 | chr1 to 22 only |

GIAB now lists v4.2.1 as deprecated for HG002, in favour of a newer draft benchmark built from the T2T HG002 assembly. I use v4.2.1 here because its files and behaviour are well documented. Moving to the newer set is on the roadmap.

## What validation means here

The input is the GIAB benchmark VCF itself, so `VALIDATE` is a known-answer test of the pipeline, not a measure of variant calling accuracy. Inside the panel and the benchmark regions, the pipeline should return every benchmark variant (recall 1.0) and nothing extra (precision 1.0). A lower number means the pipeline lost or changed variants, for example through normalization or region filtering.

For the synthetic PatientA, the spiked-in ClinVar variants are not in the benchmark. They should show up as false positives, exactly as many as were added, and nothing else.

Measuring variant calling accuracy needs reads, a caller and a comparison tool that checks genotypes, such as hap.py. That is on the roadmap.

## Limitations

- Germline small variants only. No copy number variants, so EPCAM deletions and other exon-level events are missed.
- PMS2 has a close pseudogene (PMS2CL). Short-read calls there are unreliable, and this pipeline does nothing about it.
- ClinVar classifications are reported as they are. The pipeline does not apply ACMG/AMP criteria.
- gnomAD genetic ancestry groups are broad. A small or missing group is reported as a limitation, not filled in from another group.

## Roadmap

- FASTQ to VCF with nf-core/sarek, then hap.py against the newer GIAB HG002 benchmark
- Variant consequence and HGVS annotation with VEP
- ACMG/AMP criteria scoring
- Copy number variants
- More panels, starting with the ACMG secondary findings list
- A polygenic risk score module

## Development

```bash
pip install ruff pytest
ruff check . && ruff format --check .
pytest
```

## Use of AI tools

AI assistants (including Claude by Anthropic) were used to help write and review code and documentation. I review every change before it is merged.

## License

MIT. See `LICENSE`.
