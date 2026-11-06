#!/usr/bin/env bash
# Download and prepare every public resource the pipeline needs.
#
# Usage: bash scripts/download_data.sh [data_dir]
# Needs: curl, python3, bcftools, samtools, bgzip, tabix (all in environment.yml)
# Disk:  about 4 GB, most of it the GRCh38 FASTA.
#
# Every file is recorded in data_dir/MANIFEST.tsv with its source URL,
# download date and md5, so the report can state exactly what it used.

set -euo pipefail

DATA="${1:-data}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
TODAY="$(date +%F)"
mkdir -p "$DATA"
MANIFEST="$DATA/MANIFEST.tsv"
[[ -f "$MANIFEST" ]] || printf 'file\tsource\tdownloaded\tmd5\tnote\n' > "$MANIFEST"

for tool in curl python3 bcftools samtools bgzip tabix; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done

md5() {  # portable across Linux and macOS
    python3 - "$1" <<'PY'
import hashlib, sys
digest = hashlib.md5()
with open(sys.argv[1], "rb") as handle:
    for chunk in iter(lambda: handle.read(1 << 20), b""):
        digest.update(chunk)
print(digest.hexdigest())
PY
}

record() {  # file, source, note
    printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$TODAY" "$(md5 "$DATA/$1")" "$3" >> "$MANIFEST"
}

fetch() {  # url, output file
    echo "Downloading $1"
    curl -fL --retry 3 -o "$2" "$1"
}

# 1. Reference: GRCh38 no-alt analysis set (UCSC-style names: chr1, chr17, ...)
NCBI_REF="https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids"
REF_NAME="GCA_000001405.15_GRCh38_no_alt_analysis_set.fna"
if [[ ! -f "$DATA/GRCh38.fa.fai" ]]; then
    fetch "$NCBI_REF/$REF_NAME.gz" "$DATA/$REF_NAME.gz"
    gunzip -c "$DATA/$REF_NAME.gz" > "$DATA/GRCh38.fa"
    rm "$DATA/$REF_NAME.gz"
    samtools faidx "$DATA/GRCh38.fa"
    record GRCh38.fa "$NCBI_REF/$REF_NAME.gz" "decompressed and indexed"
fi

# 2. Panel BED from Ensembl (gene spans, GRCh38)
python3 "$REPO/scripts/make_panel_bed.py" "$REPO/assets/panel_genes.txt" "$DATA/panel.bed"
record panel.bed "Ensembl REST lookup/symbol" "see panel.bed.provenance.txt"

# 3. ClinVar (GRCh38). The weekly file is renamed with its own fileDate.
CLINVAR_URL="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz"
fetch "$CLINVAR_URL" "$DATA/clinvar_raw.vcf.gz"
fetch "$CLINVAR_URL.tbi" "$DATA/clinvar_raw.vcf.gz.tbi"
CLINVAR_DATE="$(bcftools view -h "$DATA/clinvar_raw.vcf.gz" | grep -m1 '^##fileDate' | cut -d= -f2)"
CLINVAR="clinvar_${CLINVAR_DATE//-/}.chr.norm.vcf.gz"
# ClinVar uses "17", the rest of the pipeline uses "chr17". Rename, then split
# multiallelics and left-align against the same FASTA as the sample.
bcftools annotate --rename-chrs "$REPO/assets/clinvar_chr_rename.tsv" "$DATA/clinvar_raw.vcf.gz" -Ou \
    | bcftools norm -m -any -f "$DATA/GRCh38.fa" --check-ref w -Oz -o "$DATA/$CLINVAR"
tabix -p vcf "$DATA/$CLINVAR"
rm "$DATA/clinvar_raw.vcf.gz" "$DATA/clinvar_raw.vcf.gz.tbi"
record "$CLINVAR" "$CLINVAR_URL" "fileDate=$CLINVAR_DATE; chr renamed; norm -m -any"

# 4. GIAB HG002 benchmark, v4.2.1 on GRCh38 (chr1-22 only)
GIAB="https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/AshkenazimTrio/HG002_NA24385_son/NISTv4.2.1/GRCh38"
GIAB_VCF="HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz"
GIAB_BED="HG002_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed"
for f in "$GIAB_VCF" "$GIAB_VCF.tbi" "$GIAB_BED"; do
    [[ -f "$DATA/$f" ]] || fetch "$GIAB/$f" "$DATA/$f"
done
record "$GIAB_VCF" "$GIAB/$GIAB_VCF" "GIAB HG002 v4.2.1 benchmark VCF"
record "$GIAB_BED" "$GIAB/$GIAB_BED" "GIAB HG002 v4.2.1 benchmark regions"

# 5. gnomAD v4.1 genomes, sliced to the panel regions over the network.
#    Only allele counts and frequencies are kept, overall and per group.
GNOMAD="https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes"
GROUPS="afr amr asj eas fin mid nfe sas remaining"
KEEP="INFO/AC,INFO/AN,INFO/AF"
for g in $GROUPS; do KEEP="$KEEP,INFO/AC_$g,INFO/AN_$g,INFO/AF_$g"; done
parts=()
for chrom in $(cut -f1 "$DATA/panel.bed" | sort -u); do
    url="$GNOMAD/gnomad.genomes.v4.1.sites.$chrom.vcf.bgz"
    echo "Slicing $url"
    awk -v c="$chrom" '$1 == c' "$DATA/panel.bed" > "$DATA/panel_$chrom.bed"
    bcftools view -R "$DATA/panel_$chrom.bed" "$url" -Ou \
        | bcftools annotate -x "^$KEEP" -Oz -o "$DATA/gnomad_$chrom.vcf.gz"
    tabix -f -p vcf "$DATA/gnomad_$chrom.vcf.gz"
    parts+=("$DATA/gnomad_$chrom.vcf.gz")
    rm "$DATA/panel_$chrom.bed"
done
bcftools concat -a "${parts[@]}" -Ou \
    | bcftools norm -m -any -f "$DATA/GRCh38.fa" --check-ref w -Oz -o "$DATA/gnomad_v4.1_genomes_panel.vcf.gz"
tabix -p vcf "$DATA/gnomad_v4.1_genomes_panel.vcf.gz"
rm -f "${parts[@]}" "${parts[@]/%/.tbi}"
record gnomad_v4.1_genomes_panel.vcf.gz "$GNOMAD" "panel regions only; groups: $GROUPS"

echo "Done. Sources are listed in $MANIFEST"
