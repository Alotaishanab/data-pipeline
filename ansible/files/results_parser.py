#!/usr/bin/env python3
import sys
import os
import csv
import json
import logging
import statistics
from collections import defaultdict

# Keep logging minimal
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    if len(sys.argv) != 3:
        logging.error("Usage: python3 results_parser.py <OUTPUT_DIR> <SEARCH_FILE_PATH>")
        sys.exit(1)

    output_dir = sys.argv[1]
    search_file_path = sys.argv[2]

    if not os.path.isfile(search_file_path):
        logging.error(f"Search file missing: {search_file_path}")
        sys.exit(1)

    search_filename = os.path.basename(search_file_path)
    if search_filename.endswith("_search.tsv"):
        file_id = search_filename[:-11]  # remove "_search.tsv"
    else:
        file_id = os.path.splitext(search_filename)[0]

    cath_ids = defaultdict(int)
    plDDT_values = []
    line_count = 1

    try:
        with open(search_file_path, "r") as fh:
            reader = csv.reader(fh, delimiter='\t')
            header = next(reader, None)
            if not header:
                logging.warning(f"No header in {search_file_path}. Exiting parser.")
                sys.exit(0)

            for row in reader:
                line_count += 1
                if len(row) < 16:
                    logging.warning(f"Row {line_count}: incomplete columns.")
                    continue
                try:
                    plddt = float(row[3])
                    plDDT_values.append(plddt)
                except ValueError:
                    logging.warning(f"Row {line_count}: invalid pLDDT.")
                    continue

                try:
                    meta = row[15]
                    data = json.loads(meta)
                    cath_id = data.get("cath", "Unknown")
                    cath_ids[cath_id] += 1
                except Exception as e:
                    logging.warning(f"Row {line_count}: JSON error => {e}")
                    continue

        parsed_name = f"{file_id}.parsed"
        parsed_path = os.path.join(output_dir, parsed_name)

        with open(parsed_path, "w", encoding="utf-8") as outfh:
            if plDDT_values:
                mean_plddt = statistics.mean(plDDT_values)
                outfh.write(f"#{search_filename} Results. mean plddt: {mean_plddt}\n")
            else:
                outfh.write(f"#{search_filename} Results. mean plddt: 0\n")

            outfh.write("cath_id,count\n")
            for c_id, ct in sorted(cath_ids.items()):
                outfh.write(f"{c_id},{ct}\n")

        logging.warning(f"Parser wrote {parsed_name} in {output_dir}.")

    except Exception as e:
        logging.error(f"Parsing error on {search_file_path}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
