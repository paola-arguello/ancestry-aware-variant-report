process ANNOTATE {
    tag "${sample}"

    input:
    tuple val(sample), path(vcf), path(vcf_index)
    tuple path(clinvar), path(clinvar_index)
    tuple path(gnomad), path(gnomad_index)
    val gnomad_groups

    output:
    tuple val(sample), path("${sample}.annotated.vcf.gz"), path("${sample}.annotated.vcf.gz.tbi"), emit: vcf

    script:
    // ClinVar fields are copied as they are. gnomAD fields get a gnomad_ prefix
    // so they can't be confused with fields already in the sample VCF.
    def clinvar_cols = 'ID,INFO/CLNSIG,INFO/CLNREVSTAT,INFO/CLNDN,INFO/CLNSIGCONF,INFO/CLNVC,INFO/GENEINFO,INFO/CLNHGVS'
    def tags = ['AC', 'AN', 'AF']
    gnomad_groups.tokenize(',').each { g -> tags += ["AC_${g}", "AN_${g}", "AF_${g}"] }
    def gnomad_cols = tags.collect { t -> "INFO/gnomad_${t}:=INFO/${t}" }.join(',')
    """
    bcftools annotate \\
        -a ${clinvar} \\
        -c ${clinvar_cols} \\
        -Ou ${vcf} \\
    | bcftools annotate \\
        -a ${gnomad} \\
        -c '${gnomad_cols}' \\
        -Oz -o ${sample}.annotated.vcf.gz
    tabix -p vcf ${sample}.annotated.vcf.gz
    """
}
