#!/usr/bin/env python3
"""
Preprocess AML heatmap TSV files into a single compact per-gene JSON for IsoVis.

Usage:
    python3 tools/preprocess_heatmap.py \\
        static/aml_data.json.gz \\
        static/aml_data.txt.gz \\
        static/aml_data_short.txt.gz \\
        static/aml_heatmap.json.gz

Output format:
    {
      "cols": ["SRSF2-0203", "SRSF2-256006", ...],   // 71 sample names
      "genes": {                                        // normalised floats (3 dp)
        "ENSG00000123456": {
          "ENST00000000233": [1.234, 5.678, ...]
        }
      },
      "genes2": {                                       // integer counts
        "ENSG00000123456": {
          "ENST00000000233": [3339, 1418, ...]
        }
      }
    }

Values in the main file are rounded to 3 decimal places.
Only transcripts that appear in the gene JSON (aml_data.json.gz) are emitted.
"""

import sys
import gzip
import json
import argparse


def load_tx_to_gene(gene_json_path):
    """Build a transcript_id -> gene_id reverse mapping from the gene JSON."""
    print(f"Loading gene JSON from {gene_json_path} …", flush=True)
    open_fn = gzip.open if gene_json_path.endswith('.gz') else open
    with open_fn(gene_json_path, 'rt', encoding='utf-8') as fh:
        gene_data = json.load(fh)
    tx_to_gene = {}
    for gene_id, gene_obj in gene_data.items():
        for tx_id in gene_obj['transcripts']:
            tx_to_gene[tx_id] = gene_id
    print(f"  Loaded {len(tx_to_gene):,} transcripts across {len(gene_data):,} genes.", flush=True)
    return tx_to_gene


def parse_heatmap(path, tx_to_gene, round_values):
    """
    Read a heatmap TSV (transcript_ID + N sample cols) and return:
      - cols: list of sample names (without transcript_ID)
      - genes_dict: {gene_id: {tx_id: [val, ...]}}
    """
    print(f"Reading {path} …", flush=True)
    open_fn = gzip.open if path.endswith('.gz') else open

    genes_dict = {}
    cols = None
    line_count = 0
    kept = 0
    skipped = 0

    with open_fn(path, 'rt', encoding='utf-8', errors='replace') as fh:
        header = fh.readline().rstrip('\r\n').split('\t')
        # First column is transcript_ID, rest are sample names
        tx_col = 0
        cols = header[1:]   # 71 sample names

        for raw_line in fh:
            line_count += 1
            if line_count % 100_000 == 0:
                print(f"  {line_count:,} lines …", flush=True)

            parts = raw_line.rstrip('\r\n').split('\t')
            if len(parts) != len(header):
                skipped += 1
                continue

            tx_id = parts[tx_col].split('.')[0]   # strip version suffix
            gene_id = tx_to_gene.get(tx_id)
            if gene_id is None:
                skipped += 1
                continue

            if round_values:
                values = [round(float(v), 3) for v in parts[1:]]
            else:
                values = [int(float(v)) for v in parts[1:]]

            if gene_id not in genes_dict:
                genes_dict[gene_id] = {}
            genes_dict[gene_id][tx_id] = values
            kept += 1

    print(f"  Done: {line_count:,} rows, {kept:,} kept, {skipped:,} skipped.", flush=True)
    return cols, genes_dict


def main():
    parser = argparse.ArgumentParser(
        description='Preprocess AML heatmap TSVs into compact per-gene JSON for IsoVis'
    )
    parser.add_argument('gene_json', help='Precomputed gene JSON (aml_data.json.gz)')
    parser.add_argument('heatmap',   help='Main normalised heatmap TSV (aml_data.txt.gz)')
    parser.add_argument('heatmap2',  help='Integer counts heatmap TSV (aml_data_short.txt.gz)')
    parser.add_argument('output',    help='Output JSON file (.json or .json.gz)')
    args = parser.parse_args()

    tx_to_gene = load_tx_to_gene(args.gene_json)

    cols, genes = parse_heatmap(args.heatmap, tx_to_gene, round_values=True)
    cols2, genes2 = parse_heatmap(args.heatmap2, tx_to_gene, round_values=False)

    if cols != cols2:
        print("WARNING: column names differ between the two heatmap files!", file=sys.stderr)

    output = {"cols": cols, "genes": genes, "genes2": genes2}
    output_str = json.dumps(output, separators=(',', ':'))

    print(f"Writing {args.output} …", flush=True)
    if args.output.endswith('.gz'):
        with gzip.open(args.output, 'wt', encoding='utf-8', compresslevel=6) as fh:
            fh.write(output_str)
    else:
        with open(args.output, 'w', encoding='utf-8') as fh:
            fh.write(output_str)

    print(f"Done. {len(genes):,} genes in main heatmap, {len(genes2):,} in counts heatmap.")
    print(f"Output: {args.output}")


if __name__ == '__main__':
    main()
