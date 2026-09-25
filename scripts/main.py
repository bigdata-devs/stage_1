from pathlib import Path
from download_sample_data import download_sample_dataset

SAMPLE_BOOK_IDS = [1342, 11, 84, 174]
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATA_PATH = REPOSITORY_ROOT / "sample_data"

def main():
    successful, failed = download_sample_dataset(SAMPLE_BOOK_IDS, SAMPLE_DATA_PATH)
    print(f"\nResults: {len(successful)} succeeded, {len(failed)} failed")

if __name__ == "__main__":
    main()
