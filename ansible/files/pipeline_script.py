#!/usr/bin/env python3
import sys
from subprocess import Popen, PIPE
import os
import shutil
import csv
import json
from collections import defaultdict
import statistics
import glob

"""
Usage: python3 pipeline_script.py [PDB_FILE] [OUTPUT_DIR] [ORGANISM]
Example: python3 pipeline_script.py /mnt/datasets/test/test.pdb /mnt/results/test/ test
"""

VIRTUALENV_PYTHON = '/opt/merizo_search/merizosearch_env/bin/python3'

def run_parser(search_file, output_dir):
    print(f"Search File: {search_file}")
    print(f"Output Directory: {output_dir}")
    parser_script = '/opt/data_pipeline/results_parser.py'
    cmd = [VIRTUALENV_PYTHON, parser_script, output_dir, search_file]
    print(f'STEP 2: RUNNING PARSER: {" ".join(cmd)}')
    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if out:
            print(f"PARSER STDOUT:\n{out.decode('utf-8')}")
        if err:
            print(f"PARSER STDERR:\n{err.decode('utf-8')}")
        if p.returncode != 0:
            raise RuntimeError("Parser encountered an error.")
    except Exception as e:
        print(f"Error during Parsing: {e}")
        raise

def run_merizo_search(pdb_file, output_dir, id, database_path):
    print(f"Checking if VIRTUALENV_PYTHON exists: {os.path.exists(VIRTUALENV_PYTHON)}")
    print(f"VIRTUALENV_PYTHON is executable: {os.access(VIRTUALENV_PYTHON, os.X_OK)}")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Using output directory: {output_dir}")
    merizo_script = '/opt/merizo_search/merizo_search/merizo.py'
    tmp_dir = os.path.join(output_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    print(f"Using tmp directory: {tmp_dir}")
    cmd = [
        VIRTUALENV_PYTHON, merizo_script, 'easy-search',
        pdb_file, database_path, output_dir, tmp_dir,
        '--iterate', '--output_headers', '-d', 'cpu', '--threads', '1'
    ]
    print(f'STEP 1: RUNNING MERIZO: {" ".join(cmd)}')
    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if out:
            print(f"MERIZO STDOUT:\n{out.decode('utf-8')}")
        if err:
            print(f"MERIZO STDERR:\n{err.decode('utf-8')}")
        if p.returncode != 0:
            raise RuntimeError("Merizo Search encountered an error.")
        old_search = os.path.join(output_dir, "_search.tsv")
        new_search = os.path.join(output_dir, f"{id}_search.tsv")
        if os.path.isfile(old_search):
            os.rename(old_search, new_search)
            print(f"Renamed '_search.tsv' to '{new_search}'")
        else:
            print(f"No hits found for {pdb_file}. Skipping parsing.")
            return None
        old_segment = os.path.join(output_dir, "_segment.tsv")
        new_segment = os.path.join(output_dir, f"{id}_segment.tsv")
        if os.path.isfile(old_segment):
            os.rename(old_segment, new_segment)
            print(f"Renamed '_segment.tsv' to '{new_segment}'")
        else:
            raise FileNotFoundError(f"Error: '_segment.tsv' not found in {output_dir}")
        return new_search
    except Exception as e:
        print(f"Error during Merizo Search: {e}")
        raise

def pipeline(pdb_file, output_dir, organism):
    search_file = run_merizo_search(
        pdb_file, output_dir,
        id=os.path.splitext(os.path.basename(pdb_file))[0],
        database_path='/home/almalinux/merizo_search/examples/database/cath-4.3-foldclassdb'
    )
    if search_file:
        run_parser(search_file, output_dir)
    else:
        print(f"No search results to parse for {pdb_file}.")
    tmp_dir = os.path.join(output_dir, "tmp")
    if os.path.exists(tmp_dir):
        try:
            shutil.rmtree(tmp_dir)
            print(f"Temporary directory '{tmp_dir}' has been removed.")
        except Exception as e:
            print(f"Error removing temporary directory '{tmp_dir}': {e}")
    else:
        print(f"Temporary directory '{tmp_dir}' does not exist. No cleanup needed.")

def aggregate_results(output_dir, organism):
    print(f"Aggregating results for {organism}...")
    cath_counts = defaultdict(int)
    plDDT_values = []
    parsed_files = glob.glob(os.path.join(output_dir, "*.parsed"))
    for parsed_file in parsed_files:
        try:
            with open(parsed_file, "r") as pf:
                reader = csv.reader(pf)
                header = next(reader)  # Skip header line
                for row in reader:
                    if len(row) != 2:
                        print(f"Warning: Invalid row format in {parsed_file}: {row}")
                        continue
                    cath_id, count_str = row
                    try:
                        cath_counts[cath_id] += int(count_str)
                    except ValueError:
                        print(f"Warning: Non-numeric count '{count_str}' in {parsed_file}")
                        continue
                pf.seek(0)
                first_line = pf.readline().strip()
                if first_line.startswith("#"):
                    parts = first_line.split("mean plddt:")
                    if len(parts) == 2:
                        mean_plddt = float(parts[1])
                        plDDT_values.append(mean_plddt)
        except Exception as e:
            print(f"Error processing {parsed_file}: {e}")
            continue
    cath_summary_file = os.path.join(output_dir, f"{organism}_cath_summary.csv")
    with open(cath_summary_file, "w", newline='', encoding="utf-8") as csf:
        writer = csv.writer(csf)
        writer.writerow(["cath_id", "count"])
        for cath, count_val in sorted(cath_counts.items()):
            writer.writerow([cath, count_val])
    print(f"Generated {cath_summary_file}")
    if plDDT_values:
        mean_plDDT = statistics.mean(plDDT_values)
        std_dev_plDDT = statistics.stdev(plDDT_values) if len(plDDT_values) > 1 else 0.0
    else:
        mean_plDDT, std_dev_plDDT = 0.0, 0.0
    plddt_means_file = os.path.join(output_dir, "plDDT_means.csv")
    with open(plddt_means_file, "a", newline='', encoding="utf-8") as pmf:
        writer = csv.writer(pmf)
        if pmf.tell() == 0:
            writer.writerow(["Organism", "Mean_plDDT", "StdDev_plDDT"])
        writer.writerow([organism.capitalize(), mean_plDDT, std_dev_plDDT])
    print(f"Updated {plddt_means_file}")

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 pipeline_script.py <PDB_FILE> <OUTPUT_DIR> <ORGANISM>")
        print("Example: python3 pipeline_script.py /mnt/datasets/test/test.pdb /mnt/results/test/ test")
        sys.exit(1)
    pdb_file = sys.argv[1]
    output_dir = sys.argv[2]
    organism = sys.argv[3].lower()
    if organism not in ["human", "ecoli", "test"]:
        print("Error: ORGANISM must be either 'human', 'ecoli', or 'test'")
        sys.exit(1)
    if not os.path.isfile(pdb_file):
        print(f"No PDB file found: {pdb_file}")
        sys.exit(1)
    pipeline(pdb_file, output_dir, organism)
    aggregate_results(output_dir, organism)

if __name__ == "__main__":
    main()
