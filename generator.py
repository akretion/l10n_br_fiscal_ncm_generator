# Links para download das tabelas:
# TIPI: https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/legislacao/documentos-e-arquivos/tipi-em-excel.xlsx/view
# uTrib: http://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=qXcw9P1RW80=


import pandas as pd
from decimal import Decimal
import csv

file_tipi_gov = "tipi_gov.xlsx"
wb_tipi_gov = pd.ExcelFile(file_tipi_gov)
df_tipi = wb_tipi_gov.parse(header=7)
df_tipi.columns = ['ncm', 'exception', 'desc', 'ipi']

df_tipi = df_tipi.astype({'exception':'str'})
df_tipi["exception"] = df_tipi["exception"].str.zfill(2)

df_old = pd.read_csv('old_l10n_br_fiscal.ncm.csv')

for i, row in df_tipi.iterrows():
    elements = str(row["ncm"]).split(".")
    if len(elements[0]) % 2 != 0:
        elements[0] = "0" + elements[0]
    df_tipi.at[i,"ncm"] = "".join(elements)

    if row["exception"] == "nan":
        df_tipi.at[i,"exception"] = ""

for i, row in df_tipi.iterrows():
    ncm = row["ncm"]
    if len(ncm) != 8:
        continue

    concat_desc = ""
    parts = [ncm[0:4],ncm[0:5],ncm[0:6],ncm[0:7],ncm[0:8]]
    for part in parts:
        result = df_tipi.query(f"ncm =='{part}'")
        if not result.empty:
            part_name = result["desc"].iloc[0]
            concat_desc = f"{concat_desc} {part_name}"
    df_tipi.at[i, "concat_desc"] = concat_desc[1:-1]

df_tipi = df_tipi.loc[df_tipi['ncm'].str.len() == 8]

df = pd.DataFrame()

file_tipi_gov = "tabela_nfe_um.xlsx"
wb_tipi_gov = pd.ExcelFile(file_tipi_gov)
df_um = wb_tipi_gov.parse()
df_um = df_um.iloc[:, [0,3]]
df_um.columns = ['ncm', 'um']
df_um = df_um.astype({'ncm':'str'})
df_um["ncm"] = df_um["ncm"].str.zfill(8)

rep = {
    "UN": "uom.product_uom_unit",
    "KG": "uom.product_uom_kgm",
    "DUZIA": "uom.product_uom_dozen",
    "G": "uom.product_uom_gram",
    "TON": "uom.product_uom_ton",
    "LT": "uom.product_uom_litre",
    "1000UN": "UOM_UN1000",
    "M3": "UOM_M3",
    "MWHORA": "UOM_MWH",
    "QUILAT": "UOM_QUILATE",
    "M2": "UOM_M2",
    "METRO": "uom.product_uom_meter",
    "PARES": "UOM_PARES",
}

df_um["um"] = df_um["um"].replace(rep)

for i, row in df_tipi.iterrows():
    odoo_id = f"ncm_{row['ncm']}"
    if row['exception'] != "":
        ncm_exception = row['exception'].replace(" ", "_").lower()
        odoo_id = f"{odoo_id}_{ncm_exception}"
    df.at[i, "id"] = odoo_id
    df.at[i, "code"] = f"{row['ncm'][:4]}.{row['ncm'][4:6]}.{row['ncm'][6:8]}"
    df.at[i, "exception"] = row['exception'].replace("Ex ", "")
    df.at[i, "name"] = row['concat_desc']
    ipi_value = row['ipi']
    if isinstance(ipi_value, float):
        ipi_value = Decimal(round(ipi_value, 2)).normalize()
        ipi_value = float(ipi_value)
    ipi = str(ipi_value).lower().replace(".","_")
    df.at[i, "tax_ipi_id:id"] = f"tax_ipi_{ipi}"  
    result = df_old.query(f"id =='{odoo_id}'")
    if not result.empty:
        ii = result["tax_ii_id:id"].iloc[0]
        df.at[i, "tax_ii_id:id"] = ii
    ncm = row['ncm']
    result = df_um.query(f"ncm =='{ncm}'")
    if not result.empty:
        um = result["um"].iloc[0]
        df.at[i, "uoe_id:id"] = um

df["active"] = True

df.loc[-1] = "ncm_00000000", "0000.00.00", "", "Sem NCM", "", "", "", "True"
df.index = df.index + 1
df.sort_index(inplace=True) 

df2 = df_old.loc[~df_old['id'].isin(df['id'])].copy()
df2["active"] = False

df_final = pd.concat([df, df2], join="inner")

# A NCM 94032000 está vindo com valor do ipi sem nenhuma informação na tabela TIPI, então estou forçando a mesma informação das NCMS do mesmo grupo.
index = df_final.loc[df_final['id'] == 'ncm_94032000'].index
df_final.loc[index, 'tax_ipi_id:id'] = 'tax_ipi_3_25'

df_final.to_csv('l10n_br_fiscal.ncm.csv', quoting=csv.QUOTE_ALL, index=False)

######################################
# PARTE 2, GERANDO IMPOSTOS QUE FALTAM
######################################

# Carregue os dois arquivos CSV nas respectivas DataFrames
ncm_df = pd.read_csv('l10n_br_fiscal.ncm.csv')
tax_df = pd.read_csv('old_l10n_br_fiscal.tax.csv')

# Extraia os IDs de imposto IPI da tabela NCM
ipi_ids_ncm = ncm_df['tax_ipi_id:id'].unique()

# Verifique se os IDs de imposto IPI existem na tabela de impostos
for ipi_id in ipi_ids_ncm:
    if isinstance(ipi_id, str) and ipi_id not in tax_df['id'].values:
        # Se não existir, adicione-o à tabela de impostos
        ipi_percentage = ipi_id.split("_")[2:]
        ipi_percentage = ".".join(ipi_percentage).replace('_', '')

        new_row = pd.DataFrame({
            'id': [ipi_id],
            'name': [f'IPI {ipi_percentage}%'],
            'tax_base_type': ['percent'],
            'percent_amount': [float(ipi_percentage)],
            'percent_reduction': [0.00],
            'tax_group_id:id': ['tax_group_ipi'],
            'cst_in_id:id': ['cst_ipi_00'],
            'cst_out_id:id': ['cst_ipi_50'],
            'value_amount': [''],
            'currency_id:id': [''],
            'uot_id:id': [''],
            'percent_debit_credit': [''],
            'icms_base_type': ['0'],
            'icmsst_base_type': ['4'],
            'icmsst_mva_percent': [''],
            'icmsst_value': ['']
        })
        tax_df = pd.concat([tax_df, new_row], ignore_index=True)
        
tax_df = tax_df.drop(tax_df.loc[tax_df['id'] == 'tax_ipi_nan'].index)  
tax_df[['percent_amount', 'percent_reduction']] = tax_df[['percent_amount', 'percent_reduction']].applymap(lambda x: f'{x:.2f}')
tax_df = tax_df.sort_values('id')
tax_df.to_csv('l10n_br_fiscal.tax.csv', index=False, quoting=csv.QUOTE_ALL)
with open('l10n_br_fiscal.tax.csv', 'r') as file:
    filedata = file.read()

# Substituir todas as ocorrências de aspas vazias por vazios
# É preciso atenção caso tenha algum caso que seja necessário duas aspas juntas '""'
filedata = filedata.replace('""', '')

with open('l10n_br_fiscal.tax.csv', 'w') as file:
    file.write(filedata)
