"""Generate demo PDFs (invoice, product spec, policy) into sample_documents/.

Run once with `python sample_documents/build_demo_samples.py`. The output files
are checked into the project so a presenter doesn't have to install reportlab
just to demo uploads.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent


def _styles():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="HeaderGold",
            parent=base["Title"],
            textColor=colors.HexColor("#b8860b"),
            fontSize=22,
            spaceAfter=12,
        )
    )
    base.add(
        ParagraphStyle(
            name="SubtleSmall",
            parent=base["Normal"],
            textColor=colors.grey,
            fontSize=9,
        )
    )
    return base


# ─── 1) Invoice ────────────────────────────────────────────────────────────
def build_invoice() -> Path:
    out = OUT / "sample_invoice_shopwave.pdf"
    styles = _styles()
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    story = []

    story.append(Paragraph("ShopWave Tax Invoice", styles["HeaderGold"]))
    story.append(
        Paragraph(
            "ShopWave Retail Pvt. Ltd. · GSTIN 27ABCDE1234F1Z5 · Mumbai, IN",
            styles["SubtleSmall"],
        )
    )
    story.append(Spacer(1, 8))

    meta = [
        ["Invoice No.", "SW/2025/04-1187", "Invoice Date", date.today().isoformat()],
        ["Order ID", "SW-ORD-90213", "Payment Status", "Paid (UPI)"],
        ["Bill To", "Aarav Mehta · aarav.mehta@example.com", "Ship To", "Bandra West, Mumbai 400050"],
    ]
    t = Table(meta, colWidths=[28 * mm, 60 * mm, 28 * mm, 60 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
                ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
                ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#222")),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#eeeeee")),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 12))

    rows = [
        ["#", "Item", "SKU", "Qty", "Unit (₹)", "Total (₹)"],
        [
            "1",
            "Boult Audio Z40 Pro Wireless Earbuds",
            "BLT-Z40P-BLK",
            "1",
            "1,799.00",
            "1,799.00",
        ],
        [
            "2",
            "Anker PowerCore 10000 Power Bank",
            "ANK-PC10-WHT",
            "2",
            "1,499.00",
            "2,998.00",
        ],
        [
            "3",
            "USB-C to Lightning Cable (1m)",
            "GEN-CBL-USC-LTG",
            "1",
            "499.00",
            "499.00",
        ],
        ["", "", "", "", "Subtotal", "5,296.00"],
        ["", "", "", "", "GST @ 18%", "953.28"],
        ["", "", "", "", "Shipping", "0.00"],
        ["", "", "", "", "Grand Total", "6,249.28"],
    ]
    table = Table(
        rows,
        colWidths=[10 * mm, 70 * mm, 35 * mm, 14 * mm, 26 * mm, 26 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e1e2f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#d4af37")),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                ("GRID", (0, 0), (-1, 3), 0.25, colors.HexColor("#cccccc")),
                ("ALIGN", (3, 0), (5, -1), "RIGHT"),
                ("FONT", (4, -1), (5, -1), "Helvetica-Bold", 10),
                ("LINEABOVE", (4, -1), (5, -1), 0.5, colors.HexColor("#b8860b")),
                ("TEXTCOLOR", (4, -1), (5, -1), colors.HexColor("#b8860b")),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 14))

    story.append(
        Paragraph(
            "<b>Return policy:</b> All items eligible for return within 7 days "
            "of delivery, provided they are in original packaging and unused. "
            "Refunds processed within 5 business days to the original payment "
            "method.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "<b>Support:</b> support@shopwave.in · +91-22-4000-9912 · "
            "Mon–Sat, 9am–8pm IST",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            "This is a computer-generated invoice and does not require a "
            "signature. Goods once sold will not be exchanged outside the "
            "return window. Subject to Mumbai jurisdiction.",
            styles["SubtleSmall"],
        )
    )

    doc.build(story)
    return out


# ─── 2) Product spec sheet ────────────────────────────────────────────────
def build_spec_sheet() -> Path:
    out = OUT / "sample_product_spec_earbuds.pdf"
    styles = _styles()
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    story = []

    story.append(Paragraph("Boult Audio Z40 Pro — Product Specification", styles["HeaderGold"]))
    story.append(
        Paragraph(
            "Wireless ANC Earbuds · Model BLT-Z40P · Revision 2025-04",
            styles["SubtleSmall"],
        )
    )
    story.append(Spacer(1, 12))

    spec = [
        ["Driver", "10 mm dynamic, neodymium"],
        ["Bluetooth", "5.3 with LE Audio, dual-device pairing"],
        ["Codecs", "AAC, SBC, LC3"],
        ["ANC", "Hybrid active noise cancellation, up to 32 dB"],
        ["Battery (buds)", "55 mAh each — 8 h playback"],
        ["Battery (case)", "500 mAh — 48 h total with case"],
        ["Charging", "USB-C, fast charge (10 min → 100 min playback)"],
        ["Water rating", "IPX5 sweat/splash resistant"],
        ["Weight (each bud)", "4.6 g"],
        ["Companion app", "Boult Drive (Android / iOS)"],
        ["Warranty", "12 months manufacturer warranty"],
        ["MRP", "₹2,999"],
        ["Selling price", "₹1,799"],
    ]
    table = Table(spec, colWidths=[40 * mm, 110 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
                ("FONT", (1, 0), (1, -1), "Helvetica", 10),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#eeeeee")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Key features", styles["Heading3"]))
    for line in [
        "Studio-tuned ANC with three transparency levels (full / partial / off).",
        "Multipoint pairing — switch between phone and laptop without re-pairing.",
        "Touch controls customisable in the Boult Drive app.",
        "Low-latency gaming mode (45 ms) for mobile FPS titles.",
        "Find-my-buds via app, plus left/right pairing memory.",
    ]:
        story.append(Paragraph(f"• {line}", styles["Normal"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("In the box", styles["Heading3"]))
    for line in [
        "Z40 Pro earbuds (pair)",
        "Charging case (USB-C)",
        "USB-C cable (15 cm)",
        "Silicone tips (S / M / L)",
        "Quick-start guide & warranty card",
    ]:
        story.append(Paragraph(f"• {line}", styles["Normal"]))

    doc.build(story)
    return out


# ─── 3) Return / refund policy ────────────────────────────────────────────
def build_policy_pdf() -> Path:
    out = OUT / "sample_return_policy.pdf"
    styles = _styles()
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    story = []

    story.append(Paragraph("ShopWave Return & Refund Policy", styles["HeaderGold"]))
    story.append(
        Paragraph(
            "Effective 1 April 2025 · Version 3.2 · Applies to shopwave.in",
            styles["SubtleSmall"],
        )
    )
    story.append(Spacer(1, 12))

    sections = [
        (
            "Eligibility",
            "Most items are eligible for return within 7 days of delivery. "
            "Items must be unused, in original packaging, with all tags and "
            "accessories. Perishable goods, intimate apparel, downloadable "
            "software, and personalised products are not eligible.",
        ),
        (
            "How to initiate a return",
            "Open your order in the Orders section and tap 'Return'. Pick a "
            "reason, choose pickup or self-ship, and confirm the address. "
            "Most pin codes qualify for free reverse pickup; if not, ship the "
            "package via India Post and we will reimburse postage up to ₹150 "
            "with the original receipt.",
        ),
        (
            "Refund timelines",
            "Refunds are initiated within 24 hours of the returned item "
            "passing quality check. Once initiated, money typically reflects "
            "in 3–5 business days for UPI / wallet and 5–7 business days for "
            "card or net banking.",
        ),
        (
            "Damaged or wrong items",
            "If you receive a damaged, defective, or wrong item, raise a "
            "return within 48 hours of delivery — we will ship a replacement "
            "at no cost, or issue a full refund including shipping.",
        ),
        (
            "Exchanges",
            "Size / colour exchanges are available on fashion items where "
            "the alternate variant is in stock. The exchange is processed as "
            "a return + new shipment; you will not be charged twice.",
        ),
        (
            "Cancellations",
            "Orders can be cancelled free of charge until they are picked by "
            "the courier. After dispatch, please initiate a return once the "
            "item is delivered.",
        ),
    ]
    for heading, body in sections:
        story.append(Paragraph(heading, styles["Heading3"]))
        story.append(Paragraph(body, styles["Normal"]))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Need help?", styles["Heading3"]))
    story.append(
        Paragraph(
            "Email <b>support@shopwave.in</b> with your order ID, or call "
            "<b>+91-22-4000-9912</b> Mon–Sat, 9am–8pm IST. For escalation, "
            "ask the chat assistant to 'Escalate to Agent'.",
            styles["Normal"],
        )
    )

    doc.build(story)
    return out


# ─── 4) Plain-text invoice (lighter, for OCR/text demo) ────────────────────
def build_text_invoice() -> Path:
    out = OUT / "sample_invoice_simple.txt"
    out.write_text(
        """SHOPWAVE — TAX INVOICE
