"""Laboratorio IA: genera dataset y resultados a partir de PCAP exportado y tc.
Uso: python procesar_y_entrenar.py --datos laboratorio_ia_fisico --salida resultados_ia
"""
import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, confusion_matrix, precision_score, recall_score

FEATURES=['tasa_mbps','tasa_lag1','tasa_lag2','num_paquetes']

def parse_tc(path):
    raw=Path(path).read_text(encoding='utf-8').splitlines()
    samples=[]
    for i in range(0,len(raw)-1,2):
        try:
            t=float(raw[i]); qs=json.loads(raw[i+1])
            obj=next((x for x in qs if x.get('kind')=='tbf' and str(x.get('handle'))=='10:'), None)
            if obj is not None: samples.append((t,int(obj['drops'])))
        except (ValueError, TypeError, json.JSONDecodeError):
            continue
    df=pd.DataFrame(samples, columns=['timestamp','drops_acumulados'])
    if df.empty: raise ValueError('No hay muestras TBF')
    df=df.sort_values('timestamp').drop_duplicates('timestamp')
    return df.reset_index(drop=True)

def load_windows(folder):
    samples=parse_tc(folder/'cola.log')
    starts=samples.timestamp.to_numpy()[:-1]; ends=samples.timestamp.to_numpy()[1:]
    deltas=ends-starts; drop_diffs=np.diff(samples.drops_acumulados.to_numpy())
    # Only windows with regular approximately 1-second interval and nonnegative counters.
    valid=(deltas>=0.65)&(deltas<=1.65)&(drop_diffs>=0)
    csv=folder/'paquetes.csv'
    pk=pd.read_csv(csv, usecols=['frame.time_epoch','frame.len'], dtype={'frame.time_epoch':float,'frame.len':float})
    pk=pk.dropna().sort_values('frame.time_epoch')
    ts=pk['frame.time_epoch'].to_numpy(); lengths=pk['frame.len'].to_numpy()
    left=np.searchsorted(ts,starts,side='left')
    right=np.searchsorted(ts,ends,side='left')
    byte_cumsum=np.r_[0,np.cumsum(lengths,dtype=np.float64)]
    byte_count=byte_cumsum[right]-byte_cumsum[left]
    counts=right-left
    df=pd.DataFrame({'corrida':folder.name,'t_inicio':starts,'t_fin':ends,'duracion_s':deltas,
                     'num_paquetes':counts,'bytes_trama':byte_count,
                     'tasa_mbps':8*byte_count/(1e6*deltas),'descartes':drop_diffs,
                     'ventana_valida':valid})
    # Leave invalid gaps in place; no lag or target may bridge those gaps.
    df['tasa_lag1']=df['tasa_mbps'].shift(1)
    df['tasa_lag2']=df['tasa_mbps'].shift(2)
    df['descartes_siguientes']=df['descartes'].shift(-1)
    df['objetivo_congestion']=(df['descartes_siguientes']>=1).astype(int)
    keep=valid & pd.Series(valid).shift(1,fill_value=False).to_numpy() & pd.Series(valid).shift(2,fill_value=False).to_numpy() & pd.Series(valid).shift(-1,fill_value=False).to_numpy()
    df['apta_modelo']=keep
    return df,{'corrida':folder.name,'paquetes_csv':int(len(pk)),'muestras_tc':int(len(samples)),
               'ventanas_total':int(len(df)),'ventanas_validas':int(sum(valid)),
               'filas_modelo':int(sum(keep)),'descartes_en_ventanas':int(sum(drop_diffs[valid])),
               'ventanas_con_descartes':int(sum((drop_diffs>0)&valid)),
               'inicios_observados':int(sum((drop_diffs[:-1]==0)&(drop_diffs[1:]>0)&valid[:-1]&valid[1:]))}

def binary_metrics(y,p):
    tn,fp,fn,tp=confusion_matrix(y,p,labels=[0,1]).ravel()
    return {'VN':int(tn),'FP':int(fp),'FN':int(fn),'VP':int(tp),
            'precision':float(precision_score(y,p,zero_division=0)),
            'sensibilidad':float(recall_score(y,p,zero_division=0))}

def onset_metrics(df,p):
    # At end of window k, y[k] = drops[k+1], and onset if drops[k]==0 and next>0.
    onset=(df['descartes'].to_numpy()==0)&(df['descartes_siguientes'].to_numpy()>0)
    observed=int(onset.sum()); anticipated=int((onset&p).sum())
    return {'inicios_evaluables':observed,'inicios_anticipados':anticipated,
            'inicios_omitidos':observed-anticipated,
            'fraccion_anticipados':float(anticipated/observed) if observed else None}

