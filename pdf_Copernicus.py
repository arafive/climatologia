
import os

import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', FutureWarning)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import gaussian_kde

from matplotlib.colors import TwoSlopeNorm
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

colori = [
    '#2a71b2', '#6bacd1', '#c2ddec',
    ###
    '#f9f9f9',
    ###
    '#fbccb4', '#e48066', '#ba2832',
]

cmap_continua = LinearSegmentedColormap.from_list('cmap_continua', colori)

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
### Media climatologica giornaliera 1991-2020
gruppo_giorni_clima = list(df_tot_clima.mean(axis=1).groupby([df_tot_clima.index.day, df_tot_clima.index.month]))
gruppo_giorni_meteo = list(df_tot_meteo.mean(axis=1).groupby([df_tot_meteo.index.day, df_tot_meteo.index.month]))

df_tmedie_clima_91_20 = pd.DataFrame(np.nan, index=pd.date_range('2020-01-01', '2020-12-31', freq='1d'), columns=['clima']).squeeze()
df_tmedie_meteo_91_20 = pd.DataFrame(np.nan, index=pd.date_range('2020-01-01', '2020-12-31', freq='1d'), columns=['meteo']).squeeze()

for giorno, df in gruppo_giorni_clima:
    df = df[(df.index.year >= 1990) & (df.index.year <= 2020)]
    df_tmedie_clima_91_20.loc[f'2020-{giorno[1]:02d}-{giorno[0]:02d} 00:00:00'] = df.mean()

for giorno, df in gruppo_giorni_meteo:
    df = df[(df.index.year >= 1990) & (df.index.year <= 2020)]
    df_tmedie_meteo_91_20.loc[f'2020-{giorno[1]:02d}-{giorno[0]:02d} 00:00:00'] = df.mean()

# df = pd.concat([df_tmedie_meteo_91_20, df_tmedie_clima_91_20], axis=1)
# df['diff'] = df['clima'] - df['meteo']
# df.plot()
# plt.ylim(0)
# plt.show()
# plt.close()

del (giorno, df, gruppo_giorni_clima, gruppo_giorni_meteo)

# %%
### Media climatologica giornaliera 2003-2020
gruppo_giorni_clima = list(df_tot_clima.mean(axis=1).groupby([df_tot_clima.index.day, df_tot_clima.index.month]))
gruppo_giorni_meteo = list(df_tot_meteo.mean(axis=1).groupby([df_tot_meteo.index.day, df_tot_meteo.index.month]))

df_tmedie_clima_03_20 = pd.DataFrame(np.nan, index=pd.date_range('2020-01-01', '2020-12-31', freq='1d'), columns=['clima']).squeeze()
df_tmedie_meteo_03_20 = pd.DataFrame(np.nan, index=pd.date_range('2020-01-01', '2020-12-31', freq='1d'), columns=['meteo']).squeeze()

for giorno, df in gruppo_giorni_clima:
    df = df[(df.index.year >= 2003) & (df.index.year <= 2022)]
    df_tmedie_clima_03_20.loc[f'2020-{giorno[1]:02d}-{giorno[0]:02d} 00:00:00'] = df.mean()

for giorno, df in gruppo_giorni_meteo:
    df = df[(df.index.year >= 2003) & (df.index.year <= 2022)]
    df_tmedie_meteo_03_20.loc[f'2020-{giorno[1]:02d}-{giorno[0]:02d} 00:00:00'] = df.mean()

# df = pd.concat([df_tmedie_meteo_03_20, df_tmedie_clima_03_20], axis=1)
# df['diff'] = df['clima'] - df['meteo']
# df.plot()
# plt.ylim(0)
# plt.show()
# plt.close()

del (giorno, df, gruppo_giorni_clima, gruppo_giorni_meteo)

# %%
### Unisco i dati meteo e clima per fare il Ridge KDE plot (Joyplot)

df_tot_clima_rinominato = df_tot_clima.rename(columns=dict(zip(df_stazioni_meteo_clima['Code9'], df_stazioni_meteo_clima['Code'])))
df_tot_clima_rinominato = df_tot_clima_rinominato[(df_tot_clima_rinominato.index.year >= 1940) & (df_tot_clima_rinominato.index.year <= 2020)]

df_tot = pd.concat([df_tot_clima_rinominato, df_tot_meteo[~df_tot_meteo.index.isin(df_tot_clima_rinominato.index)]])
df_tot = df_tot.sort_index()

# df_tot = df_tot[df_stazioni_meteo_clima['Code']] # ??? modifica solo quelle molto vecchie... non so perché

# %%
### Contro sul sottoinsieme clima di df_tot
# !!! df_tot_clima e df_tot_clima_rinominato sono identici

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

gruppo_tot = list(df_tot.mean(axis=1).groupby(df_tot.index.year))

