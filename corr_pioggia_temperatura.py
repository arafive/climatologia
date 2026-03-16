
import os

import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', FutureWarning)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import gaussian_kde

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

# %%

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

df_coord_meteo = df_coord_meteo[df_coord_meteo.index != 'BOACM'] # È la boa, non la uso
df_coord_meteo = df_coord_meteo[df_coord_meteo.index != 'MTMEZ'] # È la boa, non la uso
df_coord_meteo = df_coord_meteo[df_coord_meteo.index != 'SLEVA'] # È la boa, non la uso
df_coord_meteo = df_coord_meteo[df_coord_meteo.index != 'SMACC'] # È la boa, non la uso
df_coord_meteo = df_coord_meteo[df_coord_meteo.index != 'STBUR'] # È la boa, non la uso
df_coord_meteo = df_coord_meteo[df_coord_meteo.index != 'TANOR'] # È la boa, non la uso
df_coord_meteo = df_coord_meteo[df_coord_meteo.index != 'UNIGE'] # È la boa, non la uso

del (df)

cartella_pioggia_cumulate = f'{cartella_lavoro}/query_pioggia_cumulate'
os.makedirs(cartella_pioggia_cumulate, exist_ok=True)

anno_corrente = pd.Timestamp.now().year
anni = np.arange(2000, 2025 + 1)

# %% PIOGGIA
### Query meteo

for s in df_coord_meteo.index:
    if not os.path.exists(f'{cartella_pioggia_cumulate}/{s}.csv'):
        f_log_ciclo_for([['Query meteo ', s, df_coord_meteo.index.tolist()]])
    
        query = f"""
        select
        to_char(data.dtrf, 'YYYY-MM-DD HH24:MI:SS') as tempo,
        anag.lon/1e5 as lon,
        anag.lat/1e5 as lat,
        anag.elev as elev,
        anag.name as name,
        data.rainc/10 as nativa
        
        from
        data,
        anag
        
        where
        data.code = anag.code and
        data.v_rainc < 'I' and
        data.code = '{s}'
        
        -- Soluzione momentanea
        -- and extract(year from data.dtrf) = 2025
        
        order by dtrf
        
        """
    
        df = pd.read_sql(query, con=connessione)
    
        df = df.set_index('TEMPO')
        df = df.drop(['NAME', 'LON', 'LAT', 'ELEV'], axis=1)
    
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df[df.index.year >= anni[0]]

        ### Qui devo fare attenzione perché la NATIVA non è sempre la stessa
        ### Alcune stazioni hanno la NATIVA a 5 min, altre a 10, altre a 15 min.
        
        dt = df.index.to_series().diff()
        # print(dt.value_counts())
        step_principale = int(dt.value_counts().index[0].total_seconds() / 60)
        
        ### Non è un modo pulitissimo ma è quello che dovrebbe andare bene il 99% dei casi,
        ### perché può succedere che una volta era a 10 min e poi è diventato a 5 min e così mi perdo l'informazione.
        df = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq=f'{step_principale}min'))
        
        df['30 min'] = (df['NATIVA'].rolling('30min').sum())
        df['1 h'] = (df['NATIVA'].rolling('1h').sum())
        df['3 h'] = (df['NATIVA'].rolling('3h').sum())
        df['6 h'] = (df['NATIVA'].rolling('6h').sum())
        df['12 h'] = (df['NATIVA'].rolling('12h').sum())
        df['24 h'] = (df['NATIVA'].rolling('24h').sum())

        if step_principale == 5:
            df = df.rename(columns={'NATIVA': '5 min'})
            df['10 min'] = (df['5 min'].rolling('10min').sum())
            df['15 min'] = (df['5 min'].rolling('15min').sum())
        elif step_principale == 10:
            df['5 min'] = np.nan
            df = df.rename(columns={'NATIVA': '10 min'})
            df['15 min'] = np.nan
        elif step_principale == 15:
            df['5 min'] = np.nan
            df['10 min'] = np.nan
            df = df.rename(columns={'NATIVA': '15 min'})
            
        df = df[['5 min', '10 min', '15 min', '30 min', '1 h', '3 h', '6 h', '12 h', '24 h']]
        
        df.to_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index=True, header=True, mode='w', na_rep=np.nan)

