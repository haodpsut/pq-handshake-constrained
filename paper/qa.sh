#!/usr/bin/env bash
# QA TRUOC KHI GUI RA NGOAI. In SO DON VI DA KIEM cho tung muc, khong chi in PASS.
# ⚠ Moi phep kiem doc tu tep THAT (log, PDF, JSON). Grep tren tep KHONG TON TAI tra ve
# rong chu khong tra ve 0, va da ba lan trong du an nay no tao ra mot "0 loi" gia.
set -u
cd "$(dirname "$0")"
FAIL=0
ok(){ printf "  ✅ %-46s %s\n" "$1" "$2"; }
no(){ printf "  ⛔ %-46s %s\n" "$1" "$2"; FAIL=$((FAIL+1)); }

echo "── dich lai tu dau ──"
rm -f main.aux main.bbl main.blg main.log main.out qa.log qa-all.log
# ⚠ Chi luot CUOI moi dung de dem. Luot dau chay TRUOC bibtex nen tham chieu chua ton tai
# la binh thuong; gom ca bon luot vao mot log thi bao dong gia 83 lan. Luat cua nha: siet
# cong thi phai do ti le bao dong gia.
for i in 1 2; do pdflatex -interaction=nonstopmode main.tex >> qa-all.log 2>&1; done
bibtex main >> qa-all.log 2>&1
pdflatex -interaction=nonstopmode main.tex >> qa-all.log 2>&1
pdflatex -interaction=nonstopmode main.tex > qa.log 2>&1
[ -s qa.log ] || { echo "  ⛔ KHONG CO LOG. Moi ket qua duoi day se la so 0 gia."; exit 2; }
[ -s main.pdf ] || { no "dich duoc" "main.pdf khong sinh ra"; exit 2; }
echo "  (log $(wc -l < qa.log) dong)"

echo "── 1. LaTeX ──"
E=$(grep -cE "^! " qa.log)||E=0; O=$(grep -c "Overfull" qa.log)||O=0
U=$(grep -cE "Citation .* undefined|Reference .* undefined|There were undefined" qa.log)||U=0
[ "$E" -eq 0 ] && ok "loi LaTeX" "0" || { no "loi LaTeX" "$E"; grep -E "^! " qa.log|sort -u|head -3|sed 's/^/       /'; }
[ "$O" -eq 0 ] && ok "tran cot (overfull)" "0" || { no "tran cot" "$O"; grep -oE "Overfull \\\\hbox \([0-9.]+pt" qa.log|sort -u|head -3|sed 's/^/       /'; }
[ "$U" -eq 0 ] && ok "tham chieu treo" "0" || no "tham chieu treo" "$U"

echo "── 2. Do dai va khuon ──"
N=$(pdfinfo main.pdf|awk '/^Pages/{print $2}')
W=$(pdftotext main.pdf - | wc -w | tr -d ' ')
[ "$N" -le 5 ] && ok "so trang (tran Networking Letters 5)" "$N" || no "so trang VUOT" "$N"
ok "so tu" "$W"

echo "── 3. Tham chieu ──"
NR=$(pdftotext main.pdf - | grep -cE '^\[[0-9]+\]')||NR=0
NB=$(grep -c '^@' refs.bib)||NB=0
ORP=$(python3 - <<'PY'
import re,glob,io
keys=set(re.findall(r"^@\w+\{([^,]+),", io.open("refs.bib",encoding='utf-8').read(), re.M))
used=set()
for f in glob.glob("*.tex"):
    for c in re.findall(r"\\cite\{([^}]*)\}", io.open(f,encoding='utf-8').read()):
        used |= {x.strip() for x in c.split(",")}
print(len(keys-used))
PY
)
[ "$NR" -ge 16 ] && ok "so tham chieu IN RA (letter nen >16)" "$NR" || no "tham chieu qua it" "$NR"
[ "$ORP" -eq 0 ] && ok "muc bib khong duoc trich" "0" || no "muc bib MO COI" "$ORP"

