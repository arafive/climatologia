
import os

import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', FutureWarning)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

from scipy.stats import gaussian_kde

from matplotlib.colors import TwoSlopeNorm
from matplotlib.colors import LinearSegmentedColormap

from cartopy.io.shapereader import Reader

from adjustText import adjust_text

lista_possibili_cartelle_lavoro = [
    '/media/daniele/Daniele2TB/test/climatologia',
    '/run/media/daniele.carnevale/Daniele2TB/test/climatologia',
]

cartella_lavoro = [x for x in lista_possibili_cartelle_lavoro if os.path.exists(x)][0]
os.chdir(cartella_lavoro)
del (lista_possibili_cartelle_lavoro)

from funzioni import f_settaggio_db
from funzioni import f_log_ciclo_for

connessione = f_settaggio_db()

from matplotlib import font_manager
# font_files = font_manager.findSystemFonts(fontpaths='./../Gill_Sans')
font_files = font_manager.findSystemFonts(fontpaths='./../NotesEsa_font')
for font_file in font_files:
    font_manager.fontManager.addfont(font_file)

# plt.rc('font', family='Gill Sans', weight='normal', size=6)
plt.rc('font', family='NotesEsa', weight='normal', size=7)

plt.rc('axes', unicode_minus=False)

colori = [
    '#08306b', '#084184', '#08519c', '#1561A9', '#2171b5', '#3282BE', '#4292c6', '#57A0CE', '#6baed6', '#85BCDC', '#9ecae1', '#B2D3E8', '#c6dbef', '#D2E3F3', '#deebf7',
    ###
    '#fee0d2', '#FDCEBA', '#fcbba1', '#FCA78A', '#fc9272', '#FC7E5E', '#fb6a4a', '#F5533B', '#ef3b2c', '#DD2A25', '#cb181d', '#B81419', '#a50f15', '#860811', '#67000d',
]

# colori = [
#     '#2a71b2', '#6bacd1', '#c2ddec',
#     ###
#     '#f9f9f9',
#     ###
#     '#fbccb4', '#e48066', '#ba2832',
# ]

cmap_continua = LinearSegmentedColormap.from_list('cmap_continua', colori)

regioni = Reader('./../shapefile/gadm41_ITA_shp/gadm41_ITA_1.shp')

for r in regioni.records():
    if r.attributes['NAME_1'] == 'Liguria':
        print(r.attributes)
        
# %%

# https://climate.copernicus.eu/GCH2025-graphics-gallery

df_stazioni_meteo_clima = pd.read_csv(f'{cartella_lavoro}/df_stazioni_meteo-clima.csv')
df_stazioni_meteo_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] != 'GEPCA'] # Alcune hanno problemi. Le tolgo.
df_stazioni_meteo_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] != 'PANES'] # Alcune hanno problemi. Le tolgo.

df_coord_clima = pd.DataFrame(np.nan, columns=['name', 'lat', 'lon', 'elev'], index=df_stazioni_meteo_clima['Code9'])
df = pd.DataFrame(np.nan, columns=['name', 'lat', 'lon', 'elev'], index=df_stazioni_meteo_clima['Code'])

# Prendo tutte quelle OMIRL
df_coord_meteo = pd.read_csv(f'{cartella_lavoro}/../query_db_osservati_AIxtreme/Osservazioni_Liguria/df_coordinate_Liguria.csv', index_col=0)[['Name', 'Latitude', 'Longitude', 'Altitude', 'is_temperatura']]
df_coord_meteo = df_coord_meteo[df_coord_meteo['is_temperatura']]
df_coord_meteo = df_coord_meteo[['Name', 'Latitude', 'Longitude', 'Altitude']]
df_coord_meteo.columns = ['name', 'lat', 'lon', 'elev']
df_coord_meteo = pd.concat([df_coord_meteo, df], axis=0)
df_coord_meteo = df_coord_meteo.loc[~df_coord_meteo.index.duplicated(keep='first')]
del (df)

df_tot_meteo = pd.DataFrame()
df_tot_clima = pd.DataFrame()

### Query meteo