# %% Cumulata MAX in tot anni per ogni stazione

df_max_cum = pd.DataFrame()

for s in df_coord_meteo.index[0:10]:
    f_log_ciclo_for([['Calcolo massimi ', s, df_coord_meteo.index.tolist()]])
    
    df = pd.read_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index_col=0, parse_dates=True)
    df = df[df.index.year != anno_corrente]

    df_max = df.max().to_frame().T

    df_max.index = [s]
    df_max_cum = pd.concat([df_max_cum, df_max])

############

df_max_cum = df_max_cum[['5 min', '10 min', '15 min', '30 min', '1 h', '3 h', '6 h', '12 h', '24 h']]

fig, ax = plt.subplots(figsize=(8, 8))
im = ax.imshow(
    df_max_cum.values,
    aspect='auto',
    interpolation='nearest',
)

ax.set_xticks(range(len(df_max_cum.columns)), labels=df_max_cum.columns, rotation=45, ha="right", rotation_mode="anchor", fontsize=8)
ax.set_yticks(range(len(df_max_cum.index)), labels=df_max_cum.index, fontsize=8)

for i in range(len(df_max_cum.index)):
    for j in range(len(df_max_cum.columns)):
        ax.text(
            j, i,
            df_max_cum.values[i, j].round(2),
            ha="center",
            va="center",
            color="w",
            fontsize=9
        )

cbar = fig.colorbar(im, ax=ax)

plt.show()
plt.close()

# %% Cumulata MAX in tot stazioni per ogni anno

df_max_annuali_tot = pd.DataFrame(np.nan, index=pd.to_datetime(anni, format='%Y'), columns=['5 min', '10 min', '15 min', '30 min', '1 h', '3 h', '6 h', '12 h', '24 h'])

for s in df_coord_meteo.index:
    f_log_ciclo_for([['Calcolo massimi ', s, df_coord_meteo.index.tolist()]])
    
    df = pd.read_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index_col=0, parse_dates=True)
    df = df[df.index.year != anno_corrente]
    
    df_max_annuali = df.groupby(df.index.year).max()
    df_max_annuali.index = pd.to_datetime(df_max_annuali.index, format='%Y')
    df_max_annuali = df_max_annuali.reindex(df_max_annuali_tot.index)
    
    ### Sovrascrive solo se il valore nuovo è maggiore
    df_max_annuali_tot = pd.DataFrame(
        np.fmax(df_max_annuali_tot.values, df_max_annuali.values),
        index=df_max_annuali_tot.index,
        columns=df_max_annuali_tot.columns
    )
    
############

df_max_annuali_tot[['5 min', '30 min', '1 h', '3 h']].plot(logy=False)
plt.legend(ncol=3, fontsize=6)
plt.axhline(10, linestyle='--', linewidth=1, color='k')
plt.show()
plt.close()

fig, ax = plt.subplots(figsize=(8, 8))
im = ax.imshow(
    df_max_annuali_tot.values,
    aspect='auto',
    interpolation='nearest',
)

ax.set_xticks(range(len(df_max_annuali_tot.columns)), labels=df_max_annuali_tot.columns, rotation=45, ha="right", rotation_mode="anchor", fontsize=8)
ax.set_yticks(range(len(df_max_annuali_tot.index)), labels=anni, fontsize=8)

for i in range(len(df_max_annuali_tot.index)):
    for j in range(len(df_max_annuali_tot.columns)):
        ax.text(
            j, i,
            df_max_annuali_tot.values[i, j].round(2),
            ha="center",
            va="center",
            color="w",
            fontsize=9
        )

cbar = fig.colorbar(im, ax=ax)

plt.show()
plt.close()

