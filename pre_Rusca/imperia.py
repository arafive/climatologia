
import datetime

import numpy as np
import pandas as pd

def _e_numero(c):
    try:
        float(c)
        return True
    except (ValueError, TypeError):
        return False
    
cartella = '/mnt/isilon-arpal/agcmi00a00_comune/archivio/Archivio_CLIMA/dati_storici_Imperia_1875-2026'

df_TEMPN = pd.read_excel(f'{cartella}/Temp_giornaliera_Imperia_1875-2026.xls', sheet_name='minime', index_col=0)
df_TEMPX = pd.read_excel(f'{cartella}/Temp_giornaliera_Imperia_1875-2026.xls', sheet_name='massime', index_col=0)
df_RAINC = pd.read_excel(f'{cartella}/Pioggia_giornaliera_Imperia_1940-2026.xls', index_col=0)

################

df_TEMPN = df_TEMPN[[type(idx) is datetime.datetime for idx in df_TEMPN.index]]
df_TEMPN.index = pd.to_datetime(df_TEMPN.index)
df_TEMPN = df_TEMPN[[c for c in df_TEMPN.columns if _e_numero(c)]]
df_TEMPN.columns = [int(x) for x in df_TEMPN.columns]

df_TEMPX = df_TEMPX[[type(idx) is datetime.datetime for idx in df_TEMPX.index]]
df_TEMPX.index = pd.to_datetime(df_TEMPX.index)
df_TEMPX = df_TEMPX[[c for c in df_TEMPX.columns if _e_numero(c)]]
df_TEMPX.columns = [int(x) for x in df_TEMPX.columns]

df_RAINC = df_RAINC.fillna(0)
df_RAINC = df_RAINC[[type(idx) is datetime.datetime for idx in df_RAINC.index]]
df_RAINC.index = pd.to_datetime(df_RAINC.index)
df_RAINC = df_RAINC[[c for c in df_RAINC.columns if _e_numero(c)]]
df_RAINC.columns = [int(x) for x in df_RAINC.columns]

range_tempi_temp = pd.date_range('1875-01-01', '2026-06-30', freq='1d')
range_tempi_rain = pd.date_range('1940-01-01', '2026-06-30', freq='1d')

df_tot = pd.DataFrame(np.nan, index=range_tempi_temp, columns=['TEMPN', 'TEMPX', 'RAINC'])

for tempo in range_tempi_temp:
    print(tempo)
    try:
        riga_tempo = df_TEMPN[(df_TEMPN.index.month == tempo.month) & (df_TEMPN.index.day == tempo.day)].index
        df_tot.loc[tempo, 'TEMPN'] = df_TEMPN.loc[riga_tempo[0], tempo.year]
    except IndexError:
        df_tot.loc[tempo, 'TEMPN'] = np.nan
    
    try:
        riga_tempo = df_TEMPX[(df_TEMPX.index.month == tempo.month) & (df_TEMPX.index.day == tempo.day)].index
        df_tot.loc[tempo, 'TEMPX'] = df_TEMPX.loc[riga_tempo[0], tempo.year]
    except IndexError:
        df_tot.loc[tempo, 'TEMPX'] = np.nan

for tempo in range_tempi_rain:
    print(tempo)
    riga_tempo = df_RAINC[(df_RAINC.index.month == tempo.month) & (df_RAINC.index.day == tempo.day)].index
    df_tot.loc[tempo, 'RAINC'] = df_RAINC.loc[riga_tempo[0], tempo.year]
    
df_tot = df_tot.apply(pd.to_numeric, errors='coerce')

# %%

for colonna in df_tot:
    print(colonna)
    df = df_tot[colonna].copy().to_frame()
    if colonna == 'RAINC':
        df = df.loc['1940-01-01':]
    df.index = [f'{x.year}{x.month:02d}{x.day:02d}' for x in df.index]
    df['stazione'] = 'IMPER'
    df['var'] = colonna
    df[colonna] = (df[colonna] * 10).round().astype('Int64').astype(str).replace('<NA>', np.nan)
    
    df = df[['stazione', 'var', colonna]]
    df.to_csv(f'{cartella}/{colonna}.pre', index=True, header=False, sep='\t')

    # sss
    
    
    
    # df[colonna] = [str(x*10) for x in df[colonna]]























print('\n\nDone')