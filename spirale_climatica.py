
import os

import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', FutureWarning)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import gaussian_kde

import matplotlib.ticker as mticker

from matplotlib.collections import LineCollection

from matplotlib.colors import TwoSlopeNorm
from matplotlib.colors import ListedColormap
from matplotlib.colors import LinearSegmentedColormap

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
font_files = font_manager.findSystemFonts(fontpaths='./../NotesEsa_font')
for font_file in font_files:
    font_manager.fontManager.addfont(font_file)

plt.rc('font', family='NotesEsa', weight='normal', size=7)

plt.rc('axes', unicode_minus=False)

colori = [
    '#08306b', '#084184', '#08519c', '#1561A9', '#2171b5', '#3282BE', '#4292c6', '#57A0CE', '#6baed6', '#85BCDC', '#9ecae1', '#B2D3E8', '#c6dbef', '#D2E3F3', '#deebf7',
    ###
    '#fee0d2', '#FDCEBA', '#fcbba1', '#FCA78A', '#fc9272', '#FC7E5E', '#fb6a4a', '#F5533B', '#ef3b2c', '#DD2A25', '#cb181d', '#B81419', '#a50f15', '#860811', '#67000d',
]

colori = [
    '#2a71b2', '#6bacd1', '#c2ddec',
    ###
    '#f9f9f9',
    ###
    '#fbccb4', '#e48066', '#ba2832',
]

cmap_continua = LinearSegmentedColormap.from_list('cmap_continua', colori)

# %% Spirale climatica

# https://svs.gsfc.nasa.gov/5190/

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
    
    df = df['TMEAN']
    df.name = s
    
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
    
    df = df['TMEAN']
    df.name = s
    
    df_tot_clima = pd.concat([df_tot_clima, df], axis=1)
    
df_tot_clima.index = pd.to_datetime(df_tot_clima.index)
df_tot_clima = df_tot_clima.sort_index()

del (df, s)

# Per allineare le due tabelle (ho chiesto a Marco)
df_tot_meteo.index = df_tot_meteo.index - pd.Timedelta(days=1)

anno_corrente = pd.Timestamp.now().year
df_tot_meteo = df_tot_meteo[df_tot_meteo.index.year != anno_corrente]

# %%
### Media climatologica mensile 1991-2020
gruppo_mesi_clima = list(df_tot_clima.mean(axis=1).groupby(df_tot_clima.index.month))
gruppo_mesi_meteo = list(df_tot_meteo.mean(axis=1).groupby(df_tot_meteo.index.month))

df_tmedie_clima_91_20 = pd.DataFrame(np.nan, index=pd.date_range('2020-01-01', '2020-12-31', freq='1MS'), columns=['media']).squeeze()
df_tmedie_meteo_91_20 = pd.DataFrame(np.nan, index=pd.date_range('2020-01-01', '2020-12-31', freq='1MS'), columns=['media']).squeeze()

for mese, df in gruppo_mesi_clima:
    df = df[(df.index.year >= 1990) & (df.index.year <= 2020)]
    df_tmedie_clima_91_20.loc[f'2020-{mese:02d}-01'] = df.mean()

for mese, df in gruppo_mesi_meteo:
    df = df[(df.index.year >= 1990) & (df.index.year <= 2020)]
    df_tmedie_meteo_91_20.loc[f'2020-{mese:02d}-01'] = df.mean()

del (mese, df, gruppo_mesi_clima, gruppo_mesi_meteo)

# df_tmedie_meteo_91_20.plot()
# df_tmedie_clima_91_20.plot()
# plt.show()
# plt.close()

# %%
### Media climatologica giornaliera 2003-2020
gruppo_mesi_clima = list(df_tot_clima.mean(axis=1).groupby(df_tot_clima.index.month))
gruppo_mesi_meteo = list(df_tot_meteo.mean(axis=1).groupby(df_tot_meteo.index.month))

df_tmedie_clima_03_20 = pd.DataFrame(np.nan, index=pd.date_range('2020-01-01', '2020-12-31', freq='1MS'), columns=['media']).squeeze()
df_tmedie_meteo_03_20 = pd.DataFrame(np.nan, index=pd.date_range('2020-01-01', '2020-12-31', freq='1MS'), columns=['media']).squeeze()

for mese, df in gruppo_mesi_clima:
    df = df[(df.index.year >= 2002) & (df.index.year <= 2020)]
    df_tmedie_clima_03_20.loc[f'2020-{mese:02d}-01'] = df.mean()

