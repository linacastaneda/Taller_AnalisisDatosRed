#!/usr/bin/env bash
# Laboratorio IA: adquisicion de seis corridas fisicas Fedora -> Windows.
set -Eeuo pipefail
IFACE="${IFACE:-enp7s0}"
SRC="${SRC:-192.168.50.10}"
DST="${DST:-192.168.50.20}"
ROOT="${ROOT:-$HOME/laboratorio_ia_fisico}"
mkdir -p "$ROOT"
RUN="${1:-}"
if [[ ! "$RUN" =~ ^0[1-6]$ ]]; then
  echo "Uso: $0 01   (o 02, 03, 04, 05, 06)" >&2
  exit 2
fi
for cmd in iperf3 tc tcpdump tshark python3 ip; do
  command -v "$cmd" >/dev/null || { echo "Falta: $cmd" >&2; exit 1; }
done
if ! ip -4 addr show dev "$IFACE" | grep -q "${SRC}/"; then
  echo "La interfaz $IFACE no tiene $SRC. Revisa ip -br addr" >&2; exit 1
fi
if ! ip route get "$DST" | grep -q "dev $IFACE"; then
  echo "La ruta a $DST NO sale por $IFACE" >&2; ip route get "$DST"; exit 1
fi
DIR="$ROOT/C$RUN"
if [[ -e "$DIR" ]]; then
  echo "Ya existe $DIR. No sobrescribo datos. Renombra o mueve esa carpeta antes de repetir." >&2
  exit 1
fi
mkdir -p "$DIR"
CAP_PID=""; LOG_PID=""; ACTIVE=0
cleanup() {
  if [[ -n "$CAP_PID" ]]; then kill -INT "$CAP_PID" 2>/dev/null || true; wait "$CAP_PID" 2>/dev/null || true; fi
  if [[ -n "$LOG_PID" ]]; then kill -TERM "$LOG_PID" 2>/dev/null || true; wait "$LOG_PID" 2>/dev/null || true; fi
}
trap 'echo "Interrumpido. Cerrando registros..."; cleanup' INT TERM
trap 'if (( ACTIVE )); then cleanup; fi' EXIT
# Perfiles: 7 fases; dos o mas sobrecargas separadas por recuperacion.
# tasa Mbit/s : duracion segundos (300 s de trafico por corrida)
case "$RUN" in
  01) phases=("4:40" "8:40" "14:45" "5:45" "9:40" "16:45" "4:45");;
  02) phases=("5:40" "16:45" "4:45" "8:40" "15:45" "5:45" "7:40");;
  03) phases=("3:40" "7:40" "12:45" "4:45" "9:40" "17:45" "5:45");;
  04) phases=("6:40" "10:40" "15:45" "4:45" "8:40" "14:45" "5:45");;
  05) phases=("4:40" "17:45" "5:45" "9:40" "13:45" "4:45" "7:40");;
  06) phases=("5:40" "9:40" "16:45" "3:45" "7:40" "18:45" "4:45");;
esac
printf 'fase,t_inicio_unix,t_fin_unix,tasa_ofrecida_mbps,duracion_programada_s,archivo_iperf\n' > "$DIR/fases.csv"
printf 'corrida=C%s\ninterfaz=%s\nemisor=%s\nreceptor=%s\n' "$RUN" "$IFACE" "$SRC" "$DST" > "$DIR/configuracion.txt"

echo "Validando servidor iperf3 de Windows $DST:5201..."
if ! timeout 8 iperf3 -c "$DST" -B "$SRC" -t 2 > "$DIR/conectividad.txt" 2>&1; then
  cat "$DIR/conectividad.txt"; echo "No hay servidor iperf3 accesible. Sin iniciar la corrida." >&2
  exit 1
fi

echo "Reiniciando contador TBF (solo interfaz experimental $IFACE)..."
sudo -v
sudo tc qdisc replace dev "$IFACE" root handle 10: tbf rate 10mbit burst 16kb limit 32kb
tc -s qdisc show dev "$IFACE" > "$DIR/cola_inicial.txt"

# tcpdump con filtro de paquetes UDP para el flujo objetivo
sudo tcpdump -i "$IFACE" -nn -s 96 -B 4096 -U -w "$DIR/captura.pcap" \
 "src host $SRC and dst host $DST and udp dst port 5201" \
 > "$DIR/tcpdump_salida.txt" 2> "$DIR/tcpdump_estado.txt" &
