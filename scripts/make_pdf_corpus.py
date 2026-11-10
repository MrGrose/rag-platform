"""Generate the small PDF corpus with two pages per document.

Requires fpdf2 (dev tooling only). The generated files are committed so tests
and demos do not need to build them.
"""

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "corpus_pdf"

DOCS = {
    "refund-policy.pdf": (
        (
            "Refund Policy. Customers may return most items within 30 days of delivery. "
            "Items must be unused and include all accessories. "
            "Refunds are issued within 5 business days."
        ),
        (
            "Electronics are refundable within 14 days of delivery and only with the "
            "original packaging. Return shipping for a change of mind costs 9 EUR and "
            "is deducted from the refund."
        ),
    ),
    "delivery-terms.pdf": (
        (
            "Delivery Terms. Standard delivery takes 2 to 5 business days inside the EU. "
            "Orders above 75 EUR are delivered free of charge."
        ),
        (
            "Express delivery costs an extra 15 EUR and arrives within 24 hours in "
            "selected cities. We ship from the Rotterdam warehouse and do not deliver "
            "to PO boxes."
        ),
    ),
    "warranty.pdf": (
        (
            "Warranty. All hardware carries a 24 month warranty from the delivery date. "
            "The warranty covers manufacturing defects and normal battery wear."
        ),
        (
            "Repairs take up to 20 business days. If a defect repeats three times, the "
            "customer may request a replacement unit."
        ),
    ),
    "sla.pdf": (
        (
            "Service Level Agreement. The service targets 99.9 percent monthly uptime "
            "for the API. Planned maintenance is announced 72 hours in advance."
        ),
        (
            "If monthly uptime falls below 99.0 percent, the customer receives a 25 "
            "percent service credit. Credits must be requested within 30 days."
        ),
    ),
    "privacy-policy.pdf": (
        (
            "Privacy Policy. We collect account data, order history and support messages "
            "to provide the service. Payment card data is processed by the payment provider."
        ),
        (
            "Personal data is stored for 24 months after the last activity, then "
            "anonymised. Data export requests go to privacy@northwind.example."
        ),
    ),
    "support.pdf": (
        (
            "Support. Support works Monday to Friday from 09:00 to 18:00 Central "
            "European Time. Channels are email, in-app chat and the customer portal."
        ),
        (
            "Priority 1 incidents receive a first response within 1 hour. Priority 2 "
            "incidents receive a first response within 4 business hours."
        ),
    ),
}


def build(name: str, pages: tuple[str, str]) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for text in pages:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 8, text)
    pdf.output(OUT / name)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, pages in DOCS.items():
        build(name, pages)
    print(f"generated {len(DOCS)} pdf files in {OUT}")


if __name__ == "__main__":
    main()