### Ho abbandonato l'idea delle distribuzioni
"""
# %% Distribuzioni di cumulate
### Per ogni valore di cumulate, devo calcolare la distribuzione (dei valori > 0).
### Le distribuzioni saranno formate da tutti i valori di ogni stazione.

dict_cumulate = {x: {y: np.array([]) for y in ['5 min', '10 min', '15 min', '30 min', '1 h', '3 h', '6 h', '12 h', '24 h']} for x in anni}

for s in df_coord_meteo.index:
    f_log_ciclo_for([['Calcolo massimi ', s, df_coord_meteo.index.tolist()]])
    
    df = pd.read_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index_col=0, parse_dates=True)
    df = df[df.index.year != anno_corrente]
    
    df = df.dropna(axis=1, how='all')

    for cum in df.columns:
        df_cum = df[cum]
        df_cum = df_cum[df_cum > 0]
        
        for anno in anni:
            cum_anno = df_cum.loc[df_cum.index.year == anno].values
            
            dict_cumulate[anno][cum] = np.concatenate([dict_cumulate[anno][cum], cum_anno])
            
############

cumulata = '30 min'

for anno in dict_cumulate.keys():
    
    for cum in dict_cumulate[anno].keys():

        valori = dict_cumulate[anno][cum]
        
        if not cum == cumulata:
            continue
        
        try:
            print(f'''
                  {anno}
                  media: {np.round(np.mean(valori), 2)}
                  max: {np.round(np.max(valori), 2)}
                  q80: {np.round(np.quantile(valori, 0.8), 2)}
                  q90: {np.round(np.quantile(valori, 0.9), 2)}
                  q95: {np.round(np.quantile(valori, 0.95), 2)}
                  q98: {np.round(np.quantile(valori, 0.98), 2)}
                  q99: {np.round(np.quantile(valori, 0.99), 2)}
                  '''
                  )

            kde = gaussian_kde(valori)  # crea l’oggetto KDE
            x = np.linspace(valori.min(), valori.max(), 1000)  # punti su cui valutare
            pdf = kde(x)
            
            plt.plot(x, pdf, lw=1)
            plt.fill_between(x, pdf, alpha=0.3)
            plt.xlabel(f'{anno} - {cum}')
            
            plt.yscale('log')
            plt.ylim(1e-10, 10**1)
            
            plt.xlim(0, 100)
            
            plt.show()
            plt.close()

        except ValueError:
            continue
"""        

# %% Vedo come sono messi gli inizi dei record delle precipitazioni
#### per provare a selezionare un sottoinsieme di stazioni.

df_tot = pd.DataFrame()

for s in df_coord_meteo.index:
    f_log_ciclo_for([['Stazione ', s, df_coord_meteo.index.tolist()]])

    df = pd.read_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index_col=0, parse_dates=True)
    df = df[df.index.year != anno_corrente]
    
    df = df['24 h'].reindex(pd.date_range('2000-01-01', '2025-12-31', freq='1d'))
    df.name = s
    
    df_tot = pd.concat([df_tot, df], axis=1)

############

df_tot_plot = df_tot.loc[pd.date_range('2005-01-01', '2025-12-31', freq='1d')]
df_tot_plot.index = pd.to_datetime(df_tot_plot.index)

# df_tot_plot = df_tot_plot.dropna(axis=1, how='all')
df_tot_plot = df_tot_plot.dropna(axis=1, thresh=len(df) * 0.7) # keep columns che hanno almeno 50% di valori NON-NaN
print(df_tot_plot.shape)

fig, ax = plt.subplots(figsize=(10, 12))
ax.imshow(
    df_tot_plot.values,
    aspect='auto',
    interpolation='nearest',
    )

dates = df_tot_plot.index

# maschera: solo 1 gennaio
mask = (dates.month == 1) & (dates.day == 1)
yticks = np.where(mask)[0]
ylabels = dates[mask].strftime('%Y')

ax.set_yticks(yticks)
ax.set_yticklabels(ylabels)

ax.grid(
    axis='y',
    which='major',
    color='red',
    linestyle='-',
    linewidth=0.8
)

ax.tick_params(which='minor', left=False, bottom=False)

plt.show()
plt.close()

# %%
"""
Alla fine le stazioni che prendo (dal 2005) sono (da df_tot_plot di sopra e osservando il plot):

"""

stazioni_scelte = df_tot_plot.columns
anni_scelti = np.arange(2005, 2026)

df_max_annuali_tot = pd.DataFrame(np.nan, index=pd.to_datetime(anni, format='%Y'), columns=['5 min', '10 min', '15 min', '30 min', '1 h', '3 h', '6 h', '12 h', '24 h'])

