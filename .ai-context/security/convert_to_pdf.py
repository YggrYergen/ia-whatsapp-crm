"""
Converts all .md files in this directory to styled PDF.
Uses: markdown (MD→HTML) + xhtml2pdf (HTML→PDF)
"""
import os
import markdown
from xhtml2pdf import pisa

DIR = os.path.dirname(os.path.abspath(__file__))

# GitHub-inspired CSS for professional PDF rendering
CSS = """
@page {
    size: A4;
    margin: 1.5cm 2cm;
    @frame footer {
        -pdf-frame-content: footerContent;
        bottom: 0;
        margin-left: 2cm;
        margin-right: 2cm;
        height: 1cm;
    }
}

body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10px;
    line-height: 1.5;
    color: #1f2328;
}

h1 {
    font-size: 22px;
    font-weight: bold;
    border-bottom: 2px solid #d1d9e0;
    padding-bottom: 8px;
    margin-top: 20px;
    margin-bottom: 12px;
    color: #1f2328;
}

h2 {
    font-size: 17px;
    font-weight: bold;
    border-bottom: 1px solid #d1d9e0;
    padding-bottom: 6px;
    margin-top: 18px;
    margin-bottom: 10px;
    color: #1f2328;
}

h3 {
    font-size: 14px;
    font-weight: bold;
    margin-top: 14px;
    margin-bottom: 8px;
    color: #1f2328;
}

h4 {
    font-size: 12px;
    font-weight: bold;
    margin-top: 10px;
    margin-bottom: 6px;
}

p {
    margin: 6px 0;
}

blockquote {
    border-left: 4px solid #d1d9e0;
    padding: 4px 12px;
    margin: 10px 0;
    color: #656d76;
    background-color: #f6f8fa;
}

code {
    background-color: #eff1f3;
    padding: 1px 4px;
    border-radius: 3px;
    font-family: Courier, monospace;
    font-size: 9px;
}

pre {
    background-color: #f6f8fa;
    border: 1px solid #d1d9e0;
    border-radius: 6px;
    padding: 12px;
    font-family: Courier, monospace;
    font-size: 8.5px;
    line-height: 1.4;
    overflow: hidden;
    white-space: pre-wrap;
    word-wrap: break-word;
}

pre code {
    background: none;
    padding: 0;
    font-size: 8.5px;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0;
    font-size: 9px;
}

th {
    background-color: #f6f8fa;
    border: 1px solid #d1d9e0;
    padding: 6px 10px;
    text-align: left;
    font-weight: bold;
}

td {
    border: 1px solid #d1d9e0;
    padding: 5px 10px;
    vertical-align: top;
}

tr:nth-child(even) td {
    background-color: #f9fafb;
}

hr {
    border: none;
    border-top: 2px solid #d1d9e0;
    margin: 16px 0;
}

ul, ol {
    padding-left: 20px;
    margin: 6px 0;
}

li {
    margin: 3px 0;
}

strong {
    font-weight: bold;
    color: #1f2328;
}

a {
    color: #0969da;
    text-decoration: none;
}

/* Alert styling for blockquotes with [!NOTE], [!WARNING], etc. */
.admonition {
    padding: 8px 12px;
    margin: 10px 0;
    border-radius: 4px;
    border-left: 4px solid;
}
"""

FOOTER_HTML = """
<div id="footerContent" style="text-align: center; font-size: 7px; color: #999;">
    Auditoría de Seguridad — IA WhatsApp CRM — Confidencial
</div>
"""


def md_to_pdf(md_path: str, pdf_path: str) -> bool:
    """Convert a Markdown file to a styled PDF."""
    print(f"  📄 Reading: {os.path.basename(md_path)}")

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Convert MD → HTML with extensions for tables, fenced code, etc.
    html_body = markdown.markdown(
        md_text,
        extensions=[
            "tables",
            "fenced_code",
            "codehilite",
            "toc",
            "sane_lists",
            "smarty",
        ],
        extension_configs={
            "codehilite": {"css_class": "highlight", "guess_lang": False}
        },
    )

    # Wrap in full HTML document
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <style>{CSS}</style>
</head>
<body>
{html_body}
{FOOTER_HTML}
</body>
</html>"""

    # Convert HTML → PDF
    print(f"  📝 Generating: {os.path.basename(pdf_path)}")
    with open(pdf_path, "wb") as pdf_file:
        status = pisa.CreatePDF(full_html, dest=pdf_file, encoding="utf-8")

    if status.err:
        print(f"  ❌ ERROR generating {os.path.basename(pdf_path)}: {status.err} errors")
        return False

    size_kb = os.path.getsize(pdf_path) / 1024
    print(f"  ✅ Saved: {os.path.basename(pdf_path)} ({size_kb:.1f} KB)")
    return True


def main():
    print("=" * 60)
    print("  Markdown → PDF Converter")
    print("=" * 60)

    md_files = sorted([f for f in os.listdir(DIR) if f.endswith(".md")])
    print(f"\n  Found {len(md_files)} markdown files\n")

    results = []
    for md_file in md_files:
        md_path = os.path.join(DIR, md_file)
        pdf_file = md_file.replace(".md", ".pdf")
        pdf_path = os.path.join(DIR, pdf_file)

        success = md_to_pdf(md_path, pdf_path)
        results.append((md_file, pdf_file, success))
        print()

    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    for md_file, pdf_file, success in results:
        icon = "✅" if success else "❌"
        print(f"  {icon} {md_file} → {pdf_file}")
    print()


if __name__ == "__main__":
    main()
