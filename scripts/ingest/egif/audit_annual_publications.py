#!/usr/bin/env python3
"""OCR auxiliar para contrastar los anuarios EGIF históricos escaneados.

Los PDF 1968-1992 enlazados por MITECO son imágenes sin texto extraíble. Este
script no altera ni interpreta el dataset: localiza, mediante OCR, las páginas
que mencionan las tres provincias valencianas y conserva extractos, página y
checksum para revisión humana. Requiere ``pdftoppm`` y ``tesseract``; ambos se
pueden indicar explícitamente para usar binarios desempaquetados en /tmp.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


TERMS = ("alicante", "castellon", "castellón", "valencia", "valenciana")


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def ocr_pdf(pdf: Path, pdftoppm: str, tesseract: str, language: str, dpi: int, env: dict[str, str]) -> dict:
    year_match = re.search(r"(?:19)?(68|69|7\d|8\d|9[0-2])", pdf.name)
    year = int("19" + year_match.group(1)) if year_match else None
    matches = []
    with tempfile.TemporaryDirectory(prefix="egif-annual-ocr-") as directory:
        prefix = Path(directory) / "page"
        subprocess.run(
            [pdftoppm, "-jpeg", "-r", str(dpi), str(pdf), str(prefix)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        for page_number, image in enumerate(sorted(Path(directory).glob("page-*.jpg")), start=1):
            result = subprocess.run(
                [tesseract, str(image), "stdout", "-l", language, "--psm", "6"],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env,
            )
            text = result.stdout.decode("utf-8", errors="replace")
            lines = text.splitlines()
            selected = []
            for index, line in enumerate(lines):
                if any(term in line.casefold() for term in TERMS):
                    selected.extend(lines[max(0, index - 2):min(len(lines), index + 3)])
            if selected:
                matches.append({"page": page_number, "excerpt": "\n".join(dict.fromkeys(selected))})
    return {
        "year": year,
        "file": str(pdf),
        "size_bytes": pdf.stat().st_size,
        "sha256": checksum(pdf),
        "ocr_matches": matches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pdftoppm", default="pdftoppm")
    parser.add_argument("--tesseract", default="tesseract")
    parser.add_argument("--tessdata-prefix")
    parser.add_argument("--language", default="spa+eng")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    env = os.environ.copy()
    if args.tessdata_prefix:
        env["TESSDATA_PREFIX"] = args.tessdata_prefix
    pdfs = sorted(args.pdf_dir.glob("*.pdf"))
    if not pdfs:
        parser.error("No se encontraron PDF")
    def run(pdf: Path) -> dict:
        print(f"OCR {pdf.name}", flush=True)
        return ocr_pdf(pdf, args.pdftoppm, args.tesseract, args.language, args.dpi, env)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        publications = list(executor.map(run, pdfs))
    atomic_json(args.output, {
        "method": "OCR candidate extraction; every numeric comparison requires human review",
        "publication_count": len(publications),
        "publications": publications,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
