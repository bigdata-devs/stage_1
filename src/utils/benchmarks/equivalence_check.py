"""Cross-language equivalence checker: runs the four ports over the same book
sample and the shared query workload, then compares the canonical files byte
by byte. Timing measurements are meaningless until this check passes, so the
benchmark runner must invoke it before any timed phase.

Each port writes three sections: the token stream of every sample book, the
posting lists of the inverted index built from them, and the result of every
shared query. A byte-identical file across languages proves the harness
measures the same work everywhere.
"""

import hashlib
import json
import logging
import shutil
import subprocess
import time
from pathlib import Path

from src.utils.benchmarks import data_source
from src.utils.benchmarks.artifacts import ARTIFACT_ROOT

EQUIVALENCE_DIRECTORY = ARTIFACT_ROOT / "equivalence"
SAMPLE_SIZE = 100
SUBPROCESS_TIMEOUT_SECONDS = 1800
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
QUERIES_PATH = Path(__file__).with_name("queries.txt")
REPORT_PATH = REPOSITORY_ROOT / "benchmarks_results" / "equivalence_report.json"
GO_PORT_DIRECTORY = REPOSITORY_ROOT / "multilang_ports" / "go"
RUST_PORT_DIRECTORY = REPOSITORY_ROOT / "multilang_ports" / "rust"
JAVA_PORT_DIRECTORY = REPOSITORY_ROOT / "multilang_ports" / "java"
BODIES_DIRECTORY = REPOSITORY_ROOT / "data_source" / "bodies"


def run() -> bool:
    """Checks every language against the others and writes the report."""
    sample_ids = select_sample(data_source.book_ids(), SAMPLE_SIZE)
    prepare_directory()
    book_ids_file = write_book_ids(sample_ids)
    outputs = produce_canonical_files(book_ids_file)
    digests = {language: sha256_file(path) for language, path in outputs.items()}
    all_equal = len(set(digests.values())) == 1
    write_report(sample_ids, digests, all_equal)
    report_outcome(outputs, digests, all_equal)
    return all_equal


