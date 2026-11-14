# Laboratorio de IA — congestión LAN

## Archivos entregados

- `resultados_ia/dataset_modelo.csv`: 1.811 ejemplos utilizables por el modelo; cada fila predice los descartes en la ventana siguiente.
- `resultados_ia/ventanas_completas.csv`: todas las ventanas, antes de retirar extremos sin rezagos y etiquetas.
- `resultados_ia/resumen_corridas.csv`: resumen y controles por corrida.
- `resultados_ia/predicciones_prueba.csv`: predicciones y alertas para C05 y C06.
- `resultados_ia/metricas.json`: MAE, matriz de confusión, precisión, sensibilidad e inicios anticipados.
- `resultados_ia/grafica_C05.png`, `grafica_C06.png`: paneles temporales.
- `procesar_y_entrenar.py`: código reproducible. No utiliza las tasas programadas de iperf3 como predictores.

## Uso en Windows + VS Code

1. Instala Python 3.11 o posterior y VS Code con la extensión Python.
2. Extrae el respaldo original `laboratorio_ia_datos.tar.gz` en la carpeta del proyecto; debe aparecer `laboratorio_ia_fisico/C01`, ..., `C06`.
3. Copia `procesar_y_entrenar.py` en la misma carpeta del proyecto.
4. Abre la terminal de VS Code en dicha carpeta y ejecuta:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe procesar_y_entrenar.py --datos laboratorio_ia_fisico --salida resultados_ia
```

Si Windows bloquea la activación de scripts, **no es necesario activarlos**; los comandos utilizan Python del entorno directamente.

## Método

- Ventanas `[t[k-1],t[k])` con marcas de `tc`, duración real `delta`.
- Tasa: `8 * suma(frame.len)/(1e6 * delta)` Mbit/s.
- Descartes por ventana: diferencia de contador acumulado de TBF.
- Predictores: tasa de k, k−1, k−2, número de paquetes de k.
- Objetivo: descartes en k+1.
- Se descartan ventanas con intervalos anómalos, reinicio de contador, sin 2 rezagos o sin objetivo siguiente.
- Entrenamiento C01–C03, validación C04, prueba C05–C06. Reglas fijas antes de prueba.
- La regresión aplica máximo(0,predicción), alerta cuando predicción >= 1.
- La regla sencilla de comparación usa un umbral de tasa ajustado exclusivamente con C04.

## Interpretación inicial

En la prueba C05–C06 el modelo consigue sensibilidad alta, pero presenta numerosas falsas alarmas. La regla simple basada en tasa tiene una precisión mayor. El modelo anticipó 3/4 inicios evaluables, mientras la regla simple anticipó 2/4. Se debe explicar la dificultad de predecir saltos bruscos de carga sin señales previas y que la tasa observada puede quedar limitada por TBF.

Los 1,3 millones de paquetes no equivalen a 1,3 millones de filas de entrenamiento. Se obtuvieron 1.811 filas temporales útiles.

*Conserva el respaldo original intacto y explica en el informe los límites de observar la salida de la interfaz y las diferencias entre descartes de TBF y pérdidas del capturador.*
