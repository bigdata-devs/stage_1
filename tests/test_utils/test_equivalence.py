from pathlib import Path

from src.utils.benchmarks.equivalence import parse_book_ids, run
from src.utils.benchmarks.equivalence_check import select_sample
from src.utils.benchmarks.queries import parse_queries
from src.utils.text_processor import process_text


def test_parse_queries_keeps_terms_and_drops_comments():
    text = "# comment\n\nalpha beta # trailing note\n\ngamma\n"

    queries = parse_queries(text)

    assert queries == [["alpha", "beta"], ["gamma"]]


def test_select_sample_picks_evenly_spaced_ids():
    book_ids = list(range(1, 101))

    sample = select_sample(book_ids, 10)

    assert sample == [1, 12, 23, 34, 45, 56, 67, 78, 89, 100]


def test_select_sample_returns_every_id_when_corpus_is_small():
    book_ids = [7, 3, 5]

    sample = select_sample(book_ids, 10)

    assert sample == [3, 5, 7]


def test_parse_book_ids_ignores_blank_lines(tmp_path: Path):
    book_ids_file = tmp_path / "ids.txt"
    book_ids_file.write_text("11\n\n84\n 1342 \n", encoding="utf-8")

    assert parse_book_ids(book_ids_file) == [11, 84, 1342]


def test_equivalence_file_has_the_three_canonical_sections(tmp_path: Path):
    bodies = tmp_path / "bodies"
    bodies.mkdir()
    (bodies / "1_body.txt").write_text("alpha beta alpha", encoding="utf-8")
    (bodies / "2_body.txt").write_text("beta gamma", encoding="utf-8")
    ids_file = tmp_path / "ids.txt"
    ids_file.write_text("1\n2\n", encoding="utf-8")
    queries_file = tmp_path / "queries.txt"
    queries_file.write_text("alpha beta\nbeta delta\n", encoding="utf-8")
    output_file = tmp_path / "out.txt"

    run(bodies, ids_file, queries_file, output_file)

    lines = output_file.read_text(encoding="utf-8").splitlines()
    first_tokens, second_tokens = lines[0], lines[1]
    assert first_tokens == "tokens\t1\t" + "\t".join(
        process_text("alpha beta alpha"))
    assert second_tokens == "tokens\t2\t" + "\t".join(process_text("beta gamma"))
    assert "postings\talpha\t1" in lines
    assert "postings\tbeta\t1,2" in lines
    assert lines[-2] == "query\t1\t1"
    assert lines[-1] == "query\t2"
