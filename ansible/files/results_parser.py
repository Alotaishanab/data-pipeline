#!/usr/bin/env python3
import sys
import os
import csv
import json
import logging
import statistics
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    if len(sys.argv) != 3:
        logging.error("Usage: python3 results_parser.py <OUTPUT_DIR> <SEARCH_FILE_PATH>")
        sys.exit(1)

    output_dir = sys.argv[1]
    search_file_path = sys.argv[2]

    if not os.path.isfile(search_file_path):
        logging.error(f"Error: File {search_file_path} not found.")
        sys.exit(1)

    # Extract the filename from the search file path
    search_filename = os.path.basename(search_file_path)

    # Extract the ID by removing '_search.tsv'
    if search_filename.endswith("_search.tsv"):
        id = search_filename[:-11]  # Remove '_search.tsv'
    else:
        id = os.path.splitext(search_filename)[0]

    try:
        with open(search_file_path, "r") as fhIn:
            reader = csv.reader(fhIn, delimiter='\t')
            header = next(reader, None)  # Skip header
            if header is None:
                logging.warning(f"No header found in {search_file_path}. Skipping parsing.")
                sys.exit(0)

            cath_ids = defaultdict(int)
            plDDT_values = []
            line_number = 1  # Starting after header

            for row in reader:
                line_number += 1
                if len(row) < 16:
                    logging.warning(f"Warning: Row {line_number} has insufficient columns.")
                    continue
                try:
                    plDDT = float(row[3])
                    plDDT_values.append(plDDT)
                except ValueError:
                    logging.warning(f"Warning: Invalid plDDT value on row {line_number}.")
                    continue
                try:
                    meta = row[15]
                    data = json.loads(meta)
                    cath_id = data.get("cath", "Unknown")
                    cath_ids[cath_id] += 1
                except (IndexError, json.JSONDecodeError):
                    logging.warning(f"Warning: Invalid metadata on row {line_number}. Content: {row[15] if len(row) > 15 else 'N/A'}")
                    logging.debug(f"Row content: {row}")
                    continue

        # Define the parsed file name
        parsed_filename = f"{id}.parsed"
        parsed_file_path = os.path.join(output_dir, parsed_filename)

        with open(parsed_file_path, "w", encoding="utf-8") as fhOut:
            if plDDT_values:
                mean_plddt = statistics.mean(plDDT_values)
                fhOut.write(f"#{search_filename} Results. mean plddt: {mean_plddt}\n")
            else:
                fhOut.write(f"#{search_filename} Results. mean plddt: 0\n")
            fhOut.write("cath_id,count\n")
            for cath, count in sorted(cath_ids.items()):
                fhOut.write(f"{cath},{count}\n")

        logging.info(f"Successfully parsed {search_filename} to {parsed_filename}")

    except FileNotFoundError:
        logging.error(f"Error: File {search_file_path} not found.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred while parsing {search_file_path}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
