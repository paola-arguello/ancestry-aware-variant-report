# Changelog

## Unreleased

### Added
- Repository layout, Nextflow config with `docker`, `conda` and `test` profiles
- `CHECK_INPUTS`: genome build, contig naming and sample name checks, with unit tests
- `NORMALIZE`, `RESTRICT_PANEL`, `ANNOTATE` (ClinVar, gnomAD v4.1 per genetic ancestry group)
- `VALIDATE`: known-answer comparison against GIAB HG002 v4.2.1 with bcftools isec
- `scripts/download_data.sh` with a manifest of sources, dates and checksums
- `scripts/make_panel_bed.py`: 14-gene hereditary cancer panel from Ensembl
- CI: ruff and pytest on every push and pull request
