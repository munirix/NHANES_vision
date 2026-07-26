import pandas as pd
df = pd.read_sas("app/src/data/VIX_D.XPT", format="xport")
print(df.columns.tolist())