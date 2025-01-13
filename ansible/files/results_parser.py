#!/usr/bin/env python3
import sys
import os
import csv
import json
import logging
import statistics
from collections import defaultdict

# Configure logging to display warnings and errors only
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    # Ensure the correct number of arguments are provided
    if len(sys.argv) != 3:
        logging.error("Usage: python3 results_parser.py <OUTPUT_DIR> <SEARCH_FILE_PATH>")
        sys.exit(1)

    # Extract command-line arguments
    output_dir = sys.argv[1]
    search_file_path = sys.argv[2]

    # Check if the provided search file exists
    if not os.path.isfile(search_file_path):
        logging.error(f"Search file missing: {search_file_path}")
        sys.exit(1)

    # Extract the filename and determine the base identifier
    search_filename = os.path.basename(search_file_path)
    if search_filename.endswith("_search.tsv"):
        file_id = search_filename[:-11]  # Remove "_search.tsv" to get the base ID
    else:
        file_id = os.path.splitext(search_filename)[0]

    # Initialize storage for CATH IDs and plDDT values
    cath_ids = defaultdict(int)  # Count occurrences of each CATH ID
    plDDT_values = []  # Store pLDDT values for statistical analysis
    line_count = 1  # Track the current line number for error reporting

    try:
        # Open the search file and read its contents
        with open(search_file_path, "r") as fh:
            reader = csv.reader(fh, delimiter='\t')  # Use tab-delimited parsing
            header = next(reader, None)  # Read the header row
            if not header:
                logging.warning(f"No header in {search_file_path}. Exiting parser.")
                sys.exit(0)

            # Process each row in the search file
            for row in reader:
                line_count += 1
                if len(row) < 16:  # Check if the row has the expected number of columns
                    logging.warning(f"Row {line_count}: incomplete columns.")
                    continue

                # Extract and validate the pLDDT value
                try:
                    plddt = float(row[3])
                    plDDT_values.append(plddt)
                except ValueError:
                    logging.warning(f"Row {line_count}: invalid pLDDT.")
                    continue

                # Parse JSON metadata and count CATH IDs
                try:
                    meta = row[15]  # Metadata column
                    data = json.loads(meta)  # Parse JSON string
                    cath_id = data.get("cath", "Unknown")  # Extract CATH ID or use "Unknown"
                    cath_ids[cath_id] += 1  # Increment count for this CATH ID
                except Exception as e:
                    logging.warning(f"Row {line_count}: JSON error => {e}")
                    continue

        # Generate the output file name and path
        parsed_name = f"{file_id}.parsed"
        parsed_path = os.path.join(output_dir, parsed_name)

        # Write parsed results to the output file
        with open(parsed_path, "w", encoding="utf-8") as outfh:
            # Write the mean pLDDT value
            if plDDT_values:
                mean_plddt = statistics.mean(plDDT_values)
                outfh.write(f"#{search_filename} Results. mean plddt: {mean_plddt}\n")
            else:
                outfh.write(f"#{search_filename} Results. mean plddt: 0\n")

            # Write CATH ID counts
            outfh.write("cath_id,count\n")
            for c_id, ct in sorted(cath_ids.items()):
                outfh.write(f"{c_id},{ct}\n")

        logging.warning(f"Parser wrote {parsed_name} in {output_dir}.")

    except Exception as e:
        # Handle any unexpected errors during parsing
        logging.error(f"Parsing error on {search_file_path}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
