"""
pdf_to_md.py  –  한국 교육문서 PDF → Markdown 변환기
=====================================================

사용법:
    # 단일 파일
    python pdf_to_md.py 파일.pdf

    # 폴더 전체 (하위 폴더 포함)
    python pdf_to_md.py 폴더경로/

    # 출력 폴더 지정
    python pdf_to_md.py 폴더경로/ --out 결과폴더/

    # 덮어쓰기 없이 (이미 md가 있으면 건너뜀)
    python pdf_to_md.py 폴더경로/ --skip-existing

설치:
    pip install pdfminer.six
"""

import os
import re
import sys
import argparse
from pathlib import Path
from pdfminer.high_level import extract_text
from pdfminer.pdfpage import PDFPage


# ── 구조 패턴 ────────────────────────────────────────────────────────────────

STRUCT_START = re.compile(
    r"^("
    r"제\d+[조장절항호]"
    r"|[①②③④⑤⑥⑦⑧⑨⑩]"
    r"|[Ⅰ-Ⅹ]\."
    r"|\d+\.\s"
    r"|부칙"
    r"|\[시행|\[법률|\[고시|\[훈령"
    r"|[가나다라마바사아자차카타파하]\.\s"
    r"|[○◦▪▸→•∙]"
    r")"
)
BULLET_RE   = re.compile(r"^[○◦•∙▪▸→]\s?")
PAGE_NO_RE  = re.compile(r"^-\s*\d+\s*-$")


# ── 줄 합치기 헬퍼 ───────────────────────────────────────────────────────────

def _is_continuation(prev: str, nxt: str) -> bool:
    """이전 줄이 문장 중간에서 끊겼고, 다음 줄이 그 이어쓰기인지 판단."""
    if not prev or not nxt:
        return False
    if STRUCT_START.match(nxt):
        return False
    if nxt.startswith(("[", "※", "(")):
        return False
    if any(prev.rstrip().endswith(c) for c in (".", ">", "]", ")", "다", "함", "임")):
        return False
    return True


def _join(a: str, b: str) -> str:
    """두 줄을 합칠 때 필요한 경우 공백 삽입."""
    a, b = a.rstrip(), b.lstrip()
    if a and b:
        l, f = a[-1], b[0]
        need_space = (
            ("가" <= l <= "힣" or l.isalnum() or l in "·ㆍ%)")
            and ("가" <= f <= "힣" or f.isalnum() or f in "·ㆍ<(")
        )
        if need_space:
            return a + " " + b
    return a + b


# ── 핵심 변환 로직 ───────────────────────────────────────────────────────────

def _get_page_count(pdf_path: str) -> int:
    with open(pdf_path, "rb") as f:
        return sum(1 for _ in PDFPage.get_pages(f))


def _extract_full_text(pdf_path: str, chunk: int = 90) -> str:
    """대용량 PDF를 청크 단위로 나눠 추출 (타임아웃 방지)."""
    total = _get_page_count(pdf_path)
    parts = []
    for start in range(0, total, chunk):
        pages = list(range(start, min(start + chunk, total)))
        parts.append(extract_text(pdf_path, page_numbers=pages))
    return "\n".join(parts)


def _merge_wrapped_lines(raw_lines: list[str]) -> list[str]:
    """PDF 단 나눔으로 잘린 줄 복원."""
    merged = []
    i = 0
    while i < len(raw_lines):
        s = raw_lines[i]
        if not s:
            merged.append("")
            i += 1
            continue
        cur = s
        j = i + 1
        while j < len(raw_lines):
            # 빈 줄 건너뜀
            while j < len(raw_lines) and not raw_lines[j]:
                j += 1
            if j >= len(raw_lines):
                break
            if _is_continuation(cur, raw_lines[j]):
                cur = _join(cur, raw_lines[j])
                j += 1
            else:
                break
        merged.append(cur)
        i = j if j > i + 1 else i + 1
    return merged


