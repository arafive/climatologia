
import numpy as np
import pandas as pd

cartella = '/mnt/isilon-arpal/agcmi00a00_comune/archivio/Archivio_CLIMA/dati_storici_Chiavari/Dati'

df = pd.read_excel(f'{cartella}/registro misure di OZONO.xls', sheet_name='dati numerici')

date = [f'{x}-{y}-{z}' for x,y,z in zip(df['anno'], df['mese'], df['giorno'])]
date = pd.to_datetime(date)
date = date - pd.Timedelta(days=1)

date_21 = date + pd.Timedelta(hours=21)
date_09 = date + pd.Timedelta(hours=9)

date_tot = sorted(pd.DatetimeIndex(np.concatenate([date_21, date_09])))

df_nuovo = pd.DataFrame(np.nan, index=date_tot, columns=['numero Schoenbein', 'Umidità'])
