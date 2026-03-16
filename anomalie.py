
import os
import pickle

import locale
locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')

import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', FutureWarning)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import matplotlib.dates as mdates
import matplotlib.cm as cm
import cartopy.crs as ccrs

from matplotlib.path import Path
from matplotlib.colors import ListedColormap
from matplotlib.colors import BoundaryNorm
from matplotlib.colors import Normalize
from matplotlib.colorbar import ColorbarBase
from matplotlib.ticker import MultipleLocator
from matplotlib.ticker import NullLocator
from matplotlib.patches import Rectangle
from shapely.geometry import Polygon, MultiPolygon

from adjustText import adjust_text
from scipy.interpolate import griddata
from scipy.stats import linregress
from cartopy.io.shapereader import Reader

from pykrige.ok import OrdinaryKriging
from pykrige.uk import UniversalKriging

lista_possibili_cartelle_lavoro = [
    '/media/daniele/Daniele2TB/test/climatologia_OLD',
    '/run/media/daniele.carnevale/Daniele2TB/test/climatologia_OLD',
]

cartella_lavoro = [x for x in lista_possibili_cartelle_lavoro if os.path.exists(x)][0]
os.chdir(cartella_lavoro)
del (lista_possibili_cartelle_lavoro)

from matplotlib import font_manager
font_files = font_manager.findSystemFonts(fontpaths='./../../NotesEsa_font')
for font_file in font_files:
    font_manager.fontManager.addfont(font_file)

plt.rc('font', family='NotesEsa', weight='normal', size=6)

regioni = Reader('./../shapefile/gadm41_ITA_shp/gadm41_ITA_1.shp')

for r in regioni.records():
    if r.attributes['NAME_1'] == 'Liguria':
        print(r.attributes)

# %%
df_stazioni_meteo_clima = pd.read_csv(f'{cartella_lavoro}/df_stazioni_meteo-clima.csv')
df_stazioni_meteo_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] != 'GEPCA'] # Alcune hanno problemi. Le tolgo.
df_stazioni_meteo_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] != 'PANES'] # Alcune hanno problemi. Le tolgo.

cartella_query_clima = f'{cartella_lavoro}/query_clima'
cartella_query_meteo = f'{cartella_lavoro}/query_meteo'

# %%
dict_massimi_annuali = {x: pd.DataFrame(columns=df_stazioni_meteo_clima['Code']) for x in range(1991, 2026)}
dict_medie_annuali = {x: pd.DataFrame(columns=df_stazioni_meteo_clima['Code']) for x in range(1991, 2026)}
dict_minimi_annuali = {x: pd.DataFrame(columns=df_stazioni_meteo_clima['Code']) for x in range(1991, 2026)}

# if not os.path.exists(f'{cartella_lavoro}/dict_medie_annuali.pkl'):
if os.path.exists(f'{cartella_lavoro}/dict_medie_annuali.pkl'):
    for anno in dict_medie_annuali.keys():
        print(anno)
        
        for s_meteo in df_stazioni_meteo_clima['Code'].tolist():
            s_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] == s_meteo]['Code9'].iloc[0]
            
            df_clima = pd.read_csv(f'{cartella_query_clima}/{s_clima}.csv', index_col=0, parse_dates=True)
            df_meteo = pd.read_csv(f'{cartella_query_meteo}/{s_meteo}.csv', index_col=0, parse_dates=True)
            
            df_tmp = pd.concat([df_clima, df_meteo], axis=0)
            dict_massimi_annuali[anno][s_meteo] = df_tmp.loc[[x for x in df_tmp.index if x.year == anno]]['TMAX']
            dict_medie_annuali[anno][s_meteo] = df_tmp.loc[[x for x in df_tmp.index if x.year == anno]]['TMEAN']
            dict_minimi_annuali[anno][s_meteo] = df_tmp.loc[[x for x in df_tmp.index if x.year == anno]]['TMIN']

        # df_tmp = dict_medie_annuali[anno].mean(axis=1)
        # ### Reindex di un anno bisestile, così le date sono sempre allineate
        # df_tmp.index = [f"2020-{str(x).split('-', 1)[-1]}" for x in df_tmp.index]
        # df_tmp.index = pd.to_datetime(df_tmp.index)
        # df_tmp = df_tmp.reindex(pd.date_range('2020-01-01', '2020-12-31', freq='1d'))
        # dict_medie_annuali[anno] = df_tmp
        
    pickle.dump(dict_massimi_annuali, open(f'{cartella_lavoro}/dict_massimi_annuali.pkl', 'wb'))
    pickle.dump(dict_medie_annuali, open(f'{cartella_lavoro}/dict_medie_annuali.pkl', 'wb'))
    pickle.dump(dict_minimi_annuali, open(f'{cartella_lavoro}/dict_minimi_annuali.pkl', 'wb'))
    del (df_tmp, s_meteo, s_clima, anno, df_clima, df_meteo)
    
