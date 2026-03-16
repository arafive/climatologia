
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
    '/media/daniele/Daniele2TB/test/climatologia',
    '/run/media/daniele.carnevale/Daniele2TB/test/climatologia',
]

cartella_lavoro = [x for x in lista_possibili_cartelle_lavoro if os.path.exists(x)][0]
os.chdir(cartella_lavoro)
del (lista_possibili_cartelle_lavoro)

from matplotlib import font_manager
# font_files = font_manager.findSystemFonts(fontpaths='./../Gill_Sans')
font_files = font_manager.findSystemFonts(fontpaths='./../NotesEsa_font')
for font_file in font_files:
    font_manager.fontManager.addfont(font_file)

# plt.rc('font', family='Gill Sans', weight='normal', size=6)
plt.rc('font', family='NotesEsa', weight='normal', size=7)

regioni = Reader('./../shapefile/gadm41_ITA_shp/gadm41_ITA_1.shp')

for r in regioni.records():
    if r.attributes['NAME_1'] == 'Liguria':
        print(r.attributes)


anno1 = 2003
anno2 = 2022
intervallo_climatologico = pd.date_range(f'{anno1}-01-01', f'{anno2}-12-31')

# %%
### Per la pioggia è un po' più semplice
cartella_df = f'{cartella_lavoro}/query_pioggia'
lista_df = os.listdir(cartella_df)

df_tot = pd.DataFrame()

for i in lista_df:
    df = pd.read_csv(f'{cartella_df}/{i}', index_col=0, parse_dates=True)
    df = df.loc[intervallo_climatologico]
    df.columns = [i.split('.')[0]]
    df_tot = pd.concat([df_tot, df], axis=1)

# %%

