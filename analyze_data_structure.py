import json
import os
from datetime import datetime


def analyze_data_files():
    """Analyze the structure of existing data files."""

    print("🔍 Analyzing data file structures...")

    # 1. Analyze Review Files
    print("\n📚 REVIEW FILES STRUCTURE:")
    reviews_folder = "data_review"
    if os.path.exists(reviews_folder):
        sample_file = None
        for filename in os.listdir(reviews_folder):
            if filename.endswith('.json'):
                sample_file = filename
                break

        if sample_file:
            with open(os.path.join(reviews_folder, sample_file), 'r') as f:
                sample_data = json.load(f)

            print(f"Sample file: {sample_file}")
            print("Top-level keys:", list(sample_data.keys()))

            if 'reviews' in sample_data and sample_data['reviews']:
                print("Sample review structure:")
                review = sample_data['reviews'][0]
                for key, value in review.items():
                    print(f"  {key}: {value} (type: {type(value).__name__})")

    # 2. Analyze Price Files
    print("\n💰 PRICE FILES STRUCTURE:")
    price_folder = "price_data"
    if os.path.exists(price_folder):
        sample_file = None
        for filename in os.listdir(price_folder):
            if filename.endswith('.json'):
                sample_file = filename
                break

        if sample_file:
            with open(os.path.join(price_folder, sample_file), 'r') as f:
                sample_data = json.load(f)

            print(f"Sample file: {sample_file}")
            print("Top-level keys:", list(sample_data.keys()))
            print("Sample price structure:")
            for key, value in sample_data.items():
                if isinstance(value, dict):
                    print(f"  {key}: (dict with keys: {list(value.keys())})")
                    for subkey, subvalue in value.items():
                        print(
                            f"    {subkey}: {subvalue} (type: {type(subvalue).__name__})")
                else:
                    print(f"  {key}: {value} (type: {type(value).__name__})")


if __name__ == "__main__":
    analyze_data_files()
