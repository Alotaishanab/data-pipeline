#!/usr/bin/env python3
import sys
import os
import shutil
import csv
import glob
import redis
import statistics
import logging
from subprocess import Popen, PIPE
from collections import defaultdict

"""
Usage:
  python3 pipeline_script.py <PDB_FILE> <OUTPUT_DIR> <ORGANISM> [AGGREGATE_MODE]

- PDB_FILE: path to the .pdb file
- OUTPUT_DIR: results directory
- ORGANISM: one of {human, ecoli, test}
- AGGREGATE_MODE (optional): "run" => aggregator runs, otherwise "skip"
"""

# Configure logging to show warnings and above
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Python path for the Merizo Search virtual environment
VIRTUALENV_PYTHON = '/opt/merizo_search/merizosearch_env/bin/python3'

# Redis connection configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# Helper function to count residues in a PDB file
def get_residue_count(pdb_path):
    """Count unique residues in the PDB file."""
    if not os.path.isfile(pdb_path):
        return 0
    residues = set()
    try:
        with open(pdb_path, 'r') as fh:
            for line in fh:
                if line.startswith("ATOM "):  # Process only ATOM lines
                    parts = line.split()
                    if len(parts) > 5:
                        try:
                            resnum = int(parts[5])  # Residue number
                            residues.add(resnum)
                        except ValueError:
                            pass  # Ignore invalid residue numbers
    except Exception:
        return 0
    return len(residues)

# Run the result parser
def run_parser(search_file, output_dir):
    """Parse search results and save outputs."""
    logging.warning(f"STEP 2: Parsing {search_file}...")
    parser_script = '/opt/data_pipeline/results_parser.py'
    cmd = [VIRTUALENV_PYTHON, parser_script, output_dir, search_file]

    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError(f"Parser error:\n{err.decode('utf-8')}")
        logging.warning(f"Parser completed for {search_file}.")
    except Exception as e:
        logging.error(f"Parser failed on {search_file}: {e}")
        raise

# Remove processed files in batches from Redis
def flush_redis_batch(redis_conn, dispatched_key):
    """
    Flush a batch of processed files from Redis.
    """
    global processed_files
    if not processed_files:
        return
    pipe = redis_conn.pipeline()
    for pdb_f in processed_files:
        pipe.srem(dispatched_key, pdb_f)  # Remove file from Redis set
    pipe.execute()
    logging.warning(f"Flushed {len(processed_files)} items from Redis in a pipeline call.")
    processed_files.clear()

