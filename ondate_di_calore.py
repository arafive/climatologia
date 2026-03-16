
import os
import pickle

import hotspell
import pkg_resources
### /home/daniele/Scrivania/dani/lib/python3.12/site-packages/hotspell/heatwaves.py:7: UserWarning:
### pkg_resources is deprecated as an API.
### See https://setuptools.pypa.io/en/latest/pkg_resources.html.
### The pkg_resources package is slated for removal as early as 2025-11-30.
### Refrain from using this package or pin to Setuptools<81.

import warnings
warnings.simplefilter('ignore', UserWarning)
from pandas.errors import SettingWithCopyWarning
warnings.simplefilter('ignore', SettingWithCopyWarning)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from adjustText import adjust_text
from scipy.stats import linregress

from matplotlib.path import Path
from matplotlib.colors import ListedColormap
from matplotlib.colors import BoundaryNorm
from matplotlib.colors import TwoSlopeNorm
from shapely.geometry import Polygon, MultiPolygon

import cartopy.crs as ccrs
from scipy.interpolate import griddata
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

from funzioni import f_log_ciclo_for
from funzioni import f_settaggio_db

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

cmap = ListedColormap([
    '#08306b', '#08519c', '#2171b5', '#4292c6', '#6baed6', '#9ecae1', '#c6dbef', '#deebf7', # blu
    '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d', # rosso
])


''' Calcolo della frequenza, intensità e durata delle ondate di calore

    ############

    Lamma --> https://www.lamma.toscana.it/news/ondate-di-calore-quale-definizione
    
    ############

    Heat Wave Duration Index (HWDI, WMO) --> è il periodo massimp in ogni anno
    di almeno 5 giorni consecutivi dove la Tmax è stata 5°C più calda
    della climatologia giornaliera.
    
    ############

    Excess Heat Factor (EHF) --> è una metrica che considera sia l'intensità
    che la durata dell'ondata di calore.
    
    ############
    
    Il pacchetto hotspell gestisce questo e altri criteri
    
    Perkins-Kirkpatrick and Lewis (2020) --> https://www.nature.com/articles/s41467-020-16970-7
   
    Nello studio “Increasing trends in regional heatwaves”, le heatwaves
    vengono definite e calcolate in modo rigoroso seguendo questo schema:

    Definizione di base (CTX90)
    Una heatwave è identificata quando si registrano almeno 3 giorni
    consecutivi con la temperatura massima (Tmax) superiore alla 90ᵃ
    percentile corrispondente al giorno dell’anno 
    
    La soglia (percentile) si basa su una finestra mobile di 15 giorni intorno
    a ciascuna data, calcolata sul periodo di riferimento 1961–1990,
    per tenere conto della stagionalità 
    
    Caratteristiche misurate
    Per ogni stagione calda (maggio‑settembre nell'emisfero nord,
    novembre‑marzo nell’emisfero sud), si calcolano:
    
    Frequenza: numero totale di giorni di heatwave in stagione.
    Durata: lunghezza (in giorni) della heatwave più intensa presente nella stagione.
    Intensità media: media degli scarti della Tmax rispetto alla soglia del
        90° percentile, considerati solo nei giorni di heatwave.
    Cumulative heat (heat₍cum₎): somma totale degli scarti termici giorno per
    giorno all’interno delle heatwave, che rappresenta il calore in eccesso cumulato 
    
    Matematicamente:
    
    heat_cum = Σ (T_ii − soglia_90)   [per tutti i giorni i appartenenti a heatwave]
    avg_anom = heat_cum / numero_di_giorni_di_heatwave
    
    Analisi delle tendenze
    Le tendenze decennali vengono calcolate usando Sen’s Kendall slope,
    un metodo robusto non parametrico, verificandone la significatività
    statistica al livello del 5% 
    
    L’analisi è condotta su dati giornalieri dal 1950, con trend che terminano
    nel 2014 (per HadGHCND) o nel 2017 (per Berkeley Earth) 
    
    Perché questa definizione?
    Garantisce coerenza spaziale (a livello globale e regionale) usando
    il dataset Berkeley Earth (~1°×1°) 
    
    La metrica del cumulative heat offre una visione più comprensiva
    dell’esposizione termica rispetto alla sola intensità media, poiché
    tiene conto anche della freq̈uenza e durata delle ondate di calore 
    
    In sintesi, le heat waves sono calcolate identificando blocchi di almeno
    3 giorni con temperature massime superiori al 90° percentile stagionale
    (periodo di riferimento 1961‑1990), e misurandone frequenza, durata,
    intensità media e cumulata. Le tendenze sono poi analizzate
    statisticamente su periodi decennali, evidenziando aumenti 
    significativi negli ultimi decenni.

'''

