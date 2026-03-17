import os, re, hashlib
from typing import List, Dict, Tuple
from .settings import settings

def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def _md_sections(text: str) -> List[Tuple[str, str]]:
    #     # Very simple section splitter by Markdown headings
    # parts = re.split(r"\n(?=#+\s)", text)
    # out = []
    # for p in parts:
    #     p = p.strip()
    #     if not p:
    #         continue
    #     lines = p.splitlines()
    #     title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else "Body"
    #     out.append((title, p))
    # return out or [("Body", text)]
    # 1. Get the Main Title of the document
    main_title = "Policy Document"
    m = re.search(r"^#\s+(.*)", text, re.M)
    if m:
        main_title = m.group(1).strip()

    # 2. Split the text into sections using the sub-headers (##)
    # This ensures "## Refund Windows" and its list stay together
    sections = re.split(r"\n(?=##\s)", text)
    out = []
    
    for p in sections:
        p = p.strip()
        if not p: continue
        
        # Determine the section name (e.g., Refund Windows, Conditions)
        lines = p.splitlines()
        if lines[0].startswith("##"):
            section_name = lines[0].lstrip("# ").strip()
        else:
            section_name = "Overview"
        
        # 3. CRITICAL FIX: Skip chunks that are just the main title
        # These provide no information and "clog" the retrieval
        if p == f"# {main_title}":
            continue
        
        out.append((section_name, p))
        
    return out

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    tokens = text.split()
    chunks = []
    i = 0
    while i < len(tokens):
        chunk = tokens[i:i+chunk_size]
        chunks.append(" ".join(chunk))
        if i + chunk_size >= len(tokens): break
        i += chunk_size - overlap
    return chunks

def load_documents(data_dir: str) -> List[Dict]:
    docs = []
    for fname in sorted(os.listdir(data_dir)):
        if not fname.lower().endswith((".md", ".txt")):
            continue
        path = os.path.join(data_dir, fname)
        text = _read_text_file(path)
        for section, body in _md_sections(text):
            docs.append({
                "title": fname,
                "section": section,
                "text": body
            })
    return docs

def doc_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
