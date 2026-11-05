#!/usr/bin/env python3
"""Turn bcftools isec output into a one-row validation table.

shared      variants in both the pipeline output and the truth set (TP)
query-only  variants only in the pipeline output (FP)
truth-only  variants only in the truth set (FN)
"""

import argparse
import sys

COLUMNS = ["sample", "tp", "fp", "fn", "recall", "precision"]


def count_records(path):
    with open(path) as handle:
        return sum(1 for line in handle if line.strip() and not line.startswith("#"))


def ratio(numerator, denominator):
    """Return a rounded ratio, or None when there is nothing to divide by."""
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def metrics(tp, fp, fn):
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "recall": ratio(tp, tp + fn),
        "precision": ratio(tp, tp + fp),
    }


def format_row(sample, values):
    cells = [sample] + [
        "NA" if values[c] is None else str(values[c]) for c in COLUMNS[1:]
    ]
    return "\t".join(cells)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--shared", required=True)
    parser.add_argument("--query-only", required=True)
    parser.add_argument("--truth-only", required=True)
    args = parser.parse_args(argv)

    values = metrics(
        tp=count_records(args.shared),
        fp=count_records(args.query_only),
        fn=count_records(args.truth_only),
    )
    print("\t".join(COLUMNS))
    print(format_row(args.sample, values))
    return 0


if __name__ == "__main__":
    sys.exit(main())
