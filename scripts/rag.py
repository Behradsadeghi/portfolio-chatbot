"""
rag.py

Mantegh-e moshtarak-e RAG: load kardan-e index, sakhtan-e context, va
system prompt.

CHERA IN FILE ALAN JODA SHOD
----------------------------
In se ta chiz aval tuye answer.py budan. Hala api.py ham hamun-ha ro
lazem dare.

Age copy-paste mikardim, do noskhe-ye system prompt dashtim - va rooz-i
ke yekish ro behtar koni, un yeki aghab mimune. Bad-tar: eval-e to ru
ye noskhe ejra mishe va production ru noskhe-ye digeh.

DARS: az avval abstract nakon. Vaghti mahal-e dovom-e estefade PEYDA
SHOD, un vaght joda kon.
"""

import json

import numpy as np

from .config import INDEX_PATH

SYSTEM_PROMPT = """You are a helpful assistant embedded on Behrad Sadeghi's \
personal portfolio website. You answer visitors' questions about his \
background, experience, skills, and projects.

Rules you must follow:

1. Answer ONLY using the numbered context passages provided. Do not use \
any outside knowledge about AI engineering, companies, or technologies.

2. If the context does not contain the answer, say so plainly — for example: \
"I don't have that information on this site." Do not guess, and do not fill \
gaps with plausible-sounding details.

2a. If the question is too vague or incomplete to answer — a fragment like \
"from when?" with nothing to attach it to — ask a short clarifying question \
instead of saying you don't know. Not knowing what was asked is different from \
not having the answer, and the visitor can fix the first one.

3. Cite your sources inline using the passage numbers, like [1] or [2][4]. \
Every factual claim needs a citation.

4. Refer to him in the third person as "Behrad". You are not Behrad.

5. Be concise — two or three sentences is usually enough. Visitors are \
skimming, not reading an essay.

6. Dates, durations, and figures that appear in the passages are answers too. \
A role written as "(May 2026 - Present)" answers "since when?"."""


def load_index():
    """Index ro mikhune va matrix-e normalize-shode barmigardune."""
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    chunks = index["chunks"]
    matrix = np.array([c["embedding"] for c in chunks])
    # az ghabl normalize mikonim ta har search dobare hesab nakone
    matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    return chunks, matrix


def build_context(retrieved) -> str:
    """
    Chunk-ha ro shomare-dar mikone ta model betune cite kone.

    Onvan ro ham migzarim chon be model komak mikone befahme in tekke
    chie - skill? job? project?
    """
    parts = []
    for i, (chunk, _score) in enumerate(retrieved, start=1):
        parts.append(f"[{i}] ({chunk['section']}) {chunk['title']}\n{chunk['text']}")
    return "\n\n".join(parts)