CAP_PID=$!
# Muestras acumuladas con marca de tiempo Unix y JSON; guardadas juntas.
(
 while true; do
   date +%s.%N
   tc -j -s qdisc show dev "$IFACE"
   sleep 1
 done
) > "$DIR/cola.log" 2> "$DIR/cola_errores.txt" &
LOG_PID=$!
ACTIVE=1
sleep 3
if ! kill -0 "$CAP_PID" 2>/dev/null; then
  echo "tcpdump terminó antes de recibir tráfico:"; cat "$DIR/tcpdump_estado.txt"; exit 1
fi
printf 'inicio_trafico_unix=%s\n' "$(date +%s.%N)" >> "$DIR/configuracion.txt"
for i in "${!phases[@]}"; do
  phase="$(printf '%02d' "$((i+1))")"
  rate="${phases[$i]%:*}"
  seconds="${phases[$i]#*:}"
  file="fase_${phase}.json"
  echo "C$RUN fase $phase: $rate Mbit/s durante ${seconds}s"
  t0="$(date +%s.%N)"
  if ! iperf3 -c "$DST" -B "$SRC" -u -b "${rate}M" -l 1200 -t "$seconds" -i 1 --get-server-output -J > "$DIR/$file"; then
    echo "Fallo de iperf3 en C$RUN fase $phase. Conservando archivos para diagnóstico." >&2; exit 1
  fi
  t1="$(date +%s.%N)"
  printf '%s,%s,%s,%s,%s,%s\n' "$phase" "$t0" "$t1" "$rate" "$seconds" "$file" >> "$DIR/fases.csv"
  # Verificar que iperf3 devolvió un objeto JSON válido sin error.
  python3 - "$DIR/$file" <<'PY'
import json,sys
with open(sys.argv[1],encoding='utf-8') as f: data=json.load(f)
if data.get('error'): raise SystemExit('iperf3 JSON error: '+str(data['error']))
PY
done
printf 'fin_trafico_unix=%s\n' "$(date +%s.%N)" >> "$DIR/configuracion.txt"
sleep 4
cleanup
CAP_PID=""; LOG_PID=""; ACTIVE=0
trap - EXIT INT TERM

echo "Validando PCAP..."
if ! command -v capinfos >/dev/null; then echo 'Falta capinfos (wireshark-cli).'; exit 1; fi
if ! capinfos "$DIR/captura.pcap" > "$DIR/capinfos.txt" 2> "$DIR/capinfos_error.txt"; then
  cat "$DIR/capinfos_error.txt"; echo "PCAP inválido/truncado. NO usar esta corrida." >&2; exit 1
fi
# Confirmar que el flujo contiene paquetes y no solo un PCAP vacío.
read -r NPKTS < <(tshark -r "$DIR/captura.pcap" -T fields -e frame.number | wc -l)
if (( NPKTS < 100 )); then echo "Solo $NPKTS paquetes; captura insuficiente." >&2; exit 1; fi
# Los valores por paquete se exportan sin necesidad de pandas.
tshark -r "$DIR/captura.pcap" -T fields -E header=y -E separator=, \
 -e frame.time_epoch -e frame.len > "$DIR/paquetes.csv"
# Para el modelo no se incluye la tasa OFRECIDA del calendario como predictor.
python3 - "$DIR/cola.log" <<'PY'
import sys,json
p=sys.argv[1]
lines=[s.strip() for s in open(p,encoding='utf-8') if s.strip()]
if len(lines)<10 or len(lines)%2: raise SystemExit('Log de cola incompleto: revisa '+p)
last=None; increments=[]
for i in range(0,len(lines),2):
    ts=float(lines[i]); items=json.loads(lines[i+1]); q=next((x for x in items if x.get('kind')=='tbf' and str(x.get('handle','')).startswith('10:')),None)
    if q is None: raise SystemExit('Falta la cola TBF 10:')
    drops=q.get('drops',q.get('dropped'))
    if drops is None: raise SystemExit('No aparece drops en tc JSON')
    if last is not None: increments.append(int(drops)-last)
    last=int(drops)
print('Muestras de cola:',len(lines)//2,'; descartes entre muestras:',sum(increments))
if any(x<0 for x in increments): raise SystemExit('Contador de descartes se reinició inesperadamente')
if sum(increments)==0: raise SystemExit('No hubo descartes: revisar perfiles/captura')
PY
printf '\nCORRIDA C%s VALIDADA: %s paquetes; carpeta %s\n' "$RUN" "$NPKTS" "$DIR"
echo 'Conserva captura.pcap, cola.log, paquetes.csv, fases.csv y los JSON.'
