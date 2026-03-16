
import os

import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', FutureWarning)

import numpy as np
import pandas as pd

from funzioni import f_settaggio_db
from funzioni import f_log_ciclo_for
from funzioni import f_crea_cartella

connessione = f_settaggio_db()

lista_possibili_cartelle_lavoro = [
    '/media/daniele/Daniele2TB/test/climatologia_OLD',
    '/run/media/daniele.carnevale/Daniele2TB/test/climatologia_OLD',
]

cartella_lavoro = [x for x in lista_possibili_cartelle_lavoro if os.path.exists(x)][0]
os.chdir(cartella_lavoro)
del (lista_possibili_cartelle_lavoro)

# %%
df_stazioni_meteo_clima = pd.read_csv(f'{cartella_lavoro}/df_stazioni_meteo-clima.csv')
df_stazioni_meteo_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] != 'GEPCA'] # Alcune hanno problemi. Le tolgo.
df_stazioni_meteo_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] != 'PANES'] # Alcune hanno problemi. Le tolgo.

cartella_query = f_crea_cartella(f'{cartella_lavoro}/query_meteo')

df_coord_meteo = pd.DataFrame(np.nan, columns=['name', 'lat', 'lon', 'elev'], index=df_stazioni_meteo_clima['Code'])

for s in df_coord_meteo.index:
    # if os.path.exists(f'{cartella_query}/{s}.csv'):
    #     continue
    f_log_ciclo_for([['Query meteo ', s, df_coord_meteo.index.tolist()]])

    query = f"""
    select
    to_char(data_1d.dtrf, 'YYYY-MM-DD HH24:MI:SS') as tempo,
    anag.lon/1e5 as lon,
    anag.lat/1e5 as lat,
    anag.elev as elev,
    anag.name as name,
    tempn/10 as TMIN,
    tempm/10 as TMEAN,
    tempx/10 as TMAX
    
    from
    data_1d,
    anag
    
    where
    data_1d.code = anag.code and
    data_1d.code = '{s}' and
    data_1d.dtrf>=to_date('202101010000', 'YYYYMMDDHH24MI') and
    data_1d.dtrf <= trunc(sysdate) - 1 -- fino a ieri, altrimenti per qualche motivo mi prende anche il "domani" che non posso avere
    
    order by dtrf
    
    """

    df = pd.read_sql(query, con=connessione)

    df_coord_meteo.loc[s, 'name'] = df.iloc[0]['NAME']
    df_coord_meteo.loc[s, 'lat'] = float(df.iloc[0]['LAT'])
    df_coord_meteo.loc[s, 'lon'] = float(df.iloc[0]['LON'])
    df_coord_meteo.loc[s, 'elev'] = float(df.iloc[0]['ELEV'])
    
    df = df.set_index('TEMPO')
    df = df.drop(['NAME', 'LON', 'LAT', 'ELEV'], axis=1)

    df.to_csv(f'{cartella_query}/{s}.csv', index=True, header=True, na_rep=np.nan, mode='w')

df_coord_meteo.to_csv(f'{cartella_lavoro}/df_coord_stazioni_meteo.csv', index=True, header=True, na_rep=np.nan, mode='w')

print('\n\nDone.')
