process RESTRICT_PANEL {
    tag "${sample}"

    input:
    tuple val(sample), path(vcf), path(vcf_index)
    path panel_bed

    output:
    tuple val(sample), path("${sample}.panel.vcf.gz"), path("${sample}.panel.vcf.gz.tbi"), emit: vcf

    script:
    // A file ending in .bed is read as 0-based, half-open coordinates
    """
    bcftools view \\
        -R ${panel_bed} \\
        -Oz -o ${sample}.panel.vcf.gz \\
        ${vcf}
    tabix -p vcf ${sample}.panel.vcf.gz
    """
}
