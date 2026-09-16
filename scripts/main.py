from pathlib import Path
from download_sample_data import download_sample_dataset

SAMPLE_BOOK_IDS = [1342, 11, 84, 174]


def main():
    output_path = Path("sample_data")
    successful, failed = download_sample_dataset(SAMPLE_BOOK_IDS, output_path)
    print(f"\nResults: {len(successful)} succeeded, {len(failed)} failed")


if __name__ == "__main__":
    main()