# %% Plot con i nomi delle stazioni cosi so dove sono
df_coord_meteo = pd.read_csv(f'{cartella_lavoro}/df_coord_stazioni_meteo.csv', index_col=0)

fig, ax = plt.subplots(figsize=(10, 4), subplot_kw={'projection': ccrs.PlateCarree()})
ax.set_extent((7.45, 10.1, 43.75, 44.7))
ax.set_aspect('auto', adjustable=None)

for r in regioni.records():
    if r.attributes['NAME_1'] == 'Liguria':
        liguria = r.geometry
        ax.add_geometries([liguria], crs=ccrs.PlateCarree(), facecolor='none', edgecolor='black', linewidth=0.5)
        
sc = ax.scatter(df_coord_meteo['lon'],
                df_coord_meteo['lat'],
                s=10,
                color='tab:red',
                transform=ccrs.PlateCarree())

texts = []
for x, y, s in zip(df_coord_meteo['lon'], df_coord_meteo['lat'], df_coord_meteo.index.tolist()):
    texts.append(plt.text(x, y, s, size=6, fontweight='normal', color='black'))
adjust_text(texts, only_move={'points':'y', 'texts':'y'})

plt.show()
plt.close()

del (ax, fig, r, sc, x, y, s, liguria, texts)

# %%
df_stazioni_meteo_clima =  pd.read_csv(f'{cartella_lavoro}/df_stazioni_meteo-clima.csv')
df_stazioni_meteo_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] != 'GEPCA'] # Alcune hanno problemi. Le tolgo.
df_stazioni_meteo_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] != 'PANES'] # Alcune hanno problemi. Le tolgo.

stazioni_meteo = df_stazioni_meteo_clima['Code'].tolist()

cartella_query_clima = f'{cartella_lavoro}/query_clima'
cartella_query_meteo = f'{cartella_lavoro}/query_meteo'

dict_opzioni_comuni = {
    'filename': f'{cartella_lavoro}/df_hotspell.csv',
    'ref_years': ('1991-01-01', '2020-12-31'),
    'summer_months': (5, 6, 7, 8, 9),
    'max_missing_days_pct': 25,
    'export': False
    }

dict_abbreviazioni = {
    'hwn': 'Heat wave number - The annual total sum of heat wave events',
    'hwf': 'Heat wave day frequency - The annual total sum of heat wave days',
    'hwd': 'Heat wave duration - The length of the longest heat wave per year',
    'hwdm': 'Heat wave duration (mean) - The average length of heat waves per year',
    'hwm': 'Heat wave magnitude - The average magnitude of all events (anomaly against seasonal mean)',
    'hwma': 'Heat wave magnitude (absolute value) - The average magnitude of all events',
    'hwa': 'Heat wave amplitude - The hottest day of hottest event per year (anomaly against seasonal mean)',
    'hwaa': 'Heat wave amplitude (absolute value) - The hottest day of hottest event per year',
    }

dict_abbreviazioni_plot = {
    'hwn': 'Numero medio all\'anno',
    'hwf': 'Somma media di tutti i giorni di evento',
    'hwd': '',
    'hwdm': 'Durata media',
    'hwm': '',
    'hwma': '',
    'hwa': '',
    'hwaa': '',
    }

