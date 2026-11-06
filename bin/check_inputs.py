#!/usr/bin/env python3
"""Stop the pipeline early if inputs are not on the expected genome build.

Checks:
- contig lengths in the sample VCF header and the FASTA index match the
  expected build (GRCh38 by default)
- contig names in resource files (ClinVar, gnomAD) use the same naming style
- the sample VCF holds exactly one sample, with the expected name

Exits with status 1 and a readable message on any problem.
"""

import argparse
import re
import sys

CONTIG_RE = re.compile(r"^##contig=<ID=([^,>]+)(?:,.*?length=(\d+))?")


def read_lines(path):
    with open(path) as handle:
        return [line.rstrip("\n") for line in handle]


def load_lengths(lines):
    """Parse 'name<TAB>length' lines, skipping comments. Works for .fai too."""
    lengths = {}
    for line in lines:
        if line and not line.startswith("#"):
            fields = line.split("\t")
            lengths[fields[0]] = int(fields[1])
    return lengths


def header_contigs(header_lines):
    """Return {contig: length} from ##contig lines (length None if absent)."""
    contigs = {}
    for line in header_lines:
        match = CONTIG_RE.match(line)
        if match:
            length = match.group(2)
            contigs[match.group(1)] = int(length) if length else None
    return contigs


def header_samples(header_lines):
    for line in header_lines:
        if line.startswith("#CHROM"):
            return line.split("\t")[9:]
    return []


def naming_problem(name, expected):
    """Explain a contig name that is a renamed version of an expected one."""
    if name not in expected and f"chr{name}" in expected:
        return f"contig '{name}' should be 'chr{name}' (chr prefix missing)"
    if name.startswith("chr") and name not in expected and name[3:] in expected:
        return f"contig '{name}' should be '{name[3:]}' (unexpected chr prefix)"
    return None


def length_problems(source, found, expected):
    problems = []
    for name, length in found.items():
        renamed = naming_problem(name, expected)
        if renamed:
            problems.append(f"{source}: {renamed}")
        elif name in expected and length is not None and length != expected[name]:
            problems.append(
                f"{source}: {name} has length {length}, expected {expected[name]} "
                "(wrong genome build?)"
            )
    if not any(name in expected for name in found):
        problems.append(f"{source}: no expected contigs found, build unknown")
    return problems


def name_problems(source, names, expected):
    problems = []
    for name in names:
        renamed = naming_problem(name, expected)
        if renamed:
            problems.append(f"{source}: {renamed}")
    if names and not any(name in expected for name in names):
        problems.append(f"{source}: no expected contig names found")
    return problems


def sample_problems(samples, sample):
    if samples != [sample]:
        return [f"sample VCF: expected one sample '{sample}', found {samples}"]
    return []


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--header", required=True, help="sample VCF header text")
    parser.add_argument("--sample", required=True, help="expected sample name")
    parser.add_argument("--expected", required=True, help="contig<TAB>length table")
    parser.add_argument("--fai", help="FASTA index (.fai) of the reference")
    parser.add_argument(
        "--names", nargs="*", default=[], help="files with one contig name per line"
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    expected = load_lengths(read_lines(args.expected))
    header = read_lines(args.header)

    problems = length_problems("sample VCF", header_contigs(header), expected)
    problems += sample_problems(header_samples(header), args.sample)
    if args.fai:
        fai = load_lengths(read_lines(args.fai))
        problems += length_problems("reference FASTA", fai, expected)
    for path in args.names:
        problems += name_problems(path, [n for n in read_lines(path) if n], expected)

    for problem in problems:
        print(f"FAIL {problem}", file=sys.stderr)
    if problems:
        return 1
    print("PASS all inputs match the expected build and contig names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
