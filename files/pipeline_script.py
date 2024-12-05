import sys
from subprocess import Popen, PIPE
import glob
import os
import multiprocessing
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

"""
usage: python3 pipeline_script.py [INPUT DIR] [OUTPUT DIR]
approx 5 seconds per analysis
"""

def run_parser(input_file, output_dir):
    search_file = input_file + "_search.tsv"
    logging.info(f"Search file: {search_file}, Output directory: {output_dir}")
    cmd = ['python3', '/opt/data_pipeline/results_parser.py', output_dir, search_file]
    logging.info(f'STEP 2: RUNNING PARSER: {" ".join(cmd)}')
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    logging.info(out.decode("utf-8"))
    if err:
        logging.error(err.decode("utf-8"))

def run_merizo_search(input_file, id):
    cmd = [
        'python3',
        '/opt/merizo_search/merizo_search/merizo.py',
        'easy-search',
        input_file,
        '/home/almalinux/merizo_search/examples/database/cath-4.3-foldclassdb',
        id,
        'tmp',
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
    if out:
        logging.info(out.decode("utf-8"))
    if err:
        logging.error(err.decode("utf-8"))

def read_dir(input_dir):
    logging.info("Getting file list")
    file_ids = list(glob.glob(os.path.join(input_dir, "*.pdb")))
    analysis_files = []
    for file in file_ids:
        id = os.path.splitext(os.path.basename(file))[0]
        analysis_files.append([file, id, sys.argv[2]])
    return analysis_files

def pipeline(filepath, id, outpath):
    run_merizo_search(filepath, id)
    run_parser(filepath, outpath)

if __name__ == "__main__":
    pdbfiles = read_dir(sys.argv[1])
    p = multiprocessing.Pool(1)
    p.starmap(pipeline, pdbfiles[:10])
