"""Render the one-page nontechnical memo for Ritu Deshpande."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph
import reportlab


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "Ritu_Deshpande_Memo.pdf"

INK = HexColor("#14251F")
GREEN = HexColor("#164F3B")
GREEN_2 = HexColor("#237457")
LIME = HexColor("#D7EF85")
PAPER = HexColor("#F4F1E9")
CARD = HexColor("#FFFDF7")
MUTED = HexColor("#62716A")
LINE = HexColor("#D7DED9")
AMBER = HexColor("#D7872A")


def register_fonts() -> None:
    reportlab_fonts = Path(reportlab.__file__).resolve().parent / "fonts"
    families = [
        (
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("C:/Windows/Fonts/seguisb.ttf"),
            Path("C:/Windows/Fonts/segoeuib.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            reportlab_fonts / "Vera.ttf",
            reportlab_fonts / "VeraBd.ttf",
            reportlab_fonts / "VeraBd.ttf",
        ),
    ]
    regular, semibold, bold = next(
        family for family in families if all(path.exists() for path in family)
    )
    pdfmetrics.registerFont(TTFont("Kestrel", regular))
    pdfmetrics.registerFont(TTFont("Kestrel-Semibold", semibold))
    pdfmetrics.registerFont(TTFont("Kestrel-Bold", bold))


def paragraph(
    canvas: Canvas,
    text: str,
    x: float,
    y_top: float,
    width: float,
    *,
    size: float = 9,
    leading: float = 12,
    color=INK,
    font: str = "Kestrel",
    max_height: float = 80 * mm,
) -> float:
    style = ParagraphStyle(
        "memo",
        fontName=font,
        fontSize=size,
        leading=leading,
        textColor=color,
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    item = Paragraph(text, style)
    _, height = item.wrap(width, max_height)
    item.drawOn(canvas, x, y_top - height)
    return height


def rounded_card(canvas: Canvas, x: float, y: float, width: float, height: float, fill, radius: float = 4 * mm) -> None:
    canvas.setFillColor(fill)
    canvas.setStrokeColor(fill)
    canvas.roundRect(x, y, width, height, radius, fill=1, stroke=0)


def metric(canvas: Canvas, x: float, y: float, width: float, value: str, label: str) -> None:
    canvas.setFillColor(GREEN)
    canvas.setFont("Kestrel-Bold", 19)
    canvas.drawString(x, y, value)
    paragraph(canvas, label, x, y - 5 * mm, width, size=7.6, leading=9.6, color=MUTED, font="Kestrel-Semibold")


def build(output: Path = OUTPUT) -> None:
    register_fonts()
    output.parent.mkdir(parents=True, exist_ok=True)
    page_w, page_h = A4
    c = Canvas(str(output), pagesize=A4, pageCompression=1)
    c.setTitle("Kestrel Home Returns Risk — Decision Memo to Ritu Deshpande")
    c.setAuthor("Kestrel Returns Risk project")

    c.setFillColor(PAPER)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.rect(0, page_h - 36 * mm, page_w, 36 * mm, fill=1, stroke=0)
    c.setFillColor(LIME)
    c.rect(0, page_h - 36 * mm, page_w, 2.5 * mm, fill=1, stroke=0)

    margin = 18 * mm
    c.setFillColor(LIME)
    c.setFont("Kestrel-Bold", 8)
    c.drawString(margin, page_h - 12 * mm, "KESTREL HOME  /  RETURNS RISK DECISION NOTE")
    c.setFillColor(white)
    c.setFont("Kestrel-Semibold", 8)
    c.drawRightString(page_w - margin, page_h - 12 * mm, "25 SEPTEMBER 2026")
    c.setFont("Kestrel-Bold", 22)
    c.drawString(margin, page_h - 24 * mm, "Call the riskiest orders.")
    c.setFont("Kestrel", 22)
    c.drawString(margin, page_h - 31 * mm, "Do not hold the customer.")

    top = page_h - 47 * mm
    rounded_card(c, margin, top - 27 * mm, page_w - 2 * margin, 27 * mm, CARD)
    c.setFillColor(GREEN_2)
    c.setFont("Kestrel-Bold", 7.5)
    c.drawString(margin + 6 * mm, top - 7 * mm, "DECISION")
    paragraph(
        c,
        "Route orders at <b>15%+ return risk</b> to a same-day confirmation call, then release within 24 hours. "
        "Use a service tone for Shield members. Never convert this score into an automatic cancellation or open-ended hold.",
        margin + 6 * mm,
        top - 10 * mm,
        page_w - 2 * margin - 12 * mm,
        size=10.2,
        leading=14,
        color=INK,
    )

    metric_top = top - 38 * mm
    col_w = (page_w - 2 * margin - 16 * mm) / 3
    metric(c, margin, metric_top, col_w, "0.786", "Forward-test ROC-AUC on the newest labelled quarter")
    metric(c, margin + col_w + 8 * mm, metric_top, col_w, "60%", "Eventual returns captured at the 15% action line")
    metric(c, margin + 2 * (col_w + 8 * mm), metric_top, col_w, "24%", "Orders sent to a confirmation call, not a long hold")

    rupee_y = metric_top - 31 * mm
    rounded_card(c, margin, rupee_y - 35 * mm, page_w - 2 * margin, 35 * mm, GREEN)
    c.setFillColor(LIME)
    c.setFont("Kestrel-Bold", 7.5)
    c.drawString(margin + 6 * mm, rupee_y - 7 * mm, "THE RUPEES  /  PER 700 ORDERS")
    c.setFillColor(white)
    c.setFont("Kestrel-Bold", 23)
    c.drawString(margin + 6 * mm, rupee_y - 19 * mm, "₹11,821")
    c.setFont("Kestrel-Semibold", 8)
    c.drawString(margin + 6 * mm, rupee_y - 26 * mm, "estimated monthly net benefit")
    c.setStrokeColor(HexColor("#4A7565"))
    c.line(margin + 57 * mm, rupee_y - 29 * mm, margin + 57 * mm, rupee_y - 7 * mm)
    paragraph(
        c,
        "<b>170 calls × ₹45 = ₹7,660</b><br/>~17 prevented returns × ₹1,150 = ₹19,481 avoided handling<br/>Paid model/API cost = ₹0",
        margin + 64 * mm,
        rupee_y - 8 * mm,
        page_w - 2 * margin - 70 * mm,
        size=9,
        leading=13,
        color=white,
        font="Kestrel",
    )

    content_top = rupee_y - 45 * mm
    left_w = 103 * mm
    gap = 9 * mm
    right_x = margin + left_w + gap
    right_w = page_w - margin - right_x

    c.setFillColor(GREEN_2)
    c.setFont("Kestrel-Bold", 8)
    c.drawString(margin, content_top, "WHAT THE NUMBER REALLY SAYS")
    paragraph(
        c,
        "A 95% accuracy promise is the wrong board measure: saying “no return” for every order already looks 88.6% accurate and catches nothing. "
        "At the chosen line, 28% of called orders actually returned and 40% of returns were missed. That is useful for a ₹45 call; it is not safe enough for cancellation. "
        "The monthly saving also assumes the spring pilot’s 35% reduction is real—an assumption still needing a controlled test.",
        margin,
        content_top - 5 * mm,
        left_w,
        size=8.7,
        leading=12.2,
        color=INK,
    )

    rounded_card(c, right_x, content_top - 49 * mm, right_w, 49 * mm, CARD)
    c.setFillColor(AMBER)
    c.setFont("Kestrel-Bold", 8)
    c.drawString(right_x + 5 * mm, content_top - 7 * mm, "EVIDENCE BOUNDARY")
    paragraph(
        c,
        "2,126 newest-quarter orders<br/><b>245</b> actual returns<br/><b>0.758–0.815</b> AUC interval<br/><br/>Service and pickup fields were excluded: they occur after dispatch and created a fake 0.996 AUC.",
        right_x + 5 * mm,
        content_top - 11 * mm,
        right_w - 10 * mm,
        size=7.9,
        leading=11.3,
        color=INK,
    )

    next_top = content_top - 61 * mm
    c.setFillColor(GREEN_2)
    c.setFont("Kestrel-Bold", 8)
    c.drawString(margin, next_top, "WHAT TO DO NEXT WEEK")
    steps = [
        ("1", "Start a four-week controlled pilot", "Randomly split eligible flagged orders between call and business-as-usual."),
        ("2", "Protect dispatch and Shield relationships", "No hold beyond 24 hours; use service-oriented calls for Shield members."),
        ("3", "Track the outcomes that matter", "Call completion, dispatch time, cancellation, return, Shield status, and reason."),
        ("4", "Fix the upstream data", "October payment scaling, backward-moving history counters, and non-as-of customer dates."),
    ]
    y = next_top - 9 * mm
    step_w = (page_w - 2 * margin - 6 * mm) / 2
    for index, (number, title, body) in enumerate(steps):
        col = index % 2
        row = index // 2
        x = margin + col * (step_w + 6 * mm)
        y_item = y - row * 23 * mm
        c.setFillColor(LIME)
        c.circle(x + 4 * mm, y_item - 1 * mm, 4 * mm, fill=1, stroke=0)
        c.setFillColor(GREEN)
        c.setFont("Kestrel-Bold", 8)
        c.drawCentredString(x + 4 * mm, y_item - 2.4 * mm, number)
        c.setFillColor(INK)
        c.setFont("Kestrel-Bold", 8.2)
        c.drawString(x + 11 * mm, y_item + 1.2 * mm, title)
        paragraph(c, body, x + 11 * mm, y_item - 2.5 * mm, step_w - 11 * mm, size=7.3, leading=9.5, color=MUTED)

    c.setStrokeColor(LINE)
    c.line(margin, 15 * mm, page_w - margin, 15 * mm)
    c.setFillColor(MUTED)
    c.setFont("Kestrel", 6.8)
    c.drawString(margin, 10 * mm, "BACKTEST ESTIMATE, NOT GUARANTEED SAVINGS  •  DECISION SUPPORT, NOT AUTOMATED DENIAL")
    c.drawRightString(page_w - margin, 10 * mm, "Prepared for Ritu Deshpande")
    c.showPage()
    c.save()
    print(f"Saved one-page memo: {output}")


if __name__ == "__main__":
    build()
