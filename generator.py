import pandas as pd

file_tipi_gov = "tipi_gov.xlsx"

wb_tipi_gov = pd.ExcelFile(file_tipi_gov)

df_tipi_gov = wb_tipi_gov.parse()
print(df_tipi_gov)