# if not os.path.exists(f'{cartella_lavoro}/dict_stazioni_oc_gc_nt.pkl'):
if os.path.exists(f'{cartella_lavoro}/dict_stazioni_oc_gc_nt.pkl'):
    dict_stazioni = {}
    
    for s_meteo in stazioni_meteo:
        f_log_ciclo_for([['Stazione ', s_meteo, stazioni_meteo]])
        
        s_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] == s_meteo]['Code9'].iloc[0]
        df = pd.read_csv(f'{cartella_query_clima}/{s_clima}.csv', index_col=0, parse_dates=True)
    
        df_meteo = pd.read_csv(f'{cartella_query_meteo}/{s_meteo}.csv', index_col=0, parse_dates=True)
        df_meteo.index.name = ''
        
        ### !!! ['MURIA', 'CAIRM', 'PIAMP', 'BUSAL', 'BRUGN', 'ROVEG', 'CABAN', 'SSTAV'] non hanno la Tmax, ma l'hanno le gemelle climatologiche
        
        # if s_meteo in ['LFMTV']:
        #     fig, ax = plt.subplots(figsize=(7, 4))
        #     df['TMEAN'].plot(ax=ax, color='tab:blue', lw=0.5, legend=False)
        #     df_meteo['TMEAN'].plot(ax=ax, color='tab:orange', lw=0.5, legend=False)
        #     plt.title(s_meteo)
        #     plt.axhline(25, color='black', lw=0.5)
        #     plt.axhline(27.5, color='black', lw=0.5)
        #     plt.ylim(-5, 35)
        #     plt.show()
        #     plt.close()
        
        df = pd.concat([df, df_meteo], axis=0)
        
        df['anno'] = df.index.year
        df['mese'] = df.index.month
        df['giorno'] = df.index.day
        
        df = df[['anno', 'mese', 'giorno', 'TMIN', 'TMAX']]
        
        ### Forzo le colonne ad essere del tipo che voglio
        df = df.astype({'anno': int, 'mese': int, 'giorno': int, 'TMIN': float, 'TMAX': float})
        
        ### Questa spiegazione si trova nella guida. Il pacchetto cerca un file e lo legge per conto suo
        df.to_csv(f'{cartella_lavoro}/df_hotspell.csv', index=False, header=False)
        
        ondate_di_calore = hotspell.get_heatwaves(
            hw_index=hotspell.index(name='ctx90pct'), 
            **dict_opzioni_comuni
            )
        
        giorni_caldi = hotspell.get_heatwaves(
            hw_index=hotspell.index(name='hot_days'),
            **dict_opzioni_comuni
            )
        
        notti_tropicali = hotspell.get_heatwaves(
            hw_index=hotspell.index(name='tropical_nights'), 
            **dict_opzioni_comuni
            )
        
        dict_stazioni[s_meteo] = {
            'Ondate di calore': {
                'eventi': ondate_di_calore.events,
                'statistiche': ondate_di_calore.events.describe()[['duration', 'avg_tmax', 'std_tmax', 'max_tmax']],
                'metriche': ondate_di_calore.metrics,
                },
            'Giorni caldi': {
                'eventi': giorni_caldi.events,
                'statistiche': giorni_caldi.events.describe()[['duration', 'avg_tmax', 'std_tmax', 'max_tmax']],
                'metriche': giorni_caldi.metrics,
                },
            'Notti tropicali': {
                'eventi': notti_tropicali.events,
                'statistiche': notti_tropicali.events.describe()[['duration', 'avg_tmin', 'std_tmin', 'max_tmin']],
                'metriche': notti_tropicali.metrics,
                }
            }
            
    pickle.dump(dict_stazioni, open(f'{cartella_lavoro}/dict_stazioni_oc_gc_nt.pkl', 'wb'))
    os.system(f'rm {cartella_lavoro}/df_hotspell.csv')
    
    del (df, ondate_di_calore, giorni_caldi, notti_tropicali, s_meteo, s_clima, df_meteo)
    
else:
    print(f'\n{cartella_lavoro}/dict_stazioni_oc_gc_nt.pkl esiste. Lo carico.\n')
    dict_stazioni = pickle.load(open(f'{cartella_lavoro}/dict_stazioni_oc_gc_nt.pkl', 'rb'))

###############
###############

lista_df_ondate_di_calore = []
lista_df_giorni_caldi = []
lista_df_notti_tropicali = []

for s_meteo in stazioni_meteo:
    lista_df_ondate_di_calore.append(dict_stazioni[s_meteo]['Ondate di calore']['metriche'])
    lista_df_giorni_caldi.append(dict_stazioni[s_meteo]['Giorni caldi']['metriche'])
    lista_df_notti_tropicali.append(dict_stazioni[s_meteo]['Notti tropicali']['metriche'])

df_media_ondate_di_calore = pd.concat(lista_df_ondate_di_calore).groupby(level=0).mean().round(2)
df_media_giorni_caldi = pd.concat(lista_df_giorni_caldi).groupby(level=0).mean().round(2)
df_media_notti_tropicali = pd.concat(lista_df_notti_tropicali).groupby(level=0).mean().round(2)

del (lista_df_ondate_di_calore, lista_df_giorni_caldi, lista_df_notti_tropicali, s_meteo)

# %% Heatmap su tutte le stazioni liguri

cmap = ListedColormap(['#e9e9e9', '#ffffff', '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d'])

dict_cmap = {
    'Ondate di calore' : [-1, 0, 5, 10, 15, 20, 25, 30, 40, 60, 80],
    'Giorni caldi' : [-1, 0, 1, 3, 5, 10, 15, 20, 25, 30, 40],
    'Notti tropicali': [-1, 0, 10, 20, 30, 50, 60, 70, 90, 100, 120]
}

dict_df_heatmap = {x: None for x in dict_cmap.keys()}

