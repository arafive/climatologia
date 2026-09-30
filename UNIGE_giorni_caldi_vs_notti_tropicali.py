"""
Creazione: Thu Sep  3 10:52:45 2026
Autore: daniele.carnevale
"""

import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', FutureWarning)

import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from adjustText import adjust_text

sys.path.insert(0, os.path.expanduser('~/.config'))
from config_percorsi_Daniele import CARTELLA_REPO_ROOT

cartella_lavoro = os.path.join(CARTELLA_REPO_ROOT, 'climatologia')
os.chdir(cartella_lavoro)

from danilib import f_settaggio_db_arpal

connessione = f_settaggio_db_arpal()

from matplotlib import font_manager
font_files = font_manager.findSystemFonts(fontpaths='./../../font/NotesEsa')
for font_file in font_files:
    font_manager.fontManager.addfont(font_file)

plt.rc('font', family='NotesEsa', weight='normal', size=12)

# %%

dict_df = {x: None for x in ['UNIGE', 'IMPER', 'SPZIA', 'INASV']}

for i in ['UNIGE', 'IMPER', 'SPZIA', 'INASV']:
    print(i)
    
    query_meteo = f"""
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
    data_1d.code = '{i}'
    
    order by dtrf
    
    """
    
    dict_clima = {
        'UNIGE': 'UNIV9',
        'IMPER': 'IMPE9',
        'SPZIA': 'SPZA9',
        'INASV': 'ISVD9'
        } 
    
    query_clima = f"""
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
    anag_clima.code='{dict_clima[i]}'
    
    order by day
    
    """

    df_meteo = pd.read_sql(query_meteo, con=connessione)
    df_clima = pd.read_sql(query_clima, con=connessione)
    
    df_meteo = df_meteo.set_index('TEMPO')
    df_meteo.index.name = ''
    df_meteo = df_meteo[['TMIN', 'TMAX']]
    df_meteo.index = pd.to_datetime(df_meteo.index)
    
    df_clima = df_clima.set_index('DAY')
    df_clima.index.name = ''
    df_clima = df_clima[['TMIN', 'TMAX']]
    df_clima.index = pd.to_datetime(df_clima.index)
    
    df = pd.concat([df_clima, df_meteo])
    df = df[~df.index.duplicated(keep='last')]
    
    df_anno = df.groupby(df.index.year).agg(
        n_notti_tropicali=('TMIN', lambda x: (x >= 20).sum()),
        n_notti_supertropicali=('TMIN', lambda x: (x >= 25).sum()),
        n_giorni_caldi=('TMAX', lambda x: (x >= 30).sum())
    )
    
    dict_df[i] = df_anno

# for chiave, valore in dict_df.items():
#     valore.plot()
#     plt.title(chiave)
#     plt.show()
#     plt.close()

# %%
df_anno = dict_df['UNIGE'].loc[1950:]

anni_notevoli_1 = list(np.arange(1950, 2030, 10))
anni_notevoli_2 = [2015, 2003, 2025, 2026, 2022]

anni_notevoli = anni_notevoli_1 + anni_notevoli_2

