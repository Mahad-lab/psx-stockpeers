from psx import tickers
from pathlib import Path

# Get all available tickers with progress bar
print("Loading tickers...")
all_tickers = tickers()
print(f"Found {len(all_tickers)} tickers")

# Save tickers to data folder
data_dir = Path(__file__).parent / "data"
data_dir.mkdir(exist_ok=True)

# # Save to tickers.csv file
# print("Saving tickers.csv...")
# all_tickers.to_csv(data_dir / "tickers.csv", index=False)
# print(f"✓ Saved tickers to {data_dir / 'tickers.csv'}")

# Extract only symbols
symbols = all_tickers[["symbol"]]

# Save to stocks.csv file
print("Saving stocks.csv...")
symbols.to_csv(data_dir / "stocks.csv", index=False)
print(f"Saved {len(symbols)} symbols to {data_dir / 'stocks.csv'}")

print("\nDone!")
