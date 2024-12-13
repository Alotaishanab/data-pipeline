# /opt/data_pipeline/pipeline_script.py

import sys
from subprocess import Popen, PIPE
import glob
import os
import shutil
import csv
import json
from collections import defaultdict
import statistics

"""
Usage: python3 pipeline_script.py [INPUT_DIR] [OUTPUT_DIR] [ORGANISM]
Example: python3 pipeline_script.py /mnt/datasets/human_input/ /mnt/results/human/ human
"""

# Path to the virtual environment's Python executable
VIRTUALENV_PYTHON = '/opt/merizo_search/merizosearch_env/bin/python3'

def run_parser(search_file, output_dir):
    """
    Run the results_parser.py over the search file to produce the output summary
    """
    print(f"Search File: {search_file}")
    print(f"Output Directory: {output_dir}")
    
    # Path to results_parser.py
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

def run_merizo_search(input_file, output_dir, id, database_path):
    """
    Runs the Merizo Search domain predictor to produce domains
    """
    # Ensure output_dir exists
    os.makedirs(output_dir, exist_ok=True)
    print(f"Using output directory: {output_dir}")
    
    # Path to merizo.py using symbolic links
    merizo_script = '/opt/merizo_search/merizo_search/merizo.py'
    
    # Define tmp_dir inside output_dir
    tmp_dir = os.path.join(output_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    print(f"Using tmp directory: {tmp_dir}")
    
    cmd = [
        VIRTUALENV_PYTHON,
        merizo_script,
        'easy-search',
        input_file,        # Pass individual file
        database_path,     # Use symlink path
        output_dir,        # Output directory: e.g., /mnt/results/human/
        tmp_dir,           # Temporary directory: e.g., /mnt/results/human/tmp/
        '--iterate',
        '--output_headers',
        '-d',
        'cpu',
        '--threads',
        '1'
    ]
    print(f'STEP 1: RUNNING MERIZO: {" ".join(cmd)}')
    
    try:
        # Run merizo.py
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        
        if out:
            print(f"MERIZO STDOUT:\n{out.decode('utf-8')}")
        if err:
            print(f"MERIZO STDERR:\n{err.decode('utf-8')}")
        if p.returncode != 0:
            raise RuntimeError("Merizo Search encountered an error.")
        
        # Rename _search.tsv to <id>_search.tsv
        old_search = os.path.join(output_dir, "_search.tsv")
        new_search = os.path.join(output_dir, f"{id}_search.tsv")
        if os.path.isfile(old_search):
            os.rename(old_search, new_search)
            print(f"Renamed '_search.tsv' to '{new_search}'")
        else:
            raise FileNotFoundError(f"Error: '_search.tsv' not found in {output_dir}")
        
        # Similarly, rename _segment.tsv to <id>_segment.tsv
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

def read_dir(input_dir):
    """
    Reads all PDB files in the input directory
    """
    print("Getting file list")
    file_ids = glob.glob(os.path.join(input_dir, "*.pdb"))
    analysis_files = []
    for file_path in file_ids:
        id = os.path.splitext(os.path.basename(file_path))[0]
        analysis_files.append([file_path, id, sys.argv[2]])
    return analysis_files

def pipeline(filepath, id, outpath):
    # STEP 1: Run Merizo Search
    search_file = run_merizo_search(filepath, outpath, id, database_path='/home/almalinux/merizo_search/examples/database/cath-4.3-foldclassdb')
    
    # STEP 2: Run Parser on the generated search file
    run_parser(search_file, outpath)
    
    # STEP 3: Clean up temporary files
    tmp_dir = os.path.join(outpath, "tmp")
    if os.path.exists(tmp_dir):
        try:
            shutil.rmtree(tmp_dir)
            print(f"Temporary directory '{tmp_dir}' has been removed.")
        except Exception as e:
            print(f"Error removing temporary directory '{tmp_dir}': {e}")
    else:
        print(f"Temporary directory '{tmp_dir}' does not exist. No cleanup needed.")

def aggregate_results(output_dir, organism):
    """
    Aggregates all .parsed files in the output_dir into summary CSV files
    """
    print(f"Aggregating results for {organism}...")
    
    # Initialize dictionaries
    cath_counts = defaultdict(int)
    plDDT_values = []
    
    # Find all .parsed files
    parsed_files = glob.glob(os.path.join(output_dir, "*.parsed"))
    
    for parsed_file in parsed_files:
        try:
            with open(parsed_file, "r") as pf:
                reader = csv.reader(pf)
                header = next(reader)  # Skip header
                for row in reader:
                    if len(row) != 2:
                        print(f"Warning: Invalid row format in {parsed_file}: {row}")
                        continue
                    cath_id, count = row
                    cath_counts[cath_id] += int(count)
                
                # Extract mean plDDT from the first line
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
    
    # Write cath_summary.csv
    cath_summary_file = os.path.join(output_dir, f"{organism}_cath_summary.csv")
    with open(cath_summary_file, "w", newline='', encoding="utf-8") as csf:
        writer = csv.writer(csf)
        writer.writerow(["cath_id", "count"])
        for cath, count in sorted(cath_counts.items()):
            writer.writerow([cath, count])
    print(f"Generated {cath_summary_file}")
    
    # Calculate mean and standard deviation of plDDT
    if plDDT_values:
        mean_plDDT = statistics.mean(plDDT_values)
        std_dev_plDDT = statistics.stdev(plDDT_values) if len(plDDT_values) > 1 else 0.0
    else:
        mean_plDDT = 0.0
        std_dev_plDDT = 0.0
    
    # Write plDDT_means.csv
    plddt_means_file = os.path.join(output_dir, "plDDT_means.csv")
    with open(plddt_means_file, "a", newline='', encoding="utf-8") as pmf:
        writer = csv.writer(pmf)
        # Write header if file is empty
        if pmf.tell() == 0:
            writer.writerow(["Organism", "Mean_plDDT", "StdDev_plDDT"])
        writer.writerow([organism.capitalize(), mean_plDDT, std_dev_plDDT])
    print(f"Updated {plddt_means_file}")
    
def main():
    if len(sys.argv) != 4:
        print("Usage: python3 pipeline_script.py <INPUT_DIR> <OUTPUT_DIR> <ORGANISM>")
        print("Example: python3 pipeline_script.py /mnt/datasets/human_input/ /mnt/results/human/ human")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    organism = sys.argv[3].lower()
    
    if organism not in ["human", "ecoli", "test"]:
        print("Error: ORGANISM must be either 'human' or 'ecoli'")
        sys.exit(1)
    
    pdbfiles = read_dir(input_dir)
    if not pdbfiles:
        print("No PDB files found in the input directory.")
        sys.exit(1)
    
    for file_info in pdbfiles:
        filepath, id, outpath = file_info
        pipeline(filepath, id, outpath)
    
    # After processing all files, aggregate results
    aggregate_results(output_dir, organism)

if __name__ == "__main__":
    main()
