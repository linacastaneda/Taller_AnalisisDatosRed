"""Gráficas del taller, con cada pronóstico en el intervalo k+1.
Uso: python graficas_entrega.py --entrada resultados_ia --salida resultados_ia/graficas_entrega
No reentrena ni usa datos de prueba para ajustar umbrales.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def graficar(df, salida):
    df = df.sort_values('t_inicio').reset_index(drop=True)
    origen = df['t_inicio'].iloc[0]
    inicio = df['t_inicio'].to_numpy()
    fin = df['t_fin'].to_numpy()
    centro_k = (inicio + fin) / 2 - origen
    # Cada predicción emitida al final de k corresponde a k+1:
    # el siguiente intervalo tiene centro en la media de sus dos bordes.
    centro_sig = (fin[:-1] + fin[1:]) / 2 - origen
    ultimo_sig = (fin[-1] + (fin[-1] + (fin[-1]-inicio[-1]))) / 2 - origen
    centro_k1 = np.r_[centro_sig, ultimo_sig]
    instante_alerta = fin - origen
    es_inicio = (df['descartes'].to_numpy() == 0) & (df['descartes_siguientes'].to_numpy() > 0)
    momentos_inicio = instante_alerta[es_inicio]

    fig, ax = plt.subplots(3, 1, figsize=(13, 8.7), sharex=True, constrained_layout=True)
    ax[0].plot(centro_k, df['tasa_mbps'], label='Tasa capturada (salida TBF)', color='#2563eb')
    ax[0].axhline(10, linestyle='--', color='gray', label='Límite TBF: 10 Mbit/s')
    ax[0].set_ylabel('Mbit/s'); ax[0].legend(loc='upper right')
    ax[1].plot(centro_k, df['descartes'], label='Descartes observados en k', color='#2563eb')
    ax[1].plot(centro_k1, df['prediccion_descartes'], label='Predicción ubicada en k+1', color='#e8792b', alpha=.9)
    ax[1].set_ylabel('Paquetes/ventana'); ax[1].legend(loc='upper right')
    ax[2].step(instante_alerta, df['alerta_modelo'], where='post', label='Alerta modelo (emitida al final de k)', color='#2563eb')
    ax[2].step(instante_alerta, df['alerta_regla_tasa'], where='post', label='Alerta regla de tasa', color='#e8792b', alpha=.8)
    for j, t in enumerate(momentos_inicio):
        for axis in ax:
            axis.axvline(t, linestyle='--', color='#d94688', alpha=.65, label='Inicio observado' if j == 0 else None)
    ax[2].set_ylim(-.1, 1.15); ax[2].set_yticks([0,1]); ax[2].set_ylabel('Alerta')
    ax[2].set_xlabel('Segundos desde el inicio de la corrida')
    ax[2].legend(loc='upper right')
    fig.suptitle(f"{df['corrida'].iloc[0]} — tasa, descartes, pronóstico k+1 y alertas")
    fig.savefig(salida, dpi=160)
    plt.close(fig)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--entrada', default='resultados_ia')
    p.add_argument('--salida', default='resultados_ia/graficas_entrega')
    a=p.parse_args()
    out=Path(a.salida); out.mkdir(parents=True, exist_ok=True)
    df=pd.read_csv(Path(a.entrada)/'predicciones_prueba.csv')
    for corrida in ('C05','C06'):
        parte=df[df['corrida']==corrida]
        if parte.empty: raise ValueError(f'No hay datos para {corrida}')
        fichero=out/f'{corrida}_pronostico_k1.png'
        graficar(parte, fichero)
        print('Generada:', fichero)

if __name__=='__main__': main()