# parametro di sovrapposizione
scale = 0.8  # quanto “alta” è la curva prima di sovrapporsi
overlap = 0.1  # frazione di sovrapposizione verticale
degradamento = 1.3 # più è grande, più il degradamento è morbido

fig, ax = plt.subplots(figsize=(8, 12))

for i, (anno, df) in enumerate(gruppo_tot):
    print(anno)
    
    df.index = [str(x) for x in df.index]
    df.index = [f'2020-{x[5:7]}-{x[8:10]} 00:00:00' for x in df.index]
    df.index = pd.to_datetime(df.index)
    df = df.reindex(pd.date_range('2020-01-01', '2020-12-31', freq='1d'))
    
    df = df - df_tmedie_clima_91_20
    # df = df - df_tmedie_meteo_91_20
    # df = df - df_tmedie_clima_03_20
    # df = df - df_tmedie_meteo_03_20
    
    df = df.dropna()

    ############    
    ############
    
    z = 100 - i
    
    # griglia su cui calcolare la KDE
    x = np.linspace(df.min() * degradamento, df.max() * degradamento, 1200)
    
    # stima KDE
    kde = gaussian_kde(df.values)
    y = kde(x)

    norm = TwoSlopeNorm(vmin=-7.5, vcenter=0, vmax=7.5)

    # ---- aggiungi offset verticale in base all’anno ----
    y_scaled = y / y.max() * scale
    
    y_offset = i * overlap
    y_plot = y_scaled + y_offset

    # creo una "striscia 2D" per colorare l'area
    X, Y = np.meshgrid(x, np.linspace(y_offset, y_offset+y_scaled.max(), 400))
    Z = np.tile(x, (400, 1))   # il colore dipende dal valore di x
    
    mask = Y - y_offset > np.interp(X[0], x, y_scaled)
    Z_masked = np.ma.masked_where(mask, Z)

    # area colorata sotto la curva
    pcm = ax.pcolormesh(X, Y , Z_masked,
                        cmap=cmap_continua,
                        norm=norm,
                        shading='auto',
                        zorder=z
                        )
    
    dict_anni_notevoli = {
        1940 + 3: 'Anno più caldo', # 2022
        1940 + 2: 'Secondo anno più caldo', # 2023
        1940 + 1: 'Terzo anno più caldo', # 2024
        
        1940 + 69: 'Anno più freddo', # 1956
        1940 + 49: 'Secondo anno più freddo', # 1976
        1940 + 34: 'Terzo Anno più freddo', # 1991
        }
    
    # traccio la curva KDE sopra
    if anno in dict_anni_notevoli.keys():
        ax.plot(x, y_plot,
                color='#2a71b2' if 'freddo' in dict_anni_notevoli[anno] else '#ba2832',
                lw=1.5,
                zorder=z
                )
        
    elif anno == 1940 + 40: # è il 1985
        ax.plot(x, y_plot,
                color='#2a71b2',
                lw=1,
                ls='--',
                zorder=z
                )
        
    else:
        ax.plot(x, y_plot,
                color='black',
                lw=0.3,
                zorder=z
                )
    
    ax.set_xlim(-12, 12)

# ax.set_title(f'scale:{scale}, overlap:{overlap}, degradamento:{degradamento}')
ax.set_title('Distribuzioni di anomalia di temperatura media giornaliera sulla Liguria\n\n', fontsize=12)
ax.set_title('         Più freddo del periodo 1991-2020', loc='left', fontsize=10, color='#2a71b2')
ax.set_title('Più caldo del periodo 1991-2020           ', loc='right', fontsize=10, color='#ba2832')

ytick_grid = [i * overlap for i in range(0, len(gruppo_tot), 5)]

ax.set_yticks(ytick_grid)
ax.set_xticks([-12.5, -10, -7.5, -5, -2.5 , 0, 2.5, 5, 7.5, 10, 12.5])
ax.set_xticklabels([int(x) if str(x).endswith('.0') else float(x) for x in list(ax.get_xticks())])

anni = np.arange(1940, 2025 + 1, 1)[::-1]
ax.set_yticklabels(anni[::5])

ax.vlines(x=0, ymin=0, ymax=ax.get_ylim()[1], linewidth=0.3, color='k', alpha=0.3, zorder=999)

ax.tick_params(axis='x', labelsize=10, length=2)
ax.tick_params(axis='y', labelsize=10, length=2)

ax.grid(axis='y', linestyle='-', alpha=0.3, zorder=-100)
ax.set_xlabel('Anomalia [°C] rispetto al periodo 1991-2020', fontsize=10)
# ax.set_ylabel('Anni')

plt.savefig('./anomalie_giornaliere_pdf_Copernicus.png', dpi=300, format='png', bbox_inches='tight')
    
plt.show()
plt.close()
