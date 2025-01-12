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
  1) Normal pipeline for a single PDB (no aggregation):
     python3 pipeline_script.py <PDB_FILE> <OUTPUT_DIR> <ORGANISM>

  2) Full-scan aggregator only (systemd timer or manual):
     python3 pipeline_script.py --aggregate-only <OUTPUT_DIR> <ORGANISM>
"""

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

VIRTUALENV_PYTHON = '/opt/merizo_search/merizosearch_env/bin/python3'

# Redis configuration (still used if you track dispatched tasks)
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0


def run_parser(search_file, output_dir):
    logging.info(f"Search File: {search_file}")
    logging.info(f"Output Directory: {output_dir}")
    parser_script = '/opt/data_pipeline/results_parser.py'
    cmd = [VIRTUALENV_PYTHON, parser_script, output_dir, search_file]
    logging.info(f"STEP 2: RUNNING PARSER: {' '.join(cmd)}")
    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if out:
            logging.debug(f"PARSER STDOUT:\n{out.decode('utf-8')}")
        if err:
            logging.debug(f"PARSER STDERR:\n{err.decode('utf-8')}")
        if p.returncode != 0:
            raise RuntimeError("Parser encountered an error.")
        logging.info(f"Parser completed successfully for {search_file}.")
    except Exception as e:
        logging.error(f"Error during Parsing: {e}")
        raise


def run_merizo_search(pdb_file, output_dir, file_id, database_path, redis_conn, dispatched_set_key):
    logging.info(f"Checking if VIRTUALENV_PYTHON exists: {os.path.exists(VIRTUALENV_PYTHON)}")
    logging.info(f"VIRTUALENV_PYTHON is executable: {os.access(VIRTUALENV_PYTHON, os.X_OK)}")
    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"Using output directory: {output_dir}")
    merizo_script = '/opt/merizo_search/merizo_search/merizo.py'
    tmp_dir = os.path.join(output_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    logging.info(f"Using tmp directory: {tmp_dir}")

    cmd = [
        VIRTUALENV_PYTHON, merizo_script, 'easy-search',
        pdb_file, database_path, output_dir, tmp_dir,
        '--iterate', '--output_headers', '-d', 'cpu', '--threads', '1'
    ]
    logging.info(f"STEP 1: RUNNING MERIZO: {' '.join(cmd)}")

    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if out:
            logging.debug(f"MERIZO STDOUT:\n{out.decode('utf-8')}")
        if err:
            logging.debug(f"MERIZO STDERR:\n{err.decode('utf-8')}")
        if p.returncode != 0:
            raise RuntimeError("Merizo Search encountered an error.")
        logging.info(f"Merizo Search completed successfully for {pdb_file}.")

        old_search = os.path.join(output_dir, "_search.tsv")
        new_search = os.path.join(output_dir, f"{file_id}_search.tsv")

        # If _search.tsv not created => no hits
        if not os.path.isfile(old_search):
            logging.warning(f"No hits found for {pdb_file}. Skipping parsing.")
            redis_conn.sadd(dispatched_set_key, pdb_file)
            return None

        # Rename _search.tsv -> <file_id>_search.tsv
        os.rename(old_search, new_search)
        logging.info(f"Renamed '_search.tsv' to '{new_search}'")

        # Check if the file has data beyond the header
        with open(new_search, 'r') as f:
            lines = f.readlines()
            if len(lines) <= 1:
                logging.warning(f"No hits found in '{new_search}'. Skipping parsing.")
                redis_conn.sadd(dispatched_set_key, pdb_file)
                return None

        old_segment = os.path.join(output_dir, "_segment.tsv")
        new_segment = os.path.join(output_dir, f"{file_id}_segment.tsv")
        if os.path.isfile(old_segment):
            os.rename(old_segment, new_segment)
            logging.info(f"Renamed '_segment.tsv' to '{new_segment}'")
        else:
            raise FileNotFoundError(f"Error: '_segment.tsv' not found in {output_dir}")

        return new_search

    except Exception as e:
        logging.error(f"Error during Merizo Search: {e}")
        raise


def aggregate_plddt(output_dir, organism):
    logging.info(f"Full-scan plDDT aggregation for {organism}...")
    plDDT_values = []

    # Always scan all .parsed files
    parsed_files = glob.glob(os.path.join(output_dir, "*.parsed"))
    if not parsed_files:
        logging.info(f"No .parsed files found in {output_dir} for {organism}, skipping plDDT aggregation.")
        return

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

    if plDDT_values:
        overall_mean_plDDT = statistics.mean(plDDT_values)
        overall_std_dev_plDDT = (statistics.stdev(plDDT_values)
                                 if len(plDDT_values) > 1 else 0.0)
    else:
        overall_mean_plDDT, overall_std_dev_plDDT = 0.0, 0.0

    logging.info(f"plDDT for {organism.capitalize()}: Mean={overall_mean_plDDT:.4f}, StdDev={overall_std_dev_plDDT:.4f}")

    # Update /mnt/results/plDDT_means.csv
    results_dir = "/mnt/results"
    os.makedirs(results_dir, exist_ok=True)
    plddt_means_file = os.path.join(results_dir, "plDDT_means.csv")
    existing_data = {}

    # Read existing CSV to preserve other organisms
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
            logging.error(f"Error reading {plddt_means_file}: {e}")
            existing_data = {}

    # Update data for this organism
    existing_data[organism] = {
        "Mean_plDDT": overall_mean_plDDT,
        "StdDev_plDDT": overall_std_dev_plDDT
    }

    # Write updated CSV
    try:
        with open(plddt_means_file, "w", newline='', encoding="utf-8") as pmf:
            writer = csv.DictWriter(pmf, fieldnames=["Organism", "Mean_plDDT", "StdDev_plDDT"])
            writer.writeheader()
            for org_lc, stats in sorted(existing_data.items()):
                writer.writerow({
                    "Organism": org_lc.capitalize(),
                    "Mean_plDDT": f"{stats['Mean_plDDT']:.4f}",
                    "StdDev_plDDT": f"{stats['StdDev_plDDT']:.4f}"
                })
        logging.info(f"Updated {plddt_means_file} with {organism.capitalize()} plDDT stats.")
    except Exception as e:
        logging.error(f"Error writing {plddt_means_file}: {e}")

def aggregate_cath_counts(output_dir, organism):
    logging.info(f"Full-scan CATH aggregation for {organism}...")
    cath_counts = defaultdict(int)

    parsed_files = glob.glob(os.path.join(output_dir, "*.parsed"))
    if not parsed_files:
        logging.info(f"No .parsed files found in {output_dir} for {organism}, skipping CATH aggregation.")
        return

    for parsed_file in parsed_files:
        try:
            with open(parsed_file, "r") as pf:
                reader = csv.reader(pf)
                # Skip comment line
                next(reader, None)
                # Skip header line
                next(reader, None)
                for row in reader:
                    if len(row) != 2:
                        logging.warning(f"Invalid row in {parsed_file}: {row}")
                        continue
                    cath_id, count_str = row
                    try:
                        count_val = int(count_str)
                        cath_counts[cath_id] += count_val
                    except ValueError:
                        logging.warning(f"Invalid count value in {parsed_file}: {count_str}")
        except Exception as e:
            logging.error(f"Error processing {parsed_file}: {e}")

    summary_file = os.path.join("/mnt/results", f"{organism}_cath_summary.csv")
    os.makedirs("/mnt/results", exist_ok=True)

    try:
        with open(summary_file, "w", newline='', encoding="utf-8") as sf:
            writer = csv.DictWriter(sf, fieldnames=["cath_id", "count"])
            writer.writeheader()
            for cid in sorted(cath_counts.keys()):
                writer.writerow({"cath_id": cid, "count": cath_counts[cid]})
        logging.info(f"Wrote {organism}_cath_summary.csv with {len(cath_counts)} unique CATH IDs.")
    except Exception as e:
        logging.error(f"Error writing to {summary_file}: {e}")

def pipeline(pdb_file, output_dir, organism):
    # We do not run aggregator here—just Merizo + parse for a single .pdb
    try:
        redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        dispatched_set_key = f"dispatched_tasks:{organism}"
    except Exception as e:
        logging.error(f"Failed to connect to Redis: {e}")
        sys.exit(1)

    file_id = os.path.splitext(os.path.basename(pdb_file))[0]
    search_file = run_merizo_search(pdb_file, output_dir, file_id,
                                    '/home/almalinux/merizo_search/examples/database/cath-4.3-foldclassdb',
                                    redis_conn, dispatched_set_key)
    if search_file:
        run_parser(search_file, output_dir)
    else:
        logging.info(f"No search results to parse for {pdb_file}. Removing .pdb.")
        try:
            os.remove(pdb_file)
        except OSError as e:
            logging.error(f"Error removing {pdb_file}: {e}")

    # Clean up tmp dir
    tmp_dir = os.path.join(output_dir, "tmp")
    if os.path.exists(tmp_dir):
        try:
            shutil.rmtree(tmp_dir)
            logging.info(f"Removed temporary directory '{tmp_dir}'.")
        except Exception as e:
            logging.error(f"Error removing tmp dir '{tmp_dir}': {e}")
    else:
        logging.info(f"No tmp dir '{tmp_dir}' to remove.")

def aggregate_results(output_dir, organism):
    aggregate_plddt(output_dir, organism)
    aggregate_cath_counts(output_dir, organism)

def main():
    """
    For normal pipeline usage (merizo+parser only):
        python3 pipeline_script.py <PDB_FILE> <OUTPUT_DIR> <ORGANISM>

    For aggregator usage (systemd timer or manual):
        python3 pipeline_script.py --aggregate-only <OUTPUT_DIR> <ORGANISM>
    """
    if len(sys.argv) == 4 and sys.argv[1] == '--aggregate-only':
        # aggregator mode only
        output_dir = sys.argv[2]
        organism = sys.argv[3].lower()
        logging.info(f"Running aggregator for {organism} on ALL .parsed files in {output_dir}")
        aggregate_results(output_dir, organism)
        return

    # Normal pipeline usage
    if len(sys.argv) != 4:
        logging.error("Usage:")
        logging.error("  1) python3 pipeline_script.py <PDB_FILE> <OUTPUT_DIR> <ORGANISM>")
        logging.error("  2) python3 pipeline_script.py --aggregate-only <OUTPUT_DIR> <ORGANISM>")
        sys.exit(1)

    pdb_file = sys.argv[1]
    output_dir = sys.argv[2]
    organism = sys.argv[3].lower()

    if organism not in ["human", "ecoli", "test"]:
        logging.error("Error: ORGANISM must be either 'human', 'ecoli', or 'test'")
        sys.exit(1)

    if not os.path.isfile(pdb_file):
        logging.error(f"No PDB file found: {pdb_file}")
        sys.exit(1)

    # Pipeline step for a single PDB (no aggregator here)
    try:
        pipeline(pdb_file, output_dir, organism)
    except Exception as e:
        logging.error(f"Pipeline execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
