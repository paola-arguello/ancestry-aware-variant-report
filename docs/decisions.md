# Decisions log

Every analysis is a pile of choices. Most of them never show up in the final report, but each one changes what the report can and can't say. This file keeps track of the ones in this pipeline: what I chose, why, what I gave up, and where the reasoning comes from.

If you are using this repo to learn, read this file before the code. If you disagree with a choice, good. Change it, rerun the pipeline and see what moves.

> DRAFT. Text in [square brackets] is still to be written or confirmed.

Each entry has the same parts:

- **Decision:** what the pipeline does.
- **Why:** the reasoning.
- **What this gives up:** the cost of the choice.
- **Sources:** where the reasoning comes from.

---

## D1. Start from a VCF, not from raw reads

**Decision:** The pipeline starts from a variant call file (VCF). Alignment and variant calling are not part of it.

**Why:** The question this project asks is about interpretation: once you have a list of variants, what can you say about them, and how much does the answer depend on who is in the reference data? Starting from reads would add hours of compute and a lot of code that has nothing to do with that question. The input is the Genome in a Bottle (GIAB) HG002 benchmark VCF, because it is public, well studied and comes with a list of regions where its calls are trusted.

**What this gives up:** Nothing here tests variant calling. Recall and precision in this pipeline measure whether the pipeline keeps or loses variants it was given, not whether a caller found them (see D7).

**Sources:** [GIAB HG002 v4.2.1 release notes]

---

## D2. Which genes: ClinGen Definitive only

**Decision:** The panel contains genes with a **Definitive** ClinGen gene-disease validity classification for a hereditary cancer condition, taken from a dated snapshot of ClinGen's curations (see D5).

**Why:** A panel should be explainable with one rule that anyone can check. ClinGen curation panels score the published genetic and experimental evidence that a gene causes a disease and give it a level: Definitive, Strong, Moderate, Limited, Disputed or Refuted. Definitive is the highest level. Using it means every gene in the report has been reviewed by experts, not picked because it appears on a commercial panel.

Two things worth knowing before reading the report:

- **Gene level is not variant level.** ClinGen says whether a *gene* causes a disease. Whether a specific *variant* in that gene is disease-causing is a separate question, answered with the ACMG/AMP classes (Pathogenic, Likely pathogenic, Uncertain significance, Likely benign, Benign). The report shows variant classes. [Link to Crosswalk post on both levels]
- **Some Definitive genes cause disease in ways this pipeline can't see.** EPCAM is Definitive for Lynch syndrome because of *deletions* at its 3′ end that switch off MSH2 next door. This pipeline only looks at small variants, so it can't detect that. PMS2 has a pseudogene (PMS2CL) so similar that short reads can't tell them apart in part of the gene. If they pass the rule, both genes stay in, with a note in the report explaining the limit. [PMS2: confirm its current ClinGen classification in the snapshot]

**Comparison panel:** For teaching only, the pipeline can also run with a wider panel: the Definitive genes plus genes often included on commercial hereditary cancer panels that ClinGen rates below Definitive. Comparing PatientA's report under both panels shows what a bigger panel adds. The expectation is that it adds mostly variants of uncertain significance, not answers.

**What this gives up:** Genes with real but weaker evidence are left out of the main report.

**Sources:**
- Lee K, et al. Clinical validity assessment of genes frequently tested on hereditary breast and ovarian cancer susceptibility sequencing panels. *Genet Med* 2019. https://www.nature.com/articles/s41436-018-0361-5
- Seifert BA, et al. Evaluating the clinical validity of genes related to hereditary colorectal cancer and polyposis. *Genet Med* 2019. https://pmc.ncbi.nlm.nih.gov/articles/PMC6579719
- ClinGen gene-disease validity. https://search.clinicalgenome.org/kb/gene-validity

---

## D3. Which part of each gene: MANE Select coding exons

**Decision:** For each gene, the pipeline looks at the coding exons of its **MANE Select** transcript, plus padding into the introns (D4).

**Why:** There are two common ways to define "the gene":

| Option | What it covers | Good for | Problem |
|---|---|---|---|
| Whole gene span | Everything from the first base of the gene to the last, introns included | Genome data, finding deep intronic variants | Hundreds of common intronic variants per gene, almost all Benign. The report fills with noise. |
| Coding exons of one transcript | The parts that code for protein, plus a little intron on each side | Matches how diagnostic labs report panels | Misses variants deep in introns and in regulatory regions |

This repo uses coding exons because the report is meant to look like a diagnostic report. A gene can have many transcripts, so we also need to say which one. MANE Select is one transcript per protein-coding gene that NCBI (RefSeq) and EMBL-EBI (Ensembl) agreed on, identical in both databases and matched exactly to GRCh38. It is published as versioned files, so anyone can rebuild the same regions from the same release. The same transcript will be used later to describe variants (HGVS names), so the regions and the variant names agree.

**What this gives up:** Deep intronic variants, untranslated regions (UTRs) and promoters are not analysed. MANE Plus Clinical transcripts, which some genes need to describe all known pathogenic variants, are not included. [Check whether any panel gene has a MANE Plus Clinical transcript]

**Sources:**
- Morales J, et al. A joint NCBI and EMBL-EBI transcript set for clinical genomics and research. *Nature* 2022. https://doi.org/10.1038/s41586-022-04558-8
- MANE project. https://www.ncbi.nlm.nih.gov/refseq/MANE/

---

## D4. Padding: 25 bp into the introns

