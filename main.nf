#!/usr/bin/env nextflow
/*
 * ancestry-aware-variant-report
 * Germline small-variant report for a hereditary cancer panel.
 * Synthetic data. Not for clinical use.
 */

include { CHECK_INPUTS                       } from './modules/local/check_inputs'
include { NORMALIZE                          } from './modules/local/normalize'
include { NORMALIZE as NORMALIZE_TRUTH       } from './modules/local/normalize'
include { RESTRICT_PANEL                     } from './modules/local/restrict_panel'
include { RESTRICT_PANEL as RESTRICT_TRUTH   } from './modules/local/restrict_panel'
include { ANNOTATE                           } from './modules/local/annotate'
include { VALIDATE                           } from './modules/local/validate'

def required(name) {
    if (!params[name]) {
        error "Missing required parameter --${name}"
    }
    return file(params[name], checkIfExists: true)
}

def with_index(name) {
    def vcf = required(name)
    return [vcf, file("${vcf}.tbi", checkIfExists: true)]
}

workflow {
    if (!params.sample) {
        error "Missing required parameter --sample"
    }

    sample_vcf = Channel.value([params.sample] + with_index('vcf'))
    fasta      = Channel.value([required('fasta'), file("${params.fasta}.fai", checkIfExists: true)])
    clinvar    = Channel.value(with_index('clinvar'))
    gnomad     = Channel.value(with_index('gnomad'))
    panel_bed  = required('panel_bed')
    expected   = required('expected_contigs')

    CHECK_INPUTS(sample_vcf, fasta, clinvar, gnomad, expected)
    NORMALIZE(CHECK_INPUTS.out.vcf, fasta)
    RESTRICT_PANEL(NORMALIZE.out.vcf, panel_bed)
    ANNOTATE(RESTRICT_PANEL.out.vcf, clinvar, gnomad, params.gnomad_groups)

    // TODO (Wed): TRIAGE (bin/triage.py) and REPORT (bin/report.py)

    if (params.truth_vcf) {
        truth = Channel.value(["${params.sample}_truth"] + with_index('truth_vcf'))
        NORMALIZE_TRUTH(truth, fasta)
        RESTRICT_TRUTH(NORMALIZE_TRUTH.out.vcf, panel_bed)
        VALIDATE(RESTRICT_PANEL.out.vcf, RESTRICT_TRUTH.out.vcf, required('truth_bed'))
    }
}
