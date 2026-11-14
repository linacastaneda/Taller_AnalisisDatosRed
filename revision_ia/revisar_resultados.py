"""Auditoría reproducible de las predicciones sin volver a entrenar el modelo.
Uso: python revisar_resultados.py --entrada resultados_ia --salida revision_resultados
"""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, mean_absolute_error, precision_score, recall_score

p=argparse.ArgumentParser()
p.add_argument('--entrada',default='resultados_ia')
p.add_argument('--salida',default='revision_resultados')
a=p.parse_args()
src=Path(a.entrada);dest=Path(a.salida);dest.mkdir(parents=True,exist_ok=True)
model=pd.read_csv(src/'dataset_modelo.csv')
pred=pd.read_csv(src/'predicciones_prueba.csv')
metrics=json.loads((src/'metricas.json').read_text(encoding='utf-8'))
required=['corrida','t_inicio','t_fin','tasa_mbps','num_paquetes','descartes','descartes_siguientes','prediccion_descartes','alerta_modelo','alerta_regla_tasa','objetivo_congestion']
assert all(c in pred.columns for c in required), 'Faltan columnas en predicciones_prueba.csv'
assert len(pred)==604 and len(model)==1811, 'Revisar las dimensiones de los archivos'
assert sorted(pred.corrida.unique())==['C05','C06']
assert pred.groupby('corrida').t_inicio.apply(lambda s:s.is_monotonic_increasing).all()
assert (pred.descartes_siguientes>=0).all()
assert ((pred.descartes_siguientes>=1).astype(int)==pred.objetivo_congestion).all()
rows=[];events=[]
for run,df in pred.groupby('corrida',sort=True):
    df=df.reset_index(drop=True)
    truth=df.objetivo_congestion.to_numpy().astype(int)
    for column,label in [('alerta_modelo','Regresión lineal'),('alerta_regla_tasa','Regla de tasa')]:
        alert=df[column].to_numpy().astype(int)
        vn,fp,fn,vp=confusion_matrix(truth,alert,labels=[0,1]).ravel()
        rows.append(dict(corrida=run,metodo=label,VN=int(vn),FP=int(fp),FN=int(fn),VP=int(vp),precision=precision_score(truth,alert,zero_division=0),sensibilidad=recall_score(truth,alert,zero_division=0)))
    onset=((df.descartes==0)&(df.descartes_siguientes>0))
    origin=df.t_inicio.iloc[0]
    for n,i in enumerate(np.flatnonzero(onset.to_numpy()),1):
        events.append(dict(corrida=run,episodio=n,segundo_inicio=float(df.t_fin.iloc[i]-origin),tasa_actual_mbps=float(df.tasa_mbps.iloc[i]),descartes_actuales=int(df.descartes.iloc[i]),descartes_siguientes=int(df.descartes_siguientes.iloc[i]),pronostico=float(df.prediccion_descartes.iloc[i]),alerta_modelo=int(df.alerta_modelo.iloc[i]),alerta_regla_tasa=int(df.alerta_regla_tasa.iloc[i])))
    # Dibujar la tasa y los descartes en su intervalo real, y alertas en el
    # instante en que se emiten (FIN de k), no en el centro de k+1.
    tx=(df.t_inicio.to_numpy()+df.t_fin.to_numpy())/2-origin
    te=df.t_fin.to_numpy()-origin
    fig,ax=plt.subplots(3,1,figsize=(13,8),sharex=True,constrained_layout=True)
    ax[0].plot(tx,df.tasa_mbps,color='#2563eb',label='Tasa capturada (después del límite TBF)')
    ax[0].axhline(10,color='#64748b',ls='--',alpha=.6,label='TBF: 10 Mbit/s');ax[0].set_ylabel('Mbit/s');ax[0].legend(loc='upper right')
    ax[1].plot(tx,df.descartes,color='#2563eb',label='Descartes reales en k')
    ax[1].plot(te,df.prediccion_descartes,color='#e8792b',alpha=.8,label='Predicción de k+1, emitida al FIN de k')
    ax[1].set_ylabel('Paquetes');ax[1].legend(loc='upper right')
    ax[2].step(te,df.alerta_modelo,where='post',color='#2563eb',label='Alerta modelo emitida al FIN de k')
    ax[2].step(te,df.alerta_regla_tasa,where='post',color='#db7836',alpha=.65,label='Alerta regla de tasa')
    for j in np.flatnonzero(onset.to_numpy()):
        for axis in ax: axis.axvline(te[j],color='#db2777',ls='--',alpha=.42)
    ax[2].set_yticks([0,1]);ax[2].set_ylabel('Alerta');ax[2].set_xlabel('Segundos desde el inicio de la corrida')
    ax[2].legend(loc='upper right');fig.suptitle(f'{run}: predicción para el siguiente intervalo (alerta emitida al final del actual)')
    fig.savefig(dest/f'{run}_alineada.png',dpi=150);plt.close(fig)
pd.DataFrame(rows).to_csv(dest/'comparacion_metricas.csv',index=False)
pd.DataFrame(events).to_csv(dest/'episodios_congestion.csv',index=False)
summary={'filas_dataset':len(model),'filas_prueba':len(pred),'correlacion_tasa_paquetes':float(model[['tasa_mbps','num_paquetes']].corr().iloc[0,1]),'tasa_maxima_mbps':float(model.tasa_mbps.max()),'MAE_prueba':float(mean_absolute_error(pred.descartes_siguientes,pred.prediccion_descartes)),'num_inicios_prueba':len(events),'inicios_modelo':int(sum(x['alerta_modelo'] for x in events)),'inicios_regla':int(sum(x['alerta_regla_tasa'] for x in events))}
(dest/'auditoria.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(summary,indent=2,ensure_ascii=False))
print('Archivos guardados en:',dest.resolve())
