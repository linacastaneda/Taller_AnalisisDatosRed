# Auditoría del laboratorio de congestión — C05 y C06

Esta revisión **no modifica los datos, el modelo ni las métricas originales**. Lee `resultados_ia/dataset_modelo.csv`, `predicciones_prueba.csv` y `metricas.json` y produce una interpretación temporal más clara.

## Ejecutar en Windows / VS Code

Desde la carpeta raíz `laboratorioCongestion`, descomprima la carpeta `revision_ia` junto a `resultados_ia` y ejecute:

```powershell
.\.venv\Scripts\python.exe revision_ia\revisar_resultados.py --entrada resultados_ia --salida revision_ia\salidas
```

Se necesitan `pandas`, `numpy`, `matplotlib` y `scikit-learn` (ya presentes en el entorno del proyecto).

## Interpretación

- El modelo de regresión predice los descartes de **k+1** a partir de variables medidas durante **k**.
- En las gráficas originales, la curva de predicción y la alerta se mostraban en el centro del intervalo **k+1**. Esto ayuda a comparar contra los descartes objetivo, pero puede sugerir equivocadamente que la alerta se emitió en ese instante futuro.
- En las gráficas revisadas, la predicción y ambas alertas están dibujadas en el **final de k**, que es el momento en que la información de k ya está disponible. Las líneas verticales rosadas señalan la frontera de inicio del siguiente intervalo que presenta descartes.
- Las tres alertas anticipadas de cuatro corresponden a la convención *alerta al final de k para detectar descartes en k+1*. No prueban una anticipación de varios segundos ni constituyen una validación operativa de tiempo real.
- La tasa observada desde el PCAP se satura alrededor de 10 Mbit/s debido a TBF: no equivale a la tasa ofrecida por `iperf3` cuando el emisor ofrece más de 10 Mbit/s.
- La tasa observada y el número de paquetes están altamente correlacionados (casi 1), por lo que los coeficientes individuales del modelo no deben interpretarse como efectos causales independientes.

## Resultados confirmados

- C05: 1 inicio previsto y 1 omitido.
- C06: 2 inicios previstos y 0 omitidos.
- Conjunto de prueba: MAE 156,82 paquetes/ventana, precisión 41,46 %, sensibilidad 98,91 %.
- Regla básica: precisión 70,31 %, sensibilidad 97,83 %, anticipación 2 de 4 inicios.
- La superior anticipación de eventos de la regresión viene con un alto coste en falsas alarmas.

## Archivos resultantes

- `salidas/C05_alineada.png`, `C06_alineada.png`: gráficas temporales con la emisión de alertas en final de k.
- `salidas/episodios_congestion.csv`: cuatro eventos de inicio y predicción previa.
- `salidas/comparacion_metricas.csv`: matrices y métricas por corrida y método.
- `salidas/auditoria.json`: resumen de verificaciones.

No borre `resultados_ia`: estos son archivos complementarios para la sustentación y el informe.
