
'''
Studio di correlazione tra aumento delle temperature medie in Liguria e aumento dei fenomini intensi di precipitazione.
'''

import gc
import os
import pickle

import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', FutureWarning)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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
anno_corrente = pd.Timestamp.now().year

query = """
select
    code,
    name,
    elev,
    lat/1e5 as lat,
    lon/1e5 as lon,
    region
from
    anag
where
    region = 'LIGURIA'
order by
    code
"""

df = pd.read_sql(query, con=connessione)

df = df.where(df.notna(), np.nan).dropna()
df = df[~df['CODE'].str[0].str.isdigit()] # tolgo le stazioni che iniziano con un numero
df = df[~df['CODE'].str[-1].str.isdigit()] # tolgo le stazioni che finiscono con un numero
df = df[~df['CODE'].str.endswith('_')] # tolgo le stazioni che finiscono con _

df = df.set_index('CODE')
df = df.drop(columns=['REGION'])

df_stazioni = df.copy()
del (query, df)

# %%
# 1. Trovare le stazioni che hanno sia il termometro che il pluviometro

if not os.path.exists('./lista_stazioni_termopluvio.pkl'):

    lista_stazioni_termopluvio = []

    for s in df_stazioni.index:
        f_log_ciclo_for([['Query ', s, df_stazioni.index.tolist()]])
        
        s_temperatura = False
    
        query_termometri = f"""
        select
        to_char(data.dtrf, 'YYYY-MM-DD HH24:MI:SS') as tempo,
        data.tempm/10 as tempm
        
        from
        data
        
        join
        anag
        
        on
        data.code = anag.code
        
        where
        data.v_tempm < 'I' and
        data.code = '{s}' and
        extract(year from data.dtrf) = {anno_corrente}
        
        """
    
        df_termometri = pd.read_sql(query_termometri, con=connessione)
        
        if df_termometri.shape[0] != 0:
            s_temperatura = True
            
        ##########
        
        s_pioggia = False
        
        query_pluviometri = f"""
        select
        to_char(data.dtrf, 'YYYY-MM-DD HH24:MI:SS') as tempo,
        data.rainc/10 as rainc
        
        from
        data
        
        join
        anag
        
        on
        data.code = anag.code
        
        where
        data.v_rainc < 'I' and
        data.code = '{s}' and
        extract(year from data.dtrf) = {anno_corrente}
        
        """
    
        df_pluviometri = pd.read_sql(query_pluviometri, con=connessione)
        
        if df_pluviometri.shape[0] != 0:
            s_pioggia = True
            
        if s_temperatura and s_pioggia:
            print(f'* {s} è un termopluvio.')
            lista_stazioni_termopluvio.append(s)
        
    with open('./lista_stazioni_termopluvio.pkl', 'wb') as f:
        pickle.dump(lista_stazioni_termopluvio, f)
        
    del (query_termometri, query_pluviometri, s_pioggia, s_temperatura, df_pluviometri, df_termometri)
    
else:
    with open('./lista_stazioni_termopluvio.pkl', 'rb') as f:
        print('lista_stazioni_termopluvio trovato.')
        lista_stazioni_termopluvio = pickle.load(f)

lista_stazioni_termopluvio.remove('UNIGE') # registrava solo a 60 min, la levo.

del (f)
# %%
# 2. Delle stazioni termopluvio prendo solo quelle che hanno un buon dataset comune.
# Ho già controllato e va bene prendere dal 2005

# Questo pezzo impiega molto tempo e richiede molta memoria

df_termo = pd.DataFrame()
dict_pluvio = {x: None for x in lista_stazioni_termopluvio}

cartella_termo = f'{cartella_lavoro}/query_termo'
os.makedirs(cartella_termo, exist_ok=True)

cartella_pioggia_cumulate = f'{cartella_lavoro}/query_pioggia_cumulate'
os.makedirs(cartella_pioggia_cumulate, exist_ok=True)

