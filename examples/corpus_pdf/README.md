# PDF corpus

Six synthetic two-page PDFs used to test page-aware citations. Every document
puts the specific fact on page 2, so a citation must report `page: 2` rather
than the chunk offset.

Regenerate with `uv run python scripts/make_pdf_corpus.py` (needs `fpdf2`).