def plot_run(df,out):
    fig,axs=plt.subplots(3,1,figsize=(12,8),sharex=True,constrained_layout=True)
    origin=df.t_inicio.iloc[0]
    t_real=((df.t_inicio+df.t_fin)/2-origin).to_numpy()
    t_next=((df.t_fin+df.t_fin.shift(-1).fillna(df.t_fin+df.duracion_s.median()))/2-origin).to_numpy()
    axs[0].plot(t_real,df.tasa_mbps,label='Tasa capturada');axs[0].set_ylabel('Mbit/s');axs[0].legend(loc='upper right')
    axs[1].plot(t_real,df.descartes,label='Descartes reales (k)',alpha=.8)
    axs[1].plot(t_next,df.prediccion_descartes,label='Predicción para k+1',alpha=.8)
    axs[1].set_ylabel('Paquetes/ventana');axs[1].legend(loc='upper right')
    axs[2].step(t_next,df.alerta_modelo,where='mid',label='Alerta emitida para k+1')
    onsets=(df.descartes.to_numpy()==0)&(df.descartes_siguientes.to_numpy()>0)
    for i in np.where(onsets)[0]: axs[2].axvline(float(df.t_fin.iloc[i]-origin),alpha=.12,color='red')
    axs[2].set_ylabel('Alerta');axs[2].set_xlabel('Segundos desde inicio de corrida');axs[2].set_yticks([0,1]);axs[2].legend(loc='upper right')
    fig.suptitle(f'{df.corrida.iloc[0]}: tasa, descartes, alertas (líneas verticales: inicios observados)')
    fig.savefig(out,dpi=145);plt.close(fig)

def main():
    a=argparse.ArgumentParser();a.add_argument('--datos',default='laboratorio_ia_fisico');a.add_argument('--salida',default='resultados_ia');args=a.parse_args()
    base=Path(args.datos);out=Path(args.salida);out.mkdir(exist_ok=True,parents=True)
    batches=[];stats=[]
    for i in range(1,7):
        folder=base/f'C{i:02d}'
        if not folder.exists(): raise FileNotFoundError(folder)
        df,report=load_windows(folder);batches.append(df);stats.append(report)
    pd.DataFrame(stats).to_csv(out/'resumen_corridas.csv',index=False)
    raw=pd.concat(batches,ignore_index=True);raw.to_csv(out/'ventanas_completas.csv',index=False)
    data=raw.loc[raw.apta_modelo].copy().reset_index(drop=True)
    data.to_csv(out/'dataset_modelo.csv',index=False)
    train=data[data.corrida.isin(['C01','C02','C03'])]
    val=data[data.corrida=='C04'];test=data[data.corrida.isin(['C05','C06'])]
    if min(len(train),len(val),len(test))==0: raise ValueError('Conjuntos insuficientes')
    model=LinearRegression().fit(train[FEATURES],train.descartes_siguientes)
    val_pred=np.maximum(0,model.predict(val[FEATURES])); test_pred=np.maximum(0,model.predict(test[FEATURES]))
    # professor default alert threshold >=1, fixed before testing
    model_threshold=1.0
    # baseline: select rate threshold on validation only, highest F1, break ties by less false positives
    candidates=np.unique(np.quantile(val.tasa_mbps,np.linspace(0,1,101)))
    yv=val.objetivo_congestion.to_numpy()
    best=None
    for thr in candidates:
        bp=(val.tasa_mbps.to_numpy()>thr).astype(int)
        m=binary_metrics(yv,bp); precision=m['precision'];recall=m['sensibilidad'];f1=2*precision*recall/(precision+recall) if precision+recall else 0
        score=(f1,-m['FP'])
        if best is None or score>best[0]:best=(score,float(thr))
    baseline_threshold=best[1]
    results={ 'modelo':'LinearRegression','variables':FEATURES,
              'coeficientes':{'intercepto':float(model.intercept_),**{k:float(v) for k,v in zip(FEATURES,model.coef_)}},
              'umbral_alerta_modelo':model_threshold,'umbral_regla_tasa_mbps':baseline_threshold,
              'tamanos':{'entrenamiento':len(train),'validacion':len(val),'prueba':len(test)},
              'validacion':{'MAE_paquetes':float(mean_absolute_error(val.descartes_siguientes,val_pred)),
                            **binary_metrics(yv,(val_pred>=model_threshold).astype(int))},
              'prueba':{} }
    test=test.copy();test['prediccion_descartes']=test_pred;test['alerta_modelo']=(test_pred>=model_threshold).astype(int)
    test['alerta_regla_tasa']=(test.tasa_mbps.to_numpy()>baseline_threshold).astype(int)
    for group,subset in [('C05',test[test.corrida=='C05']),('C06',test[test.corrida=='C06']),('total',test)]:
        truth=subset.objetivo_congestion.to_numpy();mp=subset.alerta_modelo.to_numpy();bp=subset.alerta_regla_tasa.to_numpy()
        results['prueba'][group]={'MAE_paquetes':float(mean_absolute_error(subset.descartes_siguientes,subset.prediccion_descartes)),
                                  'modelo':{**binary_metrics(truth,mp),**onset_metrics(subset,mp)},
                                  'regla_tasa':{**binary_metrics(truth,bp),**onset_metrics(subset,bp)}}
    test.to_csv(out/'predicciones_prueba.csv',index=False)
    for run in ('C05','C06'):plot_run(test[test.corrida==run],out/f'grafica_{run}.png')
    (out/'metricas.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    print(pd.DataFrame(stats).to_string(index=False));print(json.dumps(results,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
