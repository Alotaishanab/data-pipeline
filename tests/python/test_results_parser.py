import pytest
import os
from unittest.mock import patch
from pathlib import Path
import sys

# If results_parser.py is in your PYTHONPATH or a package:
import results_parser

@pytest.fixture
def fake_search_file(tmp_path):
    """Create a fake _search.tsv file."""
    search_file = tmp_path / "fake_search.tsv"
    content = (
        "header1\theader2\theader3\tplDDT\theader5\theader6\theader7\theader8\theader9\theader10\theader11\theader12\theader13\theader14\theader15\tmeta\n"
        "row1col1\trow1col2\trow1col3\t55.0\t...\t...\t...\t...\t...\t...\t...\t...\t...\t...\t... \t{\"cath\":\"1abc\"}\n"
        "row2col1\trow2col2\trow2col3\t65.5\t...\t...\t...\t...\t...\t...\t...\t...\t...\t...\t... \t{\"cath\":\"2xyz\"}\n"
    )
    search_file.write_text(content)
    return str(search_file)

def test_results_parser_valid_input(tmp_path, fake_search_file):
    """Test the main logic with a valid _search.tsv file."""
    output_dir = tmp_path / "results"
    output_dir.mkdir()

    # We’ll call results_parser.main directly.
    # We'll need to patch sys.argv to mimic command-line usage.
    test_args = ["results_parser.py", str(output_dir), fake_search_file]
    
    with patch.object(sys, 'argv', test_args):
        # This calls main(), which should parse the file and produce a .parsed output
        results_parser.main()

    # The parser should create <id>.parsed file in output_dir
    parsed_filename = os.path.join(str(output_dir), "fake.parsed")
    assert os.path.isfile(parsed_filename), "Parsed file was not created."

    # Check file contents
    parsed_content = Path(parsed_filename).read_text()
    assert "mean plddt: 60.25" in parsed_content  # average of 55.0 and 65.5
    assert "1abc,1" in parsed_content
    assert "2xyz,1" in parsed_content

def test_results_parser_no_data(tmp_path):
    """
    If the search file has only a header or is empty, 
    results_parser should exit gracefully without creating a .parsed file.
    """
    output_dir = tmp_path / "results"
    output_dir.mkdir()

    empty_search_file = tmp_path / "empty_search.tsv"
    empty_search_file.write_text("header1\theader2\theader3\tplDDT\t...\n")

    test_args = ["results_parser.py", str(output_dir), str(empty_search_file)]
    
    with patch.object(sys, 'argv', test_args):
        # Attempt to parse an empty file
        results_parser.main()

    # Should not create a .parsed file because there is no data beyond the header
    parsed_filename = os.path.join(str(output_dir), "empty.parsed")
    assert not os.path.exists(parsed_filename), "Parser created a parsed file unexpectedly for empty data."

def test_results_parser_missing_file(tmp_path):
    """If the search file doesn't exist, results_parser should error out (sys.exit)."""
    output_dir = tmp_path / "results"
    missing_file = str(tmp_path / "no_such_file_search.tsv")

    test_args = ["results_parser.py", str(output_dir), missing_file]
    with patch.object(sys, 'argv', test_args), pytest.raises(SystemExit):
        results_parser.main()
    # We expect a SystemExit because the script calls sys.exit(1) if the file is missing.