for s in lista_stazioni_termopluvio:
    
    f_log_ciclo_for([['Termopluvio ', s, lista_stazioni_termopluvio]])
    if not os.path.exists(f'{cartella_termo}/{s}.csv'):
    
        query_termo = f'''
        
        select
        to_char(data_1d.dtrf, 'YYYY-MM-DD HH24:MI:SS') as tempo,
        data_1d.tempm/10 as tempm
        
        from
        data_1d
        
        join
        anag
        
        on
        data_1d.code = anag.code
        
        where
        data_1d.v_tempm < 'I' and
        data_1d.code = '{s}'and
        data_1d.dtrf < date '{anno_corrente}-01-01'
        
        order by dtrf
        '''
    
        df = pd.read_sql(query_termo, con=connessione)
        df = df.set_index('TEMPO')
        df.columns = [s]
        df.index.name = ''
        df.index = pd.to_datetime(df.index)
        df = df.reindex(pd.date_range('2005-01-01', f'{anno_corrente - 1}-12-31', freq='1d'))
        
        df.to_csv(f'{cartella_termo}/{s}.csv', index=True, header=True, mode='w', na_rep=np.nan)
    
    else:
        df = pd.read_csv(f'{cartella_termo}/{s}.csv', index_col=0, parse_dates=True)
        
    df_termo = pd.concat([df_termo, df], axis=1)
    
    ##########
    
    query_pluvio = f'''
    select
    to_char(data.dtrf, 'YYYY-MM-DD HH24:MI:SS') as tempo,
    data.rainc/10 as nativa
    
    from
    data
    
    join
    anag
    
    on
    data.code = anag.code
    
    where
    data.v_rainc < 'I' and
    data.code = '{s}'and
    data.dtrf < date '{anno_corrente}-01-01'
    
    order by dtrf
    '''

    if not os.path.exists(f'{cartella_pioggia_cumulate}/{s}.csv'):
        df = pd.read_sql(query_pluvio, con=connessione)
        df = df.set_index('TEMPO')
        df.index.name = ''
        df.index = pd.to_datetime(df.index)
        
        ### Qui devo fare attenzione perché la NATIVA non è sempre la stessa
        ### Alcune stazioni hanno la NATIVA a 5 min, altre a 10, altre a 15 min.
        
        dt = df.index.to_series().diff()
        print(dt.value_counts())
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
        
    else:
        # print(f'Trovata {cartella_pioggia_cumulate}/{s}.csv')
        df = pd.read_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index_col=0, parse_dates=True)
        
    df = df[df.index.year < anno_corrente]
    df = df[['30 min', '1 h', '3 h', '24 h']]
    
    dict_pluvio[s] = df
    
del (df, dt, query_pluvio, query_termo, s)
gc.collect()

##############
# %% Controllo grafico sui termometri e selezione

def f_plot_controllo_grafico(df, titolo):
    """
    Funzione per il plot delle serie per vedere quanti dati non NaN.

    Il dataframe deve avere:
        indici -> nomi stazioni
        colonne -> tempi che spannano negli anni

    """
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(df.values, aspect='auto', interpolation='nearest')
    
    # maschera: solo 1 gennaio
    mask = (df.index.month == 1) & (df.index.day == 1)
    yticks = np.where(mask)[0]
    ylabels = df.index[mask].strftime('%Y')
    
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels)
    ax.tick_params(which='minor', left=False, bottom=False)
    
    ax.grid(axis='y', which='major', color='red', linestyle='-', linewidth=0.8)
    
    ax.set_title(titolo)
    
    plt.show()
    plt.close()

f_plot_controllo_grafico(df_termo, 'df_termo')

perc = 10
f_plot_controllo_grafico(
    df_termo.dropna(axis=1, thresh=int((1 - perc/100) * len(df_termo))), # elimina le colonne con {perc}% di NaN
    f"df_termo {perc}% ({df_termo.dropna(axis=1, thresh=int((1 - perc/100) * len(df_termo))).shape[1]} stazioni)"
    )

stazioni_termo_perc = df_termo.dropna(axis=1, thresh=int((1 - perc/100) * len(df_termo))).columns.tolist()

# %% Seleziono un sottoinsieme abbastanza popolato di pluviometri