for d in dict_df_heatmap.keys():
    df_heatmap = pd.DataFrame(np.nan, index=df_media_giorni_caldi.index, columns=stazioni_meteo)
    
    for s_meteo in stazioni_meteo:
        df_heatmap[s_meteo] = dict_stazioni[s_meteo][d]['metriche']['hwf']
    
    df_heatmap = df_heatmap[::-1]
    df = df_heatmap.fillna(-1)

    dict_df_heatmap[d] = df_heatmap
    
    bounds = dict_cmap[d]
    norm = BoundaryNorm(bounds, cmap.N)
    
    ###############
    
    fig, ax = plt.subplots(figsize=(9, 5))
    
    cax = ax.imshow(df.values, cmap=cmap, norm=norm, aspect='auto')
    
    if d == 'Ondate di calore':
        ax.set_title('Giorni di ondate di calore in Liguria')
    else:
        ax.set_title(f'{d} in Liguria')
        
    ax.set_yticks(range(0, len(df.index), 2))
    ax.set_yticklabels(df.index[::2], fontsize=5)
    
    ylabel = 'nomi_stazioni' # nomi_stazioni, niente
    if ylabel == 'nomi_stazioni': 
        ax.set_xticks(range(len(df.columns)))
        ax.set_xticklabels(df.columns, fontsize=5, rotation=90)
        ax.tick_params(axis='x', which='both', length=0, size=0)
    
    elif ylabel == 'niente':
        ax.set_xticks(range(len(df.columns)))
        ax.set_xticklabels(['' for _ in range(len(df.columns))])
        ax.tick_params(axis='x', which='both', length=0, size=0)
        ax.set_xlabel('Stazioni', fontsize=7)
    
    ## Aggiungi testo nei quadretti
    for i in range(len(df.index)):
        for j in range(len(df.columns)):
            if df.iloc[i, j] >= bounds[3]:
                if df.iloc[i, j] >= bounds[-2]:
                    ax.text(j, i, f'{df.iloc[i, j]:.0f}', va='center', ha='center', color='white', fontsize=4)
                else:
                    ax.text(j, i, f'{df.iloc[i, j]:.0f}', va='center', ha='center', color='black', fontsize=4)
    
    cbar = fig.colorbar(cax, ax=ax)
    cbar.set_ticks(bounds)
    bounds[0] = 'NaN'
    cbar.set_ticklabels(bounds)
    
    plt.savefig(f"./heatmap_{d.replace(' ', '_')}.png", dpi=300, format='png', bbox_inches='tight')
    
    plt.show()
    plt.close()
    
del (df, bounds, cmap, i, j, norm, ax, cbar, ylabel, d, cax, fig, s_meteo, df_heatmap)

# %% Andamento di "Giorni di ondate di calore", "Notti tropicali" e "Giorni caldi" nei 4 capoluoghi

dict_df_heatmap = {x: None for x in dict_cmap.keys()}

dict_stazioni_capoluoghi = {
    'UNIGE': 'Genova',
    'SPZIA': 'La Spezia',
    'INASV': 'Savona',
    'IMPER': 'Imperia'
    }

dict_opts = {
    'Ondate di calore' : {'vmin': 0, 'vmax': 35},
    'Giorni caldi' : {'vmin': 0, 'vmax': 10},
    'Notti tropicali': {'vmin': 0, 'vmax': 100},
    }

for d in dict_df_heatmap.keys():
    df_heatmap = pd.DataFrame(np.nan, index=df_media_giorni_caldi.index, columns=dict_stazioni_capoluoghi.keys())
    
    for s in dict_stazioni_capoluoghi.keys():
        df_heatmap[s] = dict_stazioni[s][d]['metriche']['hwf']
        
        df_heatmap = df_heatmap[::-1]
    
        dict_df_heatmap[d] = df_heatmap

    fig, axes = plt.subplots(2, 2, figsize=(9, 5), sharex=True, sharey=True)
    
    if d == 'Ondate di calore':
        fig.suptitle('Giorni di ondate di calore', fontsize=14)
    else:
        fig.suptitle(d, fontsize=14)
    
    for ax, col in zip(axes.flatten(), dict_stazioni_capoluoghi.keys()):
        
        mask = dict_df_heatmap[d][col].notna()
        
        ax.plot(dict_df_heatmap[d].index[mask], dict_df_heatmap[d][col][mask], marker='', color='gray', alpha=0.4, lw=1, zorder=-1) # Linee
        
        sc = ax.scatter(
            dict_df_heatmap[d].index[mask],
            dict_df_heatmap[d][col][mask],
            c=dict_df_heatmap[d][col][mask],
            cmap='jet',
            vmin=dict_opts[d]['vmin'],
            vmax=dict_opts[d]['vmax'],
            marker='.',
            s=80,
            zorder=10
        )
        
        ax.set_title(dict_stazioni_capoluoghi[col], fontsize=10)
        ax.grid(True, alpha=0.2)
    
    # axes[0, 0].set_ylabel("Numero")
    # axes[1, 0].set_ylabel("Numero")
    
    axes[1, 0].set_xlabel("Anno")
    axes[1, 1].set_xlabel("Anno")
    
    plt.tight_layout()
    
    plt.savefig(f"./heatmap_capoluoghi_{d.replace(' ', '_')}.png", dpi=300, format='png', bbox_inches='tight')

    plt.show()
    plt.close()

