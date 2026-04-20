from dataclasses import dataclass

from medstratix.models import AlterationFamily


@dataclass(frozen=True)
class OntologyEntry:
    canonical_symbol: str
    aliases: tuple[str, ...]
    alteration_family: str
    category: str
    molecular_styles: tuple[str, ...] = ()


SHARED_BIOMARKER_ONTOLOGY = (
    OntologyEntry("EGFR", ("egfr", "epidermal growth factor receptor", "exon 19 deletion", "l858r", "exon 20 insertion"), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("ALK", ("alk", "alk fusion", "alk rearrangement"), AlterationFamily.FUSION, "gene"),
    OntologyEntry("ROS1", ("ros1", "ros1 fusion", "ros1 rearrangement"), AlterationFamily.FUSION, "gene"),
    OntologyEntry("BRAF", ("braf", "braf v600e"), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("KRAS", ("kras", "kras g12c"), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("NRAS", ("nras",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("MET", ("met", "met exon 14", "met exon 14 skipping"), AlterationFamily.EXON_SKIPPING, "gene"),
    OntologyEntry("RET", ("ret", "ret fusion"), AlterationFamily.FUSION, "gene"),
    OntologyEntry("ERBB2", ("erbb2", "her2", "her2-positive", "her2 amplification"), AlterationFamily.AMPLIFICATION, "gene"),
    OntologyEntry("NTRK", ("ntrk", "ntrk1", "ntrk2", "ntrk3", "trk fusion", "ntrk fusion"), AlterationFamily.FUSION, "gene"),
    OntologyEntry("PIK3CA", ("pik3ca",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("ESR1", ("esr1",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("FLT3", ("flt3", "flt3-itd", "flt3-tkd"), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("IDH1", ("idh1",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("IDH2", ("idh2",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("KIT", ("kit",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("PDGFRA", ("pdgfra",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("TP53", ("tp53",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("NPM1", ("npm1",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("BCRABL1", ("bcr-abl1", "bcr::abl1", "philadelphia chromosome", "ph-positive"), AlterationFamily.FUSION, "gene"),
    OntologyEntry("BRCA", ("brca", "brca1", "brca2"), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("PALB2", ("palb2",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("ATM", ("atm",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("FGFR3", ("fgfr", "fgfr3"), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("CLDN18", ("cldn18", "cldn18.2"), AlterationFamily.PROTEIN_OVEREXPRESSION, "protein"),
    OntologyEntry("DLL3", ("dll3",), AlterationFamily.PROTEIN_OVEREXPRESSION, "protein"),
    OntologyEntry("VHL", ("vhl",), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("TFE3", ("tfe3",), AlterationFamily.FUSION, "gene"),
    OntologyEntry("FH", ("fh", "fumarate hydratase"), AlterationFamily.MUTATION, "gene"),
    OntologyEntry("RAS", ("ras", "hras", "nras", "kras"), AlterationFamily.MUTATION, "pathway"),
    OntologyEntry("HRR", ("hrr", "homologous recombination repair", "homologous recombination deficiency", "hrd"), AlterationFamily.OTHER, "pathway"),
    OntologyEntry("MSI", ("msi", "msi-h", "mss", "dmmr", "pmmr", "mmr", "mismatch repair"), AlterationFamily.OTHER, "pan_tumor"),
    OntologyEntry("TMB", ("tmb", "tmb-h", "tumor mutational burden"), AlterationFamily.OTHER, "pan_tumor"),
    OntologyEntry("CD274", ("pd-l1", "cps"), AlterationFamily.PROTEIN_OVEREXPRESSION, "protein"),
    OntologyEntry("CD19", ("cd19",), AlterationFamily.PROTEIN_OVEREXPRESSION, "protein"),
    OntologyEntry("CD20", ("cd20",), AlterationFamily.PROTEIN_OVEREXPRESSION, "protein"),
    OntologyEntry("CD30", ("cd30",), AlterationFamily.PROTEIN_OVEREXPRESSION, "protein"),
    OntologyEntry("FOLR1", ("folr1", "folate receptor alpha", "fralpha", "fr-alpha"), AlterationFamily.PROTEIN_OVEREXPRESSION, "protein"),
    OntologyEntry("FOLH1", ("psma", "folh1", "psma-positive"), AlterationFamily.PROTEIN_OVEREXPRESSION, "protein"),
)


def find_biomarkers_in_text(text: str) -> list[OntologyEntry]:
    haystack = (text or "").lower()
    matches: list[OntologyEntry] = []
    for entry in SHARED_BIOMARKER_ONTOLOGY:
        if any(alias in haystack for alias in entry.aliases):
            matches.append(entry)
    return matches
