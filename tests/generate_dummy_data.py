from tax_commander.sample_data import generate_sample_csv

if __name__ == "__main__":
    path = generate_sample_csv("dummy_duplicate.csv")
    print(f"Generated dummy data at: {path}")