echo "── 4. Ngon ngu ──"
V=$(pdftotext main.pdf - | grep -cE '[àáâãèéêìíòóôõùúăđơưạảấầẩậắằặẹẻếềểệỉịọỏốồổộớờởợụủứừửựỳỹ]')||V=0
[ "$V" -eq 0 ] && ok "ky tu tieng Viet trong PDF" "0" || no "CON TIENG VIET" "$V dong"

echo "── 5. Khai dung AI (bat buoc neu repo ghi cong AI) ──"
AI=$(cd .. && git log --format='%B' | grep -ci 'claude\|anthropic')||AI=0
AK=$(pdftotext main.pdf - | grep -ci "acknowledg")||AK=0
if [ "$AI" -gt 0 ]; then
  [ "$AK" -gt 0 ] && ok "commit ghi cong AI / muc Acknowledgment" "$AI / co" \
                  || no "BAT NHAT: $AI commit ghi cong AI, bai KHONG khai" ""
else ok "repo khong ghi cong AI" "0"; fi
ART=$(pdftotext main.pdf - | grep -c "github.com")||ART=0
[ "$ART" -gt 0 ] && ok "link artifact trong bai" "co" || no "THIEU link artifact" ""

echo "── 6. Dong bo so lieu ──"
python3 check-no-typed-numbers.py > /tmp/qa1.txt 2>&1
grep -q "✅" /tmp/qa1.txt && ok "so go tay chua giai trinh" "$(grep -oE 'da kiem [0-9]+ tep, [0-9]+ con so' /tmp/qa1.txt)" \
  || { no "CO SO GO TAY" ""; sed 's/^/       /' /tmp/qa1.txt; }
python3 check-sync.py > /tmp/qa2.txt 2>&1
grep -q "DONG BO" /tmp/qa2.txt && ok "JSON <-> macro <-> PDF" "$(grep -oE 'kiem [0-9]+ gia tri' /tmp/qa2.txt | head -1)" \
  || { no "LECH SO LIEU" ""; sed 's/^/       /' /tmp/qa2.txt; }

echo "── 7. Muc bi bo lai / cau doi lap ──"
# ⚠ Cong nay CANH BAO chu khong chan: no khong doc duoc y, chi chi cho nguoi doc dung cho.
# Ly do co no: mot vong doc ngoai bi CHAN vi muc De doa khong duoc sua cung cac muc khac,
# va bai tu mau thuan o ba cho ma khong cong so nao thay.
python3 check-cross-section.py | sed 's/^/  /'

echo "── 7b. Hai nguon ket qua do CUNG dai luong co khop khong ──"
# ⛔ Lop loi rieng. Ba cong truoc deu hoi "so nay tu dau ra?" va MOI so deu tra loi duoc, nen
# ca ba deu xanh trong khi m3 in "23 manh xong" con m5 in "23 manh hong 20/20". Khong cong nao
# hoi "hai cau tra loi co GIONG NHAU khong?". Cong nay hoi dung cau do.
if ! python3 check-source-agreement.py | sed 's/^/  /'; then FAIL=$((FAIL+1)); fi

echo "── 8. Cover letter: mat tien phai khop than bai ──"
if [ -f cover-letter.tex ]; then
  pdflatex -interaction=nonstopmode cover-letter.tex >> qa-all.log 2>&1
  OUT=$(python3 check-cover-letter.py); RC=$?
  echo "$OUT" | sed 's/^/  /'
  [ "$RC" -eq 0 ] || FAIL=$((FAIL+1))
else
  ok "cover letter" "(chua co)"
fi

echo
[ "$FAIL" -eq 0 ] && echo "  ✅ QA DAT — san sang gui doc ngoai" || echo "  ⛔ QA HONG $FAIL cho"
exit "$FAIL"