def _to_markdown(merged: list[str]) -> str:
    """합쳐진 줄을 Markdown으로 변환."""
    seen_titles: set[str] = set()
    md: list[str] = []
    prev_blank = False

    for line in merged:
        s = line.strip()

        # 빈 줄
        if not s:
            if not prev_blank:
                md.append("")
            prev_blank = True
            continue
        prev_blank = False

        # 제거 대상
        if PAGE_NO_RE.match(s) or re.match(r"^\d+$", s):
            continue
        if "법제처" in s and "국가법령정보센터" in s:
            continue

        # 법 제목 (중복 제거)
        if (
            re.match(r"^[가-힣\s·「」（）()\-]+법$", s)
            and len(s) < 40
            and not s.startswith("제")
        ):
            if s not in seen_titles:
                seen_titles.add(s)
                md.append(f"# {s}")
            continue

        # 구조 요소 → 헤딩
        if s.startswith(("[시행", "[법률", "[고시", "[훈령")):
            md.append(f"> {s}")
        elif re.match(r"^[Ⅰ-Ⅹ]\.\s", s):
            md.append(f"# {s}")
        elif re.match(r"^제\d+장\s", s):
            md.append(f"## {s}")
        elif re.match(r"^제\d+절\s", s):
            md.append(f"### {s}")
        elif re.match(r"^제\d+조", s):
            md.append(f"#### {s}")
        elif re.match(r"^\d+\.\s", s) and len(s.split()[0]) <= 3:
            md.append(f"## {s}")
        elif re.match(r"^[가나다라마바사아자차카타파하]\.\s", s):
            md.append(f"### {s}")
        elif re.match(r"^\(\d+\)\s", s):
            md.append(f"#### {s}")
        elif re.match(r"^부\s*칙", s):
            md.append(f"## {s}")
        # 목록
        elif re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩]", s):
            md.append(f"- {s}")
        elif BULLET_RE.match(s):
            md.append("- " + BULLET_RE.sub("", s))
        # 참고
        elif s.startswith("※"):
            md.append(f"> {s}")
        else:
            md.append(s)

    return "\n".join(md)


def convert(pdf_path: str) -> str:
    """PDF 파일 하나를 Markdown 문자열로 변환."""
    raw_text = re.sub(r"  +", " ", _extract_full_text(pdf_path))
    raw_lines = [l.strip() for l in raw_text.split("\n")]
    merged = _merge_wrapped_lines(raw_lines)
    return _to_markdown(merged)


# ── CLI ──────────────────────────────────────────────────────────────────────

def _find_pdfs(target: str) -> list[Path]:
    p = Path(target)
    if p.is_file() and p.suffix.lower() == ".pdf":
        return [p]
    if p.is_dir():
        return sorted(p.rglob("*.pdf"))
    print(f"[오류] 경로를 찾을 수 없습니다: {target}")
    return []


def main():
    parser = argparse.ArgumentParser(
        description="한국 교육문서 PDF → Markdown 변환기"
    )
    parser.add_argument("target", help="변환할 PDF 파일 또는 폴더")
    parser.add_argument(
        "--out", default=None,
        help="출력 폴더 (기본값: PDF와 같은 폴더)"
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="이미 .md 파일이 있으면 건너뜀"
    )
    args = parser.parse_args()

    pdfs = _find_pdfs(args.target)
    if not pdfs:
        sys.exit(1)

    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    ok = fail = skip = 0
    for pdf in pdfs:
        dest_dir = out_dir if out_dir else pdf.parent
        md_path = dest_dir / (pdf.stem + ".md")

        if args.skip_existing and md_path.exists():
            print(f"[건너뜀] {pdf.name}")
            skip += 1
            continue

        try:
            pages = _get_page_count(str(pdf))
            print(f"[변환] {pdf.name} ({pages}p) ...", end=" ", flush=True)
            md = convert(str(pdf))
            md_path.write_text(md, encoding="utf-8")
            print(f"{len(md):,}자 → {md_path.name}")
            ok += 1
        except Exception as e:
            print(f"\n[오류] {pdf.name}: {e}")
            fail += 1

    print(f"\n완료: {ok}개 변환, {skip}개 건너뜀, {fail}개 실패")


if __name__ == "__main__":
    main()
