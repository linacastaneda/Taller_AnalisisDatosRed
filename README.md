# Taller de análisis de datos en redes — predicción de congestión LAN

## Reproducción del experimento

Montaje realizado: computador A Fedora (192.168.50.10/24, interfaz enp7s0) — cable Ethernet — computador B Windows (192.168.50.20/24). En A se utilizó `tc` con TBF (`rate 10mbit burst 16kb limit 32kb`), `iperf3` como cliente UDP, `tcpdump` para la captura y `tshark` para exportar los campos `frame.time_epoch` y `frame.len`. En B se ejecutó el servidor `iperf3` en el puerto 5201.

El código **original utilizado** para adquirir las seis corridas está en `recolectar_fedora.sh`. Se ejecutó una vez por corrida (`01` a `06`). Cada corrida registró `captura.pcap`, `cola.log`, `fase_01.json`–`fase_07.json`, `fases.csv`, `paquetes.csv`, `tcpdump_estado.txt` y verificaciones. El archivo `fases.csv` contiene los horarios reales y las tasas **ofrecidas**; estas tasas no se usan como predictores. Las trazas originales `.pcap` se conservan en el respaldo independiente `laboratorio_ia_datos.tar.gz` por su tamaño.

## Procesamiento y evaluación

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe procesar_y_entrenar.py --datos laboratorio_ia_fisico --salida resultados_ia
.\.venv\Scripts\python.exe graficas_entrega.py --entrada resultados_ia --salida resultados_ia/graficas_entrega
```

`procesar_y_entrenar.py` agrupa paquetes en ventanas entre muestras consecutivas de `tc`, con duración real; calcula `tasa_mbps` a partir de bytes de trama y de la duración, y descartes mediante diferencias del contador `drops`. Usa `r[k]`, `r[k-1]`, `r[k-2]` y `n[k]` para predecir `drops[k+1]`. C01–C03 entrenan `LinearRegression`; C04 valida; C05–C06 son prueba reservada. Las predicciones negativas se llevan a cero y se usa alerta de un paquete o más. La regla de tasa se ajusta solo con validación.

Las **gráficas de entrega** de C05 y C06 generadas por `graficas_entrega.py` ubican cada pronóstico en el centro de la ventana futura `k+1`, las alertas al **final de k**, y marcan con líneas verticales los inicios observados. Esto separa el tiempo al que corresponde la predicción del tiempo en el que se emitió la alerta.

## Resultados de prueba verificados (C05–C06)

| Métrica | Regresión lineal | Regla de tasa |
|---|---:|---:|
| Precisión | 41,46 % | 70,31 % |
| Sensibilidad | 98,91 % | 97,83 % |
| Inicios anticipados | 3 de 4 | 2 de 4 |

MAE de regresión: 156,82 paquetes/ventana. Estos resultados no demuestran superioridad general de la regresión: anticipa más inicios, pero presenta más falsas alarmas.

## Archivos de entrega

- `laboratorio_ia_fisico/C01`–`C06`: `cola.log`, JSON de iperf3, CSV de paquetes/fases y controles.
- `resultados_ia/ventanas_completas.csv`: ventanas y descartes observados.
- `resultados_ia/dataset_modelo.csv`: 1.811 filas de modelo.
- `resultados_ia/predicciones_prueba.csv` y `metricas.json`: evaluación.
- `resultados_ia/graficas_entrega/`: gráficas con alineación temporal del pronóstico.
- `recolectar_fedora.sh`, `procesar_y_entrenar.py`, `graficas_entrega.py`: código reproducible.
- **Entregar por separado** `laboratorio_ia_datos.tar.gz` (incluye los seis PCAP) y conservar su copia original.

Para detalles comprobados sobre las pausas y las limitaciones de la evidencia, consultar `NOTAS_DE_ADQUISICION.md`. El informe breve de discusión requerido por la guía se prepara por separado.
