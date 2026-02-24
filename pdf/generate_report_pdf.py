#!/usr/bin/env python3
"""
Generate a styled PDF from a markdown SEO report using Playwright.
Usage: python generate_report_pdf.py <input.md> <output.pdf>
"""

import sys
import re
from pathlib import Path
from playwright.sync_api import sync_playwright


def md_to_html(md_text: str) -> str:
    """Minimal markdown-to-HTML converter (no external deps)."""
    lines = md_text.split("\n")
    html_lines = []
    in_code = False
    in_table = False
    in_ul = False
    table_header_done = False

    for line in lines:
        # Code blocks
        if line.startswith("```"):
            if not in_code:
                lang = line[3:].strip()
                cls = f' class="language-{lang}"' if lang else ""
                html_lines.append(f"<pre><code{cls}>")
                in_code = True
            else:
                html_lines.append("</code></pre>")
                in_code = False
            continue
        if in_code:
            html_lines.append(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            continue

        # Tables
        if "|" in line and line.strip().startswith("|"):
            stripped = line.strip()
            if re.match(r"^\|[-| :]+\|$", stripped):
                # Separator row
                if not in_table:
                    html_lines.append("<table>")
                    in_table = True
                html_lines.append("<tbody>")
                table_header_done = True
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not in_table:
                html_lines.append("<table><thead><tr>")
                html_lines.extend(f"<th>{c}</th>" for c in cells)
                html_lines.append("</tr>")
                in_table = True
                table_header_done = False
            elif not table_header_done:
                # Still in header area
                html_lines.append("<tr>")
                html_lines.extend(f"<th>{c}</th>" for c in cells)
                html_lines.append("</tr></thead>")
            else:
                html_lines.append("<tr>")
                html_lines.extend(f"<td>{c}</td>" for c in cells)
                html_lines.append("</tr>")
            continue
        else:
            if in_table:
                html_lines.append("</tbody></table>")
                in_table = False
                table_header_done = False

        # Horizontal rules
        if re.match(r"^---+$", line.strip()):
            html_lines.append("<hr>")
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            content = inline_format(m.group(2))
            # Generate anchor id
            anchor = re.sub(r"[^a-z0-9-]", "", content.lower().replace(" ", "-"))
            html_lines.append(f"<h{level} id=\"{anchor}\">{content}</h{level}>")
            continue

        # Unordered lists
        m = re.match(r"^(\s*)[-*]\s+(.*)", line)
        if m:
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li>{inline_format(m.group(2))}</li>")
            continue
        else:
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False

        # Blank line
        if not line.strip():
            html_lines.append("")
            continue

        # Paragraph
        html_lines.append(f"<p>{inline_format(line)}</p>")

    if in_table:
        html_lines.append("</tbody></table>")
    if in_ul:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def inline_format(text: str) -> str:
    """Apply inline markdown formatting."""
    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # Bold
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 10pt;
  line-height: 1.6;
  color: #1a1a2e;
  background: #fff;
}

.page-wrap {
  max-width: 760px;
  margin: 0 auto;
  padding: 40px 48px;
}