del (s)

# %% Andamento di "Giorni di ondate di calore", "Notti tropicali" e "Giorni caldi" SOLO su UNIGE/UNIV9

connessione = f_settaggio_db()

query_meteo = """
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
data_1d.code = 'UNIGE' and
data_1d.dtrf>=to_date('202101010000', 'YYYYMMDDHH24MI') and
data_1d.dtrf <= trunc(sysdate) - 1 -- fino a ieri, altrimenti per qualche motivo mi prende anche il "domani" che non posso avere

order by dtrf

"""

query_clima = """
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
anag_clima.code='UNIV9'

order by day

"""

df_clima = pd.read_sql(query_clima, con=connessione)

df_clima = df_clima.set_index('DAY')
df_clima = df_clima.drop(['NAME', 'LON', 'LAT', 'ELEV'], axis=1)
df_clima['TMEAN'] = df_clima.mean(axis=1)
df_clima.index.name = ''

###

df_meteo = pd.read_sql(query_meteo, con=connessione)

df_meteo = df_meteo.set_index('TEMPO')
df_meteo = df_meteo.drop(['NAME', 'LON', 'LAT', 'ELEV'], axis=1)
df_meteo.index.name = ''

###

df_UNIGE = pd.concat([df_clima, df_meteo], axis=0)
df_UNIGE.index = pd.to_datetime(df_UNIGE.index)
# !!! Per uniformarmi al plot Copernicus inizio dal 1940
# Vedi https://climate.copernicus.eu/copernicus-2025-was-third-hottest-year-record
df_UNIGE = df_UNIGE.loc[df_UNIGE.index > '1940-01-01']

anno_corrente = pd.Timestamp.now().year
df_UNIGE = df_UNIGE[df_UNIGE.index.year != anno_corrente]

df_UNIGE['anno'] = df_UNIGE.index.year
df_UNIGE['mese'] = df_UNIGE.index.month
df_UNIGE['giorno'] = df_UNIGE.index.day

df_UNIGE = df_UNIGE[['anno', 'mese', 'giorno', 'TMIN', 'TMAX']]

### Forzo le colonne ad essere del tipo che voglio
df_UNIGE = df_UNIGE.astype({'anno': int, 'mese': int, 'giorno': int, 'TMIN': float, 'TMAX': float})

### Questa spiegazione si trova nella guida. Il pacchetto cerca un file e lo legge per conto suo
df_UNIGE.to_csv(f'{cartella_lavoro}/df_hotspell_UNIGE.csv', index=False, header=False)

ondate_di_calore_UNIGE = hotspell.get_heatwaves(
    hw_index=hotspell.index(name='ctx90pct'),
    filename='./df_hotspell_UNIGE.csv',
    ref_years=('1991-01-01', '2020-12-31'),
    summer_months=(5, 6, 7, 8, 9),
    max_missing_days_pct=25,
    export=False
    )

giorni_caldi_UNIGE = hotspell.get_heatwaves(
    hw_index=hotspell.index(name='hot_days'),
    filename='./df_hotspell_UNIGE.csv',
    ref_years=('1991-01-01', '2020-12-31'),
    summer_months=(5, 6, 7, 8, 9),
    max_missing_days_pct=25,
    export=False
    )

notti_tropicali_UNIGE = hotspell.get_heatwaves(
    hw_index=hotspell.index(name='tropical_nights'), 
    filename='./df_hotspell_UNIGE.csv',
    ref_years=('1991-01-01', '2020-12-31'),
    summer_months=(5, 6, 7, 8, 9),
    max_missing_days_pct=25,
    export=False
    )

dict_UNIGE = {
    'Ondate di calore': {
        'eventi': ondate_di_calore_UNIGE.events,
        'statistiche': ondate_di_calore_UNIGE.events.describe()[['duration', 'avg_tmax', 'std_tmax', 'max_tmax']],
        'metriche': ondate_di_calore_UNIGE.metrics,
        },
    'Giorni caldi': {
        'eventi': giorni_caldi_UNIGE.events,
        'statistiche': giorni_caldi_UNIGE.events.describe()[['duration', 'avg_tmax', 'std_tmax', 'max_tmax']],
        'metriche': giorni_caldi_UNIGE.metrics,
        },
    'Notti tropicali': {
        'eventi': notti_tropicali_UNIGE.events,
        'statistiche': notti_tropicali_UNIGE.events.describe()[['duration', 'avg_tmin', 'std_tmin', 'max_tmin']],
        'metriche': notti_tropicali_UNIGE.metrics,
        }
    }
    
