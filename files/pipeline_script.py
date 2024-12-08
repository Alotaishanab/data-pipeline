import sys
from subprocess import Popen, PIPE
import glob
import os
import multiprocessing

"""
usage: python pipeline_script.py [INPUT DIR] [OUTPUT DIR]
approx 5seconds per analysis
"""

def run_parser(input_file, output_dir):
    """
    Run the results_parser.py over the hhr file to produce the output summary
    """
    search_file = input_file+"_search.tsv"
    print(search_file, output_dir)
    cmd = ['python', './results_parser.py', output_dir, search_file]
    print(f'STEP 2: RUNNING PARSER: {" ".join(cmd)}')
    p = Popen(cmd, stdin=PIPE,stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    print(out.decode("utf-8"))

def run_merizo_search(input_file, id):
    """
    Runs the merizo domain predictor to produce domains
    """
    cmd = ['python3',
           '/home/almalinux/merizo_search/merizo_search/merizo.py',
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
    print(f'STEP 1: RUNNING MERIZO: {" ".join(cmd)}')
    p = Popen(cmd, stdin=PIPE,stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    
def read_dir(input_dir):
    """
    Function reads a fasta formatted file of protein sequences
    """
    print("Getting file list")
    file_ids = list(glob.glob(input_dir+"*.pdb"))
    analysis_files = []
    for file in file_ids:
        id = file.rsplit('/', 1)[-1]
        analysis_files.append([file, id, sys.argv[2]])
    return(analysis_files)

def pipeline(filepath, id, outpath):
    # STEP 1
    run_merizo_search(filepath, id)
    # STEP 2
    run_parser(id, outpath)

if __name__ == "__main__":
    pdbfiles = read_dir(sys.argv[1])
    p = multiprocessing.Pool(1)
    p.starmap(pipeline, pdbfiles[:10])

        