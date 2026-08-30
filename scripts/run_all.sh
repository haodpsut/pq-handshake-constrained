#!/usr/bin/env bash
# Chay toan bo goi. Moi buoc tu in cach doc ket qua cua chinh no.
set -u
cd "$(dirname "$0")/.."
mkdir -p results
FAIL=0

run() {
  echo; echo "════════════════════════════════════════════════════════════"
  echo "  $1"
  echo "════════════════════════════════════════════════════════════"
  python3 "$2" || { echo "  ⛔ BUOC NAY LOI: $2"; FAIL=$((FAIL+1)); }
}

echo "  moi truong:"
printf "    python   %s\n" "$(python3 --version 2>&1)"
printf "    aiocoap  %s\n" "$(python3 -c 'import importlib.metadata as m; print(m.version("aiocoap"))' 2>/dev/null || echo 'CHUA CAI')"
printf "    gnutls   %s\n" "$(gnutls-serv --version 2>/dev/null | head -1 || echo 'khong co')"
printf "    openssl  %s\n" "$(openssl version 2>/dev/null || echo 'khong co')"

run "A1 ti so kich thuoc"            analysis/a1_size_ratio.py
run "A2 che do truyen tai"           analysis/a2_transport_mode.py
run "A3 quet co khoi"                analysis/a3_blocksize_sweep.py
run "A4 tach theo tung ban tin"      analysis/a4_per_message.py
run "M1 DO: CoAP block-wise"         measure/m1_coap_blockwise.py
run "M2 DO: DTLS theo flight"        measure/m2_dtls_flights.py
run "M3 DO: nguong so manh  <-- QUYET DINH"  measure/m3_fragment_threshold.py

echo; echo "════════════════════════════════════════════════════════════"
if [ "$FAIL" -eq 0 ]; then echo "  ✅ tat ca $((7)) buoc chay xong"; else echo "  ⛔ $FAIL buoc LOI"; fi
echo "  ket qua JSON:"; ls -1 results/ 2>/dev/null | sed 's/^/    /'
exit "$FAIL"