else:
    print(f'\n{cartella_lavoro}/dict_medie_annuali.pkl esiste. Lo carico.\n')
    dict_massimi_annuali = pickle.load(open(f'{cartella_lavoro}/dict_massimi_annuali.pkl', 'rb'))
    dict_medie_annuali = pickle.load(open(f'{cartella_lavoro}/dict_medie_annuali.pkl', 'rb'))
    dict_minimi_annuali = pickle.load(open(f'{cartella_lavoro}/dict_minimi_annuali.pkl', 'rb'))

# %% Plot stile Copernicus Report ESOTC 2024 (pag. 19)

anno = 2025
printa_giorni_max_min = False
previsioni_di_ensemble, oggi = False, pd.to_datetime('2025-11-12') # (EXPERIMENTAL)

dict_cmap = {
    'All time\nminimum': '#2a71b2',
    'Much cooler\nthan average': '#6bacd1',
    'Cooler\nthan average': '#c2ddec',
    'Warmer\nthan average': '#fbccb4',
    'Much warmer\nthan average': '#e48066',
    'All time\nmaximum': '#ba2832',
    '': 'white',
    '25°-75°\npercentile': 'gray',
    'Min-Max\nrange': 'lightgray'
    }

dict_cmap_traduzione = {
    'All time\nminimum': 'Minimo\nassoluto',
    'Much cooler\nthan average': 'Molto più freddo\ndella media',
    'Cooler\nthan average': 'Più freddo\ndella media',
    'Warmer\nthan average': 'Più caldo\ndella media',
    'Much warmer\nthan average': 'Molto più caldo\ndella media',
    'All time\nmaximum': 'Massimo\nassoluto',
    '': '',
    '25°-75°\npercentile': '25°-75°\npercentile',
    'Min-Max\nrange': 'Min-Max\nrange'
    }

lista_clima = []
lista_max_clima = []
lista_min_clima = []

# for a in range(1991, 2021):
for a in range(2003, 2022):
    df_tmp = dict_medie_annuali[a]
    df_tmp.index = [f"2020-{str(x).split('-', 1)[-1]}" for x in df_tmp.index]
    df_tmp.index = pd.to_datetime(df_tmp.index)
    df_tmp = df_tmp.reindex(pd.date_range('2020-01-01', '2020-12-31', freq='1d'))

    lista_clima.append(df_tmp)
    
    df_tmp = dict_massimi_annuali[a]
    df_tmp.index = [f"2020-{str(x).split('-', 1)[-1]}" for x in df_tmp.index]
    df_tmp.index = pd.to_datetime(df_tmp.index)
    df_tmp = df_tmp.reindex(pd.date_range('2020-01-01', '2020-12-31', freq='1d'))

    lista_max_clima.append(df_tmp.mean(axis=1))

    df_tmp = dict_minimi_annuali[a]
    df_tmp.index = [f"2020-{str(x).split('-', 1)[-1]}" for x in df_tmp.index]
    df_tmp.index = pd.to_datetime(df_tmp.index)
    df_tmp = df_tmp.reindex(pd.date_range('2020-01-01', '2020-12-31', freq='1d'))

    lista_min_clima.append(df_tmp.mean(axis=1))

