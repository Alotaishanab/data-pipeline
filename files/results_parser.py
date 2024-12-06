import sys
import csv
import json
from collections import defaultdict
import statistics
import os

def main():
    if len(sys.argv) != 3:
        print("Usage: results_parser.py <output_directory> <search_file_path>")
        sys.exit(1)

    output_dir = sys.argv[1]
    search_file_path = sys.argv[2]

    # Extract the filename from the search file path
    search_filename = os.path.basename(search_file_path)

    # Use the absolute search file path directly
    full_search_path = search_file_path

    try:
        with open(full_search_path, "r") as fhIn:
            next(fhIn)  # Skip header
            msreader = csv.reader(fhIn, delimiter='\t')
            tot_entries = 0
            cath_ids = defaultdict(int)
            plDDT_values = []

            for i, row in enumerate(msreader):
                tot_entries = i + 1
                plDDT_values.append(float(row[3]))
                meta = row[15]
                data = json.loads(meta)
                cath_ids[data["cath"]] += 1

        # Define the parsed file name
        parsed_filename = search_filename.replace('_search.tsv', '.parsed')
        parsed_file_path = os.path.join(output_dir, parsed_filename)

        with open(parsed_file_path, "w", encoding="utf-8") as fhOut:
            if plDDT_values:
                mean_plDDT = statistics.mean(plDDT_values)
                fhOut.write(f"#{search_filename} Results. mean plddt: {mean_plDDT}\n")
            else:
                fhOut.write(f"#{search_filename} Results. mean plddt: 0\n")
            fhOut.write("cath_id,count\n")
            for cath, count in cath_ids.items():
                fhOut.write(f"{cath},{count}\n")

        print(f"Successfully parsed {search_filename} to {parsed_filename}")

    except FileNotFoundError:
        print(f"Error: File {full_search_path} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