decadi = sorted(set((df_anno.index // 10) * 10))
cmap = plt.cm.YlOrRd
decade_colors = {d: cmap(i / (len(decadi) - 1)) for i, d in enumerate(decadi)}
decade_arr = pd.Series(df_anno.index // 10 * 10, index=df_anno.index)
colori = decade_arr.map(decade_colors)

media_notti_9120 = df_anno.loc[1991:2020, 'n_notti_tropicali'].mean()
media_giorni_9120 = df_anno.loc[1991:2020, 'n_giorni_caldi'].mean()
media_supertrop_9120 = df_anno.loc[1991:2020, 'n_notti_supertropicali'].mean()

# dimensione del pallino in base al numero di notti supertropicali
s_min, s_max = 20, 300
valori_supertrop = df_anno['n_notti_supertropicali']

def scala_dimensione(valori):
    v_min, v_max = valori_supertrop.min(), valori_supertrop.max()
    valori = np.asarray(valori, dtype=float)
    if v_max == v_min:
        return np.full_like(valori, (s_min + s_max) / 2)
    return s_min + (valori - v_min) / (v_max - v_min) * (s_max - s_min)

dimensioni = pd.Series(scala_dimensione(valori_supertrop), index=df_anno.index)

fig, ax = plt.subplots(figsize=(6, 5))

edgecolors = np.where(df_anno.index.isin(anni_notevoli), 'black', 'none')
linewidths = np.where(df_anno.index.isin(anni_notevoli), 0.8, 0)

df_anno.plot(
    ax=ax,
    kind='scatter',
    x='n_notti_tropicali',
    y='n_giorni_caldi',
    c=colori,
    s=dimensioni.values,
    edgecolors=edgecolors,
    linewidths=linewidths,
    zorder=10
    )

df_notevoli = df_anno.loc[anni_notevoli]
ax.scatter(
    df_notevoli['n_notti_tropicali'],
    df_notevoli['n_giorni_caldi'],
    c=colori.loc[anni_notevoli],
    s=dimensioni.loc[anni_notevoli].values,
    edgecolors='black',
    linewidths=0.8,
    zorder=14
    )
ax.scatter(media_notti_9120, media_giorni_9120, marker='^', c='black',
           s=scala_dimensione([media_supertrop_9120])[0], zorder=15)

ax.set_ylim(-5, 55)
ax.set_xlim(15, 145)

ax.grid(alpha=0.5)
ax.tick_params(left=False, bottom=False, labelsize=8)

ax.set_ylabel('N. di giorni caldi')
ax.set_xlabel('N. di notti tropicali')
ax.set_title('Genova')

for spine in ax.spines.values():
    spine.set_visible(False)

handles_decadi = [
    plt.Line2D([0], [0], marker='o', color='w',
               markerfacecolor=decade_colors[d], markersize=8, label=f'{d}')
    for d in decadi
    ]
handles_decadi.append(
    plt.Line2D([0], [0], marker='^', color='w',
               markerfacecolor='black', markersize=8, label='Media\n1991-2020')
    )
legenda_decadi = ax.legend(handles=handles_decadi, title='Decade', bbox_to_anchor=(1.02, 1),
          loc='upper left', fontsize=8, title_fontsize=8, frameon=False)
ax.add_artist(legenda_decadi)

# valori_legenda = sorted(set((np.round(np.linspace(valori_supertrop.min(), valori_supertrop.max(), 4) / 5) * 5).astype(int)))
valori_legenda = [0, 10, 25, 50]
handles_dimensione = [
    ax.scatter([], [], s=scala_dimensione([v])[0], color='grey',
               edgecolors='black', linewidths=0.5, label=str(v))
    for v in valori_legenda
    ]
legenda_dimensione = ax.legend(handles=handles_dimensione, title=r'N. di giorni con' + '\n' + r'T minima $\geq$ 25°C', bbox_to_anchor=(1.02, 0.4),
          loc='upper left', fontsize=8, title_fontsize=8, frameon=False, labelspacing=1.5,
          alignment='center')
legenda_dimensione.get_title().set_multialignment('center')

testi = []
for anno in anni_notevoli:
    x_anno = df_anno.loc[anno, 'n_notti_tropicali']
    y_anno = df_anno.loc[anno, 'n_giorni_caldi']
    fs = 6 if anno in anni_notevoli_1 else 7
    ft = 'normal' if anno in anni_notevoli_1 else 'bold'
    if anno == 1950:
        dx = 3
        dy = 0.5
    elif anno == 1990:
        dx = -1
        dy = 0
    elif anno == 2020:
        dx = 3
        dy = 0
    elif anno == 2003:
        dx = 0
        dy = 0.7
    elif anno == 2025:
        dx = 0
        dy = 0.7
    elif anno == 2010:
        dx = 0
        dy = 0.3
    elif anno in [2026, 2022, 2015]:
        dx = 0
        dy = 1.2
    else:
        dx = 0
        dy = 0
        
    testi.append(ax.text(x_anno + dx, y_anno + 0.8 + dy, str(anno), fontsize=fs, fontweight=ft,
                          color='black', ha='center', va='bottom', zorder=20))
    
plt.savefig('plot_UNIGE.png', dpi=300, format='png', bbox_inches='tight')
plt.show()
plt.close()

print('\n\nDone.')
