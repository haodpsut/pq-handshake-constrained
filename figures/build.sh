#!/usr/bin/env bash
# Sinh TOAN BO hien vat hinh anh cua bai. Mot lenh, khong buoc thu cong nao.
#
# ⚠ Hinh flow (fig0) dich bang pdflatex chu khong phai matplotlib, nen no de thanh
# hien vat MO COI: sua model.py xong ma quen dich lai thi hinh in ra so CU. Nen no
# nam trong CUNG script nay, va numbers.tex phai duoc sinh TRUOC khi dich.
set -eu
cd "$(dirname "$0")/.."

echo "── 1/2  hinh + bang + caption + numbers.tex (matplotlib) ──"
python3 figures/make_figures.py

echo
echo "── 2/2  hinh flow (pdflatex + TikZ) ──"
cd figures
pdflatex -interaction=nonstopmode -halt-on-error fig0-flow.tex > /tmp/pqhs-tex.log 2>&1 || {
  echo "  ⛔ pdflatex LOI:"; grep -E "^! " /tmp/pqhs-tex.log | head -4 | sed 's/^/    /'; exit 1; }
mv -f fig0-flow.pdf out/fig0-flow.pdf
command -v pdftoppm >/dev/null && pdftoppm -r 130 -png -singlefile out/fig0-flow.pdf out/fig0-flow
rm -f fig0-flow.aux fig0-flow.log
echo "  → fig0-flow.pdf / .png"
echo
echo "✅ xong. Hien vat trong figures/out/"
