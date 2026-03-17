#!/usr/bin/env python3
"""
Preprocess a SQANTI3 classification file into compact per-transcript JSON for IsoVis.

Usage:
    python3 tools/preprocess_sqanti.py input.txt output.json.gz [filter.json.gz]

The optional filter argument is a precomputed gene JSON (e.g. aml_data.json.gz).
When provided, only transcripts present in that file are emitted.

Output format:
    {
      "cats": ["antisense", "full-splice_match", ...],
      "data": {
        "ENST00000016171": [1, 2356, 9, 410, 0],
        "ENST00000002501": [2, 893, 4, null, 0]
      }
    }

Each data array is [cat_index, length, exons, orf_length_or_null, nmd_0_or_1].

Column indices (0-based) in the SQANTI TSV:
    0  isoform
    3  length
    4  exons
    5  structural_category
    30 ORF_length
    36 predicted_NMD
"""

import sys
import gzip
import json
import argparse


def load_filter_set(path):
    """Return set of transcript IDs present in a precomputed gene JSON."""
    print(f"Loading filter set from {path} …", flush=True)
    open_fn = gzip.open if path.endswith('.gz') else open
    with open_fn(path, 'rt', encoding='utf-8') as fh:
        gene_data = json.load(fh)
    tx_ids = set()
    for gene in gene_data.values():
        tx_ids.update(gene['transcripts'].keys())
    print(f"  Filter set: {len(tx_ids):,} transcripts.", flush=True)
    return tx_ids


def main():
    parser = argparse.ArgumentParser(
        description='Preprocess a SQANTI3 classification file to compact JSON for IsoVis'
    )
    parser.add_argument('input',  help='Input TSV file (SQANTI3 classification)')
    parser.add_argument('output', help='Output JSON file (.json or .json.gz)')
    parser.add_argument('filter', nargs='?', default=None,
                        help='Optional precomputed gene JSON to filter transcripts (e.g. aml_data.json.gz)')
    args = parser.parse_args()

    filter_set = load_filter_set(args.filter) if args.filter else None

    # First pass: collect all structural categories in filtered set to build index
    open_fn = gzip.open if args.input.endswith('.gz') else open
    print(f"Reading {args.input} …", flush=True)

    rows = []       # (isoform, length, exons, sc, orf, nmd)
    line_count = 0
    skipped = 0
    cat_set = set()

    with open_fn(args.input, 'rt', encoding='utf-8', errors='replace') as fh:
        fh.readline()  # skip header
        for raw_line in fh:
            line_count += 1
            if line_count % 100_000 == 0:
                print(f"  {line_count:,} lines processed, {len(rows):,} kept …", flush=True)

            cols = raw_line.rstrip('\r\n').split('\t')
            if len(cols) <= 36:
                skipped += 1
                continue

            isoform = cols[0].strip()
            if not isoform:
                skipped += 1
                continue

            if filter_set is not None and isoform not in filter_set:
                continue

            try:
                length = int(cols[3])
                exons  = int(cols[4])
            except ValueError:
                skipped += 1
                continue

            sc      = cols[5].strip()
            orf_raw = cols[30].strip()
            orf     = None if orf_raw in ('NA', '') else int(float(orf_raw))
            nmd     = 1 if cols[36].strip().upper() == 'TRUE' else 0

            cat_set.add(sc)
            rows.append((isoform, length, exons, sc, orf, nmd))

    print(f"Finished reading: {line_count:,} lines total, {len(rows):,} kept, "
          f"{skipped:,} skipped.", flush=True)

    cats = sorted(cat_set)
    cat_index = {c: i for i, c in enumerate(cats)}
    print(f"Structural categories ({len(cats)}): {cats}", flush=True)

    data = {isoform: [cat_index[sc], length, exons, orf, nmd]
            for isoform, length, exons, sc, orf, nmd in rows}

    output = {"cats": cats, "data": data}
    output_str = json.dumps(output, separators=(',', ':'))

    print(f"Writing {args.output} …", flush=True)
    if args.output.endswith('.gz'):
        with gzip.open(args.output, 'wt', encoding='utf-8', compresslevel=6) as fh:
            fh.write(output_str)
    else:
        with open(args.output, 'w', encoding='utf-8') as fh:
            fh.write(output_str)

    print(f"Done. Wrote {len(data):,} transcripts to {args.output}.")


if __name__ == '__main__':
    main()