df_max_clima = pd.concat(lista_max_clima, axis=1).mean(axis=1)
df_min_clima = pd.concat(lista_min_clima, axis=1).mean(axis=1)
df_25perc_clima = pd.concat(lista_clima, axis=1).quantile(0.25, axis=1)
df_mean_clima = pd.concat(lista_clima, axis=1).mean(axis=1)
df_75perc_clima = pd.concat(lista_clima, axis=1).quantile(0.75, axis=1)

### Nel caso voglio dei valori smooth come nella figura originale
# df_25perc_clima = df_25perc_clima.rolling(window=20, center=True).mean().fillna(method='bfill').fillna(method='ffill')
# df_75perc_clima = df_75perc_clima.rolling(window=20, center=True).mean().fillna(method='bfill').fillna(method='ffill')

df_anno = dict_medie_annuali[anno].mean(axis=1)
df_anno.index = [f"2020-{str(x).split('-', 1)[-1]}" for x in df_anno.index]
df_anno.index = pd.to_datetime(df_anno.index)
df_anno = df_anno.reindex(pd.date_range('2020-01-01', '2020-12-31', freq='1d'))

#############

fig, ax = plt.subplots(figsize=(7, 4))

y_max = df_max_clima.values.flatten()
y_75perc = df_75perc_clima.values.flatten()
y_mean = df_mean_clima.values.flatten()
y_25perc = df_25perc_clima.values.flatten()
y_min = df_min_clima.values.flatten()
y_anno = df_anno.values.flatten()

dict_fill_between = {
    'alpha': 1,
    'interpolate': True,
    'zorder': 1,
    'edgecolor': 'black',
    'lw': 0.0
}

df_mean_clima.plot(ax=ax, color='white', ls='-', lw=1, zorder=5)

ax.fill_between(
    df_max_clima.index,
    df_min_clima.values,
    df_max_clima.values,
    color='lightgray',
    alpha=0.15, edgecolor='none')

ax.fill_between(
    df_75perc_clima.index,
    df_25perc_clima.values,
    df_75perc_clima.values,
    color='gray',
    alpha=0.15, edgecolor='none')

ax.fill_between(df_anno.index, y_anno, y_mean, where=(y_anno > y_mean), color=dict_cmap['Warmer\nthan average'], **dict_fill_between)
ax.fill_between(df_anno.index, y_anno, y_75perc, where=(y_anno > y_75perc), color=dict_cmap['Much warmer\nthan average'], **dict_fill_between)
ax.fill_between(df_anno.index, y_anno, y_max, where=(y_anno > y_max), color=dict_cmap['All time\nmaximum'], **dict_fill_between)

ax.fill_between(df_anno.index, y_anno, y_mean, where=(y_anno < y_mean), color=dict_cmap['Cooler\nthan average'], **dict_fill_between)
ax.fill_between(df_anno.index, y_anno, y_25perc, where=(y_anno < y_25perc), color=dict_cmap['Much cooler\nthan average'], **dict_fill_between)
ax.fill_between(df_anno.index, y_anno, y_min, where=(y_anno < y_min), color=dict_cmap['All time\nminimum'], **dict_fill_between)

### Massimi e minimi medi
y_massimi_medi = np.where(y_anno > y_max, y_anno, np.nan)
y_minimi_medi = np.where(y_anno < y_min, y_anno, np.nan)

ax.scatter(df_anno.index, y_massimi_medi, zorder=10, s=4, c=dict_cmap['All time\nmaximum'], lw=0.2, edgecolor='black')
ax.scatter(df_anno.index, y_minimi_medi, zorder=10, s=4, c=dict_cmap['All time\nminimum'], lw=0.2, edgecolor='black')

date_massimi_medi = df_anno[~np.isnan(y_massimi_medi)].index
date_minimi_medi = df_anno[~np.isnan(y_minimi_medi)].index

