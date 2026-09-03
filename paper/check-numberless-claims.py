"""LOP LOI 16 — TUYEN BO THUC NGHIEM KHONG CO CHU SO thi moi cong truy-xuat-xu deu MU.

⛔ CA SINH RA CONG NAY (bai P3 EDHOC, 03/09/2026). Muc Threats viet:

    "The failures are not an artefact of an impatient harness; given an allowance far beyond
     the probe timeout the client still abandons the handshake on its own retransmission
     schedule."

`grep -rl "allowance" measure/ results/` -> KHONG TEP NAO. Khong phep do nao trong kho tung
dung dong ho dai. Cau do CHUA TUNG CO NGUON, va no nam trong bai nhieu ngay.

Vi sao moi cong deu mu: toan bo he cong so bam vao CHU SO. check_number_provenance tim so go
tay; check_macro_vs_tables doi chieu so trong PDF voi JSON; check_source_agreement so so giua
hai nguon. CAU NAY KHONG CO CHU SO NAO, nen khong cong nao co gi de bam.

Te hon: day dung la cau CHONG DO PHAN BIEN NANG NHAT cua bai. No chan truoc cau hoi hien nhien
"co phai anh cat ngang khi no sap xong khong?". Cang la cau chiu luc thi cang phai co nguon.

⇒ LUAT: tuyen bo dang "chung toi da loai tru X" la tuyen bo THUC NGHIEM du trong cau khong co
   so nao. Phai khai vao SO TUYEN BO kem tep ket qua chong do no, y nhu mot con so.

CACH DUNG. Tao `paper/claims.txt`, moi dong: <cum tu khoa> => <duong dan tep ket qua>
Vi du:   not an artefact of an impatient harness => results/m6_boundary_mechanism.json
Cong quet van xuoi tim cac cum duoi day; cum nao bat duoc ma khong co dong khai thi BAO.

⚠ Day la CANH BAO co chu dinh, khong phai phan quyet: no khong doc duoc y. Nhung no bat nguoi
  viet phai TRA LOI cau hoi "cai nay do o dau", va do la toan bo muc dich.
"""

import io
import os
import re
import sys

# Cum tu bao hieu mot tuyen bo THUC NGHIEM ma thuong khong kem chu so nao.
PATTERNS = [
    r"not an artefact of", r"not an artifact of", r"is not explained by",
    r"cannot be explained by", r"rules? out", r"we verified", r"we confirmed",
    r"we checked", r"far beyond", r"still completes", r"still succeeds",
    r"remains? unchanged", r"is not due to", r"independent of the",
    r"no evidence (?:of|that)", r"we exclude",
]


def body(path):
    s = io.open(path, encoding="utf-8", errors="replace").read()
    if "\\begin{document}" in s:
        s = s.split("\\begin{document}", 1)[1]
    s = re.sub(r"^%.*$", "", s, flags=re.M)
    return re.sub(r"\s+", " ", s)


def sentence(text, m):
    a = text.rfind(".", 0, m.start()) + 1
    b = text.find(".", m.end())
    return text[a:(b + 1) if b > 0 else len(text)].strip()


def main(paper_dir="paper"):
    if not os.path.isdir(paper_dir):
        print("  (khong thay %s)" % paper_dir)
        return 0
    ledger_path = os.path.join(paper_dir, "claims.txt")
    ledger = {}
    if os.path.exists(ledger_path):
        for line in io.open(ledger_path, encoding="utf-8"):
            if "=>" in line and not line.strip().startswith("#"):
                k, v = line.split("=>", 1)
                ledger[k.strip().lower()] = v.strip()

    texs = [f for f in sorted(os.listdir(paper_dir)) if f.endswith(".tex")]
    hits, unbacked, seen = 0, [], set()
    for f in texs:
        t = body(os.path.join(paper_dir, f))
        for pat in PATTERNS:
            for m in re.finditer(pat, t, re.I):
                s = sentence(t, m)
                hits += 1
                # Co chu so trong chinh cau do? Neu co thi cong truy-xuat-xu da phu duoc.
                if re.search(r"\\num[A-Za-z]+|\d", s):
                    continue
                key = next((k for k in ledger if k in s.lower()), None)
                if key and os.path.exists(ledger[key]):
                    continue
                # mot cau co the khop NHIEU mau; bao mot lan thoi, khong thi con so bao dong
                # tu phong len va nguoi doc thoi tin no. Xem feedback-siet-cong-phai-do-bao-dong-gia
                if (f, s) in seen:
                    continue
                seen.add((f, s))
                unbacked.append((f, s[:150]))

    print("  quet %d tep · %d cum tuyen bo · so tuyen bo khai %d dong"
          % (len(texs), hits, len(ledger)))
    if not texs:
        print("  ⚠ KIEM 0 TEP. Day khong phai la sach.")
        return 1
    if unbacked:
        print("  ⚠ %d cau tuyen bo THUC NGHIEM khong co chu so VA khong khai nguon:"
              % len(unbacked))
        for f, s in unbacked:
            print("     %s: ...%s..." % (f, s))
        print("  => Moi cau: HOAC do va khai vao paper/claims.txt, HOAC xoa cau do.")
    else:
        print("  ✅ moi tuyen bo thuc nghiem deu co chu so hoac co dong khai nguon")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "paper"))