**Decision:** Each coding exon is extended by 25 bp on both sides.

**Why:** Variants just outside an exon can break splicing, so they belong in the analysis. The most conserved splice-site bases are the first two and last two bases of each intron, but nearby bases also matter. Published hereditary cancer panels extend exons by between 10 and 30 bp. 25 bp sits inside that range and covers the canonical splice sites with margin.

[Your note on first considering 50 bp, and why read length is a different question]

**What this gives up:** Splice variants deeper than 25 bp into the intron are missed.

**Sources:**
- Chan et al. Development and validation of next generation sequencing based 35-gene hereditary cancer panel. *Hered Cancer Clin Pract* 2020 (exons plus 20 bp). https://pmc.ncbi.nlm.nih.gov/articles/PMC7189534
- Invitae Common Hereditary Cancers Panel, FDA decision summary DEN210011 (10 to 20 bp)
- Labcorp VistaSeq Hereditary Cancer Panels technical summary (±20 bp for BRCA1 and BRCA2, ±10 bp for other genes)

---

## D5. Every downloaded file gets a timestamp and a record

**Decision:** Each external resource is saved with the UTC date and time of download in its file name, for example `clingen_gene_validity_20261107T0215Z.csv`. Next to it goes a small provenance file with the source URL, the download time, how it was obtained (by script or by hand), who downloaded it, the release or version when the source states one, and a checksum (SHA-256). Files downloaded by hand are registered with the same script, so every resource has the same kind of record.

**Why:** ClinVar changes every week, ClinGen re-curates genes, MANE has releases. A result is only reproducible if you know exactly which version of each resource produced it. The checksum proves the file wasn't changed after download.

**What this gives up:** A few extra files, and a step to remember when downloading by hand.

---

## D6. ClinVar: rename, cut to the panel, normalize

**Decision:** Before ClinVar is used, its contig names are changed from `17` to `chr17`, it is cut down to the panel regions, and its variants are normalized against the same reference FASTA as the sample.

**Why:**

- **Rename:** ClinVar writes chromosome 17 as `17`, our reference writes `chr17`. To bcftools these are different chromosomes, and nothing would match.
- **Cut to the panel:** ClinVar also contains variants on unplaced scaffolds, pieces of sequence the reference assembly couldn't place on a chromosome (names like `NT_113889.1`). Our reference, the GRCh38 "no-alt analysis set", leaves these out, so normalizing failed with `sequence "NT_113889.1" was not found`. We only annotate panel variants, so we keep only the panel.
- **Normalize:** The same variant can be written in more than one way, for example an indel in a repeat can be placed at several positions. Normalizing both ClinVar and the sample against the same FASTA writes each variant in one standard way, so matches are not missed.

**What this gives up:** Re-running with a different panel means rebuilding the ClinVar file.

---

## D7. Validation is a known-answer test

**Decision:** The pipeline compares its output with the GIAB truth set inside the panel and inside GIAB's trusted regions, and reports recall and precision.

**Why:** The input is the GIAB VCF itself, so this does not measure how good a variant caller is. It checks that the pipeline did not lose or change variants on the way. For HG002 the expected result is recall and precision of 1.0. For PatientA, the variants added on purpose should be the only extras.

**What this gives up:** No statement about calling accuracy. That needs reads, a caller and a genotype-aware comparison tool such as hap.py, which is on the roadmap.

**Sources:** [GIAB benchmark description]

---

## D8. Two real genomes, one synthetic patient

**Decision:** The pipeline uses three inputs, each with one job:

| Input | Who it is | Job in this project |
|---|---|---|
| HG002 | A man of Ashkenazi Jewish ancestry, from the GIAB family trio | Known-answer validation (D7), and one side of the ancestry comparison |
| HG00733 | A Puerto Rican individual from 1000 Genomes (Admixed American group) | The other side of the ancestry comparison. No validation, because no benchmark exists for this sample. |
| PatientA | Synthetic: HG002 plus a few ClinVar variants added on purpose | Demonstrating the report. Has a made-up clinical history, clearly labelled. |

**Why:** GIAB benchmarks exist only for Ashkenazi Jewish, European and Han Chinese genomes. HG00733 is one of the best-studied Latin American genomes: it has long-read data and has been used as a "silver-standard" sample because GIAB doesn't cover this ancestry. Running both genomes through the same pipeline and panels shows *how* reference data shapes interpretation: how many variants have a ClinVar classification, and how many people stand behind each gnomAD frequency.

Real genomes never get invented clinical stories. Only PatientA, which is synthetic, has a family history.

**What this gives up:** Two genomes show the mechanism, they do not measure a difference between groups. For the size of the effect, the write-up cites cohort studies instead [Caswell-Jin et al. 2018; Ndugga-Kabuye and Issaka 2019]. HG00733 is one person, and "Latin American" is not one population.

**Sources:**
- Lin et al. Improving variant calling using population data and deep learning. *BMC Bioinformatics* 2023 (HG00733 as a silver-standard sample). https://link.springer.com/article/10.1186/s12859-023-05294-0
- Caswell-Jin JL, et al. Racial/ethnic differences in multiple-gene sequencing results for hereditary cancer risk. *Genet Med* 2018.
- Ndugga-Kabuye MK, Issaka RB. Inequities in multi-gene hereditary cancer testing. *Fam Cancer* 2019. https://pmc.ncbi.nlm.nih.gov/articles/PMC6785397
- [Source for the HG00733 high-coverage VCF: to confirm]
