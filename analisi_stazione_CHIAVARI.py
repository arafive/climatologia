
import os

import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', FutureWarning)

import locale
locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from adjustText import adjust_text

lista_possibili_cartelle_lavoro = [
    '/media/daniele/Daniele2TB/repo/climatologia',
    '/run/media/daniele.carnevale/Daniele2TB/repo/climatologia',
]

cartella_lavoro = [x for x in lista_possibili_cartelle_lavoro if os.path.exists(x)][0]
os.chdir(cartella_lavoro)
del (lista_possibili_cartelle_lavoro)

from funzioni import f_settaggio_db

connessione = f_settaggio_db()

from matplotlib import font_manager
font_files = font_manager.findSystemFonts(fontpaths='./../../font/NotesEsa')
for font_file in font_files:
    font_manager.fontManager.addfont(font_file)

plt.rc('font', family='NotesEsa', weight='normal', size=6)

# %%
# Dati scaricati da: https://opendata.unige.net/dataset.xhtml?persistentId=doi:10.15167/OPENDATA/CCVUZU

cartella_stazione = '/mnt/isilon-arpal/agcmi00a00_comune/archivio/Archivio_CLIMA/dati_storici_Chiavari/Dati/tabulati dati grezzi'

df = pd.read_csv(f'{cartella_stazione}/database.meteo.chiavari.csv', sep=';', low_memory=False)
date = [f'{x}-{y}-{z}' for x, y, z in zip(df['anno'], df['mese'], df['giorno'])]
date = pd.to_datetime(date)
df.index = date

df = df[['temp.min', 'temp.max', 'tot_prec_mm']]
df.columns = ['TEMPN', 'TEMPX', 'RAINC']

# Aggiungo l'ultimo anno
query = """
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
data_1d.code = 'CHIRI' and
data_1d.dtrf>=to_date('201408010000', 'YYYYMMDDHH24MI')
-- and data_1d.dtrf <= trunc(sysdate) - 1 -- fino a ieri, altrimenti per qualche motivo mi prende anche il "domani" che non posso avere

order by dtrf

"""

dict_mesi = {
    'Gennaio': 1,
    'Febbraio': 2,
    'Marzo': 3,
    'Aprile': 4,
    'Maggio': 5,
    'Giugno': 6,
    'Luglio': 7,
    'Agosto': 8,
    'Settembre': 9,
    'Ottobre': 10,
    'Novembre': 11,
    'Dicembre': 12
    }

df_mq = pd.DataFrame(np.nan, index=dict_mesi.keys(), columns=['m_massime', 'q_massime', 'm_minime', 'q_minime'])

