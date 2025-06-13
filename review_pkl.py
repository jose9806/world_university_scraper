import pandas as pd

file = pd.read_pickle("data/processed/rankings_processed_20250613_161250.pkl")
print(file.head())
print(file.columns)
