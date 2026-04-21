import csv
import io
import re
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction

from medstratix.models import Company, CompanyType, Gene, Panel, PanelGene, SampleType


PRIMARY_ENTRY_SPLIT_PATTERN = re.compile(r"[,;\r\n\t|]+")
WHITESPACE_FALLBACK_PATTERN = re.compile(r"\s+")


def _decode_uploaded_file(uploaded_file) -> str:
    content = uploaded_file.read()
    if isinstance(content, bytes):
        return content.decode("utf-8-sig", errors="ignore")
    return str(content)


def _extract_tokens(raw_text: str) -> list[str]:
    raw_value = raw_text or ""
    tokens = []

    if PRIMARY_ENTRY_SPLIT_PATTERN.search(raw_value):
        pieces = PRIMARY_ENTRY_SPLIT_PATTERN.split(raw_value)
    else:
        pieces = WHITESPACE_FALLBACK_PATTERN.split(raw_value)

    for piece in pieces:
        token = re.sub(r"\s+", " ", piece).strip().upper()
        if not token:
            continue
        tokens.append(token)
    return tokens


def _parse_gene_payload(gene_text: str = "", gene_file=None) -> list[str]:
    chunks = []
    if gene_text:
        chunks.append(gene_text)

    if gene_file:
        file_text = _decode_uploaded_file(gene_file)
        if gene_file.name.lower().endswith(".csv"):
            reader = csv.reader(io.StringIO(file_text))
            for row in reader:
                chunks.append(",".join(row))
        else:
            chunks.append(file_text)

    seen = set()
    genes = []
    for chunk in chunks:
        for token in _extract_tokens(chunk):
            if token not in seen:
                seen.add(token)
                genes.append(token)
    return genes


def _normalize_price_to_bdt(price, price_currency: str) -> tuple[Decimal | None, str]:
    if price in (None, ""):
        return None, ""

    currency = (price_currency or "BDT").upper().strip()
    multiplier = Decimal(str(settings.PANEL_PRICE_FX.get(currency, 1)))
    normalized_price = (Decimal(price) * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    note = "Stored as BDT."
    if currency != "BDT":
        note = f"Converted from {currency} to BDT using rate {multiplier}."
    return normalized_price, note


@transaction.atomic
def save_uploaded_panel(
    *,
    company_name: str,
    company_type: str,
    panel_name: str,
    sample_type: str,
    supports_dna_ngs: bool,
    supports_rna_ngs: bool,
    supports_fusions: bool,
    supports_cnv: bool,
    supports_msi: bool,
    supports_tmb: bool,
    supports_ihc: bool,
    supports_fish: bool,
    price,
    price_currency: str,
    tat: str,
    gene_text: str = "",
    gene_file=None,
    existing_panel: Panel | None = None,
) -> dict:
    if existing_panel:
        company = existing_panel.company
        incoming_company_name = company_name.strip()
        if incoming_company_name and company.name != incoming_company_name:
            company.name = incoming_company_name
        if company.type != company_type and company_type:
            company.type = company_type
        company.save(update_fields=["name", "type", "updated_at"])
    else:
        company, _ = Company.objects.get_or_create(
            name=company_name.strip(),
            defaults={"type": company_type or CompanyType.OTHER},
        )
        if company.type != company_type and company_type:
            company.type = company_type
            company.save(update_fields=["type", "updated_at"])

    normalized_price, price_note = _normalize_price_to_bdt(price, price_currency)

    if existing_panel:
        panel = existing_panel
        created = False
        panel.company = company
        panel.name = panel_name.strip()
        panel.sample_type = sample_type or SampleType.TISSUE
        panel.supports_dna_ngs = supports_dna_ngs
        panel.supports_rna_ngs = supports_rna_ngs
        panel.supports_fusions = supports_fusions
        panel.supports_cnv = supports_cnv
        panel.supports_msi = supports_msi
        panel.supports_tmb = supports_tmb
        panel.supports_ihc = supports_ihc
        panel.supports_fish = supports_fish
        panel.price = normalized_price
        panel.tat = tat.strip()
        panel.save(
            update_fields=[
                "company",
                "name",
                "sample_type",
                "supports_dna_ngs",
                "supports_rna_ngs",
                "supports_fusions",
                "supports_cnv",
                "supports_msi",
                "supports_tmb",
                "supports_ihc",
                "supports_fish",
                "price",
                "tat",
                "updated_at",
            ]
        )
    else:
        panel, created = Panel.objects.get_or_create(
            company=company,
            name=panel_name.strip(),
            defaults={
                "sample_type": sample_type or SampleType.TISSUE,
                "supports_dna_ngs": supports_dna_ngs,
                "supports_rna_ngs": supports_rna_ngs,
                "supports_fusions": supports_fusions,
                "supports_cnv": supports_cnv,
                "supports_msi": supports_msi,
                "supports_tmb": supports_tmb,
                "supports_ihc": supports_ihc,
                "supports_fish": supports_fish,
                "price": normalized_price,
                "tat": tat.strip(),
            },
        )
        if not created:
            panel.sample_type = sample_type or SampleType.TISSUE
            panel.supports_dna_ngs = supports_dna_ngs
            panel.supports_rna_ngs = supports_rna_ngs
            panel.supports_fusions = supports_fusions
            panel.supports_cnv = supports_cnv
            panel.supports_msi = supports_msi
            panel.supports_tmb = supports_tmb
            panel.supports_ihc = supports_ihc
            panel.supports_fish = supports_fish
            panel.price = normalized_price
            panel.tat = tat.strip()
            panel.save(
                update_fields=[
                    "sample_type",
                    "supports_dna_ngs",
                    "supports_rna_ngs",
                    "supports_fusions",
                    "supports_cnv",
                    "supports_msi",
                    "supports_tmb",
                    "supports_ihc",
                    "supports_fish",
                    "price",
                    "tat",
                    "updated_at",
                ]
            )

    symbols = _parse_gene_payload(gene_text=gene_text, gene_file=gene_file)
    panel.panel_genes.all().delete()
    gene_count = 0
    for symbol in symbols:
        gene, _ = Gene.objects.get_or_create(symbol=symbol)
        PanelGene.objects.get_or_create(panel=panel, gene=gene)
        gene_count += 1

    return {
        "company": company,
        "panel": panel,
        "created": created,
        "gene_count": gene_count,
        "company_type": company.type,
        "normalized_price": normalized_price,
        "price_note": price_note,
    }