y_massimi_medi = y_massimi_medi[~np.isnan(y_massimi_medi)]
y_minimi_medi = y_minimi_medi[~np.isnan(y_minimi_medi)]

if printa_giorni_max_min:
    texts = []
    for data, temperatura in zip(date_massimi_medi, y_massimi_medi):
        txt = ax.annotate(
            data.strftime('%d %b'),
            xy=(data, temperatura),
            xytext=(data, temperatura + 0.7),
            textcoords='data',
            fontsize=4,
            color='black',
            ha='center',
            arrowprops=dict(
                arrowstyle='-',
                color='black',
                lw=0.2,
                shrinkA=0,   # niente shrink all’origine (testo)
                shrinkB=1,   # un po' di shrink al punto (freccia scende giù)
            )
        )
                
        texts.append(txt)
    
    adjust_text(
        texts,
        expand=(2, 2),
        only_move={'text': 'x'}
    )
    
    texts = []
    for data, temperatura in zip(date_minimi_medi, y_minimi_medi):
        txt = ax.annotate(
            data.strftime('%d %b'),
            xy=(data, temperatura),
            xytext=(data, temperatura + 0.7),
            textcoords='data',
            fontsize=4,
            color='black',
            ha='center',
            arrowprops=dict(
                arrowstyle='-',
                color='black',
                lw=0.2,
                shrinkA=0,   # niente shrink all’origine (testo)
                shrinkB=1,   # un po' di shrink al punto (freccia scende giù)
            )
        )
                
        texts.append(txt)
    
    adjust_text(
        texts,
        expand=(2, 2),
        only_move={'text': 'x'}
    )

# txt_perc = ax.text(pd.Timestamp('2020-03-05'), 4.7, '25°-75°\npercentili', color='gray', fontweight='bold', fontsize=6, ha='center', va='center', zorder=9)
# txt_perc.set_path_effects([path_effects.Stroke(linewidth=2, foreground='white'), path_effects.Normal()])
# txt_maxmin = ax.text(pd.Timestamp('2020-05-06'), 9.5, 'Min-max\nrange', color='lightgray', fontweight='bold', fontsize=6, ha='center', va='center', zorder=9)
# txt_maxmin.set_path_effects([path_effects.Stroke(linewidth=2, foreground='white'), path_effects.Normal()])

### Previsioni di ensemble (EXPERIMENTAL)
if previsioni_di_ensemble:
    df_ensemble_t2m = pd.read_csv(f"{cartella_lavoro}/df_ensemble_t2m_{oggi.strftime('%Y-%m-%d')}.csv", index_col=0, parse_dates=True)
    df_ensemble_t2m.index = pd.to_datetime([str(x).replace(str(anno), '2020') for x in df_ensemble_t2m.index])
    df_ensemble_t2m = df_ensemble_t2m.reindex(pd.date_range('2020-01-01', '2020-12-31', freq='1d')).dropna()

    ieri_2020 = df_anno.dropna().index[-1]
    df_tmp = pd.DataFrame({
            'perc_25': df_anno.dropna().iloc[-1],
            'media': df_anno.dropna().iloc[-1],
            'perc_75': df_anno.dropna().iloc[-1],
            },
        index=[df_anno.dropna().index[-1]]
        )
    
    df_ensemble_t2m = pd.concat([df_tmp, df_ensemble_t2m], axis=0).iloc[0:15]
    # df_ensemble_t2m.plot(ax=ax, color='tab:purple', lw=0.5, zorder=5, legend=False)
    styles = {
        'perc_25': ':',
        'media': '-',
        'perc_75': ':'
    }
    for col in df_ensemble_t2m.columns:
        ax.plot(df_ensemble_t2m.index, df_ensemble_t2m[col], linestyle=styles.get(col, '-'), zorder=5, lw=0.5, color='tab:purple')

ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))

### Tolgo l'ultimo 'dic'
labels = [label.get_text() for label in ax.get_xticklabels()]
labels = labels[:-1]
ticks = ax.get_xticks()[:-1]
ax.set_xticks(ticks)
ax.set_xticklabels(labels)