if not os.path.exists('./df_pluvio_perc.csv'):
    df_pluvio_perc = pd.DataFrame(np.nan, index=dict_pluvio.keys(), columns=[list(dict_pluvio['AGORR'].keys())])
    
    for s in lista_stazioni_termopluvio:
        f_log_ciclo_for([['Stazione ', s, lista_stazioni_termopluvio]])
    
        for cum in dict_pluvio['AGORR']:
            
            if cum == '30 min':
                df_cum = dict_pluvio[s][cum].loc[[x for x in dict_pluvio[s][cum].index if x.minute in [0, 30]]]
                df_cum = df_cum.reindex(pd.date_range('2005-01-01 00:00:00', f'{anno_corrente-1}-12-31 23:30:00', freq='30min'))
            
            elif cum == '1 h':
                df_cum = dict_pluvio[s][cum].loc[[x for x in dict_pluvio[s][cum].index if x.minute == 0]]
                df_cum = df_cum.reindex(pd.date_range('2005-01-01 00:00:00', f'{anno_corrente-1}-12-31 23:00:00', freq='1h'))
            
            elif cum == '3 h':
                df_cum = dict_pluvio[s][cum].loc[[x for x in dict_pluvio[s][cum].index if x.minute == 0 and x.hour % 3 == 0]]
                df_cum = df_cum.reindex(pd.date_range('2005-01-01 00:00:00', f'{anno_corrente-1}-12-31 21:00:00', freq='3h'))
            
            elif cum == '24 h':
                df_cum = dict_pluvio[s][cum].loc[[x for x in dict_pluvio[s][cum].index if x.minute == 0 and x.hour == 0]]
                df_cum = df_cum.reindex(pd.date_range('2005-01-01', f'{anno_corrente-1}-12-31', freq='24h'))
                
            len_prima = df_cum.shape[0]
            len_dopo = df_cum.dropna().shape[0]
            perc_NaN = ((len_prima - len_dopo) / len_prima) * 100
            df_pluvio_perc.loc[s, cum] = round(perc_NaN, 2)
            
    del (df_cum, len_prima, len_dopo, perc_NaN)
    
    df_pluvio_perc.to_csv('./df_pluvio_perc.csv', index=True, header=True, mode='w', na_rep=np.nan)

else:
    df_pluvio_perc = pd.read_csv('./df_pluvio_perc.csv', index_col=0)

# %%
### Seleziono le stazioni rispetto a quelle termo prese con perc={perc}%
df_pluvio_perc_selezione = df_pluvio_perc.loc[stazioni_termo_perc]

### Faccio una seconda pulizia perché ci sono pluvio che praticamente non hanno registrato niente e lo faccio su '1 h'
### prendendo solo le stazioni che hanno meno di {perc}% di NaN
perc = 10
df_pluvio_perc_selezione = df_pluvio_perc_selezione[df_pluvio_perc_selezione['1 h'] < perc].dropna(how='all')

stazioni_pluvio_perc = df_pluvio_perc_selezione.index.tolist()
### Da dict_pluvio prendo solo questo nuovo sottoinsieme
dict_pluvio = {x: dict_pluvio[x] for x in stazioni_pluvio_perc if x in dict_pluvio}

#%% Alla fine scelgo un subset fisso di stazioni che sarà uguale alle chiavi di dict_pluvio
stazioni_scelte = ['AGORR','ALASS','ALPIC','AVOBB','BELEN','BESTA','BONUO',
                   'BRGEL','BRUGN','BUSAL','CABAN','CAIRM','CALIZ','CASON',
                   'CASRB','CAVIP','CCADB','CCHER','CEMBR','CENES','CERPG',
                   'CFUNZ','CLARI','CMELO','CNAVA','CRETO','CRORE','DOLCE',
                   'ELLRA','FFRES','FIORI','GEBOL','GEPEG','GEPTX','GIACO',
                   'GOUTA','IMPER','INASV','ISBLL','ISOVE','LAVAG','LERCA',
                   'LEVAN','LGIAC','LOCOC','LVTSG','MARIN','MELEE','MGAZZ',
                   'MIGNA','MMAUR','MNINF','MOBRA','MROCC','MROSS','MSETT',
                   'MURIA','PDVRM','PIAMP','PORNA','PREMA','PTECO','PTURC',
                   'PVENE','RANZO','REPPI','RIGHI','ROCNE','ROSGL','ROVEG',
                   'SALBE','SANDA','SANTU','SASSL','SEGOD','SMVAR','SPZIA',
                   'SREMO','SRZAN','SSGIU','SSTAV','SZIGN','TAGLT','TAVRN',
                   'TESTI','TRIOR','TRRIG','VICOM','VREGI','XXMIG']
        
### Faccio un plot della '1 h' per vedere se veramente vanno bene anche dal lato pluvio

df_cum = pd.DataFrame()

for s in stazioni_scelte:
    f_log_ciclo_for([['Stazione ', s, stazioni_scelte]])
    
    df = pd.read_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index_col=0, parse_dates=True)['1 h']
    df = df.reindex(pd.date_range('2005-01-01 00:00:00', f'{anno_corrente}-01-01 00:00:00', freq='1h'))
    df.name = s
    df_cum = pd.concat([df_cum, df], axis=1)
    
df_cum.index = pd.to_datetime(df_cum.index)
del (df)

f_plot_controllo_grafico(df_cum, 'df_cum 1 h stazioni_scelte')
f_plot_controllo_grafico(df_termo[stazioni_scelte], 'df_termo stazioni_scelte')