def select_sample(book_ids: list[int], sample_size: int) -> list[int]:
    """Returns up to sample_size ids evenly spaced over the sorted corpus."""
    ordered = sorted(book_ids)
    if len(ordered) <= sample_size:
        return ordered
    return [ordered[index * (len(ordered) - 1) // (sample_size - 1)]
            for index in range(sample_size)]


def prepare_directory() -> None:
    if EQUIVALENCE_DIRECTORY.exists():
        shutil.rmtree(EQUIVALENCE_DIRECTORY)
    EQUIVALENCE_DIRECTORY.mkdir(parents=True)


def write_book_ids(sample_ids: list[int]) -> Path:
    book_ids_file = EQUIVALENCE_DIRECTORY / "book_ids.txt"
    book_ids_file.write_text(
        "".join(f"{book_id}\n" for book_id in sample_ids), encoding="utf-8")
    return book_ids_file


def produce_canonical_files(book_ids_file: Path) -> dict[str, Path]:
    outputs = {
        "python": EQUIVALENCE_DIRECTORY / "python.txt",
        "go": EQUIVALENCE_DIRECTORY / "go.txt",
        "rust": EQUIVALENCE_DIRECTORY / "rust.txt",
        "java": EQUIVALENCE_DIRECTORY / "java.txt",
    }
    run_python(book_ids_file, outputs["python"])
    run_go(book_ids_file, outputs["go"])
    run_rust(book_ids_file, outputs["rust"])
    run_java(book_ids_file, outputs["java"])
    return outputs


def run_python(book_ids_file: Path, output_file: Path) -> None:
    from src.utils.benchmarks.equivalence import run as run_python_port
    logging.info("equivalence: running python port")
    run_python_port(BODIES_DIRECTORY, book_ids_file, QUERIES_PATH, output_file)


def run_go(book_ids_file: Path, output_file: Path) -> None:
    binary = EQUIVALENCE_DIRECTORY / "search_engine_bench"
    logging.info("equivalence: building go port")
    run_command(["go", "build", "-o", str(binary), "."], GO_PORT_DIRECTORY)
    run_command([str(binary), "equivalence", str(BODIES_DIRECTORY),
                 str(book_ids_file), str(QUERIES_PATH), str(output_file)],
                GO_PORT_DIRECTORY)


def run_rust(book_ids_file: Path, output_file: Path) -> None:
    logging.info("equivalence: building rust port")
    run_command(["cargo", "build", "--quiet", "--bin", "index"], RUST_PORT_DIRECTORY)
    binary = RUST_PORT_DIRECTORY / "target" / "debug" / "index"
    run_command([str(binary), "equivalence", str(BODIES_DIRECTORY),
                 str(book_ids_file), str(QUERIES_PATH), str(output_file)],
                RUST_PORT_DIRECTORY)


def run_java(book_ids_file: Path, output_file: Path) -> None:
    logging.info("equivalence: building and running java port")
    arguments = " ".join(str(path) for path in
                         (BODIES_DIRECTORY, book_ids_file, QUERIES_PATH, output_file))
    run_command(["mvn", "-q", "compile", "exec:java",
                 "-Dexec.mainClass=benchmark.Main",
                 f"-Dexec.args=equivalence {arguments}"], JAVA_PORT_DIRECTORY)


def run_command(command: list[str], working_directory: Path) -> None:
    logging.info("equivalence: %s (cwd %s)", " ".join(command), working_directory)
    result = subprocess.run(
        command, cwd=working_directory, capture_output=True, text=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stderr[-2000:]}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_report(sample_ids: list[int], digests: dict[str, str], all_equal: bool) -> None:
    report = {
        "sample_size": len(sample_ids),
        "book_ids": sample_ids,
        "queries_file": str(QUERIES_PATH.relative_to(REPOSITORY_ROOT)),
        "canonical_sections": [
            "tokens<TAB>book_id<TAB>token...", 
            "postings<TAB>term<TAB>id1,id2,...",
            "query<TAB>ordinal<TAB>id1,id2,...",
        ],
        "languages": {
            language: {
                "canonical_file": f"{EQUIVALENCE_DIRECTORY.name}/{language}.txt",
                "sha256": digest,
            }
            for language, digest in digests.items()
        },
        "all_equal": all_equal,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    logging.info("equivalence: report written to %s", REPORT_PATH)


def report_outcome(outputs: dict[str, Path], digests: dict[str, str], all_equal: bool) -> None:
    for language, digest in digests.items():
        logging.info("equivalence: %s sha256=%s", language, digest)
    if all_equal:
        logging.info("equivalence: all %s languages produced identical files", len(digests))
        return
    languages = sorted(outputs)
    for position in range(1, len(languages)):
        describe_first_difference(outputs[languages[0]], outputs[languages[position]])


def describe_first_difference(expected_path: Path, actual_path: Path) -> None:
    expected_lines = expected_path.read_text(encoding="utf-8").splitlines()
    actual_lines = actual_path.read_text(encoding="utf-8").splitlines()
    for line_number in range(max(len(expected_lines), len(actual_lines))):
        expected = expected_lines[line_number] if line_number < len(expected_lines) else "<missing>"
        actual = actual_lines[line_number] if line_number < len(actual_lines) else "<missing>"
        if expected != actual:
            logging.error("equivalence: %s vs %s first difference at line %s:\n  %s: %s\n  %s: %s",
                          expected_path.stem, actual_path.stem, line_number + 1,
                          expected_path.stem, expected[:200], actual_path.stem, actual[:200])
            return
    logging.error("equivalence: %s vs %s differ only by trailing content",
                  expected_path.stem, actual_path.stem)


def main() -> None:
    from src.utils.benchmarks.logging_setup import configure_logging
    configure_logging()
    if not run():
        raise SystemExit("equivalence check failed: the languages diverge")


if __name__ == "__main__":
    main()