ax.set_title(anno, fontsize=8)
ax.text(1.0, 1.02, "Climatologia 2003-2022", transform=ax.transAxes, ha='right', va='bottom', fontsize=8)
ax.set_ylim(0, 30)
ax.set_yticks([0, 5, 10, 15, 20, 25, 30])
ax.set_yticklabels([0, 5, 10, 15, 20, 25, '30°C'])
ax.grid(which='major', axis='both', zorder=0, lw=0.075, ls='-')

cmap_copernicus = ListedColormap(list(dict_cmap.values()))
bounds = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] # 7 è di fatto uno spazio vuoto
norm = BoundaryNorm(bounds, cmap_copernicus.N)

cbar_ax = fig.add_axes([0.14, 0.02, 0.75, 0.04])  # [left, bottom, width, height]
cbar = ColorbarBase(
    cbar_ax,
    cmap=cmap_copernicus,
    norm=norm,
    boundaries=bounds,
    orientation='horizontal',
    spacing='uniform',
    drawedges=False)

### Cambia colore e spessore dei bordi interni
if cbar.solids and hasattr(cbar.solids, 'get_edgecolor'):
    cbar.solids.set_edgecolor('white')
    cbar.solids.set_linewidth(2)  # puoi aumentare lo spessore se serve

cbar.outline.set_visible(False)
cbar.ax.tick_params(axis='both', which='both', length=0, size=0)

cbar.set_ticks([i + 0.5 for i in range(len(bounds)-1)])
cbar.set_ticklabels(list(dict_cmap_traduzione.values()), fontsize=5.5)

plt.savefig(f'./Copernicus_3_{anno}.png', dpi=300, format='png', bbox_inches='tight')
plt.show()
plt.close()

# del (dict_cmap, cmap_copernicus, bounds, norm, a, anno, ax, fig, cbar, cbar_ax, labels, ticks)
# del (df_25perc_clima, df_75perc_clima, df_max_clima, df_mean_clima, df_min_clima, df_tmp, df_ensemble_t2m)
# del (y_25perc, y_75perc, y_anno, y_massimi_medi, y_max, y_mean, y_min, y_minimi_medi, df_anno, date_minimi_medi, date_massimi_medi)
# del (lista_clima, lista_max_clima, lista_min_clima, dict_fill_between, dict_cmap_traduzione, texts, data, temperatura)


# %% Plot stile Copernicus "Annual temperature anomalies since 1979 (Europe)" (https://climate.copernicus.eu/graphics-gallery)
df_medie_annuali = pd.Series(np.nan, index=dict_medie_annuali.keys())

for anno in dict_medie_annuali.keys():
    df_medie_annuali.loc[anno] = dict_medie_annuali[anno].mean(axis=1).mean()

df_medie_annuali_ultima_data = pd.Series(np.nan, index=dict_medie_annuali.keys())
ultima_data = dict_medie_annuali[2025].index[-1]

for anno in dict_medie_annuali.keys():
    df_tmp = dict_medie_annuali[anno].mean(axis=1)
    df_tmp = df_tmp[(df_tmp.index.month < ultima_data.month) | ((df_tmp.index.month == ultima_data.month) & (df_tmp.index.day <= ultima_data.day))]
    df_medie_annuali_ultima_data.loc[anno] = df_tmp.mean()

###############

fig, ax = plt.subplots(figsize=(11, 4))

inizio_gradiente, fine_gradiente = 4, 18

### Barre di df_medie_annuali
cmap = plt.get_cmap('Reds')
norm = Normalize(vmin=inizio_gradiente, vmax=fine_gradiente)

df_medie_annuali.plot(ax=ax, kind='bar',edgecolor='black', lw=0.2, zorder=3, width=0.7,
    color='none',  # niente riempimento perché mettiamo il gradiente dopo
)