# %% Ok, stazioni_scelte va benissimo. Posso procedere all'analisi        

temperature_medie_annuali = df_termo.resample('Y').mean().mean(axis=1)

### Sui pluviometri si può procedere in due modi:
#   1. Per ogni anno e per ogni cumulata, si trova il massimo dei massimi, cioè l'"estremo".
#   2. Per ogni anno e per ogni cumulata, si trova quante volte viene superata una soglia, ad esempio il 95° percentile della distribuzione completa osservata.

# %% Approccio 1. ai pluviometri

df_estremi_cum = pd.DataFrame(np.nan, index=pd.to_datetime(np.arange(2005, anno_corrente), format='%Y'), columns=['30 min', '1 h', '3 h', '24 h'])

for s in stazioni_scelte:
    f_log_ciclo_for([['Calcolo massimi ', s, stazioni_scelte]])
    
    df = pd.read_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index_col=0, parse_dates=True)
    df = df[df.index.year != anno_corrente]
    
    df_estremi_annuali = df.groupby(df.index.year).max()
    df_estremi_annuali.index = pd.to_datetime(df_estremi_annuali.index, format='%Y')
    df_estremi_annuali = df_estremi_annuali.reindex(df_estremi_cum.index)
    df_estremi_annuali = df_estremi_annuali[df_estremi_cum.columns]
    
    ### Sovrascrive solo se il valore nuovo è maggiore
    df_estremi_cum = pd.DataFrame(
        np.fmax(df_estremi_cum.values, df_estremi_annuali.values),
        index=df_estremi_cum.index,
        columns=df_estremi_cum.columns
    )
    
# Credo si possa cancellare
# df_estremi_cum = df_estremi_cum[df_estremi_cum.index.year != anno_corrente]

df_estremi_cum.plot(logy=True)
plt.grid()
plt.show()
plt.close()

# %% Approccio 2. ai pluviometri

soglia_di_pioggia = 1 # mm
dict_serie_cumulate = {x: np.array([]) for x in ['30 min', '1 h', '3 h', '24 h']}

for s in stazioni_scelte:
    f_log_ciclo_for([['Stazione ', s, stazioni_scelte]])
    
    df = pd.read_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index_col=0, parse_dates=True)[['30 min', '1 h', '3 h', '24 h']]
    df = df[df.index.year != anno_corrente]

    for cum in ['30 min', '1 h', '3 h', '24 h']:
        dict_serie_cumulate[cum] = np.concatenate([dict_serie_cumulate[cum], df[cum][df[cum] > soglia_di_pioggia].values])
    
# %% Calcolo i quantili
dict_quantili = {x: {y: None for y in [0.9, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]} for x in ['30 min', '1 h', '3 h', '24 h']}

for cum in dict_quantili.keys():
    for quantile in dict_quantili[cum].keys():
        dict_quantili[cum][quantile] = np.quantile(dict_serie_cumulate[cum], quantile)

# %% Calcolo i superi per uno specifico quantile
quantile = 0.95

df_superi_tot = pd.DataFrame(0, index=pd.to_datetime(np.arange(2005, anno_corrente), format='%Y'), columns=['30 min', '1 h', '3 h', '24 h'])

for s in stazioni_scelte:
    f_log_ciclo_for([['Calcolo massimi ', s, stazioni_scelte]])

    df_superi_s = pd.DataFrame(0, index=pd.to_datetime(np.arange(2005, anno_corrente), format='%Y'), columns=['30 min', '1 h', '3 h', '24 h'])
    
    df = pd.read_csv(f'{cartella_pioggia_cumulate}/{s}.csv', index_col=0, parse_dates=True)
    df = df[df.index.year != anno_corrente]
    
    for cum in ['30 min', '1 h', '3 h', '24 h']:
        gruppi_anni = list(df.resample('YS'))
        
        for anno, df_anno in gruppi_anni:
            try:
                df_superi_s.loc[f'{anno.year}-01-01', cum] = df_superi_s.loc[f'{anno.year}-01-01', cum] + np.sum(df_anno[cum] > dict_quantili[cum][quantile])
            except KeyError:
                # L'anno selezionato è precedente al 2005
                continue

    df_superi_tot = df_superi_tot + df_superi_s
    
    print(df_superi_tot, '\n\n')
    
df_superi_tot.plot(logy=True)
plt.title(f'quantile {quantile}')
plt.grid()
plt.show()
plt.close()

print('\n\nDone.')
