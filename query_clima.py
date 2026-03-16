
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

cartella_query = f_crea_cartella(f'{cartella_lavoro}/query_clima')
intervallo_climatologico = pd.date_range('1991-01-01', '2020-12-31', freq='1d') # questo intervallo è fissato dal WMO, ma se cambio intervallo non mi fa il kriging (tutto NaN)

df_coord_clima = pd.DataFrame(np.nan, columns=['name', 'lat', 'lon', 'elev'], index=df_stazioni_meteo_clima['Code9'])

for s in df_coord_clima.index:
    # if os.path.exists(f'{cartella_query}/{s}.csv'):
    #     continue
    f_log_ciclo_for([['Query clima ', s, df_coord_clima.index.tolist()]])

    query = f"""
    select
    anag_clima.name,
    anag_clima.lon as lon,
    anag_clima.lat as lat,
    anag_clima.elev as elev,
    clima_1d.day,
    tempn/10 as TMIN,
    tempx/10 as TMAX
    
    from
    anag_clima,
    clima_1d
    
    where
    anag_clima.code = clima_1d.code and
    anag_clima.code='{s}'
    
    order by day
    
    """
    
    df = pd.read_sql(query, con=connessione)

    df_coord_clima.loc[s, 'name'] = df.iloc[0]['NAME']
    df_coord_clima.loc[s, 'lat'] = float(df.iloc[0]['LAT'])
    df_coord_clima.loc[s, 'lon'] = float(df.iloc[0]['LON'])
    df_coord_clima.loc[s, 'elev'] = float(df.iloc[0]['ELEV'])
    
    df = df.set_index('DAY')
    df = df.reindex(intervallo_climatologico)
    df = df.drop(['NAME', 'LON', 'LAT', 'ELEV'], axis=1)
    df['TMEAN'] = df.mean(axis=1)
    
    df.to_csv(f'{cartella_query}/{s}.csv', index=True, header=True, na_rep=np.nan, mode='w')
    
df_coord_clima.to_csv(f'{cartella_lavoro}/df_coord_stazioni_clima.csv', index=True, header=True, na_rep=np.nan, mode='w')

print('\n\nDone.')