for rect, media_annuale in zip(ax.patches, df_medie_annuali.values):
    x0, y0, w = rect.get_x(), rect.get_y(), rect.get_width()

    gradient = np.linspace(inizio_gradiente, fine_gradiente, 100).reshape(-1, 1)
    gradient = np.flipud(gradient)
    gradient_colors = cmap(norm(gradient))

    rel_height = (media_annuale - inizio_gradiente) / (fine_gradiente - inizio_gradiente)
    rel_height = np.clip(rel_height, 0, 1)
    rows_to_keep = int(rel_height * gradient_colors.shape[0])
    gradient_cut = gradient_colors[-rows_to_keep:] if rows_to_keep > 0 else np.zeros((0, 1, 4))

    extent = [x0, x0 + w, y0 + inizio_gradiente, y0 + media_annuale]
    ax.imshow(gradient_cut, aspect='auto', extent=extent, origin='upper', zorder=2)

### La griglia è stata seccante. La minore e la maggiore devono rimanere separate
ax.minorticks_on()  # Attiva i tick minori
ax.grid(which='minor', axis='y', ls=':', lw=0.3, color='lightgray', zorder=1)
ax.xaxis.set_minor_locator(NullLocator()) # serve a togliere i tick minor
ax.yaxis.set_minor_locator(MultipleLocator(1 / 4))

### Barre di df_medie_annuali_ultima_data
cmap = plt.get_cmap('Oranges')
norm = Normalize(vmin=inizio_gradiente, vmax=fine_gradiente)

df_medie_annuali_ultima_data.plot(ax=ax, kind='bar',edgecolor='black', lw=0.2, zorder=3, width=0.7,
    color='none',  # niente riempimento perché mettiamo il gradiente dopo
)

for rect, media_annuale in zip(ax.patches, df_medie_annuali_ultima_data.values):
    x0, y0, w = rect.get_x(), rect.get_y(), rect.get_width()

    gradient = np.linspace(inizio_gradiente, fine_gradiente, 100).reshape(-1, 1)
    gradient = np.flipud(gradient)
    gradient_colors = cmap(norm(gradient))

    rel_height = (media_annuale - inizio_gradiente) / (fine_gradiente - inizio_gradiente)
    rel_height = np.clip(rel_height, 0, 1)
    rows_to_keep = int(rel_height * gradient_colors.shape[0])
    gradient_cut = gradient_colors[-rows_to_keep:] if rows_to_keep > 0 else np.zeros((0, 1, 4))

    extent = [x0, x0 + w, y0 + inizio_gradiente, y0 + media_annuale]
    ax.imshow(gradient_cut, aspect='auto', extent=extent, origin='upper', zorder=2)
    
ax.grid(which='major', axis='y', lw=0.4, ls='-', zorder=1)

'''
### Trend
pendenza, intercetta, _, _, _ = linregress(df_medie_annuali.index, df_medie_annuali.values)
trend = intercetta + pendenza * df_medie_annuali.index
ax.plot(np.arange(len(df_medie_annuali)), trend, label='Trend', color='tab:red', ls='--', lw=1.5, zorder=10)

pendenza, intercetta, _, _, _ = linregress(df_medie_annuali_ultima_data.index, df_medie_annuali_ultima_data.values)
trend = intercetta + pendenza * df_medie_annuali_ultima_data.index
ax.plot(np.arange(len(df_medie_annuali_ultima_data)), trend, label='Trend', color='tab:orange', ls='--', lw=1.5, zorder=10)
'''

ax.set_title('Temperatura media annuale in Liguria', fontsize=9)
ax.set_ylim(inizio_gradiente + 4, fine_gradiente - 2)
ax.set_yticks([8, 9, 10, 11, 12, 13, 14, 15, 16]) # é un po' artigianale perché potrei cambiare inizio e fine gradiente e dover modificare qui a mano
ax.set_yticklabels([8, 9, 10, 11, 12, 13, 14, 15, '16°C'])
ax.set_xticklabels(labels=df_medie_annuali.index, rotation=45, ha='center', fontsize=5)

plt.savefig('./Copernicus_2.png', dpi=300, format='png', bbox_inches='tight')

plt.show()
plt.close()

