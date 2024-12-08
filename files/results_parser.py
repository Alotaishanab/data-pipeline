import sys
import csv
import json
from collections import defaultdict
import statistics
import os

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 results_parser.py <OUTPUT_DIR> <SEARCH_FILE_PATH>")
        sys.exit(1)

    output_dir = sys.argv[1]
    search_file_path = sys.argv[2]

    if not os.path.isfile(search_file_path):
        print(f"Error: File {search_file_path} not found.")
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
            next(fhIn)  # Skip header
            msreader = csv.reader(fhIn, delimiter='\t')
            tot_entries = 0
            cath_ids = defaultdict(int)
            plDDT_values = []

            for i, row in enumerate(msreader):
                if len(row) < 16:
                    print(f"Warning: Row {i+2} has insufficient columns.")
                    continue
                tot_entries = i + 1
                try:
                    plDDT = float(row[3])
                    plDDT_values.append(plDDT)
                except ValueError:
                    print(f"Warning: Invalid plDDT value on row {i+2}.")
                    continue
                try:
                    meta = row[15]
                    data = json.loads(meta)
                    cath_id = data.get("cath", "Unknown")
                    cath_ids[cath_id] += 1
                except (IndexError, json.JSONDecodeError):
                    print(f"Warning: Invalid metadata on row {i+2}.")
                    continue

        # Define the parsed file name
        parsed_filename = f"{id}.parsed"
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
        print(f"Error: File {search_file_path} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
