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

# 1) Reduce logging overhead: set level to WARNING
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

VIRTUALENV_PYTHON = '/opt/merizo_search/merizosearch_env/bin/python3'

# Redis configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB   = 0

################################################################
# Optional helper: Get approximate residue count for skipping
# or enabling --iterate. Called before run_merizo_search().
################################################################
def get_residue_count(pdb_path):
    """
    Returns a quick estimate of residue count by parsing ATOM lines.
    Typically good enough to decide if we want --iterate.
    """
    if not os.path.isfile(pdb_path):
        return 0
    residues = set()
    try:
        with open(pdb_path, 'r') as fh:
            for line in fh:
                if line.startswith("ATOM "):
                    parts = line.split()
                    # Usually residue index is in parts[5], but we
                    # do a small check in case the line doesn't match
                    if len(parts) > 5:
                        try:
                            resnum = int(parts[5])
                            residues.add(resnum)
                        except ValueError:
                            pass
    except Exception:
        return 0
    return len(residues)

def run_parser(search_file, output_dir):
    """
    Spawns a new process to parse the Merizo results.
    """
    logging.warning(f"STEP 2: Parsing {search_file} ...")
    parser_script = '/opt/data_pipeline/results_parser.py'
    cmd = [VIRTUALENV_PYTHON, parser_script, output_dir, search_file]

    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError(f"Parser error:\n{err.decode('utf-8')}")
        logging.warning(f"Parser completed successfully for {search_file}.")
    except Exception as e:
        logging.error(f"Parser failed on {search_file}: {e}")
        raise

def run_merizo_search(pdb_file, output_dir, file_id, database_path, redis_conn, dispatched_set_key):
    """
    Runs Merizo-search with threads=1, skipping --iterate if <800 residues
    to speed up smaller structures. Uses 'easy-search' for combined segment+search.
    """
    logging.warning(f"STEP 1: Deciding Merizo mode for {pdb_file} ...")
    tmp_dir = os.path.join(output_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    # 2) Decide on --iterate if ~800+ residues
    res_count = get_residue_count(pdb_file)
    use_iterate = (res_count >= 800)

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
        '-k', '50'   # <<-- NEW: limit top hits to 50
    ]

    if use_iterate:
        cmd.append('--iterate')
        logging.warning(f"{pdb_file}: {res_count} residues => using --iterate.")
    else:
        logging.warning(f"{pdb_file}: {res_count} residues => skipping --iterate for speed.")

    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError(f"Merizo error:\n{err.decode('utf-8')}")

        old_search = os.path.join(output_dir, "_search.tsv")
        new_search = os.path.join(output_dir, f"{file_id}_search.tsv")

        # If no _search.tsv => no hits
        if not os.path.isfile(old_search):
            logging.warning(f"No hits found for {pdb_file}. Skipping parse.")
            redis_conn.sadd(dispatched_set_key, pdb_file)
            return None

        # rename _search.tsv => <id>_search.tsv
        os.rename(old_search, new_search)

        # quick check of search file
        with open(new_search, 'r') as f:
            lines = f.readlines()
            if len(lines) <= 1:
                logging.warning(f"No hits in {new_search}, skipping parse.")
                redis_conn.sadd(dispatched_set_key, pdb_file)
                return None

        old_segment = os.path.join(output_dir, "_segment.tsv")
        new_segment = os.path.join(output_dir, f"{file_id}_segment.tsv")
        if os.path.isfile(old_segment):
            os.rename(old_segment, new_segment)
        else:
            raise FileNotFoundError(f"Missing _segment.tsv in {output_dir}")

        return new_search

    except Exception as e:
        logging.error(f"Merizo search failed for {pdb_file}: {e}")
        raise

def aggregate_plddt(output_dir, organism):
    """
    Gathers all .parsed files to compute plDDT stats, then updates plDDT_means.csv
    """
    logging.warning(f"Aggregating plDDT for {organism}...")
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
            logging.error(f"Error in {parsed_file}: {e}")
            continue

    if plDDT_values:
        overall_mean = statistics.mean(plDDT_values)
        overall_std = statistics.stdev(plDDT_values) if len(plDDT_values) > 1 else 0.0
    else:
        overall_mean, overall_std = 0.0, 0.0

    results_dir = "/mnt/results"
    os.makedirs(results_dir, exist_ok=True)
    plddt_means_file = os.path.join(results_dir, "plDDT_means.csv")

    existing_data = {}
    if os.path.isfile(plddt_means_file):
        try:
            with open(plddt_means_file, "r", newline='', encoding="utf-8") as fh:
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
        with open(plddt_means_file, "w", newline='', encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["Organism", "Mean_plDDT", "StdDev_plDDT"])
            writer.writeheader()
            for org, stats in sorted(existing_data.items()):
                writer.writerow({
                    "Organism": org.capitalize(),
                    "Mean_plDDT": f"{stats['Mean_plDDT']:.4f}",
                    "StdDev_plDDT": f"{stats['StdDev_plDDT']:.4f}"
                })
        logging.warning(f"Updated {plddt_means_file} for {organism.capitalize()}: mean={overall_mean:.2f}, std={overall_std:.2f}")
    except Exception as e:
        logging.error(f"Error writing {plddt_means_file}: {e}")

