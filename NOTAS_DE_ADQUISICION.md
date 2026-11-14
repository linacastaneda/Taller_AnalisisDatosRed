# Verificación de la adquisición (sin alterar los datos)

Seis corridas físicas ejecutadas en Fedora → Windows. En cada corrida se capturaron paquetes y se registró una cola TBF. Las tasas del calendario son **carga ofrecida** y no se utilizaron en el entrenamiento.

| Corrida | Paquetes capturados | Paquetes perdidos por tcpdump | Pausa mínima (s) | Pausa máxima (s) |
|---|---:|---:|---:|---:|
| C01 | 220,359 | 0 | 0.027 | 0.033 |
| C02 | 216,191 | 0 | 0.021 | 0.030 |
| C03 | 212,025 | 0 | 0.021 | 0.029 |
| C04 | 231,487 | 0 | 0.022 | 0.031 |
| C05 | 216,192 | 0 | 0.025 | 0.031 |
| C06 | 210,982 | 0 | 0.021 | 0.033 |

Los tiempos por fase y las pausas exactas están en `fases.csv`; las pausas de esta tabla se midieron restando fin de fase anterior a inicio de la siguiente. Los contadores del capturador (`tcpdump`) no deben confundirse con los descartes de la cola TBF.

## Configuración original y restauración

- En el respaldo de cada corrida, `cola_inicial.txt` contiene el estado de la **cola TBF recién reiniciada**, no la disciplina de cola previa a la primera configuración del laboratorio.
- No hay, en el respaldo actual, una evidencia suficiente para afirmar cuál era exactamente la disciplina de cola original antes de la primera prueba.
- El comando para eliminar la cola experimental es `sudo tc qdisc del dev enp7s0 root`. La ejecución efectiva de ese comando al finalizar debe documentarse solo si se dispone de evidencia o confirmación.

## Alcance y límites de las observaciones

- Cada corrida tuvo siete fases con dos períodos de sobrecarga, separados por recuperación.
- Los cambios se generaron con `iperf3` a distintas tasas; son cambios escalonados, no rampas continuas. Se deben describir como **ascensos por escalones y saltos bruscos**, sin afirmar que se probó una rampa continua.
- El requisito de entregar las trazas PCAP se atiende anexando el respaldo original `laboratorio_ia_datos.tar.gz`; los seis `.pcap` fueron excluidos de Git para evitar archivos pesados.
- No se realizó una nueva captura ni se modificaron los resultados experimentales al producir estas notas.
