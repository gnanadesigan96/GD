"""Build ATS-friendly PDF and DOCX versions of the resume.

Usage:  python3 build_resume.py
Needs:  python-docx, and Node.js with the `playwright` package for the PDF.

ATS rules followed in both outputs:
  * single column, no tables, text boxes, images, icons or headers/footers
  * standard section headings (Professional Summary, Skills, ...)
  * real text bullets and plain-text contact details
  * standard fonts (Arial / Liberation Sans)
"""

import html
import os
import subprocess

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Inches

import resume_data as R

HERE = os.path.dirname(os.path.abspath(__file__))
BASENAME = "Athi_Shree_V_Resume"
ACCENT = "1F4E79"


def e(text):
    return html.escape(text)


# --------------------------------------------------------------------------- HTML / PDF
def build_html():
    skills = "\n".join(
        f'<p class="skill"><strong>{e(k)}:</strong> {e(v)}</p>' for k, v in R.SKILLS
    )
    projects = ""
    for p in R.PROJECTS:
        bullets = "".join(f"<li>{e(b)}</li>" for b in p["bullets"])
        projects += (
            f'<p class="proj"><span class="l">Client: {e(p["client"])} | {e(p["role"])}</span>'
            f'<span class="r">{e(p["dates"])}</span></p>\n<ul>{bullets}</ul>\n'
        )
    edu = "".join(
        f'<p class="edu"><span class="l"><strong>{e(d)}</strong> | {e(s)} | {e(g)}</span>'
        f'<span class="r">{e(y)}</span></p>'
        for d, s, y, g in R.EDUCATION
    )
    achievements = "".join(f"<li>{e(a)}</li>" for a in R.ACHIEVEMENTS)
    certs = "".join(f"<li>{e(c)}</li>" for c in R.CERTIFICATIONS)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{e(R.NAME.title())} - Resume</title>