for s in df_coord_meteo.index:
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
    data_1d.code = '{s}'
    
    order by dtrf
    
    """

    df = pd.read_sql(query, con=connessione)

    df_coord_meteo.loc[s, 'name'] = df.iloc[0]['NAME']
    df_coord_meteo.loc[s, 'lat'] = float(df.iloc[0]['LAT'])
    df_coord_meteo.loc[s, 'lon'] = float(df.iloc[0]['LON'])
    df_coord_meteo.loc[s, 'elev'] = float(df.iloc[0]['ELEV'])
    
    df = df.set_index('TEMPO')
    df = df.drop(['NAME', 'LON', 'LAT', 'ELEV'], axis=1)

    df.index = pd.to_datetime(df.index)
    
    df = df[['TMIN', 'TMAX']]
    df.columns = [f'{x}_{s}' for x in df.columns]
    
    df_tot_meteo = pd.concat([df_tot_meteo, df], axis=1)
    
df_tot_meteo.index = pd.to_datetime(df_tot_meteo.index)
df_tot_meteo = df_tot_meteo.sort_index()
df_tot_meteo = df_tot_meteo[df_tot_meteo.index.year >= 2000]

del (df, s)

### Query clima

for s in df_coord_clima.index:
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
    df = df.drop(['NAME', 'LON', 'LAT', 'ELEV'], axis=1)
    df['TMEAN'] = df.mean(axis=1)

    df.index = pd.to_datetime(df.index)
    
    df = df[['TMIN', 'TMAX']]
    df.columns = [f'{x}_{s}' for x in df.columns]
    
    df_tot_clima = pd.concat([df_tot_clima, df], axis=1)
    
df_tot_clima.index = pd.to_datetime(df_tot_clima.index)
df_tot_clima = df_tot_clima.sort_index()

del (df, s)

# Per allineare le due tabelle (ho chiesto a Marco)
df_tot_meteo.index = df_tot_meteo.index - pd.Timedelta(days=1)

anno_corrente = pd.Timestamp.now().year
df_tot_meteo = df_tot_meteo[df_tot_meteo.index.year != anno_corrente]

# %%
stazioni_scelte = ['UNIGE', 'INASV', 'IMPER', 'CHIRI', 'SPZIA']
df_coord_meteo = pd.read_csv(f'{cartella_lavoro}/df_coord_stazioni_meteo.csv', index_col=0).loc[stazioni_scelte]

mapping = dict(zip(df_stazioni_meteo_clima['Code9'], df_stazioni_meteo_clima['Code']))

df_tot_clima_rinominato = df_tot_clima.rename(columns=lambda c: next((c.replace(code9, code) for code9, code in mapping.items() if code9 in c), c))
df_tot_clima_rinominato = df_tot_clima_rinominato[(df_tot_clima_rinominato.index.year >= 1940) & (df_tot_clima_rinominato.index.year <= 2020)]

df_tot = pd.concat([df_tot_clima_rinominato, df_tot_meteo[~df_tot_meteo.index.isin(df_tot_clima_rinominato.index)]])
df_tot = df_tot.sort_index()

df_tot_clima_rinominato = df_tot_clima_rinominato[[x for x in df_tot_clima_rinominato.columns for y in stazioni_scelte if y in x]]
df_tot_meteo = df_tot_meteo[[x for x in df_tot_meteo.columns for y in stazioni_scelte if y in x]]
df_tot = df_tot[[x for x in df_tot.columns for y in stazioni_scelte if y in x]]

norm = TwoSlopeNorm(vmin=df_tot_meteo.min().quantile(0.3), vcenter=df_tot_meteo.mean().mean(), vmax=df_tot_meteo.max().quantile(0.7))

for nome, df_i in zip(['df_tot_meteo', 'df_tot_clima_rinominato', 'df_tot'], [df_tot_meteo, df_tot_clima_rinominato, df_tot]):
    
    df_i = df_i.reindex(pd.date_range('1940-01-01', '2025-12-31', freq='1d'))
    
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.imshow(
        df_i.values,
        aspect='auto',
        interpolation='nearest',
        cmap=cmap_continua,
        norm=norm
        )
    
    ax.set_xticks(np.arange(len(df_i.columns)))
    ax.set_xticklabels(df_i.columns, rotation=90)
    
    idx = df_i.index
    mask = (idx.month == 1) & (idx.day == 1)
    y_ticks = np.where(mask)[0]
    y_labels = idx[mask].year.astype(str)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels, fontsize=8)
    
    ax.set_title(nome, fontsize=12)
    plt.show()
    plt.close()
    
# %%

# Di queste stazioni devo calcolare le anomalie di TMAX e TMIN annuali rispetto al periodo 2003-2022

df_anomalie_TMAX = pd.DataFrame(np.nan, columns=stazioni_scelte, index=pd.date_range('1940', '2025', freq='1YS'))
df_anomalie_TMIN = pd.DataFrame(np.nan, columns=stazioni_scelte, index=pd.date_range('1940', '2025', freq='1YS'))

for s in stazioni_scelte:
    
    for anno in df_anomalie_TMAX.index.year:
        
        tmax = df_tot[f'TMAX_{s}'].loc[df_tot.index.year == anno].mean()
        tmax_ref = df_tot.loc[(df_tot.index.year >= 2003) & (df_tot.index.year <= 2022)][f'TMAX_{s}'].mean()
        
        df_anomalie_TMAX.loc[f'{anno}-01-01', s] = tmax - tmax_ref
        
        ########################
        
        tmin = df_tot[f'TMIN_{s}'].loc[df_tot.index.year == anno].mean()
        tmin_ref = df_tot.loc[(df_tot.index.year >= 2003) & (df_tot.index.year <= 2022)][f'TMIN_{s}'].mean()
        
        df_anomalie_TMIN.loc[f'{anno}-01-01', s] = tmin - tmin_ref
        
df_anomalie_TMAX = df_anomalie_TMAX.where((df_anomalie_TMAX >= -2) & (df_anomalie_TMAX <= 2)) # Alcuni valori non vanno bene perché mancano dati
df_anomalie_TMIN = df_anomalie_TMIN.where((df_anomalie_TMIN >= -2) & (df_anomalie_TMIN <= 2)) # Alcuni valori non vanno bene perché mancano dati

# %%

for anno in range(1990, 2026):
    
    fig, ax = plt.subplots(figsize=(10, 4), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent((7.45, 10.1, 43.75, 44.7))
    ax.set_aspect('auto', adjustable=None)
    
    for r in regioni.records():
        if r.attributes['NAME_1'] == 'Liguria':
            liguria = r.geometry
            ax.add_geometries([liguria], crs=ccrs.PlateCarree(), facecolor='#d9dadb', edgecolor='black', linewidth=0.5, zorder=-10)
    
    shift_lon = 0.085
    norm = TwoSlopeNorm(vmin=-1.5, vcenter=0, vmax=1.5)
    
    ### TMAX
    for s in stazioni_scelte:
        sc = ax.scatter(df_coord_meteo.loc[s, 'lon'] - shift_lon,
                    df_coord_meteo.loc[s, 'lat'],
                    s=1000,
                    cmap=cmap_continua,
                    norm=norm,
                    c=df_anomalie_TMAX.loc[f'{anno}-01-01', s],
                    edgecolor=colori[-5],
                    linewidth=3,
                    transform=ccrs.PlateCarree())
        
    texts = []
    for x, y, s in zip(df_coord_meteo['lon'] - shift_lon, df_coord_meteo['lat'], df_anomalie_TMAX.loc[f'{anno}-01-01'].round(1)):
        if np.abs(s) > 1:
            color='white'
        else:
            color='black'
            
        if np.isnan(s):
            s=''
            
        texts.append(plt.text(x, y, s, size=12, fontweight='normal', color=color, ha='center', va='center'))
    
    ### TMIN
    for s in stazioni_scelte:
        sc = ax.scatter(df_coord_meteo.loc[s, 'lon'] + shift_lon,
                    df_coord_meteo.loc[s, 'lat'],
                    s=1000,
                    cmap=cmap_continua,
                    norm=norm,
                    c=df_anomalie_TMIN.loc[f'{anno}-01-01', s],
                    edgecolor=colori[9],
                    linewidth=3,
                    transform=ccrs.PlateCarree())
    
    texts = []
    for x, y, s in zip(df_coord_meteo['lon']+ shift_lon, df_coord_meteo['lat'], df_anomalie_TMIN.loc[f'{anno}-01-01'].round(1)):
        if np.abs(s) > 1:
            color='white'
        else:
            color='black'

        if np.isnan(s):
            s=''
            
        texts.append(plt.text(x, y, s, size=12, fontweight='normal', color=color, ha='center', va='center'))
    
    ###############
    
    texts = []
    for x, y, s in zip(df_coord_meteo['lon'] - shift_lon*0.8, df_coord_meteo['lat'] - shift_lon*2, ['Genova', 'Savona', 'Imperia', 'Chiavari', 'La Spezia']):
        texts.append(plt.text(x, y, s, size=12, fontweight='normal', color='black'))
    adjust_text(texts, only_move={'points':'y', 'texts':'y'})
    
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    ax.set_title(f'Anomalie [°C] della temperatura media massima (bordo rosso) e media minima (bordo azzurro)\ndell\'{anno} rispetto al periodo di riferimento 2003-2022', fontsize=11)
    
    plt.savefig(f'./anomalie_max_min_{anno}.png', dpi=300, format='png', bbox_inches='tight')
    
    plt.show()
    plt.close()
