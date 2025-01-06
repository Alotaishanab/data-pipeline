import pytest
import os
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path

# Assuming pipeline_script.py is in your PYTHONPATH or a package:
from pipeline_script import pipeline, aggregate_results

@pytest.fixture
def fake_input_pdb(tmp_path):
    """Create a fake PDB file in a temp directory."""
    pdb_file = tmp_path / "fake.pdb"
    pdb_file.write_text("FAKE PDB CONTENT\n")
    return str(pdb_file)

@pytest.fixture
def fake_output_dir(tmp_path):
    """Provide an output directory path."""
    out_dir = tmp_path / "results"
    out_dir.mkdir(exist_ok=True)
    return str(out_dir)

@pytest.mark.parametrize("organism", ["human", "ecoli", "test"])
def test_pipeline_runs_with_mocked_merizo_and_parser(fake_input_pdb, fake_output_dir, organism):
    """
    Test the pipeline() function with a mocked run of Merizo Search and Parser.
    We patch the internal calls so no real external processes run.
    """

    # Mock out the Merizo search part
    with patch("pipeline_script.run_merizo_search") as mock_merizo:
        mock_merizo.return_value = "/some/fake/path_search.tsv"
        # Mock out the parser part
        with patch("pipeline_script.run_parser") as mock_parser:
            pipeline(fake_input_pdb, fake_output_dir, organism)
            
            # Check that run_merizo_search was called
            mock_merizo.assert_called_once()
            # Check that run_parser was called
            mock_parser.assert_called_once()

def test_pipeline_no_pdb_file(tmp_path):
    """If the PDB file doesn't exist, pipeline() prints an error and returns without throwing an exception."""
    pdb_file = str(tmp_path / "nonexistent.pdb")
    out_dir = str(tmp_path / "results")
    os.mkdir(out_dir)

    # We'll just call pipeline() and ensure it doesn't raise an exception.
    # In your real code, pipeline() might sys.exit(1), so you'd need to patch sys.exit or catch the SystemExit exception.
    pipeline(pdb_file, out_dir, "test")
    # If we reach here without an uncaught exception, the test passes.

def test_aggregate_results(tmp_path):
    """
    Test aggregate_results() by creating some .parsed files in the output directory
    and verifying the aggregated output is generated.
    """
    out_dir = tmp_path / "results"
    out_dir.mkdir()

    # Create a couple of .parsed files
    parsed_file_1 = out_dir / "example1.parsed"
    parsed_file_2 = out_dir / "example2.parsed"

    # Write a mock header + data
    parsed_file_1.write_text(
        "#example1_search.tsv Results. mean plddt: 50.0\n"
        "cath_id,count\n"
        "1abc,3\n"
        "2xyz,5\n"
    )

    parsed_file_2.write_text(
        "#example2_search.tsv Results. mean plddt: 70.0\n"
        "cath_id,count\n"
        "3def,2\n"
    )

    # Now call aggregate_results()
    aggregate_results(str(out_dir), "human")

    # Check that the summary file got created
    cath_summary = out_dir / "human_cath_summary.csv"
    assert cath_summary.exists(), "Expected CATH summary CSV not found."
    summary_content = cath_summary.read_text()
    assert "1abc,3" in summary_content
    assert "2xyz,5" in summary_content
    assert "3def,2" in summary_content

    # Check that plDDT_means.csv is appended in /mnt/results (mocked here).
    # We'll just check if the file is in tmp_path/mnt/results because we aren’t 
    # actually mounting /mnt in a test environment. Let's mimic that path:
    mock_mnt = tmp_path / "mnt" / "results"
    # If your code strictly writes to "/mnt/results", you'll need to patch that path or do an integration test.

    # Just to illustrate, let's check if the pipeline_script wrote the file somewhere:
    # In reality, you'd probably patch 'os.path.exists' or patch the open call to test this thoroughly.

    # We'll skip that check if your code truly writes to an absolute /mnt path. 
    # For local tests, consider parameterizing that path so you can override it in tests.


@pytest.mark.parametrize("organism", ["human", "ecoli", "test"])
def test_aggregate_results_with_no_parsed_files(tmp_path, organism):
    """
    If no *.parsed files exist, aggregate_results should still create the 
    <organism>_cath_summary.csv (empty) and append to plDDT_means.csv with zero values.
    """
    out_dir = tmp_path / "results"
    out_dir.mkdir()

    # Directory is empty, no parsed files.
    aggregate_results(str(out_dir), organism)

    # Check the summary file
    summary_file = out_dir / f"{organism}_cath_summary.csv"
    assert summary_file.exists(), "Expected summary CSV not created even if no parsed files."

    # Check if it has only header
    content = summary_file.read_text().strip().splitlines()
    assert len(content) == 1, "Expected only 1 header row if no parsed data."
    assert content[0] == "cath_id,count"

    # For plDDT_means.csv => same note about absolute /mnt path. 
    # You might want to patch that or verify manually in an integration test.
