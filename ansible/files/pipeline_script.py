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

    Where:
      - PDB_FILE is the path to the .pdb file
      - OUTPUT_DIR is where results are written
      - ORGANISM is one of {human, ecoli, test}
      - AGGREGATE_MODE is optional, either "run" or "skip"
        (default: "skip" => do NOT aggregate)
        (use "run" => DO call aggregate_results() at the end)
"""

# 1) Lower the logging level to WARNING to reduce overhead.
logging.basicConfig(
    level=logging.WARNING,  # <<-- CHANGED from INFO to WARNING
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

VIRTUALENV_PYTHON = '/opt/merizo_search/merizosearch_env/bin/python3'

# Redis configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB   = 0

def run_parser(search_file, output_dir):
    logging.warning(f"Search File: {search_file}")  # downgraded info->warning
    parser_script = '/opt/data_pipeline/results_parser.py'
    cmd = [VIRTUALENV_PYTHON, parser_script, output_dir, search_file]
    logging.warning(f'STEP 2: RUNNING PARSER: {" ".join(cmd)}')
    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        # We'll keep debug logs minimal
        if p.returncode != 0:
            raise RuntimeError(f"Parser encountered an error:\n{err.decode('utf-8')}")
        logging.warning(f"Parser completed successfully for {search_file}.")
    except Exception as e:
        logging.error(f"Error during Parsing: {e}")
        raise

def run_merizo_search(pdb_file, output_dir, id, database_path, redis_conn, dispatched_set_key):
    logging.warning(f"Checking if VIRTUALENV_PYTHON is ready: {os.path.exists(VIRTUALENV_PYTHON)} / {os.access(VIRTUALENV_PYTHON, os.X_OK)}")
    os.makedirs(output_dir, exist_ok=True)
    merizo_script = '/opt/merizo_search/merizo_search/merizo.py'
    tmp_dir = os.path.join(output_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    # 2) Increase Merizo's threads from 1 to 4 to use more CPU cores.
    cmd = [
        VIRTUALENV_PYTHON, merizo_script, 'easy-search',
        pdb_file, database_path, output_dir, tmp_dir,
        '--iterate', '--output_headers', '-d', 'cpu', '--threads', '1'  # <<-- CHANGED
    ]
    logging.warning(f'STEP 1: RUNNING MERIZO: {" ".join(cmd)}')
    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError(f"Merizo Search error:\n{err.decode('utf-8')}")
        logging.warning(f"Merizo Search completed for {pdb_file}.")

        old_search = os.path.join(output_dir, "_search.tsv")
        new_search = os.path.join(output_dir, f"{id}_search.tsv")

        if not os.path.isfile(old_search):
            logging.warning(f"No hits found for {pdb_file}. Skipping parsing.")
            redis_conn.sadd(dispatched_set_key, pdb_file)
            return None

        os.rename(old_search, new_search)
        logging.warning(f"Renamed '_search.tsv' to '{new_search}'")

        # Quick data check
        with open(new_search, 'r') as f:
            lines = f.readlines()
            if len(lines) <= 1:
                logging.warning(f"No hits in '{new_search}'. Skipping parsing.")
                redis_conn.sadd(dispatched_set_key, pdb_file)
                return None

        old_segment = os.path.join(output_dir, "_segment.tsv")
        new_segment = os.path.join(output_dir, f"{id}_segment.tsv")
        if os.path.isfile(old_segment):
            os.rename(old_segment, new_segment)
            logging.warning(f"Renamed '_segment.tsv' to '{new_segment}'")
        else:
            raise FileNotFoundError(f"Error: '_segment.tsv' not found in {output_dir}")

        return new_search

    except Exception as e:
        logging.error(f"Error during Merizo Search: {e}")
        raise

def aggregate_plddt(output_dir, organism):
    logging.info(f"Aggregating plDDT values for {organism}...")
    plDDT_values = []
    parsed_files = glob.glob(os.path.join(output_dir, "*.parsed"))

    for parsed_file in parsed_files:
        try:
            with open(parsed_file, "r") as pf:
                first_line = pf.readline().strip()
                if first_line.startswith("#"):
                    parts = first_line.split("mean plddt:")
                    if len(parts) == 2:
                        try:
                            mean_plddt = float(parts[1])
                            plDDT_values.append(mean_plddt)
                        except ValueError:
                            logging.warning(f"Invalid plDDT in {parsed_file}")
        except Exception as e:
            logging.error(f"Error processing {parsed_file}: {e}")
            continue

    if plDDT_values:
        overall_mean_plDDT = statistics.mean(plDDT_values)
        overall_std_dev_plDDT = (statistics.stdev(plDDT_values)
                                 if len(plDDT_values) > 1 else 0.0)
    else:
        overall_mean_plDDT, overall_std_dev_plDDT = 0.0, 0.0

    logging.info(f"Organism: {organism.capitalize()}, Mean plDDT: {overall_mean_plDDT}, Std Dev plDDT: {overall_std_dev_plDDT}")

    results_dir = "/mnt/results"
    os.makedirs(results_dir, exist_ok=True)
    plddt_means_file = os.path.join(results_dir, "plDDT_means.csv")
    existing_data = {}

    if os.path.isfile(plddt_means_file):
        try:
            with open(plddt_means_file, "r", newline='', encoding="utf-8") as pmf:
                reader = csv.DictReader(pmf)
                for row in reader:
                    existing_data[row['Organism'].lower()] = {
                        "Mean_plDDT": float(row["Mean_plDDT"]),
                        "StdDev_plDDT": float(row["StdDev_plDDT"])
                    }
        except Exception as e:
            logging.error(f"Error reading existing {plddt_means_file}: {e}")
            existing_data = {}

    existing_data[organism] = {
        "Mean_plDDT": overall_mean_plDDT,
        "StdDev_plDDT": overall_std_dev_plDDT
    }

    try:
        with open(plddt_means_file, "w", newline='', encoding="utf-8") as pmf:
            writer = csv.DictWriter(pmf, fieldnames=["Organism", "Mean_plDDT", "StdDev_plDDT"])
            writer.writeheader()
            for org, stats in sorted(existing_data.items()):
                writer.writerow({
                    "Organism": org.capitalize(),
                    "Mean_plDDT": f"{stats['Mean_plDDT']:.4f}",
                    "StdDev_plDDT": f"{stats['StdDev_plDDT']:.4f}"
                })
        logging.info(f"Updated {plddt_means_file} with organism '{organism.capitalize()}'")
    except Exception as e:
        logging.error(f"Error writing to {plddt_means_file}: {e}")

def aggregate_cath_counts(output_dir, organism):
    logging.info(f"Aggregating CATH counts for {organism}...")
    cath_counts = defaultdict(int)
    parsed_files = glob.glob(os.path.join(output_dir, "*.parsed"))

    for parsed_file in parsed_files:
        try:
            with open(parsed_file, "r") as pf:
                reader = csv.reader(pf)
                next(reader, None)  # skip comment line
                next(reader, None)  # skip header
                for row in reader:
                    if len(row) != 2:
                        logging.warning(f"Invalid row format in {parsed_file}: {row}")
                        continue
                    cath_id, count_str = row
                    try:
                        count = int(count_str)
                        cath_counts[cath_id] += count
                    except ValueError:
                        logging.warning(f"Invalid count value in {parsed_file}: {count_str}")
        except Exception as e:
            logging.error(f"Error processing {parsed_file}: {e}")
            continue

    summary_file = os.path.join("/mnt/results", f"{organism}_cath_summary.csv")
    try:
        with open(summary_file, "w", newline='', encoding="utf-8") as sf:
            writer = csv.DictWriter(sf, fieldnames=["cath_id", "count"])
            writer.writeheader()
            for cath_id, count in sorted(cath_counts.items()):
                writer.writerow({"cath_id": cath_id, "count": count})
        logging.info(f"Aggregated CATH counts written to {summary_file}")
    except Exception as e:
        logging.error(f"Error writing to {summary_file}: {e}")

def aggregate_results(output_dir, organism):
    # Aggregates plDDT + CATH in one go
    aggregate_plddt(output_dir, organism)
    aggregate_cath_counts(output_dir, organism)

def pipeline(pdb_file, output_dir, organism):
    try:
        redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        dispatched_set_key = f"dispatched_tasks:{organism}"
    except Exception as e:
        logging.error(f"Failed to connect to Redis: {e}")
        sys.exit(1)

    search_file = run_merizo_search(
        pdb_file, output_dir,
        id=os.path.splitext(os.path.basename(pdb_file))[0],
        database_path='/home/almalinux/merizo_search/examples/database/cath-4.3-foldclassdb',
        redis_conn=redis_conn,
        dispatched_set_key=dispatched_set_key
    )

    if search_file:
        run_parser(search_file, output_dir)
    else:
        logging.warning(f"No search results to parse for {pdb_file}.")
        try:
            os.remove(pdb_file)  # remove so it won't get redispatched
        except OSError as e:
            logging.error(f"Error removing {pdb_file}: {e}")

    # Remove from Redis
    try:
        redis_conn.srem(dispatched_set_key, pdb_file)
    except Exception as e:
        logging.warning(f"Could not remove {pdb_file} from Redis set: {e}")

    # Clean up tmp dir
    tmp_dir = os.path.join(output_dir, "tmp")
    if os.path.exists(tmp_dir):
        try:
            shutil.rmtree(tmp_dir)
        except Exception as e:
            logging.error(f"Error removing tmp dir '{tmp_dir}': {e}")

def main():
    if len(sys.argv) < 4:
        logging.error("Usage: python3 pipeline_script.py <PDB_FILE> <OUTPUT_DIR> <ORGANISM> [AGGREGATE_MODE]")
        sys.exit(1)

    pdb_file = sys.argv[1]
    output_dir = sys.argv[2]
    organism = sys.argv[3].lower()

    if organism not in ["human", "ecoli", "test"]:
        logging.error("Error: ORGANISM must be either 'human', 'ecoli', or 'test'")
        sys.exit(1)

    # aggregator by default => skip
    aggregate_mode = "skip"
    if len(sys.argv) >= 5:
        aggregate_mode = sys.argv[4].lower()

    try:
        pipeline(pdb_file, output_dir, organism)
    except Exception as e:
        logging.error(f"Pipeline execution failed: {e}")
        sys.exit(1)

    if aggregate_mode == "run":
        logging.warning(f"AGGREGATE_MODE='run' => aggregator for {organism} ...")
        try:
            aggregate_results(output_dir, organism)
        except Exception as e:
            logging.error(f"Aggregation failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()