del (df_medie_annuali, anno, df_medie_annuali_ultima_data, ultima_data, df_tmp, fig, ax)
del (inizio_gradiente, fine_gradiente, cmap, norm, rect, media_annuale, x0, y0, w, gradient, gradient_colors)
del (rel_height, rows_to_keep, gradient_cut, extent)
# del (pendenza, intercetta, trend)

# %% Interpolazione e plot geografici di anomalie di temperatura media

df_coord_meteo = pd.read_csv(f'{cartella_lavoro}/df_coord_stazioni_meteo.csv', index_col=0)

cmap = ListedColormap([
    '#08306b', '#08519c', '#2171b5', '#4292c6',
    '#6baed6', '#9ecae1', '#c6dbef', '#deebf7',
    '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a',
    '#ef3b2c', '#cb181d', '#a50f15', '#67000d',
])

anno = 2025

df = pd.DataFrame(np.nan, index=df_stazioni_meteo_clima['Code'], columns=['clima', f'{anno}', 'anomalia'])

for s_meteo in df.index:
    s_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] == s_meteo]['Code9'].iloc[0]
    
    df_clima = pd.read_csv(f'{cartella_query_clima}/{s_clima}.csv', index_col=0, parse_dates=True)
    df_meteo = pd.read_csv(f'{cartella_query_meteo}/{s_meteo}.csv', index_col=0, parse_dates=True)
    df_meteo = df_meteo.loc[[x for x in df_meteo.index if x.year == anno]]

    if not str(df_meteo.index[-1]) == f'{anno}-12-31 00:00:00':
        ultima_data = df_meteo.index[-1]
        ### Sono nell'anno in corso, devo togliere dal clima i giorni che non ci sono ancora
        df_clima = df_clima[(df_clima.index.month < ultima_data.month) | ((df_clima.index.month == ultima_data.month) & (df_clima.index.day <= ultima_data.day))]

    df.loc[s_meteo, 'clima'] = float(df_clima['TMEAN'].mean())
    df.loc[s_meteo, f'{anno}'] = float(df_meteo['TMEAN'].mean())
    df.loc[s_meteo, 'anomalia'] = float(df_meteo['TMEAN'].mean()) - float(df_clima['TMEAN'].mean())
    
df = df.round(2)

##################

estremi_cbar = [-1.5, 1.5] # 1.5 --> 13 levels

lat_stazioni = df_coord_meteo['lat'].values
lon_stazioni = df_coord_meteo['lon'].values
elev_stazioni = df_coord_meteo['elev'].values
anom_stazioni = df['anomalia'].values

modello = 'moloch'
kriging = 'ordinary'

##################

lat_interp = np.linspace(43.2, 45.3, 1000)[::-1]
lon_interp = np.linspace(7.2, 10.5, 1000)
lon_2D_interp, lat_2D_interp = np.meshgrid(lon_interp, lat_interp)

if kriging == 'ordinary':
    ### Ordinary Kriging
    print('Definisco il kriging...')
    OK = OrdinaryKriging(
        lon_stazioni,
        lat_stazioni,
        anom_stazioni,
        variogram_model='spherical',
        variogram_parameters={'sill': 0.5, 'range': 1.2, 'nugget': 0.03}, # 'nugget': 0.0 --> valori esatti
        verbose=False,
        enable_plotting=False
    )
    
    # Interpolazione sulla griglia
    print('Interpolo...')
    z_interp, ss = OK.execute('grid', lon_interp, lat_interp)

