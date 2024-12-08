import sys
import csv
import json
from collections import defaultdict
import statistics
from subprocess import Popen, PIPE
import glob
import os
import multiprocessing
import logging
import uuid  # For generating unique directory names

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

"""
Usage: python3 pipeline_script.py [INPUT_DIR] [OUTPUT_DIR]
Approx 5 seconds per analysis
"""

def run_parser(search_file_path, output_dir):
    logging.info(f"Search file: {search_file_path}, Output directory: {output_dir}")
    cmd = ['python3', '/opt/data_pipeline/results_parser.py', output_dir, search_file_path]
    logging.info(f'STEP 2: RUNNING PARSER: {" ".join(cmd)}')
    
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    
    logging.info(f"PARSER STDOUT:\n{out.decode('utf-8')}")
    if err:
        logging.error(f"PARSER STDERR:\n{err.decode('utf-8')}")
    logging.info(f"PARSER Return Code: {p.returncode}")
    
    if p.returncode != 0:
        logging.error("Parser encountered an error.")

def run_merizo_search(input_file, id, output_dir):
    # Generate a unique identifier for the run
    unique_id = uuid.uuid4().hex
    # Create a unique subdirectory within the output directory
    unique_output_dir = os.path.join(output_dir, f"{id}_{unique_id}")
    
    # Ensure the unique output directory exists
    os.makedirs(unique_output_dir, exist_ok=True)
    logging.info(f"Created unique output directory: {unique_output_dir}")
    
    # Set the database path without the '.pt' extension
    database_base_path = '/home/almalinux/merizo_search/examples/database/cath-4.3-foldclassdb'
    cmd = [
        'python3',
        '/opt/merizo_search/merizo_search/merizo.py',
        'easy-search',
        input_file,
        database_base_path,  # No '.pt' here to prevent duplication
        id,
        unique_output_dir,    # Output directory set to the unique subdirectory
        '--iterate',
        '--output_headers',
        '-d',
        'cpu',
        '--threads',
        '1'
    ]
    logging.info(f'STEP 1: RUNNING MERIZO: {" ".join(cmd)}')
    
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    
    logging.info(f"MERIZO STDOUT:\n{out.decode('utf-8')}")
    if err:
        logging.error(f"MERIZO STDERR:\n{err.decode('utf-8')}")
    logging.info(f"MERIZO Return Code: {p.returncode}")
    
    if p.returncode != 0:
        logging.error("Merizo Search encountered an error.")
    
    # List contents of the unique_output_dir
    try:
        contents = os.listdir(unique_output_dir)
        logging.info(f"Contents of {unique_output_dir}: {contents}")
    except Exception as e:
        logging.error(f"Failed to list contents of {unique_output_dir}: {e}")
    
    return unique_output_dir

def read_dir(input_dir):
    logging.info("Getting file list")
    file_ids = glob.glob(os.path.join(input_dir, "*.pdb"))
    analysis_files = []
    
    for file_path in file_ids:
        id = os.path.splitext(os.path.basename(file_path))[0]
        analysis_files.append([file_path, id])
    
    return analysis_files

def pipeline(filepath, id, output_dir):
    unique_output_dir = run_merizo_search(filepath, id, output_dir)
    search_file_path = os.path.join(unique_output_dir, "test_search.tsv")
    # After running Merizo Search, verify the search file exists
    if not os.path.isfile(search_file_path):
        logging.error(f"Search file {search_file_path} was not created by Merizo Search.")
        return
    run_parser(search_file_path, output_dir)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 pipeline_script.py <INPUT_DIR> <OUTPUT_DIR>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    pdbfiles = read_dir(input_dir)
    if not pdbfiles:
        logging.error("No PDB files found in the input directory.")
        sys.exit(1)
    
    pool = multiprocessing.Pool(processes=1)
    pool.starmap(pipeline, [[fp, id, output_dir] for fp, id in pdbfiles[:10]])