os.system(f'rm {cartella_lavoro}/df_hotspell_UNIGE.csv')

###############
###############

cmap = ListedColormap([
    '#08306b', '#084184', '#08519c', '#1561A9', '#2171b5', '#3282BE', '#4292c6', '#57A0CE', '#6baed6', '#85BCDC', '#9ecae1', '#B2D3E8', '#c6dbef', '#D2E3F3', '#deebf7',
    ###
    '#fee0d2', '#FDCEBA', '#fcbba1', '#FCA78A', '#fc9272', '#FC7E5E', '#fb6a4a', '#F5533B', '#ef3b2c', '#DD2A25', '#cb181d', '#B81419', '#a50f15', '#860811', '#67000d',
])

fig, axes = plt.subplots(4, 1, figsize=(7, 9))

for ax, d in zip(axes.flatten(), dict_UNIGE.keys()):
        
    dict_UNIGE[d]['metriche']['hwf'].plot(ax=ax, marker='', color='gray', alpha=0.4, lw=1, zorder=-1)
    
    sc = ax.scatter(
        dict_UNIGE[d]['metriche']['hwf'].index,
        dict_UNIGE[d]['metriche']['hwf'],
        c=dict_UNIGE[d]['metriche']['hwf'],
        cmap=cmap,
        vmin=dict_opts[d]['vmin'],
        vmax=dict_opts[d]['vmax'],
        marker='.',
        s=30,
        zorder=10
    )    
    
    ax.set_title(d, fontsize=10)
    ax.set_xticks(np.arange(1940, 2025 + 5, 5))
    ax.set_xticklabels(np.arange(1940, 2025 + 5, 5), rotation=45)
    ax.margins(x=0.01)
    ax.set_xlabel('')
    ax.set_ylabel('Numero')
    ax.grid(True, alpha=0.2)
    
###

tmean_UNIGE = df_UNIGE[['TMIN', 'TMAX']].mean(axis=1).groupby(pd.Grouper(freq="Y")).mean()
tmean_UNIGE.index = dict_UNIGE[d]['metriche']['hwf'].index
tmean_UNIGE.index.name = ''

tmean_UNIGE_2003_2022 = tmean_UNIGE.loc[2003:2022].mean()

num_colors = cmap.N
half = num_colors // 2
norm = TwoSlopeNorm(vmin=tmean_UNIGE_2003_2022-2, vcenter=tmean_UNIGE_2003_2022, vmax=tmean_UNIGE_2003_2022+2)

colors = [cmap(norm(val)) for val in tmean_UNIGE.values]

tmean_UNIGE.plot(ax=axes[-1], kind='bar', width=1, color=colors)

anni = tmean_UNIGE.index
anni_sel = anni[(anni >= 1940) & (anni <= 2025) & (anni % 5 == 0)]
posizioni = [list(anni).index(a) for a in anni_sel]

axes[-1].set_title('Temperatura media annuale rispetto alla media 2003-2022 (linea orizzontale)', fontsize=10)
axes[-1].set_xticks(posizioni)
axes[-1].set_xticklabels(anni_sel, rotation=45)
axes[-1].set_xlabel('Anni')
axes[-1].set_ylabel('Temperatura [°C]')
axes[-1].set_ylim(14, 19)

axes[-1].hlines(y=tmean_UNIGE_2003_2022, xmin=axes[-1].get_xlim()[0], xmax=axes[-1].get_xlim()[1], linewidth=0.5, color='k', alpha=0.5)

plt.tight_layout()

plt.savefig("./andamento_UNIGE.png", dpi=300, format='png', bbox_inches='tight')
plt.show()
plt.close()

# ### Controllo sulle notti tropicali
# conteggio = (
#     df_UNIGE[df_UNIGE["TMIN"] > 20]
#     .groupby(pd.Grouper(freq="Y"))
#     .size()
# )

# conteggio.plot()
# plt.show()
# plt.close()

# %%
### https://climate.copernicus.eu/GCH2025-graphics-gallery
### Normalizzato secondo la media

df_Copernicus_3a = pd.read_csv('./GCH2025_Fig3a_timeseries_annual_global_temperature_anomalies_preindustrial_data.csv', index_col=0, skiprows=11)

df_confronto = pd.concat([df_Copernicus_3a['2t'], tmean_UNIGE], axis=1)
df_confronto.columns = ['Globale', 'UNIGE']

# !!! Devo normalizzare rispetto alle rispettive medie per confrontarli
df_confronto['Globale'] = df_confronto['Globale'] / df_confronto['Globale'].mean()
df_confronto['UNIGE'] = df_confronto['UNIGE'] / df_confronto['UNIGE'].mean()

