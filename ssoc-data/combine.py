import pandas as pd
import numpy as np

powers = np.linspace(10, 100, 10)
# powers = np.array([10])
runs = [1, 2, 3]
output = "combined-ssoc-data.xlsx"

sheets = []
for power in powers:
    frames = []
    for run in runs:
        filename = f"power-{power:.1f}-run-{run}.csv"
        #print(filename)
        df = pd.read_csv(filename)
        #print(df)
        frames.append(df)

    df = pd.concat(frames, axis=1)
    #print(df)
    sheets.append(df)

for n, sheet in enumerate(sheets):
    with pd.ExcelWriter(output, if_sheet_exists="replace", mode="a") as writer:
        sheet.to_excel(writer, sheet_name=f"{powers[n]}", index=False)
