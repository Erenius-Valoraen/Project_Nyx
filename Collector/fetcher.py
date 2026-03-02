import pyarrow.parquet as pq
df = pq.read_table("data/2026-03-02/2885_04.23.56_11rows.parquet").to_pandas()
print(df)