for mese, n_mese in dict_mesi.items():
    df_meteo = pd.read_sql(query, con=connessione)
    df_meteo.index = pd.to_datetime(df_meteo['TEMPO'])
    df_meteo = df_meteo.drop(['TEMPO', 'NAME', 'LON', 'LAT', 'ELEV', 'TMEAN'], axis=1)
    df_meteo.columns = ['TEMPN', 'TEMPX']
    
    df = pd.concat([df, df_meteo], axis=0)

    ### Massime delle massime
    max_max_annuale = (
        df.loc[df.index.month == n_mese, "TEMPX"]
          .groupby(df.index[df.index.month == n_mese].year)
          .max()
    )
    
    x = max_max_annuale.index.astype('int64')
    y = max_max_annuale.values
    
    m, q = np.polyfit(x, y, 1)
    df_mq.loc[mese, 'm_massime'] = m
    df_mq.loc[mese, 'q_massime'] = q
    
    trend_max = m * x + q
    
    ### Minime delle massime
    max_min_annuale = (
        df.loc[df.index.month == n_mese, "TEMPN"]
          .groupby(df.index[df.index.month == n_mese].year)
          .max()
    )
    
    x = max_min_annuale.index.astype('int64')
    y = max_min_annuale.values
    
    m, q = np.polyfit(x, y, 1)
    df_mq.loc[mese, 'm_minime'] = m
    df_mq.loc[mese, 'q_minime'] = q
    
    trend_min = m * x + q
    
    for lab, colore, df_T, trend in zip(['massime', 'minime'], ['tab:red', 'tab:blue'], [max_max_annuale, max_min_annuale], [trend_max, trend_min]):

        fig, ax = plt.subplots(figsize=(11, 5))
        
        df_T.plot(ax=ax, marker='.', color=colore, zorder=10, lw=0.8, markersize=5, ls='-')
        ax.plot(x, trend, color='black', zorder=-10, label='Trend', lw=0.8)
        
        ax.set_ylabel('°C', fontsize=10)
        ax.grid(True, which='major', axis='y', linestyle='-', linewidth=0.8, alpha=0.6)
        ax.tick_params(axis='both', which='both', length=1, size=4, labelsize=9)
        
        if lab == 'massime':
            ax.set_title(f'Massime delle massime di {mese}', fontsize=12, loc='left')
        elif lab == 'minime':
            ax.set_title(f'Massime delle minime di {mese}', fontsize=12, loc='left')
        
        ax.margins(x=0)
        
        ax.legend(
            prop={'size': 10},
            loc='upper left',
            ncol=2
            )
        
        val = df_T[df_T.idxmax()]
        m_mese = df_T.idxmax()
    
        texts = []
        txt = ax.annotate(
            f'{val}°C ({m_mese})',
            xy=(m_mese, val),
            xytext=(m_mese, val + 0.7),
            textcoords='data',
            fontsize=8,
            color='black',
            ha='center',
            arrowprops=dict(
                arrowstyle='-',
                color='black',
                lw=0.5,
                shrinkA=0,   # niente shrink all’origine (testo)
                shrinkB=0,   # un po' di shrink al punto (freccia scende giù)
            )
        )
        
        texts.append(txt)
        
        adjust_text(
            texts,
            expand=(4, 2),
            only_move={'text': 'x'}
        )
    
        plt.savefig(f'./CHIRI_{lab}_{mese}.png', dpi=300, format='png', bbox_inches='tight')
        plt.show()
        plt.close()
    
# %% Andamento del trend mensile

df_mq[['q_massime', 'q_minime']].plot()
df_mq[['m_massime', 'm_minime']].plot()

# %% File .pre per Luca Rusca (commentata perché non deve rigirare)

df = pd.read_csv(f'{cartella_stazione}/database.meteo.chiavari.csv', sep=';',low_memory=False)
df.index = pd.to_datetime(df['data'], format='mixed')
date = [f'{x.year}{x.month:02d}{x.day:02d}' for x in df.index]
df.index = date

df = df[['temp.min', 'temp.max', 'tot_prec_mm']]
df.columns = ['TEMPN', 'TEMPX', 'RAINC']

df_temp = df[['TEMPN', 'TEMPX']]
df_tp = df['RAINC']

df_TEMPX = df_temp['TEMPX']
df_TEMPN = df_temp['TEMPN']
df_RAINC = df_tp.copy()

cartella_destinazione = '/mnt/isilon-arpal/agcmi00a00_comune/archivio/Archivio_CLIMA/dati_storici_Chiavari/Dati/tabulati dati grezzi'

for nome, df_pre in zip(['TEMPN', 'TEMPX', 'RAINC'], [df_TEMPN, df_TEMPX, df_RAINC]):
    df_pre = df_pre.to_frame()
    df_pre['name'] = nome
    df_pre['stazione'] = 'CHIV0'
    
    df_pre = df_pre[['stazione', 'name', nome]]

    df_pre[nome] = df_pre[nome] * 10
    df_pre[nome] = [str(x).split('.')[0] for x in df_pre[nome]]
    
    df_pre.to_csv(f'{cartella_destinazione}/{nome}.pre', index=True, header=False, sep='\t')
    
print('\n\nDone')