# fpdf2 Unicode Pitfalls

When generating PDF from Python without LaTeX (no xelatex/pdflatex available), fpdf2 works but has encoding issues with Helvetica font.

## Problem
Helvetica only supports latin-1. Characters that fail:
- Em dash (—) → `FPDFUnicodeEncodingException`
- Greek letters (Σ α β)
- Math symbols (∝ ≥ ≠ ² °)
- Smart quotes (' ")

## Fix
Normalize before calling `multi_cell()` or `cell()`:

```python
def safe_text(text):
    text = text.replace('\u2014', '--').replace('\u2013', '-')
    text = text.replace('\u03a3', 'SUM').replace('\u03b1', 'alpha').replace('\u03b2', 'beta')
    text = text.replace('\u2265', '>=').replace('\u2260', '!=').replace('\u221d', '~')
    text = text.replace('\u00b2', '^2').replace('\u00b0', ' deg')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    return text
```

## Alternative
Use `add_font()` with a TTF that supports Unicode, or use a different PDF library (reportlab, weasyprint).
