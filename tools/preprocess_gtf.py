#!/usr/bin/env python3
"""
Preprocess a GTF file into a compact per-gene JSON for IsoVis.

The output JSON is organised by gene ID and contains only the data IsoVis
needs (exon and CDS coordinates per transcript), eliminating the need to
decompress and scan the full GTF on every page load.

Usage:
    python preprocess_gtf.py input.gtf[.gz] output.json[.gz]

Output format:
    {
      "GENE_ID": {
        "chr": "chr1",
        "transcripts": {
          "TX_ID": {
            "strand": "+",
            "exons": [[start, end], ...],
            "cds":   [[start, end], ...]   // omitted when empty
          }
        }
      }
    }

Gene IDs are stored uppercase to match IsoVis case-insensitive lookup.
Ensembl version suffixes (e.g. ".3") are stripped from gene and transcript
IDs unless the source column contains "stringtie".
"""

import sys
import gzip
import json
import argparse


def parse_attributes(attr_str):
    """Parse a GTF attributes column into a dict."""
    attrs = {}
    for entry in attr_str.split(';'):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(' ', 1)
        if len(parts) < 2:
            continue
        key = parts[0].lower()
        val = parts[1].strip('"').strip()
        attrs[key] = val
    return attrs


def strip_version(id_str):
    """Remove Ensembl version suffix (e.g. 'ENSG00000001.4' → 'ENSG00000001')."""
    dot = id_str.find('.')
    return id_str[:dot] if dot != -1 else id_str


def main():
    parser = argparse.ArgumentParser(
        description='Preprocess a GTF to compact per-gene JSON for IsoVis'
    )
    parser.add_argument('input',  help='Input GTF file (.gtf or .gtf.gz)')
    parser.add_argument('output', help='Output JSON file (.json or .json.gz)')
    args = parser.parse_args()

    # gene_id  ->  { "chr": str, "transcripts": { tx_id: {"strand": str, "exons": [], "cds": []} } }
    genes = {}
    # tx_id -> gene_id  (needed to attach CDS lines to the right gene)
    tx_to_gene = {}

    open_fn = gzip.open if args.input.endswith('.gz') else open

    print(f"Reading {args.input} …", flush=True)
    line_count = 0
    exon_count = 0
    cds_count  = 0

    with open_fn(args.input, 'rt', encoding='utf-8', errors='replace') as fh:
        for raw_line in fh:
            line_count += 1
            if line_count % 500_000 == 0:
                print(f"  {line_count:,} lines processed, {len(genes):,} genes so far …", flush=True)

            line = raw_line.rstrip('\r\n')
            if not line or line.startswith('#'):
                continue

            cols = line.split('\t')
            if len(cols) < 9:
                continue

            feature = cols[2].strip()
            if feature not in ('exon', 'CDS'):
                continue

            try:
                start = int(cols[3])
                end   = int(cols[4])
            except ValueError:
                continue

            strand = cols[6].strip()
            if strand not in ('+', '-'):
                continue

            chrom      = cols[0].strip()
            source     = cols[1].strip()
            is_stringtie = 'stringtie' in source.lower()

            attrs = parse_attributes(cols[8])

            gene_id = attrs.get('gene_id', '').strip()
            tx_id   = attrs.get('transcript_id', '').strip()
            if not gene_id or not tx_id:
                continue

            # Strip version numbers (skip for StringTie, which uses them as IDs)
            if not is_stringtie:
                gene_id = strip_version(gene_id)
                tx_id   = strip_version(tx_id)

            gene_id = gene_id.upper()

            if feature == 'exon':
                exon_count += 1

                if gene_id not in genes:
                    genes[gene_id] = {'chr': chrom, 'transcripts': {}}

                gene = genes[gene_id]

                if tx_id not in gene['transcripts']:
                    gene['transcripts'][tx_id] = {'strand': strand, 'exons': [], 'cds': []}
                    tx_to_gene[tx_id] = gene_id

                gene['transcripts'][tx_id]['exons'].append([start, end])

            else:  # CDS
                cds_count += 1

                # Look up the gene via the transcript index
                gid = tx_to_gene.get(tx_id)
                if gid is None:
                    continue

                tx_data = genes[gid]['transcripts'].get(tx_id)
                if tx_data is None:
                    continue

                tx_data['cds'].append([start, end])

    print(f"Finished reading: {line_count:,} lines, {exon_count:,} exons, "
          f"{cds_count:,} CDS, {len(genes):,} genes.", flush=True)

    # Post-process: sort exons/CDS by start, remove empty cds lists
    for gene_data in genes.values():
        for tx_data in gene_data['transcripts'].values():
            tx_data['exons'].sort(key=lambda x: x[0])
            if tx_data['cds']:
                tx_data['cds'].sort(key=lambda x: x[0])
            else:
                del tx_data['cds']

    print(f"Writing {args.output} …", flush=True)
    output_str = json.dumps(genes, separators=(',', ':'))

    if args.output.endswith('.gz'):
        with gzip.open(args.output, 'wt', encoding='utf-8', compresslevel=6) as fh:
            fh.write(output_str)
    else:
        with open(args.output, 'w', encoding='utf-8') as fh:
            fh.write(output_str)

    print(f"Done. Wrote {len(genes):,} genes to {args.output}.")


if __name__ == '__main__':
    main()