for s in stazioni_scelte:
    f_log_ciclo_for([['Calcolo massimi ', s, stazioni_scelte]])
    
    df = pd.read_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index_col=0, parse_dates=True)
    df = df[df.index.year != anno_corrente]
    df = df[df.index.year >= anni_scelti[0]]

    df_max_annuali = df.groupby(df.index.year).max()
    df_max_annuali.index = pd.to_datetime(df_max_annuali.index, format='%Y')
    df_max_annuali = df_max_annuali.reindex(df_max_annuali_tot.index)
    
    ### Sovrascrive solo se il valore nuovo è maggiore
    df_max_annuali_tot = pd.DataFrame(
        np.fmax(df_max_annuali_tot.values, df_max_annuali.values),
        index=df_max_annuali_tot.index,
        columns=df_max_annuali_tot.columns
    )
    
############

df_max_annuali_tot[['5 min', '30 min', '1 h', '3 h']].plot(logy=False)
plt.legend(ncol=3, fontsize=6)
plt.axhline(10, linestyle='--', linewidth=1, color='k')
plt.show()
plt.close()

fig, ax = plt.subplots(figsize=(8, 8))
im = ax.imshow(
    df_max_annuali_tot.values,
    aspect='auto',
    interpolation='nearest',
)

ax.set_xticks(range(len(df_max_annuali_tot.columns)), labels=df_max_annuali_tot.columns, rotation=45, ha="right", rotation_mode="anchor", fontsize=8)
ax.set_yticks(range(len(df_max_annuali_tot.index)), labels=anni, fontsize=8)

for i in range(len(df_max_annuali_tot.index)):
    for j in range(len(df_max_annuali_tot.columns)):
        ax.text(
            j, i,
            df_max_annuali_tot.values[i, j].round(2),
            ha="center",
            va="center",
            color="w",
            fontsize=9
        )

cbar = fig.colorbar(im, ax=ax)

plt.show()
plt.close()

# %% TEMPERATURE

df_tot_temp = pd.DataFrame()

### Query meteo

for s in stazioni_scelte:
    f_log_ciclo_for([['Query meteo ', s, stazioni_scelte]])
    
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
    data_1d.code = '{s}' and
    extract(year from data_1d.dtrf) >= 2005
    
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
    
    df = df[['TMEAN']]
    df.columns = [s for x in df.columns]
    
    df_tot_temp = pd.concat([df_tot_temp, df], axis=1)
    
df_tot_temp.index = pd.to_datetime(df_tot_temp.index)
df_tot_temp = df_tot_temp.sort_index()
df_tot_temp = df_tot_temp[df_tot_temp.index.year != anno_corrente]

# %% Calcolo la temperatura media anno per anno e PLOT FINALE
df_temp_annuale = df_tot_temp.resample('Y').mean().mean(axis=1)
df_temp_annuale.index.name = ''

df_temp_annuale.index = df_temp_annuale.index.to_period('Y').to_timestamp(how='start')
df_max_annuale = df_max_annuali_tot[['5 min', '30 min', '1 h', '3 h']].loc[df_temp_annuale.index]
df_max_annuale.index = df_temp_annuale.index = anni_scelti

############

fig, ax1 = plt.subplots(figsize=(10,5))
ax2 = ax1.twinx()

### primo asse y
df_temp_annuale.plot(ax=ax1, kind='line', color='tab:red', lw=3)
ax1.set_ylim(10, 15)
ax1.set_ylabel('Temperatura [°C, linea rossa]', fontsize=10)
ax1.set_xticks(anni_scelti)
ax1.set_xticklabels(anni_scelti)
ax1.tick_params(axis='both', rotation=0, labelsize=9)
ax1.grid(axis='both', zorder=-10, lw=0.5, alpha=0.5)

### secondo asse y
df_max_annuale.plot(ax=ax2, kind='line', color=['tab:blue', 'tab:orange', 'tab:green', 'tab:purple'])
ax2.set_ylim(0, 400)
ax2.set_yticks([0, 80, 160, 240, 320, 400])
ax2.set_yticklabels([0, 80, 160, 240, 320, 400])

