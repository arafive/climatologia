
import os

import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', FutureWarning)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.path import Path
from matplotlib.colors import ListedColormap
from shapely.geometry import Polygon, MultiPolygon

import cartopy.crs as ccrs
from scipy.interpolate import griddata
from cartopy.io.shapereader import Reader

from pykrige.ok import OrdinaryKriging
from pykrige.uk import UniversalKriging

plt.rc('font', weight='normal', size=6)

lista_possibili_cartelle_lavoro = [
    '/media/daniele/Daniele2TB/test/mappe_anomalia_termica',
    '/run/media/daniele.carnevale/Daniele2TB/test/mappe_anomalia_termica',
]

cartella_lavoro = [x for x in lista_possibili_cartelle_lavoro if os.path.exists(x)][0]
os.chdir(cartella_lavoro)
del (lista_possibili_cartelle_lavoro)

regioni = Reader('./../shapefile/gadm41_ITA_shp/gadm41_ITA_1.shp')

for r in regioni.records():
    if r.attributes['NAME_1'] == 'Liguria':
        print(r.attributes)

cmap = ListedColormap([
    '#08306b', '#08519c', '#2171b5', '#4292c6',
    '#6baed6', '#9ecae1', '#c6dbef', '#deebf7',
    '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a',
    '#ef3b2c', '#cb181d', '#a50f15', '#67000d',
])

# %%

# TODO --> Cold Spells

print('\n\nDone.')