for mese, df in gruppo_mesi_meteo:
    df = df[(df.index.year >= 2002) & (df.index.year <= 2020)]
    df_tmedie_meteo_03_20.loc[f'2020-{mese:02d}-01'] = df.mean()

del (mese, df, gruppo_mesi_clima, gruppo_mesi_meteo)

# df_tmedie_meteo_03_20.plot()
# df_tmedie_clima_03_20.plot()
# plt.show()
# plt.close()

# %%

df_tot_clima_rinominato = df_tot_clima.rename(columns=dict(zip(df_stazioni_meteo_clima['Code9'], df_stazioni_meteo_clima['Code'])))

df_tot = pd.concat([df_tot_clima_rinominato[(df_tot_clima_rinominato.index.year >= 1940) & (df_tot_clima_rinominato.index.year <= 2020)], df_tot_meteo[df_tot_meteo.index.year > 2020]])

# df_tot = df_tot[df_stazioni_meteo_clima['Code']] # ??? modifica solo quelle molto vecchie... non so perché

##########
##########

gruppo_tot = list(df_tot.mean(axis=1).groupby(df_tot.index.month))#[:5]

df = pd.DataFrame(np.nan, columns=range(1, 13), index=range(1940, 2026))

for mese in range(0, 12):
    tref = float(df_tmedie_clima_91_20.loc[f'2020-{mese+1:02d}-01'])

    for anno in range(1940, 2026):
        t = gruppo_tot[mese][1].loc[gruppo_tot[mese][1].index.year == anno].mean()
        
        df.loc[anno, mese+1] = float(t - tref)
        
plt.imshow(df)
plt.show()
plt.close()

df.plot()
plt.show()
plt.close()

# Non capisco perché sia sottosopra... lo giro
df.index = df.index[::-1]

# %%

dict_colori = {
    (-6, -4): '#2a71b2',
    (-4, -2.5): '#6bacd1',
    (-2.5, -1): '#c2ddec',
    (-1, 1): '#f9f9f9',
    (1, 2.5): '#fbccb4',
    (2.5, 4): '#e48066',
    (4, 6): '#ba2832'
}

def colore_per_valore(val):
    for (vmin, vmax), color in dict_colori.items():
        if vmin <= val < vmax:
            return color
    return '#ba2832'  # colore default se non rientra in nessun intervallo


# -----------------------------
# 1) Angoli per i 12 mesi
# -----------------------------
theta = np.linspace(0, 2*np.pi, 12, endpoint=False)

# chiudiamo il cerchio ripetendo il primo punto
theta_closed = np.append(theta, theta[0])

norm = TwoSlopeNorm(vmin=-3, vcenter=0, vmax=3)


for anno, riga in reversed(list(df.iterrows())):
    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(7,7))
    r = np.append(riga.values, riga.values[0])  # chiudi il poligono

    # Creiamo i segmenti
    points = np.array([theta_closed, r]).T.reshape(-1,1,2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # LineCollection
    # lc = LineCollection(segments, cmap=cmap_continua, norm=norm, linewidth=4, zorder=100)
    
    colors = [colore_per_valore(val) for val in r[1:]]
    lc = LineCollection(segments, colors=colors, linewidth=4, zorder=100)

    # Assegniamo a ogni segmento il colore basato sul valore **finale del segmento**
    # (cioè il valore del secondo punto di ciascun segmento)
    lc.set_array(r[1:])  
    ax.add_collection(lc)

    lc_border = LineCollection(segments, color='black', linewidth=5, zorder=100 - 1)
    ax.add_collection(lc_border)
    
    # -----------------------------
    # 4) Estetica
    # -----------------------------
    ax.set_theta_offset(np.pi / 2) # 0° in alto (gennaio in alto)
    # ax.set_theta_direction(-1) # senso orario (gen → feb → mar ...)
    
    ax.set_thetagrids(
        np.degrees(theta),
        labels=["Gen","Feb","Mar","Apr","Mag","Giu", "Lug","Ago","Set","Ott","Nov","Dic"],
        fontsize=15
    )
    
    ax.set_title(anno)
    
    ax.set_ylim(-6, 6)
    ax.set_yticks([-6, -4, -2.5, -1, 0, 1, 2.5, 4, 6])
    
    ax.axhline(0, color='black', lw=2, linestyle='-', zorder=-999)

    plt.tight_layout()
    plt.show()
    plt.close()
    # sss

# TODO Da finire e ricontrollare. Non mi tornano tanto i mesi freddi e caldi a guardare Copernicus_3_{anno}.png

print('\n\nDone')
