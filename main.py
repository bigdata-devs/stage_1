"""Global entry point for the Stage 1 search engine pipeline.

Until the datalake and datamart modules are integrated, it runs the control
layer with mock downloader and indexer callbacks. Usage: python main.py
"""

from src.control.__main__ import main

if __name__ == "__main__":
    main()