fig, ax = plt.subplots()

df_confronto.plot(ax=ax)
ax.set_xlim(1940, 2025)

ax.tick_params(axis='x', labelsize=5, rotation=45)
ax.set_ylim(0.85, 1.15)

plt.show()
plt.close()

del (df_confronto)

### Anomalie

t_ref_0, t_ref_1 = 2003, 2022
anomalia_UNIGE = tmean_UNIGE - tmean_UNIGE.loc[t_ref_0:t_ref_1].mean()
anomalia_GLOBO = df_Copernicus_3a['2t'] - df_Copernicus_3a.loc[t_ref_0:t_ref_1]['2t'].mean()

df_confronto = pd.concat([anomalia_GLOBO, anomalia_UNIGE], axis=1)
df_confronto.columns = ['Globale', 'UNIGE']

fig, ax = plt.subplots()

cmap = ListedColormap([
    '#08306b', '#08519c', '#2171b5', '#4292c6', '#6baed6', '#9ecae1', '#c6dbef', '#deebf7', # blu
    '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d', # rosso
])


df_confronto.plot(ax=ax, color=['#4292c6', '#ef3b2c'])

ax.hlines(y=0, xmin=df_confronto.index[0], xmax=df_confronto.index[-1], linewidth=0.4, alpha=0.4, color='k', zorder=-3)
ax.margins(x=0.0)
ax.set_ylim(-2.5, 2.5)
ax.set_xticks(np.arange(1940, 2025 + 5, 5))
ax.grid(True, alpha=0.2)
ax.set_title(f'Anomalia media di temperatura rispetto alla media del periodo {t_ref_0}-{t_ref_1}')
ax.set_xlabel('Anni')    
ax.set_ylabel('Anomalia [°C]')    
ax.tick_params(axis='x', labelsize=6, rotation=45)

plt.savefig("./andamento_UNIGE_vs_Globale.png", dpi=300, format='png', bbox_inches='tight')

plt.show()
plt.close()

sss

# %% "Giorni di ondate di calore", "Notti tropicali" e "Giorni caldi" considerando la Liguria come una media di stazioni

dict_colori = {'hwn': 'tab:blue', 'hwf': 'tab:red', 'hwdm': 'tab:green'}
dict_colori_rimappato = {dict_abbreviazioni_plot[k]: v for k, v in dict_colori.items() if k in dict_abbreviazioni_plot}

for i, df in zip(dict_stazioni['AIROL'].keys(), [df_media_ondate_di_calore, df_media_giorni_caldi, df_media_notti_tropicali]):
    
    df = df[['hwn', 'hwf', 'hwdm']]
    if i == 'Notti tropicali' or i == 'Giorni caldi':
        df = df[['hwf']] # Tolgo il numero di eventi e la durata che andrebbero insieme ma possono generare confusione
        
    df = df.rename(columns=dict_abbreviazioni_plot)
    
    df = df.drop(2025) # Droppo l'ultimo anno altrimenti mi scombina il trend
    df.index.name = '' # Non c'è bisogno che scrivo 'Anni'. Si capisce.
    anni = df.index.values
    
    fig, ax = plt.subplots(figsize=(7, 4))
    
    df.plot(ax=ax, marker='.', color=dict_colori_rimappato, lw=1)
    
    # Regressione lineare per i tren temporali
    for c in df.columns:
        pendenza, intercetta, R, p_value, std_err = linregress(anni, df[c].values)
        print(f"Trend per {c}:")
        print(f"  slope = {pendenza:.4f} per anno")
        print(f"  intercept = {intercetta:.2f}")
        print(f"  R² = {R**2:.3f}")
        if p_value < 0.05:
            print(f"  p-value SIGNIFICATIVO = {p_value:.4f}")
        else:
            print(f"  p-value NON SIGNIFICATIVO = {p_value:.4f}")
        print()
        
        # Calcola valori della retta
        trend_col = intercetta + pendenza * anni
        ax.plot(anni, trend_col, label='Trend', color=dict_colori_rimappato[c], ls='--', lw=0.75)
        
    ax.set_xticks(np.append(anni[anni % 2 == 0], 2025))
    ax.set_xticklabels(np.append(anni[anni % 2 == 0], 2025))
    ax.tick_params(axis='x', labelsize=5)
    
    ax.legend(ncol=2, loc='upper left')
    ax.set_title(f'{i} in Liguria')
    ax.grid(True, lw=0.25)
    ax.set_ylim(bottom=0)
    ax.set_ylabel('Giorni / Numero di eventi') if i == 'Ondate di calore' else ax.set_ylabel('Giorni')
    ax.margins(x=0.02)
    
    plt.savefig(f"./trend_{i.replace(' ', '_')}_mediate.png", dpi=300, format='png', bbox_inches='tight')
    plt.show()
    plt.close()

