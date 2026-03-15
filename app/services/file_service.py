"""Extract text from uploaded files (PDF, DOCX, HWP/HWPX)."""
from __future__ import annotations

import io
import logging
import struct
import zipfile
import zlib
from xml.etree import ElementTree

import olefile
import pdfplumber
from docx import Document

logger = logging.getLogger(__name__)


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from file bytes based on filename extension."""
    name = filename.lower()
    try:
        if name.endswith(".pdf"):
            return _extract_pdf(file_bytes)
        elif name.endswith(".docx"):
            return _extract_docx(file_bytes)
        elif name.endswith(".hwpx"):
            return _extract_hwpx(file_bytes)
        elif name.endswith(".hwp"):
            return _extract_hwp(file_bytes)
        elif name.endswith(".txt"):
            return file_bytes.decode("utf-8", errors="replace")
        else:
            return f"[지원하지 않는 파일 형식: {filename}]"
    except Exception:
        logger.exception("Failed to extract text from %s", filename)
        return f"[파일 텍스트 추출 실패: {filename}]"


def _extract_pdf(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)


def _extract_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_hwpx(data: bytes) -> str:
    """HWPX is a ZIP-based format with XML content."""
    texts = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in sorted(zf.namelist()):
            if name.startswith("Contents/") and name.endswith(".xml"):
                try:
                    tree = ElementTree.parse(zf.open(name))
                    for elem in tree.iter():
                        if elem.text and elem.text.strip():
                            texts.append(elem.text.strip())
                except Exception:
                    continue
    return "\n".join(texts)


def _extract_hwp(data: bytes) -> str:
    """HWP (OLE compound document) text extraction."""
    ole = olefile.OleFileIO(io.BytesIO(data))
    try:
        if not ole.exists("BodyText/Section0"):
            return "[HWP 본문을 찾을 수 없습니다]"

        texts = []
        section_idx = 0
        while ole.exists(f"BodyText/Section{section_idx}"):
            raw = ole.openstream(f"BodyText/Section{section_idx}").read()
            text = _decompress_hwp_section(raw, ole)
            if text:
                texts.append(text)
            section_idx += 1

        return "\n\n".join(texts)
    finally:
        ole.close()


def _decompress_hwp_section(raw: bytes, ole: olefile.OleFileIO) -> str:
    """Decompress and extract text from HWP section stream."""
    # Check if compressed (FileHeader flags)
    is_compressed = False
    if ole.exists("FileHeader"):
        header = ole.openstream("FileHeader").read()
        if len(header) > 36:
            flags = struct.unpack_from("<I", header, 36)[0]
            is_compressed = bool(flags & 0x01)

    if is_compressed:
        try:
            raw = zlib.decompress(raw, -15)
        except zlib.error:
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                pass

    # Extract UTF-16LE text characters from binary stream
    chars = []
    i = 0
    while i < len(raw) - 1:
        code = struct.unpack_from("<H", raw, i)[0]
        i += 2
        if code == 0:
            continue
        # Control characters in HWP
        if code < 32:
            if code == 13 or code == 10:
                chars.append("\n")
            elif code == 9:
                chars.append("\t")
            # Skip other control codes and their extended data
            continue
        chars.append(chr(code))

    return "".join(chars).strip()
