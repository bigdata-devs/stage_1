"""Global entry point for the Stage 1 search engine pipeline.

Runs the control layer with the real datalake downloader and datamart
indexer. Usage: python main.py [--steps N]
"""

from src.control.__main__ import main

if __name__ == "__main__":
    main()