/* Cover / Header */
.report-header {
  border-left: 5px solid #6c3fc5;
  padding: 24px 24px 20px;
  background: linear-gradient(135deg, #f8f5ff 0%, #eef2ff 100%);
  border-radius: 0 8px 8px 0;
  margin-bottom: 32px;
}
.report-header h1 {
  font-size: 22pt;
  font-weight: 700;
  color: #6c3fc5;
  margin-bottom: 6px;
  border: none;
  padding: 0;
}
.report-header .meta {
  font-size: 9pt;
  color: #555;
  display: grid;
  grid-template-columns: auto auto;
  gap: 2px 24px;
  margin-top: 12px;
}
.report-header .meta span { display: block; }
.report-header .meta strong { color: #333; }

/* Score badge */
.score-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  border: 2px solid #e0e0e0;
  border-radius: 10px;
  padding: 10px 18px;
  margin: 16px 0 24px;
}
.score-badge .score-num {
  font-size: 36pt;
  font-weight: 700;
  color: #e07b39;
  line-height: 1;
}
.score-badge .score-label {
  font-size: 10pt;
  color: #666;
  line-height: 1.3;
}
.score-badge .score-label strong {
  display: block;
  color: #333;
  font-size: 11pt;
}

/* Headings */
h1, h2, h3, h4, h5, h6 {
  font-weight: 600;
  color: #1a1a2e;
  margin: 20px 0 8px;
  line-height: 1.3;
}
h2 {
  font-size: 14pt;
  border-bottom: 2px solid #e8e3f5;
  padding-bottom: 6px;
  color: #3d2b7a;
}
h3 { font-size: 11.5pt; color: #4a3a8a; }
h4 { font-size: 10.5pt; color: #555; }

/* Severity badges */
h3[id^="c"] .badge, h3[id*="critical"] .badge { background: #fde8e8; color: #c0392b; }
h3[id^="h"] .badge { background: #fef3e2; color: #d35400; }

.severity-critical { color: #c0392b; font-weight: 700; }
.severity-high { color: #d35400; font-weight: 700; }
.severity-medium { color: #b7770d; font-weight: 700; }
.severity-low { color: #27ae60; font-weight: 600; }

/* Paragraphs */
p { margin: 8px 0; }

/* Lists */
ul, ol { margin: 8px 0 8px 20px; }
li { margin: 3px 0; }

/* Code */
code {
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 8.5pt;
  background: #f4f1fb;
  border: 1px solid #e0d9f7;
  border-radius: 3px;
  padding: 1px 5px;
  color: #6c3fc5;
}
pre {
  background: #1e1b2e;
  border-radius: 6px;
  padding: 14px 16px;
  margin: 12px 0;
  overflow: hidden;
}
pre code {
  background: none;
  border: none;
  color: #c8c2e8;
  font-size: 8pt;
  padding: 0;
  display: block;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Tables */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 9pt;
}
thead {
  background: #6c3fc5;
  color: #fff;
}
th {
  padding: 8px 10px;
  text-align: left;
  font-weight: 600;
  font-size: 8.5pt;
  letter-spacing: 0.02em;
}
td {
  padding: 7px 10px;
  border-bottom: 1px solid #ede8fa;
}
tbody tr:nth-child(even) { background: #faf8ff; }
tbody tr:hover { background: #f0ebff; }

/* HR */
hr {
  border: none;
  border-top: 1px solid #e8e3f5;
  margin: 24px 0;
}

/* Links */
a { color: #6c3fc5; text-decoration: none; }
a:hover { text-decoration: underline; }

/* Blockquote */
blockquote {
  border-left: 3px solid #6c3fc5;
  margin: 12px 0;
  padding: 8px 16px;
  background: #f8f5ff;
  border-radius: 0 4px 4px 0;
  font-style: italic;
  color: #444;
}

/* Strong */
strong { font-weight: 600; color: #1a1a2e; }

/* Footer */
.report-footer {
  margin-top: 40px;
  padding-top: 16px;
  border-top: 1px solid #e8e3f5;
  font-size: 8pt;
  color: #888;
  text-align: center;
}

/* Page breaks */
h2 { page-break-before: auto; }
table { page-break-inside: avoid; }
pre { page-break-inside: avoid; }
"""


def generate_pdf(md_path: str, pdf_path: str) -> None:
    md_text = Path(md_path).read_text(encoding="utf-8")

    # Extract the first H1 as the report title for the cover header
    title_match = re.search(r"^# (.+)$", md_text, re.MULTILINE)
    title = title_match.group(1) if title_match else "SEO Report"

    # Extract meta lines (lines 2–8, the bold/URL header block)
    meta_lines = []
    for line in md_text.split("\n")[1:10]:
        m = re.match(r"\*\*(.+?):\*\*\s*(.*)", line.strip())
        if m:
            meta_lines.append((m.group(1), m.group(2)))

    # Build meta HTML
    meta_html = ""
    for key, val in meta_lines:
        meta_html += f"<span><strong>{key}:</strong> {val}</span>"

    # Convert body (skip the first H1 line, we render it separately)
    body_md = re.sub(r"^# .+\n", "", md_text, count=1)
    body_html = md_to_html(body_md)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
<div class="page-wrap">

<div class="report-header">
  <h1>{title}</h1>
  <div class="meta">{meta_html}</div>
</div>

{body_html}

<div class="report-footer">
  Generated by Claude SEO Skill v1.2.0 &mdash; claude-sonnet-4-6 &mdash; {Path(md_path).name}
</div>

</div>
</body>
</html>"""

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="domcontentloaded")
        page.pdf(
            path=pdf_path,
            format="A4",
            margin={"top": "12mm", "bottom": "12mm", "left": "0mm", "right": "0mm"},
            print_background=True,
        )
        browser.close()

    print(f"PDF saved: {pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_report_pdf.py <input.md> <output.pdf>")
        sys.exit(1)
    generate_pdf(sys.argv[1], sys.argv[2])
