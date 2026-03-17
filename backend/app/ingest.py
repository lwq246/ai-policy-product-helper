import os, re, hashlib
from typing import List, Dict, Tuple
from .settings import settings

def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def _md_sections(text: str) -> List[Tuple[str, str, str]]:
    # Split the document by sub-headers (##)
    sections = re.split(r"\n(?=#+\s)", text)
    out = []
    
    for p in sections:
        p = p.strip()
        if not p: continue
        lines = p.splitlines()
        
        # 1. Logic to identify the Section Name (always the first line)
        first_line = lines[0]
        section_name = first_line.lstrip("# ").strip()

        # 2. Logic to strip the Header from the Body
        # If the first line starts with # or ##, we remove it.
        if first_line.startswith("#"):
            body_text = "\n".join(lines[1:]).strip()
        else:
            # If there's no header at all (unlikely), keep it all
            body_text = p

        # 3. Skip empty title-only chunks (Your smart logic)
        if not body_text or (len(lines) < 2 and first_line.startswith("#")):
            continue

        # Return: (Section Name, Clean Body, Full Original Text)
        out.append((section_name, body_text, p))
        
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
        if not fname.lower().endswith((".md", ".txt")): continue
        path = os.path.join(data_dir, fname)
        text = _read_text_file(path)
        
        # FIX: Unpack the 3 values now
        for section, body, full in _md_sections(text):
            docs.append({
                "title": fname,
                "section": section,
                "text": body,      # The 'Clean' body
                "full_text": full  # The 'Full' original chunk
            })
    return docs

def doc_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
