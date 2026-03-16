    
import os
import cx_Oracle

import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', FutureWarning)

import numpy as np
import pandas as pd

def f_settaggio_db():
    dsnStr = cx_Oracle.makedsn('cfmi_db.regione.liguria.it', '1522', 'cfmi')
    connessione = cx_Oracle.connect(user='cmi', password='cmi', dsn=dsnStr)

    return connessione

connessione = f_settaggio_db()

def f_log_ciclo_for(lista_di_liste):
    """Log per un ciclo for."""
    # lista_di_liste. Ogni lista contiene 3 elementi:
    # Il primo è la descrizione, il secondo è l'elemento di ogni ciclo, il terzo è la lista iterata.

    str_output = ''
    for n, i in enumerate(lista_di_liste, 1):
        assert len(i) == 3, 'Ci sono meno di 3 elementi. Modifica.'

        if not type(i[2]) == list:
            i[2] = list(i[2])

        sub_str = f'{i[0]}{i[1]} [{i[2].index(i[1]) + 1}/{len(i[2])}]'
        str_output = str_output + sub_str
        if not n == len(lista_di_liste):
            str_output = str_output + ' · '

    print(str_output)
    

def f_crea_cartella(percorso_cartella):
    """Crea una cartella, printa per conferma e ritorna il percorso passato."""
    os.makedirs(percorso_cartella, exist_ok=True)
    print(f'Creata cartella {percorso_cartella}')

    return percorso_cartella


lista_possibili_cartelle_lavoro = [
    '/media/daniele/Daniele2TB/test/climatologia',
    '/run/media/daniele.carnevale/Daniele2TB/test/climatologia',
]

cartella_lavoro = [x for x in lista_possibili_cartelle_lavoro if os.path.exists(x)][0]
os.chdir(cartella_lavoro)
del (lista_possibili_cartelle_lavoro)

# %%
df_stazioni_meteo_clima =  pd.read_csv(f'{cartella_lavoro}/df_stazioni_meteo-clima.csv')
df_stazioni_meteo_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] != 'GEPCA'] # Alcune hanno problemi. Le tolgo.
df_stazioni_meteo_clima = df_stazioni_meteo_clima[df_stazioni_meteo_clima['Code'] != 'PANES'] # Alcune hanno problemi. Le tolgo.

cartella_query = f_crea_cartella(f'{cartella_lavoro}/query_pioggia')

df_coord_meteo = pd.DataFrame(np.nan, columns=['name', 'lat', 'lon', 'elev'], index=df_stazioni_meteo_clima['Code']) # la pioggia non ha la climatologia

for s in df_coord_meteo.index:
    # if os.path.exists(f'{cartella_query}/{s}.csv'):
    #     continue
    f_log_ciclo_for([['Query meteo ', s, df_coord_meteo.index.tolist()]])

    query = f"""
    select
    anag.name,
    anag.lon/1e5 as lon,
    anag.lat/1e5 as lat,
    anag.elev as elev,
    to_char(data_1d.dtrf, 'YYYY-MM-DD HH24:MI:SS') as tempo,
    rainc/10 as rain_cum

    from
    anag,
    data_1d

    where
    anag.code = data_1d.code and
    anag.code='{s}'

    order by tempo
    
    """

    df = pd.read_sql(query, con=connessione)
    df = df.set_index('TEMPO')
    df.index = pd.to_datetime(df.index)
    df = df.reindex(pd.date_range('2003-01-01', df.index[-1], freq='1d')) # il 2003 è stato scelto da Rusca
    df = df.drop(['NAME', 'LON', 'LAT', 'ELEV'], axis=1)

    df.to_csv(f'{cartella_query}/{s}.csv', index=True, header=True, na_rep=np.nan, mode='w')

print('\n\nDone.')