del (i, c, df, fig, ax, anni, dict_colori, dict_colori_rimappato, trend_col, R, p_value, std_err, pendenza, intercetta)

# %% Interpolazione e plot geografici di anomalie

cmap = ListedColormap([
    '#08306b', '#08519c', '#2171b5', '#4292c6',
    '#6baed6', '#9ecae1', '#c6dbef', '#deebf7',
    '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a',
    '#ef3b2c', '#cb181d', '#a50f15', '#67000d',
])

dict_livelli = {
    'Ondate di calore': np.arange(-20, 20 + 1, 1),
    'Giorni caldi': np.arange(-6, 6 + 1, 1),
    'Notti tropicali': np.arange(-20, 20 + 1, 1)
}

anno = 2024 ### Non lo faccio rispetto all'ultimo anno che è incompleto. Dovrei ricaldolare 'dict_df_heatmap' prendendo solo i giorni comuni passati.
tipo_di_anomalia = '90percentile' # media, 90percentile
modello = 'moloch'
kriging = 'ordinary'

dict_anomalie = {y: {x: {'clima': pd.DataFrame(), 'anno': pd.DataFrame()} for x in dict_df_heatmap.keys()} for y in dict_df_heatmap.keys()}

fig, axs = plt.subplots(1, 3, figsize=(12, 3), subplot_kw={'projection': ccrs.PlateCarree()})

if tipo_di_anomalia == 'media':
    titolo = f'{anno} - Anomalia in giorni rispetto alla media climatologica 1991-2020'
elif tipo_di_anomalia == '90percentile':
    titolo = f'{anno} - Anomalia in giorni rispetto al 90° percentile della climatologia 1991-2020'

fig.suptitle(titolo)

for i, ax in zip(dict_anomalie.keys(), axs.flatten()):
    df_anni_stazioni = dict_df_heatmap[i]
    
    if tipo_di_anomalia == 'media':
        df_clima = df_anni_stazioni.loc[range(1991, 2021)].mean()
    elif tipo_di_anomalia == '90percentile':
        df_clima = df_anni_stazioni.loc[range(1991, 2021)].quantile(0.9, axis=0)

    df_anno = df_anni_stazioni.loc[anno]
    
    df = pd.DataFrame({'clima': df_clima, 'anno': df_anno})
    df = df.dropna() ### devo togliere i NaN perché altrimenti non posso interpolare
    df['anomalia'] = df['anno'] - df['clima']
    
    df_coord_meteo = pd.read_csv(f'{cartella_lavoro}/df_coord_stazioni_meteo.csv', index_col=0)
    df_coord_meteo = df_coord_meteo.loc[df.index]
    
    lat_stazioni = df_coord_meteo['lat'].values
    lon_stazioni = df_coord_meteo['lon'].values
    elev_stazioni = df_coord_meteo['elev'].values
    anom_stazioni = df['anomalia'].values

    ##################
    
    lat_interp = np.linspace(43.2, 45.3, 800)[::-1]
    lon_interp = np.linspace(7.2, 10.5, 800)
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
    
    ax.set_extent((7.45, 10.1, 43.75, 44.7))
    ax.set_aspect('auto', adjustable=None)
    ax.set_title(i)
    
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
        levels=dict_livelli[i],
        cmap=cmap,
        vmin=dict_livelli[i][0],
        vmax=dict_livelli[i][-1],
        transform=ccrs.PlateCarree(),
        extend='both'
    )
    
    sc = ax.scatter(df_coord_meteo['lon'], df_coord_meteo['lat'], c=df['anomalia'],
                    cmap=cmap,
                    vmin=dict_livelli[i][0],
                    vmax=dict_livelli[i][-1],
                    s=15,
                    edgecolor='black',
                    lw=0.3,
                    zorder=10,
                    transform=ccrs.PlateCarree())
    
    cb = plt.colorbar(pcm, ax=ax, orientation='horizontal', shrink=0.75, pad=0.05)
    cb.outline.set_visible(False)

plt.tight_layout()

plt.savefig(f"./{anno}_anomalia_{tipo_di_anomalia}.png", dpi=300, format='png', bbox_inches='tight')
plt.show()
plt.close()
        
del (anno, i, df_anni_stazioni, df_clima, df_anno, df, df_coord_meteo, cb, ax, fig, sc, kriging, mask, masks)
del (anom_stazioni, lat_stazioni, lon_stazioni, elev_stazioni, poly, pcm, ss, verts, z_interp, z_masked)
del (paths, points, modello, lat_2D_interp, lat_interp, lon_2D_interp, lon_interp, mask_flat, cmap, titolo, tipo_di_anomalia)

print('\n\nDone.')