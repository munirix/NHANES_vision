import pandas as pd
df = pd.read_sas("app/src/data/NHANES/2005-2006/VIX_D.XPT", format="xport")
print(df.columns.tolist())