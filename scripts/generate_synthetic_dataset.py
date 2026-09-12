"""Generate the public, synthetic document used by the deterministic benchmark."""

from pathlib import Path

from reportlab.pdfgen import canvas

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPOSITORY_ROOT / "datasets" / "samples" / "invoice_native_001.pdf"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(str(OUTPUT), invariant=1)
    document.setTitle("Synthetic Invoice Benchmark")
    lines = [
        "INVOICE",
        "Invoice Number: INV-2026-001",
        "Invoice Date: 12/09/2026",
        "Due Date: 19/09/2026",
        "Vendor: PT Contoh Nusantara",
        "Buyer: Toko Belajar AI",
        "Subtotal: Rp 100.000,00",
        "PPN: Rp 10.000,00",
        "Grand Total: Rp 110.000,00",
    ]
    y = 800
    for line in lines:
        document.drawString(60, y, line)
        y -= 28
    document.save()


if __name__ == "__main__":
    main()
