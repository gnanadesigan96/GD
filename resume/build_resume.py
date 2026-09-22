"""Build ATS-friendly PDF and DOCX resumes in two designs (Classic and Modern).

Usage:  python3 build_resume.py
Needs:  pip install reportlab python-docx

ATS rules followed in every output:
  * single column, no tables, text boxes, images, icons or headers/footers
  * standard section headings (Professional Summary, Skills, ...)
  * real text bullets and plain-text contact details
  * standard fonts (Helvetica in the PDF, Arial in the DOCX)
"""

import html
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Inches

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, HRFlowable, Paragraph, SimpleDocTemplate, Spacer

import resume_data as R

HERE = os.path.dirname(os.path.abspath(__file__))
BASENAME = "Athi_Shree_V_Resume"

# Each design is the same content with a different look.
DESIGNS = {
    "Classic": {
        "accent": "1F4E79",       # navy
        "header_align": "center",
        "heading": "rule",        # uppercase title with a full-width underline
        "name_color": "1F4E79",
        "body_size": 10.5,
        "leading": 14.6,
    },
    "Modern": {
        "accent": "0F766E",       # teal
        "header_align": "left",
        "heading": "band",        # tinted band with a solid accent bar on the left
        "name_color": "1E293B",   # slate
        "body_size": 10.5,
        "leading": 14.6,
    },
}


def e(text):
    return html.escape(text)


# --------------------------------------------------------------------------- PDF
# Built with ReportLab using the standard Helvetica fonts (simple Type1 fonts,
# WinAnsi encoding, classic xref table). This is the most widely parsable PDF
# structure; browser-printed PDFs use embedded CID fonts that some ATS reject.
class DatedLine(Flowable):
    """One line with bold text on the left and a right-aligned date."""

    def __init__(self, left, right, size, color, space_before=0, rest="", date_color="#333333"):
        super().__init__()
        self.left, self.right, self.size, self.color = left, right, size, color
        self.spaceBefore = space_before
        self.rest = rest  # optional regular-weight text after the bold part
        self.date_color = date_color
        self.keepWithNext = True

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return avail_w, self.size * 1.35

    def draw(self):
        c = self.canv
        c.setFont("Helvetica-Bold", self.size)
        c.setFillColor(self.color)
        c.drawString(0, 3, self.left)
        if self.rest:
            c.setFont("Helvetica", self.size)
            c.drawString(c.stringWidth(self.left, "Helvetica-Bold", self.size), 3, self.rest)
            c.setFont("Helvetica-Bold", self.size)
        c.setFillColor(colors.HexColor(self.date_color))
        c.drawRightString(self.width, 3, self.right)


class BandHeading(Flowable):
    """Section heading drawn as a light tinted band with an accent bar."""

    def __init__(self, text, accent, tint, size):
        super().__init__()
        self.text, self.accent, self.tint, self.size = text, accent, tint, size
        self.spaceBefore, self.spaceAfter = 12, 6
        self.keepWithNext = True

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return avail_w, self.size + 9

    def draw(self):
        c = self.canv
        h = self.size + 9
        c.setFillColor(self.tint)
        c.rect(0, 0, self.width, h, stroke=0, fill=1)
        c.setFillColor(self.accent)
        c.rect(0, 0, 3.5, h, stroke=0, fill=1)
        c.setFont("Helvetica-Bold", self.size)
        c.drawString(10, 5.2, self.text)


def build_pdf(pdf_path, d):
    accent = colors.HexColor("#" + d["accent"])
    tint = colors.Color(accent.red, accent.green, accent.blue, alpha=0.10)
    ink = colors.HexColor("#1a1a1a")
    muted = colors.HexColor("#4b5563")
    size, lead = d["body_size"], d["leading"]
    align = TA_CENTER if d["header_align"] == "center" else TA_LEFT
    base = dict(fontName="Helvetica", fontSize=size, leading=lead, textColor=ink)
    st = {
        "name": ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=26, leading=31,
                               alignment=align, textColor=colors.HexColor("#" + d["name_color"])),
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=11.2, leading=16,
                                alignment=align,
                                textColor=accent if d["heading"] == "band" else colors.HexColor("#333333")),
        "contact": ParagraphStyle("contact", **{**base, "fontSize": 10, "textColor": muted},
                                  alignment=align, spaceBefore=1),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=15,
                             textColor=accent, spaceBefore=13, keepWithNext=True),
        "body": ParagraphStyle("body", **base),
        "skill": ParagraphStyle("skill", **base, spaceAfter=3.5),
        "sub": ParagraphStyle("sub", **{**base, "textColor": muted}, spaceBefore=1, spaceAfter=3,
                              keepWithNext=True),
        "bullet": ParagraphStyle("bullet", **base, leftIndent=14, bulletIndent=3, spaceAfter=3.2),
    }

    def heading(text):
        if d["heading"] == "band":
            return [BandHeading(text.upper(), accent, tint, 11.5)]
        rule = HRFlowable(width="100%", thickness=1.1, color=accent, spaceBefore=2, spaceAfter=7)
        rule.keepWithNext = True
        return [Paragraph(text.upper(), st["h2"]), rule]

    def bullets(items):
        return [Paragraph(e(t), st["bullet"], bulletText="•") for t in items]

    story = [
        Paragraph(e(R.NAME), st["name"]),
        Paragraph(e(R.TITLE), st["title"]),
        Paragraph("  |  ".join(e(c) for c in R.CONTACT), st["contact"]),
    ]
    if d["heading"] == "band":
        story.append(HRFlowable(width="100%", thickness=2.2, color=accent, spaceBefore=8, spaceAfter=0))
    story += heading("Professional Summary")
    story.append(Paragraph(e(R.SUMMARY), st["body"]))
    story += heading("Skills")
    for k, v in R.SKILLS:
        story.append(Paragraph(f'<font name="Helvetica-Bold" color="#{d["accent"]}">{e(k)}:</font> {e(v)}',
                               st["skill"]))
    story += heading("Professional Experience")
    story.append(DatedLine(R.JOB_TITLE, R.EMPLOYER_DATES, 11.2, ink))
    story.append(Paragraph(f"{e(R.EMPLOYER)}  |  {e(R.EMPLOYER_DETAIL)}", st["sub"]))
    for p in R.PROJECTS:
        story.append(DatedLine(f"Client: {p['client']} | {p['role']}", p["dates"], size, accent,
                               space_before=8, date_color="#4b5563"))
        story.append(Spacer(1, 2))
        story += bullets(p["bullets"])
    story += heading("Certifications") + bullets(R.CERTIFICATIONS)
    story += heading("Education")
    for deg, school, years, grade in R.EDUCATION:
        story.append(DatedLine(deg, years, size, ink, space_before=2))
        story.append(Paragraph(f"{e(school)}  |  {e(grade)}", st["sub"]))
    story += heading("Achievements") + bullets(R.ACHIEVEMENTS)

    doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            title=f"{R.NAME.title()} - Resume", author=R.NAME.title(),
                            subject="Resume", creator="build_resume.py")
    doc.build(story)


