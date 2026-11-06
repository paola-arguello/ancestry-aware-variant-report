#!/usr/bin/env python3
"""Build the panel BED from a gene list, using the Ensembl REST API.

Each gene becomes one region spanning the full gene (introns included),
optionally padded. Coordinates are GRCh38, written as 0-based BED with
UCSC-style contig names (chr17, not 17). A provenance file records the
Ensembl release and the date of the lookup.

Usage:
    python scripts/make_panel_bed.py assets/panel_genes.txt data/panel.bed
"""

import argparse
import datetime
import json
import sys
import time
import urllib.error
import urllib.request

ENSEMBL = "https://rest.ensembl.org"


def read_genes(path):
    with open(path) as handle:
        lines = [line.strip() for line in handle]
    return [line for line in lines if line and not line.startswith("#")]


RETRY_CODES = {429, 500, 502, 503, 504}


def get_json(url, opener=urllib.request.urlopen, tries=5, wait=10, sleep=time.sleep):
    """Fetch JSON, waiting and retrying when the server is busy or down."""
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    for attempt in range(1, tries + 1):
        try:
            with opener(request) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in RETRY_CODES or attempt == tries:
                raise
            print(f"Ensembl returned {error.code}, retry {attempt} in {wait} s")
            sleep(wait)
            wait *= 2


def lookup_gene(symbol, opener=urllib.request.urlopen):
    return get_json(f"{ENSEMBL}/lookup/symbol/homo_sapiens/{symbol}", opener)


def ensembl_release(opener=urllib.request.urlopen):
    return get_json(f"{ENSEMBL}/info/data", opener)["releases"][0]


def bed_record(gene, symbol, pad=0):
    """Turn an Ensembl lookup result into (chrom, start, end, name)."""
    if gene.get("assembly_name") != "GRCh38":
        raise ValueError(f"{symbol}: assembly is {gene.get('assembly_name')}")
    start = max(gene["start"] - 1 - pad, 0)  # Ensembl is 1-based, BED is 0-based
    return (f"chr{gene['seq_region_name']}", start, gene["end"] + pad, symbol)


def merge_records(records):
    """Sort regions and merge any that overlap, so no variant is output twice."""
    merged = []
    for chrom, start, end, name in sorted(records):
        if merged and merged[-1][0] == chrom and start <= merged[-1][2]:
            last = merged.pop()
            merged.append((chrom, last[1], max(end, last[2]), f"{last[3]};{name}"))
        else:
            merged.append((chrom, start, end, name))
    return merged


def write_bed(records, path):
    with open(path, "w") as handle:
        for chrom, start, end, name in records:
            handle.write(f"{chrom}\t{start}\t{end}\t{name}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("genes")
    parser.add_argument("bed")
    parser.add_argument("--pad", type=int, default=0)
    args = parser.parse_args(argv)

    symbols = read_genes(args.genes)
    records = []
    for symbol in symbols:
        records.append(bed_record(lookup_gene(symbol), symbol, args.pad))
        time.sleep(0.2)  # stay well under Ensembl's rate limit
    write_bed(merge_records(records), args.bed)

    with open(args.bed + ".provenance.txt", "w") as handle:
        handle.write(f"source\tEnsembl REST {ENSEMBL}\n")
        handle.write(f"ensembl_release\t{ensembl_release()}\n")
        handle.write(f"date\t{datetime.date.today().isoformat()}\n")
        handle.write(f"padding_bp\t{args.pad}\n")
        handle.write(f"genes\t{','.join(symbols)}\n")
    print(f"Wrote {len(records)} genes to {args.bed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