<style>
  @page {{ size: A4; margin: 9mm 12mm 8mm 12mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: Arial, "Liberation Sans", Helvetica, sans-serif;
         font-size: 9.3pt; line-height: 1.26; color: #1a1a1a; }}
  h1 {{ margin: 0; text-align: center; font-size: 22pt; letter-spacing: 2.5px;
        color: #{ACCENT}; font-weight: 700; }}
  .title {{ text-align: center; margin: 3px 0 2px; font-size: 10.6pt; font-weight: 700; color: #333; }}
  .contact {{ text-align: center; margin: 0 0 4px; font-size: 9.4pt; color: #333; }}
  h2 {{ font-size: 10.8pt; text-transform: uppercase; letter-spacing: 1.2px; color: #{ACCENT};
        margin: 6px 0 3px; padding-bottom: 1.5px; border-bottom: 1.4px solid #{ACCENT}; }}
  p {{ margin: 0; }}
  .summary {{ text-align: justify; }}
  .skill {{ margin: 1px 0; }}
  .skill strong {{ color: #{ACCENT}; }}
  .job, .proj {{ display: flex; justify-content: space-between; gap: 12px; }}
  .job {{ font-weight: 700; font-size: 10.2pt; margin-top: 2px; }}
  .proj {{ font-weight: 700; color: #{ACCENT}; margin: 4px 0 0; }}
  .r {{ white-space: nowrap; font-weight: 700; color: #333; }}
  .edu {{ display: flex; justify-content: space-between; gap: 10px; margin: 1.5px 0; }}
  .sub {{ font-style: italic; color: #444; margin-bottom: 2px; }}
  ul {{ margin: 1px 0 0; padding-left: 15px; }}
  li {{ margin: 0.8px 0; padding-left: 1px; }}
</style></head>
<body>
<h1>{e(R.NAME)}</h1>
<p class="title">{e(R.TITLE)}</p>
<p class="contact">{' | '.join(e(c) for c in R.CONTACT)}</p>

<h2>Professional Summary</h2>
<p class="summary">{e(R.SUMMARY)}</p>

<h2>Skills</h2>
{skills}

<h2>Professional Experience</h2>
<p class="job"><span class="l">{e(R.EMPLOYER_ROLE)} | {e(R.EMPLOYER)}</span><span class="r">{e(R.EMPLOYER_DATES)}</span></p>
{projects}
<h2>Certifications</h2>
<ul>{certs}</ul>

<h2>Education</h2>
{edu}

<h2>Achievements</h2>
<ul>{achievements}</ul>
</body></html>
"""


def build_pdf(html_path, pdf_path):
    js = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://{html_path}');
  await p.pdf({{ path: '{pdf_path}', format: 'A4', preferCSSPageSize: true, printBackground: true }});
  await b.close();
}})();
"""
    env = dict(os.environ)
    env.setdefault("NODE_PATH", subprocess.check_output(["npm", "root", "-g"], text=True).strip())
    subprocess.run(["node", "-e", js], check=True, env=env)


# --------------------------------------------------------------------------- DOCX
def _bottom_border(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", "10"), ("space", "1"), ("color", ACCENT)):
        b.set(qn(f"w:{k}"), v)
    bdr.append(b)
    pPr.append(bdr)


def build_docx(path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    sec.left_margin = sec.right_margin = Inches(0.6)
    sec.top_margin = sec.bottom_margin = Inches(0.5)
    accent = RGBColor.from_string(ACCENT)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.08

    def para(text="", bold=False, size=None, color=None, align=None, italic=False, after=0, before=0):
        p = doc.add_paragraph()
        if text:
            r = p.add_run(text)
            r.bold, r.italic = bold, italic
            if size:
                r.font.size = Pt(size)
            if color:
                r.font.color.rgb = color
        if align is not None:
            p.alignment = align
        p.paragraph_format.space_after = Pt(after)
        p.paragraph_format.space_before = Pt(before)
        return p

    def heading(text):
        p = para(text.upper(), bold=True, size=11, color=accent, before=8, after=3)
        _bottom_border(p)

    def bullet(text):
        p = doc.add_paragraph(text, style="List Bullet")
        p.paragraph_format.space_after = Pt(1)

    def dated(left, right, color=None, before=2):
        # Right-aligned date via a tab stop (no tables, stays ATS-safe).
        p = para(before=before)
        p.paragraph_format.tab_stops.add_tab_stop(sec.page_width - sec.left_margin - sec.right_margin,
                                                  alignment=2)
        r = p.add_run(left)
        r.bold = True
        if color:
            r.font.color.rgb = color
        r2 = p.add_run("\t" + right)
        r2.bold = True
        return p

    para(R.NAME, bold=True, size=22, color=accent, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(R.TITLE, bold=True, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, before=2)
    para(" | ".join(R.CONTACT), size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER, after=2)

    heading("Professional Summary")
    para(R.SUMMARY).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    heading("Skills")
    for k, v in R.SKILLS:
        p = para(after=1)
        r = p.add_run(k + ": ")
        r.bold = True
        r.font.color.rgb = accent
        p.add_run(v)

    heading("Professional Experience")
    dated(f"{R.EMPLOYER_ROLE} | {R.EMPLOYER}", R.EMPLOYER_DATES)
    for p in R.PROJECTS:
        dated(f"Client: {p['client']} | {p['role']}", p["dates"], color=accent, before=5)
        for b in p["bullets"]:
            bullet(b)

    heading("Certifications")
    for c in R.CERTIFICATIONS:
        bullet(c)

    heading("Education")
    for d, s, y, g in R.EDUCATION:
        p = dated(d, y)
        p.runs[0]._r.addnext(p.add_run(f" | {s} | {g}")._r)

    heading("Achievements")
    for a in R.ACHIEVEMENTS:
        bullet(a)

    doc.core_properties.title = f"{R.NAME.title()} - Resume"
    doc.core_properties.author = R.NAME.title()
    doc.save(path)


if __name__ == "__main__":
    html_path = os.path.join(HERE, BASENAME + ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(build_html())
    build_pdf(html_path, os.path.join(HERE, BASENAME + ".pdf"))
    build_docx(os.path.join(HERE, BASENAME + ".docx"))
    print("Built", BASENAME + ".pdf / .docx / .html")