# --------------------------------------------------------------------------- DOCX
def _border(paragraph, side, color, size="10"):
    pPr = paragraph._p.get_or_add_pPr()
    bdr = pPr.find(qn("w:pBdr"))
    if bdr is None:
        bdr = OxmlElement("w:pBdr")
        pPr.append(bdr)
    b = OxmlElement(f"w:{side}")
    for k, v in (("val", "single"), ("sz", size), ("space", "4"), ("color", color)):
        b.set(qn(f"w:{k}"), v)
    bdr.append(b)


def _shade(paragraph, fill):
    shd = OxmlElement("w:shd")
    for k, v in (("val", "clear"), ("color", "auto"), ("fill", fill)):
        shd.set(qn(f"w:{k}"), v)
    paragraph._p.get_or_add_pPr().append(shd)


def _tint(hex_color, amount=0.9):
    rgb = [int(hex_color[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(c + (255 - c) * amount):02X}" for c in rgb)


def build_docx(path, d):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    sec.left_margin = sec.right_margin = Inches(0.7)
    sec.top_margin = sec.bottom_margin = Inches(0.6)
    accent = RGBColor.from_string(d["accent"])
    muted = RGBColor.from_string("4B5563")
    center = d["header_align"] == "center"

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(d["body_size"])
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.15

    def para(text="", bold=False, size=None, color=None, align=None, after=0, before=0):
        p = doc.add_paragraph()
        if text:
            r = p.add_run(text)
            r.bold = bold
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
        p = para(text.upper(), bold=True, size=12, color=accent, before=12, after=6)
        p.paragraph_format.keep_with_next = True
        if d["heading"] == "band":
            _shade(p, _tint(d["accent"]))
            _border(p, "left", d["accent"], size="24")
        else:
            _border(p, "bottom", d["accent"])

    def bullet(text):
        p = doc.add_paragraph(text, style="List Bullet")
        p.paragraph_format.space_after = Pt(3)

    def dated(left, right, color=None, before=2, size=None):
        # Right-aligned date via a tab stop (no tables, stays ATS-safe).
        p = para(before=before)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.tab_stops.add_tab_stop(sec.page_width - sec.left_margin - sec.right_margin,
                                                  alignment=2)
        r = p.add_run(left)
        r.bold = True
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
        r2 = p.add_run("\t" + right)
        r2.bold = True
        return p

    align = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    para(R.NAME, bold=True, size=26, color=RGBColor.from_string(d["name_color"]), align=align)
    para(R.TITLE, bold=True, size=11.5, color=None if center else accent, align=align, before=2)
    p = para("  |  ".join(R.CONTACT), size=10, color=muted, align=align, after=2)
    if not center:
        _border(p, "bottom", d["accent"], size="18")

    heading("Professional Summary")
    para(R.SUMMARY)

    heading("Skills")
    for k, v in R.SKILLS:
        p = para(after=3)
        r = p.add_run(k + ": ")
        r.bold = True
        r.font.color.rgb = accent
        p.add_run(v)

    heading("Professional Experience")
    dated(R.JOB_TITLE, R.EMPLOYER_DATES, size=11)
    p = para(f"{R.EMPLOYER}  |  {R.EMPLOYER_DETAIL}", color=muted, after=2)
    p.paragraph_format.keep_with_next = True
    for proj in R.PROJECTS:
        dated(f"Client: {proj['client']} | {proj['role']}", proj["dates"], color=accent, before=8)
        for b in proj["bullets"]:
            bullet(b)

    heading("Certifications")
    for c in R.CERTIFICATIONS:
        bullet(c)

    heading("Education")
    for deg, school, years, grade in R.EDUCATION:
        dated(deg, years)
        para(f"{school}  |  {grade}", color=muted, after=4)

    heading("Achievements")
    for a in R.ACHIEVEMENTS:
        bullet(a)

    doc.core_properties.title = f"{R.NAME.title()} - Resume"
    doc.core_properties.author = R.NAME.title()
    doc.save(path)


if __name__ == "__main__":
    for name, design in DESIGNS.items():
        stem = os.path.join(HERE, f"{BASENAME}_{name}")
        build_pdf(stem + ".pdf", design)
        build_docx(stem + ".docx", design)
        print(f"Built {BASENAME}_{name}.pdf / .docx")