=======================
Invoice No.: SW/2025/04-1188
Invoice Date: """ + date.today().isoformat() + """
Order ID: SW-ORD-90214
Customer: Priya Sharma · priya.s@example.com
Shipping: Indiranagar, Bengaluru 560038

Line items
----------
1 × Logitech MX Master 3S Mouse        ₹  8,995.00
2 × Keychron K2 Pro Keyboard           ₹ 11,990.00  (₹5,995 ea)
1 × Pelican Laptop Sleeve (15")        ₹  1,499.00

Subtotal                               ₹ 22,484.00
GST @ 18%                              ₹  4,047.12
Shipping                               ₹      0.00
--------------------------------------------------
GRAND TOTAL                            ₹ 26,531.12

Payment: Razorpay (UPI · paid)
Return window: 7 days from delivery
Support: support@shopwave.in · +91-22-4000-9912
""",
        encoding="utf-8",
    )
    return out


# ─── 5) Markdown company brief ─────────────────────────────────────────────
def build_company_brief() -> Path:
    out = OUT / "sample_company_brief.md"
    out.write_text(
        """# LiRiS — Company Brief

LiRiS is a professional AI assistant designed for ecommerce operations
teams. It answers product questions, processes uploaded invoices and
specs, converts currency, and hands off complex queries to human agents.

## Headline capabilities
- Multilingual chat (18 languages, including Indic)
- Document Q&A over PDFs, images (OCR) and plain text
- Live ecommerce URL ingestion (Amazon search pages, direct product URLs)
- Currency conversion against live exchange rates
- WhatsApp transcript export and one-click agent escalation

## Differentiators
- Runs fully self-hosted: FastAPI backend + Streamlit UI, no external LLM
- Reuses ChromaDB for both ingested products and uploaded documents
- All sidebar tools localized in the user's chosen language

## Founding team
- Rhea Iyer — CEO & former ops lead at a top-3 Indian marketplace
- Karan Bhatt — CTO, distributed-systems background
- Maya Ahuja — Head of AI, focuses on retrieval quality and evals
""",
        encoding="utf-8",
    )
    return out


def main() -> None:
    written = [
        build_invoice(),
        build_spec_sheet(),
        build_policy_pdf(),
        build_text_invoice(),
        build_company_brief(),
    ]
    for path in written:
        print(f"wrote {path.relative_to(OUT.parent)}  ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
