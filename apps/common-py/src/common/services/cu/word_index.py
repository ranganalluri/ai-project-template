# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from typing import Any


from dataclasses import dataclass

from common.models.content_understanding import AnalyzedResult

@dataclass
class WordBox:
    """Represents a word with its position and metadata from a CU document."""
    
    text: str
    offset: int
    length: int
    source: str  # e.g., "D(1, ... polygon ...)"
    confidence: float


def build_word_index(analyze_result: AnalyzedResult) -> list[WordBox]:
    """Build a sorted index of all words from a CU document.
    
    Args:
        cu_doc: CU document dictionary with 'pages' containing 'words' arrays
        
    Returns:
        List of WordBox objects sorted by offset for fast overlap search
    """
    out: list[WordBox] = []
    for page in analyze_result.result.contents[0].pages:
        for word in page.words:
            out.append(
                WordBox(
                    text=word.content,
                    offset=word.span.offset,
                    length=word.span.length,
                    source=word.source,
                    confidence=word.confidence,
                )
            )
    # Sort by offset to allow fast overlap search
    out.sort(key=lambda x: x.offset)
    return out

def overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return max(a0, b0) < min(a1, b1)

def span_to_sources(word_index: list[WordBox], spans: list[dict[str, int]]) -> list[str]:
    sources = list[Any]()
    for sp in spans:
        s0, s1 = sp["offset"], sp["offset"] + sp["length"]
        for w in word_index:
            if w.offset > s1:  # since sorted, can break early
                break
            if overlap(s0, s1, w.offset, w.offset + w.length) and w.source:
                sources.append(w.source)
    # de-dup while preserving order
    seen = set[Any]()
    uniq = list[Any]()
    for s in sources:   
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq