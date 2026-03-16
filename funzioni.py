
import os
import cx_Oracle

def f_settaggio_db():
    dsnStr = cx_Oracle.makedsn('cfmi_db.regione.liguria.it', '1522', 'cfmi')
    connessione = cx_Oracle.connect(user='cmi', password='cmi', dsn=dsnStr)

    return connessione


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