elif kriging == 'universal':
    ### Universal Kriging
    # ??? Funziona, ma dà un campo costante...
    
    orog = pd.read_csv(f'{cartella_lavoro}/{modello}/orog_{modello}.csv', index_col=0).values
    lat_orog_2D = pd.read_csv(f'{cartella_lavoro}/{modello}/lat_2D_{modello}.csv', index_col=0).values
    lon_orog_2D = pd.read_csv(f'{cartella_lavoro}/{modello}/lon_2D_{modello}.csv', index_col=0).values
    
    print('Creo un grigliato regolare...')
    lat_orog_reg_1D = np.linspace(43.2, 45.3, 100)[::-1]
    lon_orog_reg_1D = np.linspace(7.2, 10.5, 100)
    lon_orog_reg_2D, lat_orog_reg_2D = np.meshgrid(lon_orog_reg_1D, lat_orog_reg_1D)
    
    orog_reg = griddata(
        np.column_stack((lon_orog_2D.ravel(), lat_orog_2D.ravel())),
        orog.ravel(),
        (lon_orog_reg_2D, lat_orog_reg_2D),
        method='cubic') # Puoi sostituire 'linear' con 'nearest' o 'cubic' se preferisci

    ##################

    print('Definisco il kriging...')
    UK = UniversalKriging(
        lon_stazioni,
        lat_stazioni,
        anom_stazioni,
        variogram_model='exponential',
        variogram_parameters={'sill': 0.5, 'range': 1.2, 'nugget': 0.05}, # 'nugget': 0.0 --> valori esatti
        external_drift=elev_stazioni,
        )
    
    # Interpolazione sulla griglia
    print('Interpolo...')
    z_interp, ss = UK.execute('grid', lat_orog_reg_1D, lon_orog_reg_1D, specified_drift_arrays=orog_reg.flatten())

fig, ax = plt.subplots(figsize=(10, 4), subplot_kw={'projection': ccrs.PlateCarree()})
ax.set_extent((7.45, 10.1, 43.75, 44.7))
ax.set_aspect('auto', adjustable=None)

##################

for r in regioni.records():
    if r.attributes['NAME_1'] == 'Liguria':
        liguria = r.geometry
        ax.add_geometries([liguria], crs=ccrs.PlateCarree(), facecolor='none', edgecolor='black', linewidth=0.5)
        
print('Plotto solo dentro lo shapefile...')
# Verifica se liguria è Polygon o MultiPolygon e costruisci Path(s)
paths = []
if isinstance(liguria, Polygon):
    verts = np.array(liguria.exterior.coords)
    paths.append(Path(verts))
elif isinstance(liguria, MultiPolygon):
    for poly in liguria.geoms:
        verts = np.array(poly.exterior.coords)
        paths.append(Path(verts))
else:
    raise ValueError("Tipo geometria non supportato")

points = np.vstack((lon_2D_interp.ravel(), lat_2D_interp.ravel())).T # Prepara i punti di interpolazione (Nx2 array)
masks = [p.contains_points(points) for p in paths] # Calcola maschere per ogni Path (array booleano 1D)
mask_flat = np.any(masks, axis=0) # Unisci maschere multiple con OR logico
mask = mask_flat.reshape(lon_2D_interp.shape) # Rimodella la maschera nella forma 2D di lon_2D_interp
z_masked = np.where(mask, z_interp.data, np.nan) # Applica la maschera: fuori Liguria diventa NaN

##################

pcm = ax.contourf(
    lon_2D_interp, lat_2D_interp, z_masked,
    levels=np.linspace(estremi_cbar[0], estremi_cbar[1], 13),
    cmap=cmap,
    vmin=estremi_cbar[0],
    vmax=estremi_cbar[1],
    transform=ccrs.PlateCarree(),
    extend='both'
)

sc = ax.scatter(df_coord_meteo['lon'], df_coord_meteo['lat'], c=df['anomalia'],
                cmap=cmap,
                vmin=estremi_cbar[0],
                vmax=estremi_cbar[1],
                s=15,
                edgecolor='black',
                lw=0.3,
                zorder=10,
                transform=ccrs.PlateCarree())

cb = plt.colorbar(pcm, ax=ax, orientation='vertical', label='Anomalia climatica')

ax.set_title(anno, fontsize=8)
ax.text(1.0, 1.02, "Climatologia 1991-2020", transform=ax.transAxes, ha='right', va='bottom', fontsize=8)

plt.savefig(f'./{anno}_anomalia.png', dpi=300, format='png', bbox_inches='tight')
plt.show()
plt.close()

print('\n\nDone')
