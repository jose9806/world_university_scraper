import pandas as pd

file = pd.read_pickle("data/processed/rankings_processed_20250313_121234.pkl")
print(file.head())
