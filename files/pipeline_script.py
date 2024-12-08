import sys
from subprocess import Popen, PIPE
import glob
import os
import multiprocessing

"""
Usage: python3 pipeline_script.py [INPUT DIR] [OUTPUT DIR]
Approx 5 seconds per analysis
"""

# Path to the virtual environment's Python executable
VIRTUALENV_PYTHON = '/opt/merizo_search/merizosearch_env/bin/python3'

def run_parser(search_file, output_dir):
    """
    Run the results_parser.py over the search file to produce the output summary
    """
    print(f"Search File: {search_file}")
    print(f"Output Directory: {output_dir}")
    
    # Correct path to results_parser.py
    parser_script = '/opt/data_pipeline/results_parser.py'
    
    cmd = [VIRTUALENV_PYTHON, parser_script, output_dir, search_file]
    print(f'STEP 2: RUNNING PARSER: {" ".join(cmd)}')
    
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    
    if out:
        print(f"PARSER STDOUT:\n{out.decode('utf-8')}")
    if err:
        print(f"PARSER STDERR:\n{err.decode('utf-8')}")
    if p.returncode != 0:
        print("Parser encountered an error.")

def run_merizo_search(input_file, output_dir, id):
    """
    Runs the Merizo Search domain predictor to produce domains
    """
    # Ensure output_dir exists
    os.makedirs(output_dir, exist_ok=True)
    print(f"Using output directory: {output_dir}")
    
    # Path to merizo.py using symbolic links
    merizo_script = '/opt/merizo_search/merizo_search/merizo.py'
    
    # Use the symbolic link path for database
    database_path = '/home/almalinux/merizo_search/examples/database/cath-4.3-foldclassdb'
    
    # Define tmp_dir inside output_dir
    tmp_dir = os.path.join(output_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    print(f"Using tmp directory: {tmp_dir}")
    
    cmd = [
        VIRTUALENV_PYTHON,
        merizo_script,
        'easy-search',
        input_file,
        database_path,  # Use symlink path
        output_dir,     # Output directory: /mnt/results/
        tmp_dir,        # Temporary directory: /mnt/results/tmp/
        '--iterate',
        '--output_headers',
        '-d',
        'cpu',
        '--threads',
        '1'
    ]
    print(f'STEP 1: RUNNING MERIZO: {" ".join(cmd)}')
    
    # Run merizo.py
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    
    if out:
        print(f"MERIZO STDOUT:\n{out.decode('utf-8')}")
    if err:
        print(f"MERIZO STDERR:\n{err.decode('utf-8')}")
    if p.returncode != 0:
        print("Merizo Search encountered an error.")
    
    # Rename _search.tsv to test_search.tsv
    old_search = os.path.join(output_dir, "_search.tsv")
    new_search = os.path.join(output_dir, f"{id}_search.tsv")
    if os.path.isfile(old_search):
        os.rename(old_search, new_search)
        print(f"Renamed '_search.tsv' to '{new_search}'")
    else:
        print(f"Error: '_search.tsv' not found in {output_dir}")
    
    # Similarly, rename _segment.tsv to test_segment.tsv
    old_segment = os.path.join(output_dir, "_segment.tsv")
    new_segment = os.path.join(output_dir, f"{id}_segment.tsv")
    if os.path.isfile(old_segment):
        os.rename(old_segment, new_segment)
        print(f"Renamed '_segment.tsv' to '{new_segment}'")
    else:
        print(f"Error: '_segment.tsv' not found in {output_dir}")
    
    return new_search

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
    search_file = run_merizo_search(filepath, outpath, id)
    
    # STEP 2: Run Parser on the generated search file
    run_parser(search_file, outpath)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 pipeline_script.py <INPUT_DIR> <OUTPUT_DIR>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    pdbfiles = read_dir(input_dir)
    if not pdbfiles:
        print("No PDB files found in the input directory.")
        sys.exit(1)
    
    # Limit to first 10 files for testing; adjust as needed
    pool = multiprocessing.Pool(processes=1)
    pool.starmap(pipeline, pdbfiles[:10])