ax2.set_ylabel('Linee di intensità di precipitazione [mm/tempo]', fontsize=10)
ax2.tick_params(axis='y', rotation=0, labelsize=9)
ax2.legend(ncol=2, fontsize=10, loc='upper left')

ax1.margins(x=0)
ax2.margins(x=0)

plt.savefig('./corr_temp_pioggia.png', dpi=300, format='png', bbox_inches='tight')

plt.show()
plt.close()

# %% Provo a fare la stessa cosa sulla frequenza
# cioè per 5 min, 30 min, 1 h e 3 h trovo le distribuzioni e per ognuna di loro calcolo il 90esimo percentile.
# Per ogni anno vedo quante volte quel percentile è stato superato.

dict_cumulate = {x: {y: np.array([]) for y in ['5 min', '30 min', '1 h', '3 h']} for x in anni_scelti}
soglia_minima_pioggia = 1 # mm

for s in stazioni_scelte:
    f_log_ciclo_for([['Raccolgo le cumulate ', s, stazioni_scelte]])
    
    df = pd.read_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index_col=0, parse_dates=True)
    df = df[df.index.year != anno_corrente]
    
    for cum in dict_cumulate[anni_scelti[0]].keys():
        df_cum = df[cum]
        df_cum = df_cum[df_cum >= soglia_minima_pioggia]
        
        for anno in anni_scelti:
            cum_anno = df_cum.loc[df_cum.index.year == anno].values
            
            dict_cumulate[anno][cum] = np.concatenate([dict_cumulate[anno][cum], cum_anno])

# %% Calcolo i quantili e i superi
quantile = 0.95

dict_quantili = {x: None for x in ['5 min', '30 min', '1 h', '3 h']}
dict_concat = {x: np.array([]) for x in ['5 min', '30 min', '1 h', '3 h']}

for anno in anni_scelti:
    print(anno)
    
    for cum in dict_quantili.keys():
        dict_concat[cum] =  np.concatenate([dict_concat[cum], dict_cumulate[anno][cum]])
    
for cum in dict_quantili.keys():
    dict_quantili[cum] = np.quantile(dict_concat[cum], quantile)

###############

df_freq_cum = pd.DataFrame(0, index=anni_scelti, columns=['5 min', '30 min', '1 h', '3 h'])

for anno in anni_scelti:
    print(anno)
    
    for cum in df_freq_cum.columns:
        df_freq_cum.loc[anno, cum] = df_freq_cum.loc[anno, cum] + np.sum(dict_cumulate[anno][cum] > dict_quantili[cum])

# %% Plot finale sulle frequenze
df_temp_annuale = df_tot_temp.resample('Y').mean().mean(axis=1)
df_temp_annuale.index.name = ''
df_temp_annuale.index = anni_scelti

############

fig, ax1 = plt.subplots(figsize=(10,5))
ax2 = ax1.twinx()

### primo asse y
df_temp_annuale.plot(ax=ax1, kind='line', color='tab:red', lw=3)
ax1.set_ylim(10, 15)
ax1.set_ylabel('Temperatura [°C, linea rossa]', fontsize=10)
ax1.set_xticks(anni_scelti)
ax1.set_xticklabels(anni_scelti)
ax1.tick_params(axis='both', rotation=0, labelsize=9)
ax1.grid(axis='both', zorder=-10, lw=0.5, alpha=0.5)

### secondo asse y
df_freq_cum.plot(ax=ax2, kind='line', color=['tab:blue', 'tab:orange', 'tab:green', 'tab:purple'])
ax2.set_ylim(0, 80_000)
ax2.set_yticks(np.linspace(0, 80_000, 6))
ax2.set_yticklabels(np.linspace(0, 80_000, 6).astype(int))

ax2.set_ylabel('Linee di frequenza intensità di precipitazione [mm/tempo]', fontsize=8)
ax2.tick_params(axis='y', rotation=0, labelsize=9)
ax2.legend(ncol=2, fontsize=10, loc='upper left')

ax1.margins(x=0)
ax2.margins(x=0)

plt.savefig('./corr_temp_pioggia_frequenze.png', dpi=300, format='png', bbox_inches='tight')

plt.show()
plt.close()











print('\n\nDone.')
