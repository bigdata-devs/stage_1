import logging
from src.utils.benchmarks import data_source, datalake_experiments, inverted_index_experiments, metadata_experiments
from src.utils.benchmarks.logging_setup import configure_logging

def main():
    data_source.prepare_books()
    skipped = datalake_experiments.run()
    skipped.extend(inverted_index_experiments.run())
    skipped.extend(metadata_experiments.run())
    logging.info("Skipped experiments: %s", ", ".join(skipped) if skipped else "none")

if __name__ == "__main__":
    configure_logging()
    main()
