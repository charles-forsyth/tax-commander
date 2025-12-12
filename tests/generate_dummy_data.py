import sys
import os

# Add src to path so we can import the package module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from tax_commander.sample_data import generate_sample_csv

if __name__ == "__main__":
    path = generate_sample_csv("dummy_duplicate.csv")
    print(f"Generated dummy data at: {path}")
