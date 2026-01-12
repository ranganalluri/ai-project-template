from dataclasses import dataclass

from common.models.content_understanding import AnalyzedResult, Span


@dataclass
class Chunk:
    chunk_id: str
    text: str
    spans: list[Span]  # list of {offset,length} in markdown
    sources: list[str]  # CU source polygons (optional precomputed)


def extract_chunks(cu_content: AnalyzedResult, markdown: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for i, p in enumerate(cu_content.result.contents[0].paragraphs):
        if not p.span or p.span.length == 0:
            continue
        txt = markdown[p.span.offset : p.span.offset + p.span.length]
        chunks.append(
            Chunk(
                chunk_id=f"para:{i}",
                text=txt.strip(),
                spans=[Span(offset=p.span.offset, length=p.span.length)],
                sources=[p.source] if p.source else [],
            )
        )

    return chunks