# Run the Merizo Search process
def run_merizo_search(pdb_file, output_dir, file_id, database_path, redis_conn, dispatched_set_key):
    """Execute Merizo Search with the given parameters."""
    logging.warning(f"STEP 1: Running Merizo on {pdb_file} with --threads=1 ...")
    tmp_dir = os.path.join(output_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    res_count = get_residue_count(pdb_file)
    use_iterate = (res_count >= 800)  # Determine whether to use --iterate

    cmd = [
        VIRTUALENV_PYTHON,
        '/opt/merizo_search/merizo_search/merizo.py',
        'easy-search',
        pdb_file,
        database_path,
        output_dir,
        tmp_dir,
        '--output_headers',
        '-d', 'cpu',
        '--threads', '1',
        '-k', '20'
    ]
    if use_iterate:
        cmd.append('--iterate')
        logging.warning(f"{pdb_file}: {res_count} residues => using --iterate.")
    else:
        logging.warning(f"{pdb_file}: {res_count} residues => skipping --iterate for speed.")

    try:
        # Execute the Merizo command
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError(f"Merizo error:\n{err.decode('utf-8')}")
        
        # Process the results
        old_search = os.path.join(output_dir, "_search.tsv")
        new_search = os.path.join(output_dir, f"{file_id}_search.tsv")
        if not os.path.isfile(old_search):
            logging.warning(f"No hits found for {pdb_file}.")
            return None
        os.rename(old_search, new_search)

        # Handle segments
        old_segment = os.path.join(output_dir, "_segment.tsv")
        new_segment = os.path.join(output_dir, f"{file_id}_segment.tsv")
        if os.path.isfile(old_segment):
            os.rename(old_segment, new_segment)
        else:
            raise FileNotFoundError(f"Missing _segment.tsv in {output_dir}")

        return new_search

    except Exception as e:
        logging.error(f"Merizo search failed: {e}")
        raise

def aggregate_plddt(output_dir, organism):
    logging.warning(f"Aggregating plDDT for {organism} ...")
    plDDT_values = []
    for parsed_file in glob.glob(os.path.join(output_dir, "*.parsed")):
        try:
            with open(parsed_file, "r") as pf:
                first_line = pf.readline().strip()
                if first_line.startswith("#"):
                    parts = first_line.split("mean plddt:")
                    if len(parts) == 2:
                        try:
                            val = float(parts[1])
                            plDDT_values.append(val)
                        except ValueError:
                            logging.warning(f"Invalid plDDT in {parsed_file}")
        except Exception as e:
            logging.error(f"Error reading {parsed_file}: {e}")

    if plDDT_values:
        overall_mean = statistics.mean(plDDT_values)
        overall_std  = statistics.stdev(plDDT_values) if len(plDDT_values) > 1 else 0.0
    else:
        overall_mean, overall_std = 0.0, 0.0

    res_dir = "/mnt/results"
    os.makedirs(res_dir, exist_ok=True)
    plddt_means_file = os.path.join(res_dir, "plDDT_means.csv")

    existing_data = {}
    if os.path.isfile(plddt_means_file):
        try:
            with open(plddt_means_file, "r", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    existing_data[row['Organism'].lower()] = {
                        "Mean_plDDT": float(row["Mean_plDDT"]),
                        "StdDev_plDDT": float(row["StdDev_plDDT"])
                    }
        except Exception as e:
            logging.error(f"Error reading {plddt_means_file}: {e}")
            existing_data = {}

    existing_data[organism] = {
        "Mean_plDDT": overall_mean,
        "StdDev_plDDT": overall_std
    }
    try:
        with open(plddt_means_file, "w", encoding="utf-8", newline='') as fh:
            writer = csv.DictWriter(fh, fieldnames=["Organism","Mean_plDDT","StdDev_plDDT"])
            writer.writeheader()
            for org, stats in sorted(existing_data.items()):
                writer.writerow({
                    "Organism": org.capitalize(),
                    "Mean_plDDT": f"{stats['Mean_plDDT']:.4f}",
                    "StdDev_plDDT": f"{stats['StdDev_plDDT']:.4f}"
                })
        logging.warning(f"Updated {plddt_means_file} with {organism.capitalize()} results.")
    except Exception as e:
        logging.error(f"Error writing {plddt_means_file}: {e}")

def aggregate_cath_counts(output_dir, organism):
    logging.warning(f"Aggregating CATH for {organism} ...")
    cath_counts = defaultdict(int)
    for parsed_file in glob.glob(os.path.join(output_dir, "*.parsed")):
        try:
            with open(parsed_file, "r") as pf:
                reader = csv.reader(pf)
                next(reader, None)  # skip comment
                next(reader, None)  # skip header
                for row in reader:
                    if len(row) != 2:
                        continue
                    c_id, c_val = row
                    try:
                        cath_counts[c_id] += int(c_val)
                    except ValueError:
                        pass
        except Exception as e:
            logging.error(f"Error reading {parsed_file}: {e}")

    summary_file = os.path.join("/mnt/results", f"{organism}_cath_summary.csv")
    try:
        with open(summary_file, "w", encoding="utf-8", newline='') as sf:
            writer = csv.DictWriter(sf, fieldnames=["cath_id", "count"])
            writer.writeheader()
            for c_id, val in sorted(cath_counts.items()):
                writer.writerow({"cath_id": c_id, "count": val})
        logging.warning(f"Wrote CATH summary => {summary_file}")
    except Exception as e:
        logging.error(f"Failed writing {summary_file}: {e}")

def aggregate_results(output_dir, organism):
    aggregate_plddt(output_dir, organism)
    aggregate_cath_counts(output_dir, organism)

def pipeline(pdb_file, output_dir, organism):
    """
    Main pipeline logic: run Merizo => run parser => batch srem => aggregator
    """
    try:
        redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        dispatched_key = f"dispatched_tasks:{organism}"

       
    except Exception as e:
        logging.error(f"Redis connection failed: {e}")
        sys.exit(1)

    file_id = os.path.splitext(os.path.basename(pdb_file))[0]
    database_path = '/home/almalinux/merizo_search/examples/database/cath-4.3-foldclassdb'

    # run merizo
    search_file = run_merizo_search(
        pdb_file, output_dir, file_id,
        database_path, redis_conn, dispatched_key
    )

    # parse if we got a valid tsv
    if search_file:
        run_parser(search_file, output_dir)
    else:
        logging.warning(f"No valid search file for {pdb_file} => removing .pdb.")
        try:
            os.remove(pdb_file)
        except OSError as e:
            logging.error(f"Error removing {pdb_file}: {e}")

    # add file to batch for removal
    from __main__ import processed_files, flush_redis_batch, BATCH_SIZE
    processed_files.append(pdb_file)

    # cleanup tmp
    tmp_dir = os.path.join(output_dir, "tmp")
    if os.path.exists(tmp_dir):
        try:
            shutil.rmtree(tmp_dir)
        except Exception as e:
            logging.error(f"Error removing tmp {tmp_dir}: {e}")

    # flush if we reached batch size
    if len(processed_files) >= BATCH_SIZE:
        flush_redis_batch(redis_conn, dispatched_key)

def main():
    if len(sys.argv) < 4:
        logging.error("Usage: python3 pipeline_script.py <PDB_FILE> <OUTPUT_DIR> <ORGANISM> [AGGREGATE_MODE]")
        sys.exit(1)

    pdb_file  = sys.argv[1]
    out_dir   = sys.argv[2]
    organism  = sys.argv[3].lower()
    agg_mode  = "skip"
    if len(sys.argv) >= 5:
        agg_mode = sys.argv[4].lower()

    # run pipeline
    try:
        pipeline(pdb_file, out_dir, organism)
    except Exception as e:
        logging.error(f"Pipeline crashed on {pdb_file}: {e}")
        sys.exit(1)

    # aggregator if "run"
    if agg_mode == "run":
        logging.warning(f"AGGREGATE_MODE='run' => aggregator for {organism}")
        try:
            aggregate_results(out_dir, organism)
        except Exception as e:
            logging.error(f"Aggregation error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
