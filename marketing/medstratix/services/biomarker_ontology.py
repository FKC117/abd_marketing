import re
from dataclasses import dataclass

from medstratix.models import AlterationFamily


@dataclass(frozen=True)
class OntologyEntry:
    canonical_symbol: str
    aliases: tuple[str, ...]
    alteration_family: str
    category: str
    molecular_styles: tuple[str, ...] = ()
    evidence_tier: str = "unknown"

    @property
    def entity_type(self) -> str:
        return self.category


def _entry(
    canonical_symbol: str,
    alteration_family: str,
    category: str,
    aliases: tuple[str, ...] = (),
    molecular_styles: tuple[str, ...] = (),
    evidence_tier: str = "unknown",
) -> OntologyEntry:
    normalized_aliases = tuple(dict.fromkeys(alias.lower().strip() for alias in (canonical_symbol, *aliases) if alias))
    return OntologyEntry(
        canonical_symbol=canonical_symbol,
        aliases=normalized_aliases,
        alteration_family=alteration_family,
        category=category,
        molecular_styles=molecular_styles,
        evidence_tier=evidence_tier,
    )


SHARED_BIOMARKER_ONTOLOGY = (
    _entry(
        "EGFR",
        AlterationFamily.MUTATION,
        "gene",
        aliases=("epidermal growth factor receptor", "exon 19 deletion", "l858r", "exon 20 insertion", "t790m"),
        molecular_styles=("mutation_driven",),
    ),
    _entry("ALK", AlterationFamily.FUSION, "gene", aliases=("alk fusion", "alk rearrangement"), molecular_styles=("mutation_driven",)),
    _entry("ROS1", AlterationFamily.FUSION, "gene", aliases=("ros1 fusion", "ros1 rearrangement"), molecular_styles=("mutation_driven",)),
    _entry("RET", AlterationFamily.FUSION, "gene", aliases=("ret fusion",), molecular_styles=("mutation_driven",)),
    _entry("MET", AlterationFamily.EXON_SKIPPING, "gene", aliases=("met exon 14", "met exon 14 skipping"), molecular_styles=("mutation_driven",)),
    _entry("ERBB2", AlterationFamily.AMPLIFICATION, "gene", aliases=("her2", "her2-positive", "her2 amplification", "her2 overexpression"), molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("ERBB3", AlterationFamily.AMPLIFICATION, "gene", aliases=("her3",), molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("NTRK", AlterationFamily.FUSION, "gene_family", aliases=("ntrk fusion", "trk fusion"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("NTRK1", AlterationFamily.FUSION, "gene", aliases=("ntrk1 fusion", "trk-a"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("NTRK2", AlterationFamily.FUSION, "gene", aliases=("ntrk2 fusion", "trk-b"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("NTRK3", AlterationFamily.FUSION, "gene", aliases=("ntrk3 fusion", "trk-c"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("BRAF", AlterationFamily.MUTATION, "gene", aliases=("braf v600e",), molecular_styles=("mutation_driven",)),
    _entry("KRAS", AlterationFamily.MUTATION, "gene", aliases=("kras g12c", "kras g12d"), molecular_styles=("mutation_driven",)),
    _entry("NRAS", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("HRAS", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("MAP2K1", AlterationFamily.MUTATION, "gene", aliases=("mek1",), molecular_styles=("mutation_driven",)),
    _entry("MAP2K2", AlterationFamily.MUTATION, "gene", aliases=("mek2",), molecular_styles=("mutation_driven",)),
    _entry("KIT", AlterationFamily.MUTATION, "gene", aliases=("c-kit", "cd117"), molecular_styles=("mutation_driven",)),
    _entry("PDGFRA", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("FGFR1", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("FGFR2", AlterationFamily.MUTATION, "gene", aliases=("fgfr2b",), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("FGFR3", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("FGFR4", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("FGFR2 fusion", AlterationFamily.FUSION, "fusion", aliases=("fgfr2 rearrangement", "fgfr2::fusion", "fgfr2 fusion-positive"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("FGFR3 fusion", AlterationFamily.FUSION, "fusion", aliases=("fgfr3 rearrangement", "fgfr3::fusion", "fgfr3 fusion-positive"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("PIK3CA", AlterationFamily.MUTATION, "gene", molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("PIK3R1", AlterationFamily.MUTATION, "gene", molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("AKT1", AlterationFamily.MUTATION, "gene", molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("AKT2", AlterationFamily.MUTATION, "gene", molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("AKT3", AlterationFamily.MUTATION, "gene", molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("AKT2 amplification", AlterationFamily.COPY_NUMBER_GAIN, "copy_number", aliases=("akt2 amp", "akt2 copy gain"), molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("ESR1", AlterationFamily.MUTATION, "gene", molecular_styles=("subtype_driven",)),
    _entry("ERBB4", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("DDR2", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("EPHA2", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("EPHB4", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("RIT1", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("PTEN", AlterationFamily.MUTATION, "gene", molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("TP53", AlterationFamily.MUTATION, "gene"),
    _entry("CDKN2A", AlterationFamily.MUTATION, "gene", aliases=("p16",), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("RB1", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("STK11", AlterationFamily.MUTATION, "gene", aliases=("lkb1",), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("KEAP1", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("NF1", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("SMAD4", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("CTNNB1", AlterationFamily.MUTATION, "gene", aliases=("beta-catenin",), molecular_styles=("pan_tumor",)),
    _entry("FBXW7", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("ARID1A", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("CDH1", AlterationFamily.MUTATION, "gene", molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("ERCC1", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("SMARCA4", AlterationFamily.MUTATION, "gene", aliases=("brg1",), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("SMARCB1", AlterationFamily.MUTATION, "gene", aliases=("ini1", "snf5"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("NF2", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("TSC1", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("TSC2", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("MTOR", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("VHL", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("TFE3", AlterationFamily.FUSION, "gene", aliases=("tfe3 fusion",), molecular_styles=("mutation_driven",)),
    _entry("FH", AlterationFamily.MUTATION, "gene", aliases=("fumarate hydratase",), molecular_styles=("mutation_driven",)),
    _entry("BAP1", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("SDHA", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("SDHB", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("SDHC", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("SDHD", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("BCRABL1", AlterationFamily.FUSION, "gene", aliases=("bcr-abl1", "bcr::abl1", "philadelphia chromosome", "ph-positive"), molecular_styles=("hematologic_marker",)),
    _entry("FLT3", AlterationFamily.MUTATION, "gene", aliases=("flt3-itd", "flt3-tkd"), molecular_styles=("hematologic_marker",)),
    _entry("IDH1", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker", "pan_tumor")),
    _entry("IDH2", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker", "pan_tumor")),
    _entry("NPM1", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("DNMT3A", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("TET2", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("ASXL1", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("RUNX1", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("CEBPA", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("WT1", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("BCOR", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("SF3B1", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("SRSF2", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("U2AF1", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("EZH2", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker", "pan_tumor")),
    _entry("JAK2", AlterationFamily.MUTATION, "gene", aliases=("jak2 v617f",), molecular_styles=("hematologic_marker",)),
    _entry("JAK1", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("CALR", AlterationFamily.MUTATION, "gene", aliases=("calreticulin mutation",), molecular_styles=("hematologic_marker",)),
    _entry("MPL", AlterationFamily.MUTATION, "gene", aliases=("mpl mutation", "mpl w515"), molecular_styles=("hematologic_marker",)),
    _entry("BCL2", AlterationFamily.AMPLIFICATION, "gene", aliases=("bcl-2",), molecular_styles=("hematologic_marker",)),
    _entry("BCL6", AlterationFamily.AMPLIFICATION, "gene", aliases=("bcl-6",), molecular_styles=("hematologic_marker",)),
    _entry("MYC", AlterationFamily.AMPLIFICATION, "gene", aliases=("c-myc",), molecular_styles=("hematologic_marker", "pan_tumor")),
    _entry("CCND1", AlterationFamily.AMPLIFICATION, "gene", aliases=("cyclin d1",), molecular_styles=("hematologic_marker",)),
    _entry("CD79B", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("BTK", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("NOTCH1", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker", "pan_tumor")),
    _entry("MYD88", AlterationFamily.MUTATION, "gene", aliases=("myd88 l265p",), molecular_styles=("hematologic_marker",)),
    _entry("BRCA", AlterationFamily.MUTATION, "gene_family", aliases=("brca mutation", "brca pathogenic variant"), molecular_styles=("dna_repair_driven",)),
    _entry("BRCA1", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("BRCA2", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("CDK12", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("PALB2", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("ATM", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("ATR", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("ATRX", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven", "pan_tumor")),
    _entry("CHEK2", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("FANCA", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("FANCD2", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("FANCL", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("RAD51C", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("RAD51D", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("RAD50", AlterationFamily.MUTATION, "gene", molecular_styles=("dna_repair_driven",)),
    _entry("MRE11", AlterationFamily.MUTATION, "gene", aliases=("mre11a",), molecular_styles=("dna_repair_driven",)),
    _entry("MLH1", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("MSH2", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("MSH6", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("PMS2", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("POLE", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("POLD1", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("CLDN18", AlterationFamily.PROTEIN_OVEREXPRESSION, "protein", aliases=("cldn18.2",), molecular_styles=("pan_tumor",)),
    _entry("DLL3", AlterationFamily.PROTEIN_OVEREXPRESSION, "protein", molecular_styles=("pan_tumor",)),
    _entry("CD274", AlterationFamily.PROTEIN_OVEREXPRESSION, "protein", aliases=("pd-l1", "cps"), molecular_styles=("pan_tumor",)),
    _entry("B2M", AlterationFamily.MUTATION, "gene", aliases=("beta-2 microglobulin",), molecular_styles=("pan_tumor",)),
    _entry("HLA-A", AlterationFamily.OTHER, "biomarker", aliases=("hla a",), molecular_styles=("pan_tumor",)),
    _entry("HLA-B", AlterationFamily.OTHER, "biomarker", aliases=("hla b",), molecular_styles=("pan_tumor",)),
    _entry("CD19", AlterationFamily.PROTEIN_OVEREXPRESSION, "protein", molecular_styles=("hematologic_marker",)),
    _entry("CD20", AlterationFamily.PROTEIN_OVEREXPRESSION, "protein", molecular_styles=("hematologic_marker",)),
    _entry("CD30", AlterationFamily.PROTEIN_OVEREXPRESSION, "protein", molecular_styles=("hematologic_marker",)),
    _entry("FOLR1", AlterationFamily.PROTEIN_OVEREXPRESSION, "protein", aliases=("folate receptor alpha", "fralpha", "fr-alpha"), molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("FOLH1", AlterationFamily.PROTEIN_OVEREXPRESSION, "protein", aliases=("psma", "psma-positive"), molecular_styles=("dna_repair_driven", "pan_tumor")),
    _entry("TROP2", AlterationFamily.PROTEIN_OVEREXPRESSION, "protein", aliases=("trop-2", "trophoblast cell surface antigen 2"), molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("RAS", AlterationFamily.MUTATION, "pathway", aliases=("ras pathway",), molecular_styles=("mutation_driven",)),
    _entry("HRR", AlterationFamily.OTHER, "pathway", aliases=("homologous recombination repair",), molecular_styles=("dna_repair_driven",)),
    _entry("HRD", AlterationFamily.OTHER, "pathway", aliases=("homologous recombination deficiency",), molecular_styles=("dna_repair_driven",)),
    _entry("MSI", AlterationFamily.OTHER, "pan_tumor", aliases=("msi-h", "microsatellite instability"), molecular_styles=("pan_tumor",)),
    _entry("MMR", AlterationFamily.OTHER, "pathway", aliases=("dmmr", "pmmr", "mismatch repair"), molecular_styles=("pan_tumor",)),
    _entry("TMB", AlterationFamily.OTHER, "pan_tumor", aliases=("tmb-h", "tumor mutational burden"), molecular_styles=("pan_tumor",)),
    _entry("LOH score", AlterationFamily.OTHER, "genomic_signature", aliases=("loh", "loss of heterozygosity score", "genomic instability score"), molecular_styles=("dna_repair_driven",)),
    _entry("CNV burden", AlterationFamily.OTHER, "genomic_signature", aliases=("copy number burden", "copy-number burden", "cnv signature"), molecular_styles=("pan_tumor",)),
    _entry("AR", AlterationFamily.AMPLIFICATION, "gene", aliases=("androgen receptor", "ar-v7"), molecular_styles=("subtype_driven",)),
    _entry("GNAQ", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("GNA11", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("CDK4", AlterationFamily.AMPLIFICATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("NECTIN4", AlterationFamily.PROTEIN_OVEREXPRESSION, "protein", aliases=("nectin-4",), molecular_styles=("pan_tumor",)),
    _entry("MDM2", AlterationFamily.AMPLIFICATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("MDM4", AlterationFamily.AMPLIFICATION, "gene", molecular_styles=("mutation_driven",)),
    _entry("CCNE1", AlterationFamily.AMPLIFICATION, "gene", molecular_styles=("subtype_driven", "pan_tumor")),
    _entry("FGF3", AlterationFamily.AMPLIFICATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("FGF4", AlterationFamily.AMPLIFICATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("FGF19", AlterationFamily.AMPLIFICATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("MET amplification", AlterationFamily.COPY_NUMBER_GAIN, "copy_number", aliases=("met amp", "met copy gain"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("BRAF fusion", AlterationFamily.FUSION, "fusion", aliases=("braf rearrangement", "braf::fusion"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("ETV6-NTRK3", AlterationFamily.FUSION, "fusion", aliases=("etv6::ntrk3", "etv6 ntrk3"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("EWSR1 fusion", AlterationFamily.FUSION, "fusion", aliases=("ewsr1 rearrangement", "ewsr1::fusion"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("TMPRSS2-ERG", AlterationFamily.FUSION, "fusion", aliases=("tmprss2::erg", "erg fusion"), molecular_styles=("dna_repair_driven",)),
    _entry("PTPN11", AlterationFamily.MUTATION, "gene", aliases=("shp2",), molecular_styles=("pan_tumor",)),
    _entry("SMAD2", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("TCF7L2", AlterationFamily.MUTATION, "gene", aliases=("tcf4",), molecular_styles=("pan_tumor",)),
    _entry("GATA3", AlterationFamily.MUTATION, "gene", molecular_styles=("subtype_driven",)),
    _entry("TERT", AlterationFamily.MUTATION, "gene", aliases=("tert promoter", "tert promoter mutation"), molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("CIC", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("FUBP1", AlterationFamily.MUTATION, "gene", molecular_styles=("mutation_driven", "pan_tumor")),
    _entry("KMT2C", AlterationFamily.MUTATION, "gene", aliases=("mll3",), molecular_styles=("pan_tumor",)),
    _entry("KMT2D", AlterationFamily.MUTATION, "gene", aliases=("mll2",), molecular_styles=("pan_tumor",)),
    _entry("KDM6A", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("APC", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("RNF43", AlterationFamily.MUTATION, "gene", molecular_styles=("pan_tumor",)),
    _entry("HLA-C", AlterationFamily.MUTATION, "gene", aliases=("hla c",), molecular_styles=("immunotherapy_related",)),
    _entry("MET fusion", AlterationFamily.FUSION, "fusion", aliases=("met rearrangement", "met::fusion", "met fusion"), molecular_styles=("mutation_driven",)),
    _entry("SETBP1", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("CSF3R", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("IKZF1", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("PHF6", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("ETV6", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("GATA2", AlterationFamily.MUTATION, "gene", molecular_styles=("hematologic_marker",)),
    _entry("KMT2A", AlterationFamily.FUSION, "fusion", aliases=("kmt2a rearrangement", "mll rearrangement", "kmt2a fusion"), molecular_styles=("hematologic_marker",)),
    _entry("LOH", AlterationFamily.OTHER, "genomic_signature", aliases=("loss of heterozygosity", "loh score"), molecular_styles=("dna_repair_driven",)),
    _entry("Genomic instability", AlterationFamily.OTHER, "genomic_signature", aliases=("genomic instability score",), molecular_styles=("dna_repair_driven",)),
)


def _compile_alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias.lower())
    escaped = escaped.replace(r"\ ", r"\s+")
    escaped = escaped.replace(r"\-", r"[-\s]?")
    if alias and alias[0].isalnum():
        escaped = r"\b" + escaped
    if alias and alias[-1].isalnum():
        escaped = escaped + r"\b"
    return re.compile(escaped, re.IGNORECASE)


_ONTOLOGY_PATTERNS = {
    entry.canonical_symbol: tuple(_compile_alias_pattern(alias) for alias in entry.aliases)
    for entry in SHARED_BIOMARKER_ONTOLOGY
}


def find_biomarkers_in_text(text: str) -> list[OntologyEntry]:
    haystack = text or ""
    matches: list[OntologyEntry] = []
    for entry in SHARED_BIOMARKER_ONTOLOGY:
        if any(pattern.search(haystack) for pattern in _ONTOLOGY_PATTERNS[entry.canonical_symbol]):
            matches.append(entry)
    return matches


def is_fusion(entry: OntologyEntry) -> bool:
    return entry.alteration_family == AlterationFamily.FUSION
