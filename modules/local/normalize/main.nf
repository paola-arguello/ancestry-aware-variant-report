process NORMALIZE {
    tag "${sample}"

    input:
    tuple val(sample), path(vcf), path(vcf_index)
    tuple path(fasta), path(fasta_fai)

    output:
    tuple val(sample), path("${sample}.norm.vcf.gz"), path("${sample}.norm.vcf.gz.tbi"), emit: vcf

    script:
    // -m -any: split multiallelic records so each ALT is matched on its own
    // --check-ref e: stop if a REF allele does not match the FASTA (build check)
    """
    bcftools norm \\
        -m -any \\
        -f ${fasta} \\
        --check-ref e \\
        -Oz -o ${sample}.norm.vcf.gz \\
        ${vcf}
    tabix -p vcf ${sample}.norm.vcf.gz
    """
}
