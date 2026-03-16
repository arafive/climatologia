
import os
import cfgrib

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from cartopy.io.shapereader import Reader

from shapely.geometry import Point
from shapely.prepared import prep

def f_dataframe_ds_variabili(lista_ds):
    """Ritorna il dataframe che lega dataset alle variabili.
    
    Parameters
    ----------
    lista_ds : list
        Lista che contiene i vari dataset.

    Returns
    -------
    df_attributi : pandas.core.frame.DataFrame
        Il dataframe che contiene gli attributi, oltre
        all'indice del dataset che contiene quella variabile.

    """
    df_attrs = pd.DataFrame()
    
    for i, ds in enumerate(lista_ds):
        for v in [x for x in ds.data_vars]:
            df_attrs = pd.concat([df_attrs, pd.DataFrame({**{'id_ds': i}, **ds[v].attrs}, index=[v])])
            
    ### Elimino le colonne i cui valori sono comuni a tutte le righe
    for i in df_attrs:
        if len(set(df_attrs[i].tolist())) == 1:
            df_attrs = df_attrs.drop(columns=[i])
    
    df_attrs = df_attrs.drop(columns=['long_name']) # doppione di 'GRIB_name'
    df_attrs = df_attrs.drop(columns=['standard_name']) # doppione di 'GRIB_cfName'
    df_attrs = df_attrs.drop(columns=['GRIB_cfName']) # non ha importanza, sono quasi tutti 'unknown'
    df_attrs = df_attrs.drop(columns=['units']) # doppione di 'GRIB_units'
    df_attrs = df_attrs.drop(columns=['GRIB_shortName', 'GRIB_cfVarName']) # doppioni dell'index
    
    if 'GRIB_dataType' not in df_attrs:
        df_attrs['GRIB_dataType'] = 'fc' # Nei grib più recenti 'an' e 'fc' sono uniti

    return df_attrs

plt.rc('font', family='DejaVu Sans', weight='normal', size=8)

lista_possibili_cartelle_lavoro = [
    '/media/daniele/Daniele2TB/test/climatologia',
    '/run/media/daniele.carnevale/Daniele2TB/test/climatologia',
]

cartella_lavoro = [x for x in lista_possibili_cartelle_lavoro if os.path.exists(x)][0]
os.chdir(cartella_lavoro)
del (lista_possibili_cartelle_lavoro)

lista_possibili_ARC_STORICO = [
    '/media/daniele/Daniele2TB/test/piccolo_ARC_STORICO',
    '/mnt/ARC_STORICO'
]

cartella_ARC_STORICO = [x for x in lista_possibili_ARC_STORICO if os.path.exists(x)][0]
del (lista_possibili_ARC_STORICO)

regioni = Reader('./../shapefile/gadm41_ITA_shp/gadm41_ITA_1.shp')

for r in regioni.records():
    if r.attributes['NAME_1'] == 'Liguria':
        liguria = r.geometry
        break

### Preparo la geometria dello shapefile (velocizza i test di inclusione)
prepared_shape = prep(liguria)

# %%
oggi = pd.to_datetime('2025-06-30')
cartella_file = f"{cartella_ARC_STORICO}/ECMWF/{oggi.strftime('%Y/%m/%d')}"

df_spaghetti = pd.DataFrame()

for n_membro in range(1, 51):
    nome_file = f"ecmf_0.2_{oggi.strftime('%Y%m%d%H')}_91x81_2_20_34_50_pf_{n_membro}.grb"
    assert os.path.exists(f'{cartella_file}/{nome_file}'), f'Non ho trovato il file {cartella_file}/{nome_file}'

    print(f'Apro il file {cartella_file}/{nome_file}...')
    lista_ds = cfgrib.open_datasets(f'{cartella_file}/{nome_file}', backend_kwargs={'decode_timedelta': True, 'indexpath': f"/tmp/{nome_file}_lista_ds.idx"})
    
    if n_membro == 1:
        df_attrs = f_dataframe_ds_variabili(lista_ds)
        lon_2D, lat_2D = np.meshgrid(lista_ds[0]['longitude'].values, lista_ds[0]['latitude'].values)
        flat_lat = lat_2D.ravel()
        flat_lon = lon_2D.ravel()
        
        df_var = df_attrs.loc[df_attrs.index == 't2m']
        ind_var = df_var['id_ds'].iloc[0]
        tempi = pd.to_datetime(lista_ds[ind_var]['valid_time'].values)
        print(tempi)

        mask_in_liguria = np.array([prepared_shape.contains(Point(lon, lat)) for lon, lat in zip(flat_lon, flat_lat)])
    
    np_var = lista_ds[ind_var]['t2m'].values
    
    n_tempi = np_var.shape[0]
    media_nel_tempo = np.empty(n_tempi)
    
    for t in range(n_tempi):
        flat_data_t = np_var[t].ravel()
        media_nel_tempo[t] = flat_data_t[mask_in_liguria].mean()
        
    media_nel_tempo = media_nel_tempo - 273.15
        
    df_spaghetti[f'{n_membro:02d}'] = media_nel_tempo
    
df_spaghetti.index = tempi

df = pd.DataFrame({'perc_25': df_spaghetti.quantile(0.25, axis=1), 'perc_75': df_spaghetti.quantile(0.75, axis=1)})
df['media'] = df_spaghetti.mean(axis=1)

df = df.resample('D').mean()
df.to_csv(f"{cartella_lavoro}/df_ensemble_t2m_{oggi.strftime('%Y-%m-%d')}.csv", index=True, header=True, na_rep=np.nan, mode='w')

print('\n\nDone.')