# for anno_selezionato in range(2003, 2025 + 1):
for anno_selezionato in [2025]:
        
    df_mmm = pd.DataFrame()
    df_cum_annuali = pd.DataFrame()
    
    for anno in range(anno1, anno2 + 1):
        cumulata_anno = df_tot.loc[[x for x in df_tot.index if x.year == anno]].mean(axis=1).cumsum()
        cumulata_anno.index = [str(x).replace(str(anno), '2024') for x in cumulata_anno.index]
        cumulata_anno.index = pd.to_datetime(cumulata_anno.index)
        cumulata_anno = cumulata_anno.reindex(pd.date_range('2024-01-01', '2024-12-31'))
        
        df_cum_annuali[anno] = cumulata_anno
    
    df_mmm['minimo'] = df_cum_annuali.min(axis=1)
    df_mmm['q20'] = df_cum_annuali.quantile(0.20, axis=1)
    df_mmm['q35'] = df_cum_annuali.quantile(0.35, axis=1)
    df_mmm['media'] = df_cum_annuali.mean(axis=1)
    df_mmm['q65'] = df_cum_annuali.quantile(0.65, axis=1)
    df_mmm['q80'] = df_cum_annuali.quantile(0.80, axis=1)
    df_mmm['massimo'] = df_cum_annuali.max(axis=1)
    
    ### Correzione per il 29 febbraio
    df_mmm.loc['2024-02-29 00:00:00'] = np.nan
    df_mmm = df_mmm.interpolate(method='linear')
    
    ###########################################################
    
    df_anno_selezionato = pd.DataFrame()
    
    for i in lista_df:
        df = pd.read_csv(f'{cartella_df}/{i}', index_col=0, parse_dates=True)
        df = df.loc[[x for x in df.index if x.year == anno_selezionato]]
        df.columns = [i.split('.')[0]]
        df_anno_selezionato = pd.concat([df_anno_selezionato, df], axis=1)
    
    df_anno_selezionato = df_anno_selezionato.mean(axis=1).cumsum()
    df_anno_selezionato.index = [str(x).replace(str(anno_selezionato), '2024') for x in df_anno_selezionato.index]
    df_anno_selezionato.index = pd.to_datetime(df_anno_selezionato.index)
    df_anno_selezionato = df_anno_selezionato.reindex(pd.date_range('2024-01-01', df_anno_selezionato.index[-1]))
    
    ## test per vedere i superi estremi
    # df_anno_selezionato.loc['2024-07-17'] = 2000
    # df_anno_selezionato.loc['2024-07-18'] = 1000
    # df_anno_selezionato.loc['2024-07-19'] = 1500
    
    ### Correzione per il 29 febbraio
    df_anno_selezionato.loc['2024-02-29 00:00:00'] = np.nan
    df_anno_selezionato = df_anno_selezionato.interpolate(method='linear')
    
    df_mmm[anno_selezionato] = df_anno_selezionato
    
    ###########################################################
    
    smooth = True
    
    dict_cmap = {
        'Driest': '#8c510a',
        'Much drier\nthan average': '#d8b365',
        'Drier\nthan average': '#f6e8c3',
        'Near\naverage': '#f5f5f5',
        'Wetter\nthan average': '#d1e5f0',
        'Much wetter\nthan average': '#67a9cf',
        'Wettest': '#2166ac',
        }
    
    dict_cmap_traduzione = {
        'Driest': 'Estremamente\nsecco',
        'Much drier\nthan average': 'Molto più secco\ndella media',
        'Drier\nthan average': 'Più secco\ndella media',
        'Near\naverage': 'In media',
        'Wetter\nthan average': 'Più piovoso\ndella media',
        'Much wetter\nthan average': 'Molto più piovoso\ndella media',
        'Wettest': 'Estremamente\npiovoso',
        }
    
    dict_fill_between = {
        'alpha': 1,
        'interpolate': True,
        'zorder': 1,
        'edgecolor': 'black',
        'lw': 0.0
    }
    
    fig, ax = plt.subplots(figsize=(7, 4))
    
    if smooth:
        df_mmm = df_mmm.rolling(window=10, center=True, min_periods=1).mean()
    
    
    for i in df_mmm.columns:
        if i != 'media':
            df_mmm[i].plot(ax=ax, color='black', lw=0.1)
    
    df_mmm[anno_selezionato].plot(ax=ax, color='black', lw=0.5)
    
    media_vera = df_mmm[['q35', 'q65']].mean(axis=1)
    media_vera.plot(ax=ax, color='black', lw=0.2, ls=':')
    
    ax.fill_between(
        df_mmm.index,
        df_mmm[anno_selezionato],
        df_mmm['minimo'],
        where=(df_mmm[anno_selezionato] < df_mmm['minimo']) & df_mmm[anno_selezionato].notna() & df_mmm['minimo'].notna(),
        color=dict_cmap['Driest'],
        **dict_fill_between
    )
    
    ax.fill_between(
        df_mmm.index,
        df_mmm['minimo'], df_mmm['q20'],
        color=dict_cmap['Much drier\nthan average'], 
        **dict_fill_between
    )
    
    ax.fill_between(
        df_mmm.index, df_mmm['q20'], df_mmm['q35'],
        color=dict_cmap['Drier\nthan average'],
        **dict_fill_between
    )
    
    ax.fill_between(
        df_mmm.index, df_mmm['q35'], df_mmm['media'],
        color=dict_cmap['Near\naverage'],
        **dict_fill_between
    )
    
    ax.fill_between(
        df_mmm.index, df_mmm['media'], df_mmm['q65'],
        color=dict_cmap['Near\naverage'],
        **dict_fill_between
    )
    
    ax.fill_between(
        df_mmm.index, df_mmm['q65'], df_mmm['q80'],
        color=dict_cmap['Wetter\nthan average'],
        **dict_fill_between
    )
    
    ax.fill_between(
        df_mmm.index, df_mmm['q80'], df_mmm['massimo'],
        color=dict_cmap['Much wetter\nthan average'],
        **dict_fill_between
    )
    
    ax.fill_between(
        df_mmm.index,
        df_mmm['massimo'],
        df_mmm[anno_selezionato],
        where=(df_mmm[anno_selezionato] > df_mmm['massimo']) & df_mmm[anno_selezionato].notna() & df_mmm['minimo'].notna(),
        color=dict_cmap['Wettest'],
        **dict_fill_between
    )
    
    cmap_copernicus = ListedColormap(list(dict_cmap.values()))
    bounds = [0, 1, 2, 3, 4, 5, 6, 7]
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
    cbar.set_ticklabels(list(dict_cmap_traduzione.values()), fontsize=6)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    
    ### Tolgo l'ultimo 'dic'
    labels = [label.get_text() for label in ax.get_xticklabels()]
    labels = labels[:-1]
    ticks = ax.get_xticks()[:-1]
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)

    ax.set_title(anno_selezionato, fontsize=8)
    ax.text(1.0, 1.02, "Climatologia 2003-2022", transform=ax.transAxes, ha='right', va='bottom', fontsize=8)
    ax.text(-0.045, 1.02, "mm", transform=ax.transAxes, ha='left', va='bottom', fontsize=6)
    
    ax.set_ylim(0, 2500)
    ax.set_yticks([0, 500, 1000, 1500, 2000, 2500])
    ax.set_yticklabels([0, 500, 1000, 1500, 2000, 2500])
    
    ax.grid(alpha=0.3, zorder=-1, lw=0.5)
    
    plt.savefig(f'./Copernicus_3_pioggia_{anno_selezionato}.png', dpi=300, format='png', bbox_inches='tight')
    
    plt.show()
    plt.close()

print('\n\nDone')