def aggregate_cath_counts(output_dir, organism):
    """
    Collects CATH IDs from all .parsed files and writes a summary CSV
    """
    logging.warning(f"Aggregating CATH for {organism}...")
    cath_counts = defaultdict(int)
    parsed_files = glob.glob(os.path.join(output_dir, "*.parsed"))

    for parsed_file in parsed_files:
        try:
            with open(parsed_file, "r") as pf:
                reader = csv.reader(pf)
                next(reader, None)  # skip comment
                next(reader, None)  # skip header
                for row in reader:
                    if len(row) != 2:
                        logging.warning(f"Invalid row in {parsed_file}: {row}")
                        continue
                    c_id, c_val = row
                    try:
                        cath_counts[c_id] += int(c_val)
                    except ValueError:
                        logging.warning(f"Bad integer {c_val} in {parsed_file}")
        except Exception as e:
            logging.error(f"Error reading {parsed_file}: {e}")
            continue

    summary_file = os.path.join("/mnt/results", f"{organism}_cath_summary.csv")
    try:
        with open(summary_file, "w", newline='', encoding="utf-8") as sf:
            writer = csv.DictWriter(sf, fieldnames=["cath_id", "count"])
            writer.writeheader()
            for c_id, cnt in sorted(cath_counts.items()):
                writer.writerow({"cath_id": c_id, "count": cnt})
        logging.warning(f"Wrote CATH summary => {summary_file}")
    except Exception as e:
        logging.error(f"Failed writing {summary_file}: {e}")

def aggregate_results(output_dir, organism):
    aggregate_plddt(output_dir, organism)
    aggregate_cath_counts(output_dir, organism)

def pipeline(pdb_file, output_dir, organism):
    """
    Main pipeline logic: run Merizo => run parser => remove from Redis => cleanup tmp
    """
    try:
        redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        dispatched_key = f"dispatched_tasks:{organism}"
    except Exception as e:
        logging.error(f"Redis connection failed: {e}")
        sys.exit(1)

    file_id = os.path.splitext(os.path.basename(pdb_file))[0]
    database_path = '/home/almalinux/merizo_search/examples/database/cath-4.3-foldclassdb'

    # 1) Run Merizo easy-search, conditionally skipping --iterate
    search_file = run_merizo_search(
        pdb_file, output_dir, file_id,
        database_path, redis_conn, dispatched_key
    )

    # 2) If we have a valid .tsv => parse
    if search_file:
        run_parser(search_file, output_dir)
    else:
        logging.warning(f"No valid search file for {pdb_file}. Removing file.")
        try:
            os.remove(pdb_file)
        except OSError as e:
            logging.error(f"File remove error {pdb_file}: {e}")

    # 3) Remove from Redis
    try:
        redis_conn.srem(dispatched_key, pdb_file)
    except Exception as e:
        logging.warning(f"Redis srem failed for {pdb_file}: {e}")

    # 4) Cleanup tmp directory
    tmp_path = os.path.join(output_dir, "tmp")
    if os.path.exists(tmp_path):
        try:
            shutil.rmtree(tmp_path)
        except Exception as e:
            logging.error(f"Failed removing {tmp_path}: {e}")

def main():
    if len(sys.argv) < 4:
        logging.error("Usage: python3 pipeline_script.py <PDB_FILE> <OUTPUT_DIR> <ORGANISM> [AGGREGATE_MODE]")
        sys.exit(1)

    pdb_file = sys.argv[1]
    output_dir = sys.argv[2]
    organism = sys.argv[3].lower()
    if organism not in ["human", "ecoli", "test"]:
        logging.error("Invalid organism specified.")
        sys.exit(1)

    # aggregator mode default = skip
    agg_mode = "skip"
    if len(sys.argv) >= 5:
        agg_mode = sys.argv[4].lower()

    try:
        pipeline(pdb_file, output_dir, organism)
    except Exception as e:
        logging.error(f"Pipeline failed on {pdb_file}: {e}")
        sys.exit(1)

    # aggregator if "run"
    if agg_mode == "run":
        logging.warning(f"Aggregator mode active for {organism}.")
        try:
            aggregate_results(output_dir, organism)
        except Exception as e:
            logging.error(f"Aggregator error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
