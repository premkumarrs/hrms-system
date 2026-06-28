"""Minimal PDF builder shared by HR letter generators."""


def escape_pdf_text(value):
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_simple_pdf(lines):
    """Build a minimal single-page PDF from text lines."""

    content_lines = ["BT", "/F1 12 Tf", "50 750 Td"]
    for index, line in enumerate(lines):
        if index == 0:
            content_lines.append(f"({escape_pdf_text(line)}) Tj")
        else:
            content_lines.append("0 -18 Td")
            content_lines.append(f"({escape_pdf_text(line)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines)

    font_obj = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    content_obj = f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"
    page_obj = (
        "<< /Type /Page /Parent 3 0 R /MediaBox [0 0 612 792] "
        "/Contents 2 0 R /Resources << /Font << /F1 1 0 R >> >> >>"
    )
    pages_obj = "<< /Type /Pages /Kids [4 0 R] /Count 1 >>"
    catalog_obj = "<< /Type /Catalog /Pages 3 0 R >>"

    objects = [font_obj, content_obj, pages_obj, page_obj, catalog_obj]

    pdf = ["%PDF-1.4"]
    offsets = [0]

    for index, body in enumerate(objects, start=1):
        offsets.append(len("\n".join(pdf).encode("latin-1")) + 1)
        pdf.append(f"{index} 0 obj\n{body}\nendobj")

    xref_start = len("\n".join(pdf).encode("latin-1")) + 1
    pdf.append("xref")
    pdf.append(f"0 {len(objects) + 1}")
    pdf.append("0000000000 65535 f ")
    for offset in offsets[1:]:
        pdf.append(f"{offset:010d} 00000 n ")

    pdf.append("trailer")
    pdf.append(f"<< /Size {len(objects) + 1} /Root 5 0 R >>")
    pdf.append("startxref")
    pdf.append(str(xref_start))
    pdf.append("%%EOF")

    return "\n".join(pdf).encode("latin-1")
