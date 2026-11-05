process CHECK_INPUTS {
    tag "${sample}"

    input:
    tuple val(sample), path(vcf), path(vcf_index)
    tuple path(fasta), path(fasta_fai)
    tuple path(clinvar), path(clinvar_index)
    tuple path(gnomad), path(gnomad_index)
    path expected_contigs

    output:
    tuple val(sample), path(vcf), path(vcf_index), emit: vcf
    path 'check_inputs.log',                        emit: log

    script:
    """
    bcftools view -h ${vcf} > sample_header.txt
    tabix -l ${clinvar} > clinvar_contigs.txt
    tabix -l ${gnomad} > gnomad_contigs.txt

    check_inputs.py \\
        --header sample_header.txt \\
        --sample ${sample} \\
        --expected ${expected_contigs} \\
        --fai ${fasta_fai} \\
        --names clinvar_contigs.txt gnomad_contigs.txt \\
        > check_inputs.log 2>&1 \\
        || { cat check_inputs.log >&2; exit 1; }
    """
}
