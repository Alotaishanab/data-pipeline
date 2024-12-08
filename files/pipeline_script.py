import sys
from subprocess import Popen, PIPE
import glob
import os
import multiprocessing
import uuid  # For generating unique directory names

"""
Usage: python3 pipeline_script.py [INPUT DIR] [OUTPUT DIR]
Approx 5 seconds per analysis
"""

VIRTUALENV_PYTHON = '/opt/merizo_search/merizosearch_env/bin/python3'  # Direct path to virtualenv's Python executable

def run_parser(search_file, output_dir):
    """
    Run the results_parser.py over the search file to produce the output summary
    """
    print(f"Search File: {search_file}")
    print(f"Output Directory: {output_dir}")
    
    cmd = [VIRTUALENV_PYTHON, '/opt/data_pipeline/results_parser.py', output_dir, search_file]
    print(f'STEP 2: RUNNING PARSER: {" ".join(cmd)}')
    
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    
    if out:
        print(f"PARSER STDOUT:\n{out.decode('utf-8')}")
    if err:
        print(f"PARSER STDERR:\n{err.decode('utf-8')}")

def run_merizo_search(input_file, id, output_dir):
    """
    Runs the Merizo Search domain predictor to produce domains
    """
    unique_id = uuid.uuid4().hex[:8]
    unique_output_dir = os.path.join(output_dir, f"{id}_{unique_id}")
    
    # Ensure the unique output directory exists
    os.makedirs(unique_output_dir, exist_ok=True)
    print(f"Created unique output directory: {unique_output_dir}")
    
    cmd = [
        VIRTUALENV_PYTHON,
        '/home/almalinux/merizo_search/merizo_search/merizo.py',
        'easy-search',
        input_file,
        '/mnt/datasets/cath_foldclassdb',
        id,
        unique_output_dir,
        '--iterate',
        '--output_headers',
        '-d',
        'cpu',
        '--threads',
        '1'
    ]
    print(f'STEP 1: RUNNING MERIZO: {" ".join(cmd)}')
    
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    
    if out:
        print(f"MERIZO STDOUT:\n{out.decode('utf-8')}")
    if err:
        print(f"MERIZO STDERR:\n{err.decode('utf-8')}")
    
    return unique_output_dir

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
    unique_output_dir = run_merizo_search(filepath, id, outpath)
    
    # STEP 2: Run Parser on the generated search file
    search_file_path = os.path.join(unique_output_dir, "test_search.tsv")
    run_parser(search_file_path, outpath)

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
