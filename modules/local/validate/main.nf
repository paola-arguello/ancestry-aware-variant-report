process VALIDATE {
    tag "${sample}"

    input:
    tuple val(sample), path(query), path(query_index)
    tuple val(truth_name), path(truth), path(truth_index)
    path truth_bed

    output:
    path "${sample}.validation.tsv", emit: tsv

    script:
    // Compare only inside the benchmark's confident regions.
    // isec -c none matches on CHROM, POS, REF and ALT exactly. It does not
    // compare genotypes (hap.py does; listed in the roadmap).
    """
    bcftools view -T ${truth_bed} -Oz -o query.conf.vcf.gz ${query}
    bcftools view -T ${truth_bed} -Oz -o truth.conf.vcf.gz ${truth}
    tabix -p vcf query.conf.vcf.gz
    tabix -p vcf truth.conf.vcf.gz

    bcftools isec -c none -p isec query.conf.vcf.gz truth.conf.vcf.gz

    summarize_validation.py \\
        --sample ${sample} \\
        --query-only isec/0000.vcf \\
        --truth-only isec/0001.vcf \\
        --shared isec/0002.vcf \\
        > ${sample}.validation.tsv
    """
}
