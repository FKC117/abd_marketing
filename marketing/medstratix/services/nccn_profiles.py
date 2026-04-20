from dataclasses import dataclass

from medstratix.models import AlterationFamily, TestingMethodType, TherapyRole


@dataclass
class BiomarkerCatalogItem:
    gene: str
    aliases: list[str]
    alteration_family: str
    variants: list[dict]
    testing_methods: list[dict]
    therapies: list[dict]
    description: str = ""
    is_actionable: bool = True
    priority_rank: int = 0


@dataclass
class ParserProfile:
    key: str
    display_name: str
    code_family: str
    molecular_style: str
    cancer_keywords: list[str]
    preferred_section_codes: tuple[str, ...]
    catalog: list[BiomarkerCatalogItem]


NSCLC_CATALOG = [
    BiomarkerCatalogItem(
        gene="EGFR",
        aliases=["egfr", "epidermal growth factor receptor"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="Common and uncommon EGFR alterations with targeted therapy implications in advanced NSCLC.",
        variants=[
            {"label": "EGFR exon 19 deletion", "variant_type": "mutation", "line": "first-line", "stage": "advanced/metastatic"},
            {"label": "EGFR L858R", "variant_type": "mutation", "line": "first-line", "stage": "advanced/metastatic"},
            {"label": "EGFR S768I / L861Q / G719X", "variant_type": "mutation", "line": "first-line", "stage": "advanced/metastatic"},
            {"label": "EGFR exon 20 insertion", "variant_type": "mutation", "line": "subsequent", "stage": "advanced/metastatic"},
        ],
        testing_methods=[
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Broad molecular profiling is preferred for EGFR detection."},
            {"method": TestingMethodType.PLASMA, "required": False, "rank": 2, "notes": "Plasma testing may complement tissue testing when time or tissue is limited."},
        ],
        therapies=[
            {"variant": "EGFR exon 19 deletion", "name": "Osimertinib", "line": "first-line", "role": TherapyRole.PREFERRED},
            {"variant": "EGFR L858R", "name": "Osimertinib", "line": "first-line", "role": TherapyRole.PREFERRED},
            {"variant": "EGFR exon 19 deletion", "name": "Amivantamab-vmjw + lazertinib", "line": "first-line", "role": TherapyRole.PREFERRED},
            {"variant": "EGFR L858R", "name": "Amivantamab-vmjw + lazertinib", "line": "first-line", "role": TherapyRole.PREFERRED},
            {"variant": "EGFR exon 20 insertion", "name": "Amivantamab-vmjw", "line": "subsequent", "role": TherapyRole.SUBSEQUENT},
        ],
    ),
    BiomarkerCatalogItem(
        gene="ALK",
        aliases=["alk", "alk fusion", "alk rearrangement"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=20,
        description="ALK rearrangements with ALK-directed therapy implications.",
        variants=[{"label": "ALK fusion", "variant_type": "fusion", "line": "first-line", "stage": "advanced/metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Broad NGS can identify ALK rearrangements."},
            {"method": TestingMethodType.RNA_NGS, "required": False, "rank": 2, "notes": "RNA-based NGS may improve fusion detection."},
        ],
        therapies=[
            {"variant": "ALK fusion", "name": "Alectinib", "line": "first-line", "role": TherapyRole.PREFERRED},
            {"variant": "ALK fusion", "name": "Lorlatinib", "line": "first-line", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="ROS1",
        aliases=["ros1", "ros1 fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=30,
        description="ROS1 fusions with ROS1-directed therapy implications.",
        variants=[{"label": "ROS1 fusion", "variant_type": "fusion", "line": "first-line", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based NGS is useful for fusion detection."}],
        therapies=[
            {"variant": "ROS1 fusion", "name": "Entrectinib", "line": "first-line", "role": TherapyRole.PREFERRED},
            {"variant": "ROS1 fusion", "name": "Crizotinib", "line": "first-line", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="BRAF",
        aliases=["braf", "braf v600e"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=40,
        description="BRAF V600E targeted therapy eligibility.",
        variants=[{"label": "BRAF V600E", "variant_type": "mutation", "line": "first-line", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Broad DNA NGS is appropriate for BRAF mutations."}],
        therapies=[{"variant": "BRAF V600E", "name": "Dabrafenib + trametinib", "line": "first-line", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="KRAS",
        aliases=["kras", "kras g12c"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=50,
        description="KRAS G12C detection informs later-line targeted treatment options.",
        variants=[{"label": "KRAS G12C", "variant_type": "mutation", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "KRAS should be assessed as part of broad molecular profiling."}],
        therapies=[{"variant": "KRAS G12C", "name": "Sotorasib", "line": "subsequent", "role": TherapyRole.SUBSEQUENT}],
    ),
    BiomarkerCatalogItem(
        gene="MET",
        aliases=["met", "met exon 14", "c-met", "hgf receptor"],
        alteration_family=AlterationFamily.EXON_SKIPPING,
        priority_rank=60,
        description="MET exon 14 skipping and MET-directed therapies.",
        variants=[{"label": "MET exon 14 skipping", "variant_type": "exon_skipping", "line": "first-line", "stage": "advanced/metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.RNA_NGS, "required": False, "rank": 1, "notes": "RNA-based testing can support exon-skipping detection."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "DNA NGS can detect MET exon 14 alterations."},
        ],
        therapies=[{"variant": "MET exon 14 skipping", "name": "Capmatinib", "line": "first-line", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="RET",
        aliases=["ret", "ret fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=70,
        description="RET fusions with RET-directed treatment options.",
        variants=[{"label": "RET fusion", "variant_type": "fusion", "line": "first-line", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based NGS is useful for RET fusion detection."}],
        therapies=[{"variant": "RET fusion", "name": "Selpercatinib", "line": "first-line", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="ERBB2",
        aliases=["erbb2", "her2", "erb-b2"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=80,
        description="ERBB2 (HER2) mutations and HER2-directed therapy implications.",
        variants=[{"label": "ERBB2 (HER2) mutation", "variant_type": "mutation", "line": "first-line", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Broad DNA NGS is appropriate for ERBB2 mutations."}],
        therapies=[
            {"variant": "ERBB2 (HER2) mutation", "name": "Zongertinib", "line": "first-line", "role": TherapyRole.PREFERRED},
            {"variant": "ERBB2 (HER2) mutation", "name": "Sevabertinib", "line": "subsequent", "role": TherapyRole.SUBSEQUENT},
        ],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk1", "ntrk2", "ntrk3"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=90,
        description="NTRK gene fusions and TRK inhibitor relevance.",
        variants=[{"label": "NTRK1/2/3 fusion", "variant_type": "fusion", "line": "first-line", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based NGS is preferred for fusion discovery."}],
        therapies=[{"variant": "NTRK1/2/3 fusion", "name": "Larotrectinib", "line": "first-line", "role": TherapyRole.PREFERRED}],
    ),
]


BREAST_CATALOG = [
    BiomarkerCatalogItem(
        gene="ERBB2",
        aliases=["her2", "erbb2", "her2-positive"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=10,
        description="HER2 receptor status and HER2-targeted therapy relevance in breast cancer.",
        variants=[
            {"label": "HER2-positive disease", "variant_type": "protein_overexpression", "line": "systemic", "stage": "early/metastatic"},
        ],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": True, "rank": 1, "notes": "HER2 IHC is standard in breast biomarker testing."},
            {"method": TestingMethodType.FISH, "required": False, "rank": 2, "notes": "Reflex FISH may be used for equivocal HER2 IHC."},
        ],
        therapies=[
            {"variant": "HER2-positive disease", "name": "Trastuzumab deruxtecan", "line": "metastatic", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="PIK3CA",
        aliases=["pik3ca", "pik3ca activating mutation"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=20,
        description="PIK3CA activating mutations relevant in HR-positive/HER2-negative recurrent disease.",
        variants=[{"label": "PIK3CA activating mutation", "variant_type": "mutation", "line": "recurrent/metastatic", "stage": "hr-positive/her2-negative"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Somatic profiling can identify PIK3CA mutations."}],
        therapies=[
            {"variant": "PIK3CA activating mutation", "name": "Alpelisib", "line": "recurrent/metastatic", "role": TherapyRole.PREFERRED},
            {"variant": "PIK3CA activating mutation", "name": "Inavolisib", "line": "recurrent/metastatic", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
    BiomarkerCatalogItem(
        gene="ESR1",
        aliases=["esr1", "esr1 mutation"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=30,
        description="ESR1 mutation testing at progression in endocrine-treated metastatic breast cancer.",
        variants=[{"label": "ESR1 mutation", "variant_type": "mutation", "line": "progression", "stage": "recurrent/metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.PLASMA, "required": False, "rank": 1, "notes": "ctDNA is preferred for ESR1 mutation assessment at progression."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "NGS profiling can detect ESR1 mutations."},
        ],
        therapies=[
            {"variant": "ESR1 mutation", "name": "Elacestrant", "line": "recurrent/metastatic", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="BRCA",
        aliases=["brca", "brca1", "brca2", "germline brca1/2"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=40,
        description="Germline BRCA1/2 pathogenic variants relevant to PARP inhibitor eligibility.",
        variants=[{"label": "Germline BRCA1/2 pathogenic variant", "variant_type": "germline_mutation", "line": "systemic", "stage": "high-risk/recurrent"}],
        testing_methods=[{"method": TestingMethodType.OTHER, "required": True, "rank": 1, "notes": "Germline testing is relevant for BRCA1/2-associated treatment decisions."}],
        therapies=[{"variant": "Germline BRCA1/2 pathogenic variant", "name": "Olaparib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion", "ntrk gene fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=50,
        description="Rare NTRK fusions with pan-tumor TRK inhibitor relevance.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "recurrent/metastatic", "stage": "pan-tumor"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing supports rare fusion discovery."}],
        therapies=[{"variant": "NTRK fusion", "name": "Larotrectinib", "line": "recurrent/metastatic", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="RET",
        aliases=["ret", "ret fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=60,
        description="Rare RET fusions with pan-tumor treatment opportunities.",
        variants=[{"label": "RET fusion", "variant_type": "fusion", "line": "recurrent/metastatic", "stage": "pan-tumor"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing supports fusion discovery."}],
        therapies=[{"variant": "RET fusion", "name": "Selpercatinib", "line": "recurrent/metastatic", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


CERVICAL_CATALOG = [
    BiomarkerCatalogItem(
        gene="CD274",
        aliases=["pd-l1", "pd-l1 positive", "cps"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=10,
        description="PD-L1 positivity in recurrent or metastatic cervical cancer.",
        variants=[{"label": "PD-L1-positive tumor", "variant_type": "protein_expression", "line": "recurrent/metastatic", "stage": "advanced"}],
        testing_methods=[{"method": TestingMethodType.IHC, "required": True, "rank": 1, "notes": "PD-L1 testing is recommended for recurrent, progressive, or metastatic disease."}],
        therapies=[{"variant": "PD-L1-positive tumor", "name": "Pembrolizumab", "line": "recurrent/metastatic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="ERBB2",
        aliases=["her2", "her2-positive", "her2-mutant", "erbb2"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=20,
        description="HER2-positive or HER2-mutant cervical tumors may have targeted therapy options.",
        variants=[
            {"label": "HER2-positive tumor", "variant_type": "protein_overexpression", "line": "subsequent", "stage": "advanced/metastatic"},
            {"label": "HER2-mutant tumor", "variant_type": "mutation", "line": "subsequent", "stage": "advanced/metastatic"},
        ],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": True, "rank": 1, "notes": "HER2 IHC with reflex FISH for equivocal cases is recommended in advanced disease."},
            {"method": TestingMethodType.FISH, "required": False, "rank": 2, "notes": "Reflex FISH may support HER2 evaluation."},
        ],
        therapies=[
            {"variant": "HER2-positive tumor", "name": "Trastuzumab deruxtecan", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
            {"variant": "HER2-mutant tumor", "name": "Neratinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
    BiomarkerCatalogItem(
        gene="MSI",
        aliases=["msi", "msi-h", "dmrr", "mmr", "mismatch repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=30,
        description="Mismatch repair deficiency and MSI-H are pan-tumor predictive biomarkers.",
        variants=[
            {"label": "MSI-H / dMMR tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced/metastatic"},
        ],
        testing_methods=[{"method": TestingMethodType.OTHER, "required": True, "rank": 1, "notes": "MMR/MSI evaluation is part of comprehensive profiling."}],
        therapies=[{"variant": "MSI-H / dMMR tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="TMB",
        aliases=["tmb", "tmb-h", "tumor mutational burden"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=40,
        description="Tumor mutational burden-high status is a pan-tumor predictive biomarker.",
        variants=[{"label": "TMB-H tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "TMB is assessed through validated comprehensive profiling."}],
        therapies=[{"variant": "TMB-H tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion", "ntrk gene fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=50,
        description="Rare NTRK gene fusions support pan-tumor TRK inhibitor use.",
        variants=[{"label": "NTRK gene fusion-positive tumor", "variant_type": "fusion", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing helps detect rare fusions."}],
        therapies=[{"variant": "NTRK gene fusion-positive tumor", "name": "Larotrectinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="RET",
        aliases=["ret", "ret fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=60,
        description="RET gene fusion-positive tumors may be eligible for RET-targeted treatment.",
        variants=[{"label": "RET gene fusion-positive tumor", "variant_type": "fusion", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing supports RET fusion discovery."}],
        therapies=[{"variant": "RET gene fusion-positive tumor", "name": "Selpercatinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


COLORECTAL_CATALOG = [
    BiomarkerCatalogItem(
        gene="KRAS",
        aliases=["kras", "kras g12c", "ras mutation"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="RAS mutation status guides anti-EGFR therapy selection in metastatic colorectal cancer.",
        variants=[
            {"label": "KRAS mutation", "variant_type": "mutation", "line": "systemic", "stage": "metastatic"},
            {"label": "KRAS G12C", "variant_type": "mutation", "line": "subsequent", "stage": "metastatic"},
        ],
        testing_methods=[
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Comprehensive profiling should include KRAS assessment."},
        ],
        therapies=[
            {"variant": "KRAS G12C", "name": "Adagrasib + cetuximab", "line": "subsequent", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="NRAS",
        aliases=["nras", "ras mutation"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=20,
        description="NRAS mutation status is important for anti-EGFR treatment selection in metastatic colorectal cancer.",
        variants=[{"label": "NRAS mutation", "variant_type": "mutation", "line": "systemic", "stage": "metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "NRAS testing is part of broad RAS profiling."},
        ],
        therapies=[],
    ),
    BiomarkerCatalogItem(
        gene="BRAF",
        aliases=["braf", "braf v600e"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=30,
        description="BRAF V600E identifies a targeted therapy subset in metastatic colorectal cancer.",
        variants=[{"label": "BRAF V600E", "variant_type": "mutation", "line": "subsequent", "stage": "metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "BRAF status should be evaluated as part of molecular workup."},
        ],
        therapies=[
            {"variant": "BRAF V600E", "name": "Encorafenib + cetuximab", "line": "subsequent", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="ERBB2",
        aliases=["her2", "erbb2", "her2 amplification", "her2-positive"],
        alteration_family=AlterationFamily.AMPLIFICATION,
        priority_rank=40,
        description="HER2 amplification or overexpression can inform HER2-targeted treatment in RAS/BRAF wild-type colorectal disease.",
        variants=[
            {"label": "HER2 amplification", "variant_type": "amplification", "line": "subsequent", "stage": "metastatic"},
            {"label": "HER2 overexpression", "variant_type": "protein_overexpression", "line": "subsequent", "stage": "metastatic"},
        ],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "HER2 IHC may be used with confirmatory in situ methods."},
            {"method": TestingMethodType.FISH, "required": False, "rank": 2, "notes": "FISH can support HER2 amplification confirmation."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 3, "notes": "Comprehensive profiling may also identify ERBB2 amplification."},
        ],
        therapies=[
            {"variant": "HER2 amplification", "name": "Tucatinib + trastuzumab", "line": "subsequent", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="MSI",
        aliases=["msi", "msi-h", "dmmr", "mmr", "mismatch repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=50,
        description="MMR deficiency and MSI-H status are predictive biomarkers for immune checkpoint therapy in colorectal cancer.",
        variants=[{"label": "MSI-H / dMMR tumor", "variant_type": "pan-tumor_marker", "line": "systemic", "stage": "metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "MMR protein testing is commonly used to assess dMMR status."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Validated comprehensive profiling can assess MSI status."},
        ],
        therapies=[
            {"variant": "MSI-H / dMMR tumor", "name": "Pembrolizumab", "line": "systemic", "role": TherapyRole.PREFERRED},
            {"variant": "MSI-H / dMMR tumor", "name": "Nivolumab + ipilimumab", "line": "systemic", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion", "trk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=60,
        description="Rare NTRK fusions support pan-tumor TRK inhibitor use in colorectal cancers.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "subsequent", "stage": "metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing improves fusion detection."},
        ],
        therapies=[
            {"variant": "NTRK fusion", "name": "Larotrectinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
    BiomarkerCatalogItem(
        gene="RET",
        aliases=["ret", "ret fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=70,
        description="RET fusions are rare but actionable pan-tumor biomarkers in colorectal cancers.",
        variants=[{"label": "RET fusion", "variant_type": "fusion", "line": "subsequent", "stage": "metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based NGS supports rare fusion discovery."},
        ],
        therapies=[
            {"variant": "RET fusion", "name": "Selpercatinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
]


PANCREATIC_CATALOG = [
    BiomarkerCatalogItem(
        gene="BRCA",
        aliases=["brca", "brca1", "brca2", "germline brca", "somatic brca"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="BRCA1/2 alterations in pancreatic adenocarcinoma inform DNA repair-directed therapy strategies.",
        variants=[
            {"label": "BRCA1/2 pathogenic variant", "variant_type": "germline_or_somatic_mutation", "line": "maintenance", "stage": "metastatic"},
        ],
        testing_methods=[
            {"method": TestingMethodType.OTHER, "required": True, "rank": 1, "notes": "Both germline and tumor testing are relevant in pancreatic cancer."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Comprehensive tumor profiling should assess BRCA1/2."},
        ],
        therapies=[
            {"variant": "BRCA1/2 pathogenic variant", "name": "Olaparib", "line": "maintenance", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="PALB2",
        aliases=["palb2", "palb2 pathogenic variant"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=20,
        description="PALB2 alterations define a homologous recombination repair-sensitive subset in pancreatic cancer.",
        variants=[
            {"label": "PALB2 pathogenic variant", "variant_type": "germline_or_somatic_mutation", "line": "systemic", "stage": "advanced/metastatic"},
        ],
        testing_methods=[
            {"method": TestingMethodType.OTHER, "required": True, "rank": 1, "notes": "PALB2 may be found through germline or somatic testing."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Broad tumor profiling can identify PALB2 alterations."},
        ],
        therapies=[],
    ),
    BiomarkerCatalogItem(
        gene="MSI",
        aliases=["msi", "msi-h", "dmmr", "mmr", "mismatch repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=30,
        description="MSI-H or dMMR pancreatic cancer supports immune checkpoint treatment options.",
        variants=[{"label": "MSI-H / dMMR tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "MMR IHC can screen for dMMR."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Validated comprehensive profiling can identify MSI-H disease."},
        ],
        therapies=[
            {"variant": "MSI-H / dMMR tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion", "trk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=40,
        description="Rare NTRK fusions support TRK inhibitor use in pancreatic cancer.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based profiling can improve fusion detection."},
        ],
        therapies=[
            {"variant": "NTRK fusion", "name": "Larotrectinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
    BiomarkerCatalogItem(
        gene="ERBB2",
        aliases=["her2", "erbb2", "her2 amplification"],
        alteration_family=AlterationFamily.AMPLIFICATION,
        priority_rank=50,
        description="HER2 amplification is an uncommon but potentially actionable finding in pancreatic adenocarcinoma.",
        variants=[{"label": "HER2 amplification", "variant_type": "amplification", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "HER2 IHC may be paired with confirmatory testing."},
            {"method": TestingMethodType.FISH, "required": False, "rank": 2, "notes": "FISH can support amplification confirmation."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 3, "notes": "Broad tumor profiling can identify ERBB2 amplification."},
        ],
        therapies=[
            {"variant": "HER2 amplification", "name": "Trastuzumab deruxtecan", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
]


OVARIAN_CATALOG = [
    BiomarkerCatalogItem(
        gene="BRCA",
        aliases=["brca", "brca1", "brca2", "germline brca", "somatic brca"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="BRCA1/2 alterations are foundational biomarkers in epithelial ovarian cancer treatment planning.",
        variants=[
            {"label": "BRCA1/2 pathogenic variant", "variant_type": "germline_or_somatic_mutation", "line": "maintenance", "stage": "advanced"},
        ],
        testing_methods=[
            {"method": TestingMethodType.OTHER, "required": True, "rank": 1, "notes": "Germline and somatic BRCA testing are both clinically important."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Tumor profiling can identify somatic BRCA alterations."},
        ],
        therapies=[
            {"variant": "BRCA1/2 pathogenic variant", "name": "Olaparib", "line": "maintenance", "role": TherapyRole.PREFERRED},
            {"variant": "BRCA1/2 pathogenic variant", "name": "Niraparib", "line": "maintenance", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="HRD",
        aliases=["hrd", "homologous recombination deficiency", "genomic instability"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=20,
        description="HRD status informs PARP inhibitor-based maintenance therapy in ovarian cancer.",
        variants=[{"label": "HRD-positive tumor", "variant_type": "genomic_signature", "line": "maintenance", "stage": "advanced"}],
        testing_methods=[
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Validated genomic assays can define HRD-positive disease."},
        ],
        therapies=[
            {"variant": "HRD-positive tumor", "name": "Olaparib + bevacizumab", "line": "maintenance", "role": TherapyRole.PREFERRED},
            {"variant": "HRD-positive tumor", "name": "Niraparib", "line": "maintenance", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="FOLR1",
        aliases=["folr1", "folate receptor alpha", "fralpha", "fr-α"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=30,
        description="Folate receptor alpha expression supports mirvetuximab soravtansine eligibility in platinum-resistant disease.",
        variants=[{"label": "FRalpha-positive tumor", "variant_type": "protein_expression", "line": "subsequent", "stage": "platinum-resistant"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": True, "rank": 1, "notes": "FOLR1 expression is assessed by validated IHC testing."},
        ],
        therapies=[
            {"variant": "FRalpha-positive tumor", "name": "Mirvetuximab soravtansine", "line": "subsequent", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="MSI",
        aliases=["msi", "msi-h", "dmmr", "mmr", "mismatch repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=40,
        description="MSI-H or dMMR ovarian tumors represent a rare but actionable immunotherapy subset.",
        variants=[{"label": "MSI-H / dMMR tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "recurrent"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "MMR IHC can be used to assess dMMR."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Comprehensive profiling can assess MSI status."},
        ],
        therapies=[
            {"variant": "MSI-H / dMMR tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
    BiomarkerCatalogItem(
        gene="ERBB2",
        aliases=["her2", "erbb2", "her2 amplification"],
        alteration_family=AlterationFamily.AMPLIFICATION,
        priority_rank=50,
        description="HER2-positive ovarian subtypes may have HER2-directed treatment opportunities.",
        variants=[{"label": "HER2 amplification", "variant_type": "amplification", "line": "subsequent", "stage": "recurrent"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "HER2 IHC may identify overexpressing disease."},
            {"method": TestingMethodType.FISH, "required": False, "rank": 2, "notes": "FISH may confirm ERBB2 amplification."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 3, "notes": "ERBB2 amplification can also be detected by tumor profiling."},
        ],
        therapies=[
            {"variant": "HER2 amplification", "name": "Trastuzumab deruxtecan", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion", "trk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=60,
        description="Rare NTRK fusions support pan-tumor TRK inhibitor use in ovarian cancer.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "subsequent", "stage": "recurrent"}],
        testing_methods=[
            {"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing helps detect rare fusions."},
        ],
        therapies=[
            {"variant": "NTRK fusion", "name": "Larotrectinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
]


PROSTATE_CATALOG = [
    BiomarkerCatalogItem(
        gene="BRCA",
        aliases=["brca", "brca1", "brca2", "hrr", "hrr mutation"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="BRCA1/2 alterations identify a homologous recombination repair-deficient subset in advanced prostate cancer.",
        variants=[
            {"label": "BRCA1/2 pathogenic variant", "variant_type": "germline_or_somatic_mutation", "line": "subsequent", "stage": "mcrpc"},
        ],
        testing_methods=[
            {"method": TestingMethodType.OTHER, "required": True, "rank": 1, "notes": "Germline and somatic testing are both clinically relevant."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Comprehensive profiling should assess HRR genes including BRCA1/2."},
        ],
        therapies=[
            {"variant": "BRCA1/2 pathogenic variant", "name": "Olaparib", "line": "subsequent", "role": TherapyRole.PREFERRED},
            {"variant": "BRCA1/2 pathogenic variant", "name": "Talazoparib + enzalutamide", "line": "subsequent", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="ATM",
        aliases=["atm", "atm mutation", "hrr"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=20,
        description="ATM is part of the HRR testing framework in advanced prostate cancer.",
        variants=[{"label": "ATM pathogenic variant", "variant_type": "mutation", "line": "subsequent", "stage": "mcrpc"}],
        testing_methods=[
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Somatic profiling should assess ATM among HRR genes."},
        ],
        therapies=[],
    ),
    BiomarkerCatalogItem(
        gene="HRR",
        aliases=["hrr", "homologous recombination repair", "dna repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=30,
        description="Homologous recombination repair deficiency is a key molecular architecture in metastatic castration-resistant prostate cancer.",
        variants=[{"label": "HRR-deficient tumor", "variant_type": "pathway_signature", "line": "subsequent", "stage": "mcrpc"}],
        testing_methods=[
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Tumor profiling should include a validated HRR gene set."},
        ],
        therapies=[
            {"variant": "HRR-deficient tumor", "name": "Olaparib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
    BiomarkerCatalogItem(
        gene="MSI",
        aliases=["msi", "msi-h", "dmmr", "mmr", "mismatch repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=40,
        description="MSI-H or dMMR prostate cancer supports immune checkpoint therapy options.",
        variants=[{"label": "MSI-H / dMMR tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced/mcrpc"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "MMR IHC can support dMMR assessment."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Validated profiling can assess MSI-H status."},
        ],
        therapies=[
            {"variant": "MSI-H / dMMR tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="TMB",
        aliases=["tmb", "tmb-h", "tumor mutational burden"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=50,
        description="TMB-H is a pan-tumor biomarker that may be relevant in advanced prostate cancer.",
        variants=[{"label": "TMB-H tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced/mcrpc"}],
        testing_methods=[
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "TMB requires validated comprehensive genomic profiling."},
        ],
        therapies=[
            {"variant": "TMB-H tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
    BiomarkerCatalogItem(
        gene="FOLH1",
        aliases=["psma", "folh1", "psma-positive"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=60,
        description="PSMA expression supports radioligand therapy selection in advanced prostate cancer.",
        variants=[{"label": "PSMA-positive disease", "variant_type": "protein_expression", "line": "subsequent", "stage": "mcrpc"}],
        testing_methods=[
            {"method": TestingMethodType.OTHER, "required": True, "rank": 1, "notes": "PSMA-targeted imaging is used to define PSMA-positive disease."},
        ],
        therapies=[
            {"variant": "PSMA-positive disease", "name": "Lutetium Lu 177 vipivotide tetraxetan", "line": "subsequent", "role": TherapyRole.PREFERRED},
        ],
    ),
]


AML_CATALOG = [
    BiomarkerCatalogItem(
        gene="FLT3",
        aliases=["flt3", "flt3-itd", "flt3-tkd"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="FLT3 alterations are foundational therapeutic biomarkers in AML.",
        variants=[
            {"label": "FLT3 mutation", "variant_type": "mutation", "line": "induction", "stage": "newly diagnosed/refractory"},
        ],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "FLT3 testing should be available rapidly at diagnosis and relapse."}],
        therapies=[
            {"variant": "FLT3 mutation", "name": "Midostaurin", "line": "induction", "role": TherapyRole.PREFERRED},
            {"variant": "FLT3 mutation", "name": "Gilteritinib", "line": "relapsed/refractory", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="IDH1",
        aliases=["idh1"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=20,
        description="IDH1 mutations identify a targetable AML subset.",
        variants=[{"label": "IDH1 mutation", "variant_type": "mutation", "line": "systemic", "stage": "newly diagnosed/refractory"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "AML molecular profiling should include IDH1 status."}],
        therapies=[{"variant": "IDH1 mutation", "name": "Ivosidenib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="IDH2",
        aliases=["idh2"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=30,
        description="IDH2 mutations identify a targetable AML subset.",
        variants=[{"label": "IDH2 mutation", "variant_type": "mutation", "line": "systemic", "stage": "relapsed/refractory"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "AML molecular profiling should include IDH2 status."}],
        therapies=[{"variant": "IDH2 mutation", "name": "Enasidenib", "line": "relapsed/refractory", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="KIT",
        aliases=["kit", "cbf-aml"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=40,
        description="KIT mutations can modify risk interpretation in core-binding factor AML.",
        variants=[{"label": "KIT mutation", "variant_type": "mutation", "line": "risk stratification", "stage": "cbf-aml"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "KIT is part of AML molecular risk workup."}],
        therapies=[],
    ),
    BiomarkerCatalogItem(
        gene="NPM1",
        aliases=["npm1"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=50,
        description="NPM1 is a key diagnostic and prognostic AML marker.",
        variants=[{"label": "NPM1 mutation", "variant_type": "mutation", "line": "risk stratification", "stage": "aml"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Molecular profiling should include NPM1 at diagnosis."}],
        therapies=[],
    ),
    BiomarkerCatalogItem(
        gene="TP53",
        aliases=["tp53"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=60,
        description="TP53 alterations define a high-risk AML subset.",
        variants=[{"label": "TP53 mutation", "variant_type": "mutation", "line": "risk stratification", "stage": "aml"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "TP53 assessment is part of modern AML molecular workup."}],
        therapies=[],
    ),
]


BLADDER_CATALOG = [
    BiomarkerCatalogItem(
        gene="FGFR3",
        aliases=["fgfr", "fgfr3"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="FGFR alterations define a targetable subset in advanced urothelial cancer.",
        variants=[{"label": "FGFR alteration", "variant_type": "mutation_or_fusion", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Comprehensive genomic profiling can identify FGFR alterations."}],
        therapies=[{"variant": "FGFR alteration", "name": "Erdafitinib", "line": "subsequent", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="ERBB2",
        aliases=["her2", "erbb2", "her2-positive"],
        alteration_family=AlterationFamily.AMPLIFICATION,
        priority_rank=20,
        description="HER2-positive urothelial tumors may support HER2-directed therapy approaches.",
        variants=[{"label": "HER2-positive tumor", "variant_type": "amplification_or_overexpression", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "HER2 IHC can help identify overexpressing tumors."},
            {"method": TestingMethodType.FISH, "required": False, "rank": 2, "notes": "FISH may confirm HER2 amplification."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 3, "notes": "Tumor profiling can capture ERBB2 amplification or mutation."},
        ],
        therapies=[{"variant": "HER2-positive tumor", "name": "Trastuzumab deruxtecan", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="MSI",
        aliases=["msi", "msi-h", "mmr", "dmmr", "mismatch repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=30,
        description="MSI-H or dMMR urothelial cancer represents a rare but actionable biomarker group.",
        variants=[{"label": "MSI-H / dMMR tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "MMR IHC may support dMMR detection."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Comprehensive profiling can define MSI-H disease."},
        ],
        therapies=[{"variant": "MSI-H / dMMR tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


KIDNEY_CATALOG = [
    BiomarkerCatalogItem(
        gene="VHL",
        aliases=["vhl"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="VHL pathway biology underlies clear cell RCC and targeted therapy selection.",
        variants=[{"label": "VHL alteration", "variant_type": "mutation", "line": "systemic", "stage": "clear cell"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": False, "rank": 1, "notes": "VHL testing is more biologic-context than routine universal selection."}],
        therapies=[],
    ),
    BiomarkerCatalogItem(
        gene="MET",
        aliases=["met", "papillary", "met-driven"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=20,
        description="MET alterations are relevant in papillary renal cell carcinoma.",
        variants=[{"label": "MET alteration", "variant_type": "mutation_or_amplification", "line": "systemic", "stage": "papillary rcc"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Genomic profiling can identify MET-driven papillary RCC."}],
        therapies=[{"variant": "MET alteration", "name": "Cabozantinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="TFE3",
        aliases=["tfe3", "translocation"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=30,
        description="TFE3 rearrangements define translocation-associated RCC.",
        variants=[{"label": "TFE3 rearranged tumor", "variant_type": "fusion", "line": "classification", "stage": "translocation rcc"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "IHC may support translocation RCC workup."},
            {"method": TestingMethodType.FISH, "required": False, "rank": 2, "notes": "FISH can confirm TFE3 rearrangement."},
        ],
        therapies=[],
    ),
    BiomarkerCatalogItem(
        gene="FH",
        aliases=["fh", "fumarate hydratase"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=40,
        description="FH-deficient RCC is a distinctive hereditary and aggressive kidney cancer subset.",
        variants=[{"label": "FH-deficient tumor", "variant_type": "mutation", "line": "classification", "stage": "hereditary rcc"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "FH alterations are identified through hereditary/tumor genomic assessment."}],
        therapies=[],
    ),
]


THYROID_CATALOG = [
    BiomarkerCatalogItem(
        gene="BRAF",
        aliases=["braf", "braf v600e"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="BRAF V600E is a central targeted biomarker in advanced thyroid cancer.",
        variants=[{"label": "BRAF V600E", "variant_type": "mutation", "line": "systemic", "stage": "advanced/anaplastic"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Thyroid cancer molecular profiling should include BRAF status."}],
        therapies=[{"variant": "BRAF V600E", "name": "Dabrafenib + trametinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="RET",
        aliases=["ret", "ret fusion", "ret mutation"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=20,
        description="RET-altered thyroid cancers support RET-directed therapy.",
        variants=[
            {"label": "RET fusion", "variant_type": "fusion", "line": "systemic", "stage": "advanced thyroid"},
            {"label": "RET mutation", "variant_type": "mutation", "line": "systemic", "stage": "medullary thyroid"},
        ],
        testing_methods=[
            {"method": TestingMethodType.RNA_NGS, "required": False, "rank": 1, "notes": "RNA-based testing helps identify RET fusions."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "DNA profiling can identify RET mutations and some rearrangements."},
        ],
        therapies=[{"variant": "RET fusion", "name": "Selpercatinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=30,
        description="NTRK fusions are rare but highly actionable in thyroid cancer.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "systemic", "stage": "advanced thyroid"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based profiling supports fusion discovery."}],
        therapies=[{"variant": "NTRK fusion", "name": "Larotrectinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="RAS",
        aliases=["ras", "hras", "nras", "kras"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=40,
        description="RAS mutations are common thyroid molecular findings with diagnostic and therapeutic relevance.",
        variants=[{"label": "RAS mutation", "variant_type": "mutation", "line": "molecular classification", "stage": "thyroid"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Targeted panels frequently include RAS genes in thyroid testing."}],
        therapies=[],
    ),
    BiomarkerCatalogItem(
        gene="TMB",
        aliases=["tmb", "tmb-h", "msi", "msi-h"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=50,
        description="TMB-H or MSI-H represent rare pan-tumor biomarkers in advanced thyroid cancer.",
        variants=[{"label": "TMB-H / MSI-H tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced thyroid"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Validated comprehensive profiling can identify TMB-H or MSI-H disease."}],
        therapies=[{"variant": "TMB-H / MSI-H tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


UTERINE_CATALOG = [
    BiomarkerCatalogItem(
        gene="ERBB2",
        aliases=["her2", "erbb2", "her2-positive"],
        alteration_family=AlterationFamily.AMPLIFICATION,
        priority_rank=10,
        description="HER2-positive uterine serous and other high-risk uterine cancers may benefit from HER2-directed therapy.",
        variants=[{"label": "HER2-positive tumor", "variant_type": "amplification_or_overexpression", "line": "systemic", "stage": "advanced/recurrent"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": True, "rank": 1, "notes": "HER2 IHC is commonly used in uterine cancer biomarker assessment."},
            {"method": TestingMethodType.FISH, "required": False, "rank": 2, "notes": "FISH can support equivocal HER2 testing."},
        ],
        therapies=[
            {"variant": "HER2-positive tumor", "name": "Trastuzumab", "line": "systemic", "role": TherapyRole.PREFERRED},
            {"variant": "HER2-positive tumor", "name": "Trastuzumab deruxtecan", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES},
        ],
    ),
    BiomarkerCatalogItem(
        gene="MSI",
        aliases=["msi", "msi-h", "mmr", "dmmr", "mismatch repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=20,
        description="MSI-H or dMMR is a key immunotherapy biomarker in recurrent uterine cancer.",
        variants=[{"label": "MSI-H / dMMR tumor", "variant_type": "pan-tumor_marker", "line": "systemic", "stage": "advanced/recurrent"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "MMR IHC is standard for dMMR assessment."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Comprehensive profiling can identify MSI-H disease."},
        ],
        therapies=[{"variant": "MSI-H / dMMR tumor", "name": "Pembrolizumab", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="TMB",
        aliases=["tmb", "tmb-h"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=30,
        description="TMB-H is a pan-tumor biomarker relevant in advanced uterine cancer.",
        variants=[{"label": "TMB-H tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced/recurrent"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Validated comprehensive profiling is required for TMB assessment."}],
        therapies=[{"variant": "TMB-H tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=40,
        description="Rare NTRK fusions support TRK inhibitor use in uterine cancer.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "subsequent", "stage": "advanced/recurrent"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing improves fusion discovery."}],
        therapies=[{"variant": "NTRK fusion", "name": "Larotrectinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="BRCA",
        aliases=["brca", "hrd"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=50,
        description="BRCA or HRD-like biology may inform selected uterine cancer treatment strategies in emerging contexts.",
        variants=[{"label": "BRCA/HRD-associated tumor", "variant_type": "dna_repair_signature", "line": "selected", "stage": "advanced/recurrent"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": False, "rank": 1, "notes": "DNA repair pathway profiling may be informative in selected cases."}],
        therapies=[],
    ),
]


UPPER_GI_CATALOG = [
    BiomarkerCatalogItem(
        gene="ERBB2",
        aliases=["her2", "erbb2", "her2-positive"],
        alteration_family=AlterationFamily.AMPLIFICATION,
        priority_rank=10,
        description="HER2-positive gastric and esophageal adenocarcinomas support HER2-directed systemic therapy.",
        variants=[{"label": "HER2-positive tumor", "variant_type": "amplification_or_overexpression", "line": "systemic", "stage": "advanced/metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": True, "rank": 1, "notes": "HER2 IHC is standard in upper GI biomarker workup."},
            {"method": TestingMethodType.FISH, "required": False, "rank": 2, "notes": "FISH may confirm equivocal HER2 testing."},
        ],
        therapies=[
            {"variant": "HER2-positive tumor", "name": "Trastuzumab", "line": "systemic", "role": TherapyRole.PREFERRED},
            {"variant": "HER2-positive tumor", "name": "Trastuzumab deruxtecan", "line": "subsequent", "role": TherapyRole.PREFERRED},
        ],
    ),
    BiomarkerCatalogItem(
        gene="CLDN18",
        aliases=["cldn18", "cldn18.2"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=20,
        description="CLDN18.2-positive disease supports zolbetuximab-based therapy in upper GI cancers.",
        variants=[{"label": "CLDN18.2-positive tumor", "variant_type": "protein_expression", "line": "first-line", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.IHC, "required": True, "rank": 1, "notes": "Validated IHC is used to assess CLDN18.2 expression."}],
        therapies=[{"variant": "CLDN18.2-positive tumor", "name": "Zolbetuximab", "line": "first-line", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="CD274",
        aliases=["pd-l1", "cps"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=30,
        description="PD-L1 expression helps guide immunotherapy use in upper GI cancers.",
        variants=[{"label": "PD-L1-positive tumor", "variant_type": "protein_expression", "line": "systemic", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.IHC, "required": True, "rank": 1, "notes": "PD-L1 is assessed by validated IHC with CPS scoring."}],
        therapies=[{"variant": "PD-L1-positive tumor", "name": "Pembrolizumab", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="MSI",
        aliases=["msi", "msi-h", "mmr", "dmmr", "mismatch repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=40,
        description="MSI-H or dMMR upper GI cancers support immunotherapy-based strategies.",
        variants=[{"label": "MSI-H / dMMR tumor", "variant_type": "pan-tumor_marker", "line": "systemic", "stage": "advanced/metastatic"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "MMR IHC can help identify dMMR tumors."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Comprehensive profiling may identify MSI-H disease."},
        ],
        therapies=[{"variant": "MSI-H / dMMR tumor", "name": "Pembrolizumab", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=50,
        description="Rare NTRK fusions are actionable in upper GI cancers.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing supports fusion detection."}],
        therapies=[{"variant": "NTRK fusion", "name": "Larotrectinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="RET",
        aliases=["ret", "ret fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=60,
        description="RET fusions are rare but actionable pan-tumor biomarkers in upper GI cancers.",
        variants=[{"label": "RET fusion", "variant_type": "fusion", "line": "subsequent", "stage": "advanced/metastatic"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based profiling supports RET fusion detection."}],
        therapies=[{"variant": "RET fusion", "name": "Selpercatinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


HCC_CATALOG = [
    BiomarkerCatalogItem(
        gene="MSI",
        aliases=["msi", "msi-h", "mmr", "dmmr", "mismatch repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=10,
        description="MSI-H or dMMR hepatocellular carcinoma is rare but actionable.",
        variants=[{"label": "MSI-H / dMMR tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "MMR IHC may be used to screen for dMMR."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Comprehensive profiling can identify MSI-H disease."},
        ],
        therapies=[{"variant": "MSI-H / dMMR tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="TMB",
        aliases=["tmb", "tmb-h"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=20,
        description="TMB-H is a rare pan-tumor biomarker that may inform immunotherapy selection in HCC.",
        variants=[{"label": "TMB-H tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Validated comprehensive profiling is needed for TMB assessment."}],
        therapies=[{"variant": "TMB-H tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=30,
        description="Rare NTRK fusions may open pan-tumor targeted options in HCC.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "subsequent", "stage": "advanced"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing supports fusion detection."}],
        therapies=[{"variant": "NTRK fusion", "name": "Larotrectinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


NEUROENDOCRINE_CATALOG = [
    BiomarkerCatalogItem(
        gene="MSI",
        aliases=["msi", "msi-h", "mmr", "dmmr", "mismatch repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=10,
        description="MSI-H or dMMR neuroendocrine neoplasms support immunotherapy in selected settings.",
        variants=[{"label": "MSI-H / dMMR tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "MMR IHC may support dMMR detection."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Comprehensive profiling can identify MSI-H disease."},
        ],
        therapies=[{"variant": "MSI-H / dMMR tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="TMB",
        aliases=["tmb", "tmb-h"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=20,
        description="TMB-H is a rare predictive biomarker in advanced neuroendocrine neoplasms.",
        variants=[{"label": "TMB-H tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Validated comprehensive profiling is required for TMB assessment."}],
        therapies=[{"variant": "TMB-H tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="BRAF",
        aliases=["braf", "braf v600e"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=30,
        description="BRAF V600E can define a targeted subset among selected neuroendocrine carcinomas.",
        variants=[{"label": "BRAF V600E", "variant_type": "mutation", "line": "subsequent", "stage": "advanced"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Tumor profiling can identify BRAF-mutant disease."}],
        therapies=[{"variant": "BRAF V600E", "name": "Dabrafenib + trametinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=40,
        description="Rare NTRK fusions support pan-tumor TRK inhibitor use in neuroendocrine neoplasms.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "subsequent", "stage": "advanced"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing improves fusion detection."}],
        therapies=[{"variant": "NTRK fusion", "name": "Larotrectinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


SCLC_CATALOG = [
    BiomarkerCatalogItem(
        gene="DLL3",
        aliases=["dll3"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=10,
        description="DLL3 is an emerging therapeutic target in small cell lung cancer.",
        variants=[{"label": "DLL3-positive tumor", "variant_type": "protein_expression", "line": "subsequent", "stage": "extensive-stage/recurrent"}],
        testing_methods=[{"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "DLL3 expression can be assessed in research or targeted-therapy contexts."}],
        therapies=[{"variant": "DLL3-positive tumor", "name": "Tarlatamab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


PAN_TUMOR_SOLID_CATALOG = [
    BiomarkerCatalogItem(
        gene="MSI",
        aliases=["msi", "msi-h", "mmr", "dmmr", "mismatch repair"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=10,
        description="MSI-H or dMMR is a reusable pan-tumor immunotherapy biomarker across solid tumors.",
        variants=[{"label": "MSI-H / dMMR tumor", "variant_type": "pan-tumor_marker", "line": "systemic", "stage": "advanced/recurrent"}],
        testing_methods=[
            {"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "MMR IHC may be used to identify dMMR."},
            {"method": TestingMethodType.DNA_NGS, "required": True, "rank": 2, "notes": "Validated genomic profiling can identify MSI-H disease."},
        ],
        therapies=[{"variant": "MSI-H / dMMR tumor", "name": "Pembrolizumab", "line": "systemic", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="TMB",
        aliases=["tmb", "tmb-h"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=20,
        description="TMB-H is a reusable pan-tumor biomarker in selected advanced solid tumors.",
        variants=[{"label": "TMB-H tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced/recurrent"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Validated comprehensive profiling is required for TMB assessment."}],
        therapies=[{"variant": "TMB-H tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=30,
        description="Rare NTRK fusions are actionable across multiple solid-tumor families.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "subsequent", "stage": "advanced/recurrent"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing improves fusion discovery."}],
        therapies=[{"variant": "NTRK fusion", "name": "Larotrectinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="RET",
        aliases=["ret", "ret fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=40,
        description="RET fusions are rare but actionable across multiple solid tumors.",
        variants=[{"label": "RET fusion", "variant_type": "fusion", "line": "subsequent", "stage": "advanced/recurrent"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing supports RET fusion discovery."}],
        therapies=[{"variant": "RET fusion", "name": "Selpercatinib", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


SARCOMA_CATALOG = [
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=10,
        description="NTRK fusions define an actionable subset in selected sarcomas and bone/soft tissue tumors.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "systemic", "stage": "advanced/unresectable"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing supports sarcoma fusion discovery."}],
        therapies=[{"variant": "NTRK fusion", "name": "Larotrectinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="TMB",
        aliases=["tmb", "tmb-h"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=20,
        description="TMB-H is an occasional pan-tumor biomarker in sarcoma-family tumors.",
        variants=[{"label": "TMB-H tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Validated comprehensive profiling is needed for TMB assessment."}],
        therapies=[{"variant": "TMB-H tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


SKIN_CATALOG = [
    BiomarkerCatalogItem(
        gene="BRAF",
        aliases=["braf", "braf v600e"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="BRAF V600E is a cornerstone targeted biomarker in melanoma-family skin cancers.",
        variants=[{"label": "BRAF V600E", "variant_type": "mutation", "line": "systemic", "stage": "advanced/unresectable"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Molecular profiling should assess BRAF status."}],
        therapies=[{"variant": "BRAF V600E", "name": "Dabrafenib + trametinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="CD274",
        aliases=["pd-l1", "cps"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=20,
        description="PD-L1 expression is a recurring immunotherapy biomarker across multiple skin cancers.",
        variants=[{"label": "PD-L1-positive tumor", "variant_type": "protein_expression", "line": "systemic", "stage": "advanced/recurrent"}],
        testing_methods=[{"method": TestingMethodType.IHC, "required": False, "rank": 1, "notes": "PD-L1 IHC may support immunotherapy selection in selected settings."}],
        therapies=[{"variant": "PD-L1-positive tumor", "name": "Pembrolizumab", "line": "systemic", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="TMB",
        aliases=["tmb", "tmb-h"],
        alteration_family=AlterationFamily.OTHER,
        priority_rank=30,
        description="TMB-H is occasionally relevant in selected skin cancers.",
        variants=[{"label": "TMB-H tumor", "variant_type": "pan-tumor_marker", "line": "subsequent", "stage": "advanced"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Comprehensive profiling can identify TMB-H disease."}],
        therapies=[{"variant": "TMB-H tumor", "name": "Pembrolizumab", "line": "subsequent", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


CNS_CATALOG = [
    BiomarkerCatalogItem(
        gene="BRAF",
        aliases=["braf", "braf v600e"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="BRAF V600E is a recurrent actionable biomarker in selected CNS tumors.",
        variants=[{"label": "BRAF V600E", "variant_type": "mutation", "line": "systemic", "stage": "recurrent/progressive"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "CNS molecular profiling should include BRAF in relevant entities."}],
        therapies=[{"variant": "BRAF V600E", "name": "Dabrafenib + trametinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=20,
        description="NTRK fusions are actionable across selected adult and pediatric CNS tumors.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "systemic", "stage": "recurrent/progressive"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based fusion testing is helpful for CNS tumors."}],
        therapies=[{"variant": "NTRK fusion", "name": "Larotrectinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
]


GIST_CATALOG = [
    BiomarkerCatalogItem(
        gene="KIT",
        aliases=["kit"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="KIT mutation status underpins standard targeted therapy selection in GIST.",
        variants=[{"label": "KIT mutation", "variant_type": "mutation", "line": "systemic", "stage": "advanced/unresectable"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Mutational analysis should include KIT in GIST."}],
        therapies=[{"variant": "KIT mutation", "name": "Imatinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="PDGFRA",
        aliases=["pdgfra", "pdgfra d842v"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=20,
        description="PDGFRA alterations define a distinct targeted subset in GIST.",
        variants=[{"label": "PDGFRA mutation", "variant_type": "mutation", "line": "systemic", "stage": "advanced/unresectable"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Mutational analysis should include PDGFRA in GIST."}],
        therapies=[{"variant": "PDGFRA mutation", "name": "Avapritinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
]


LYMPHOID_CATALOG = [
    BiomarkerCatalogItem(
        gene="CD20",
        aliases=["cd20"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=10,
        description="CD20 is a defining surface target across many B-cell malignancies.",
        variants=[{"label": "CD20-positive disease", "variant_type": "protein_expression", "line": "systemic", "stage": "lymphoid"}],
        testing_methods=[{"method": TestingMethodType.IHC, "required": True, "rank": 1, "notes": "Immunophenotyping defines CD20 expression."}],
        therapies=[{"variant": "CD20-positive disease", "name": "Rituximab", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
]


HODGKIN_CATALOG = [
    BiomarkerCatalogItem(
        gene="CD30",
        aliases=["cd30"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=10,
        description="CD30 is the classic targetable marker in Hodgkin lymphoma.",
        variants=[{"label": "CD30-positive disease", "variant_type": "protein_expression", "line": "systemic", "stage": "hodgkin lymphoma"}],
        testing_methods=[{"method": TestingMethodType.IHC, "required": True, "rank": 1, "notes": "Immunophenotyping defines CD30 expression."}],
        therapies=[{"variant": "CD30-positive disease", "name": "Brentuximab vedotin", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
]


ALL_CATALOG = [
    BiomarkerCatalogItem(
        gene="BCRABL1",
        aliases=["bcr-abl1", "bcr::abl1", "ph-positive", "philadelphia chromosome"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=10,
        description="BCR::ABL1-positive ALL defines a targeted therapeutic subset.",
        variants=[{"label": "BCR::ABL1-positive disease", "variant_type": "fusion", "line": "systemic", "stage": "all"}],
        testing_methods=[
            {"method": TestingMethodType.RTPCR, "required": True, "rank": 1, "notes": "Rapid molecular testing is important for Ph-positive ALL."},
            {"method": TestingMethodType.DNA_NGS, "required": False, "rank": 2, "notes": "Genomic profiling may support broader risk classification."},
        ],
        therapies=[{"variant": "BCR::ABL1-positive disease", "name": "Ponatinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="CD19",
        aliases=["cd19"],
        alteration_family=AlterationFamily.PROTEIN_OVEREXPRESSION,
        priority_rank=20,
        description="CD19 is a key targetable lineage marker in B-cell ALL.",
        variants=[{"label": "CD19-positive disease", "variant_type": "protein_expression", "line": "relapsed/refractory", "stage": "all"}],
        testing_methods=[{"method": TestingMethodType.IHC, "required": True, "rank": 1, "notes": "Immunophenotyping defines CD19 expression."}],
        therapies=[{"variant": "CD19-positive disease", "name": "Blinatumomab", "line": "relapsed/refractory", "role": TherapyRole.PREFERRED}],
    ),
]


HISTIOCYTIC_CATALOG = [
    BiomarkerCatalogItem(
        gene="BRAF",
        aliases=["braf", "braf v600e"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="BRAF V600E is a central targetable biomarker in several histiocytic neoplasms.",
        variants=[{"label": "BRAF V600E", "variant_type": "mutation", "line": "systemic", "stage": "histiocytic neoplasm"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Molecular workup should assess BRAF status."}],
        therapies=[{"variant": "BRAF V600E", "name": "Dabrafenib + trametinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
    BiomarkerCatalogItem(
        gene="ALK",
        aliases=["alk", "alk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=20,
        description="ALK rearrangements can define a targetable subset in histiocytic neoplasms.",
        variants=[{"label": "ALK fusion", "variant_type": "fusion", "line": "systemic", "stage": "histiocytic neoplasm"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing supports fusion discovery."}],
        therapies=[{"variant": "ALK fusion", "name": "Alectinib", "line": "systemic", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
]


PEDIATRIC_SOLID_CATALOG = [
    BiomarkerCatalogItem(
        gene="ALK",
        aliases=["alk", "alk mutation"],
        alteration_family=AlterationFamily.MUTATION,
        priority_rank=10,
        description="ALK is a key targeted biomarker in selected pediatric solid tumors such as neuroblastoma.",
        variants=[{"label": "ALK alteration", "variant_type": "mutation", "line": "relapsed/refractory", "stage": "pediatric solid tumor"}],
        testing_methods=[{"method": TestingMethodType.DNA_NGS, "required": True, "rank": 1, "notes": "Genomic profiling can identify ALK-driven tumors."}],
        therapies=[{"variant": "ALK alteration", "name": "Lorlatinib", "line": "relapsed/refractory", "role": TherapyRole.USEFUL_IN_CIRCUMSTANCES}],
    ),
    BiomarkerCatalogItem(
        gene="NTRK",
        aliases=["ntrk", "ntrk fusion"],
        alteration_family=AlterationFamily.FUSION,
        priority_rank=20,
        description="NTRK fusions are actionable across multiple pediatric solid tumors.",
        variants=[{"label": "NTRK fusion", "variant_type": "fusion", "line": "systemic", "stage": "pediatric solid tumor"}],
        testing_methods=[{"method": TestingMethodType.RNA_NGS, "required": True, "rank": 1, "notes": "RNA-based testing supports fusion discovery."}],
        therapies=[{"variant": "NTRK fusion", "name": "Larotrectinib", "line": "systemic", "role": TherapyRole.PREFERRED}],
    ),
]


PROFILES = {
    "NSCL": ParserProfile(
        key="nscl",
        display_name="NCCN NSCLC Mutation-Driven Profile",
        code_family="NSCL",
        molecular_style="mutation_driven",
        cancer_keywords=["nscl", "non-small cell lung", "non small cell lung"],
        preferred_section_codes=("NSCL-H", "NSCL-J", "NSCL-19", "NSCL-20"),
        catalog=NSCLC_CATALOG,
    ),
    "BINV": ParserProfile(
        key="breast",
        display_name="NCCN Breast Subtype-Driven Profile",
        code_family="BINV",
        molecular_style="subtype_driven",
        cancer_keywords=["breast", "binv"],
        preferred_section_codes=("BINV-A", "BINV-Q", "BINV-18", "BINV-21"),
        catalog=BREAST_CATALOG,
    ),
    "CERV": ParserProfile(
        key="cervical",
        display_name="NCCN Cervical Pan-Tumor Biomarker Profile",
        code_family="CERV",
        molecular_style="pan_tumor",
        cancer_keywords=["cervical", "cerv"],
        preferred_section_codes=("CERV-A", "CERV-F", "CERV-12"),
        catalog=CERVICAL_CATALOG,
    ),
    "COL": ParserProfile(
        key="colon",
        display_name="NCCN Colon Molecular-Directed Profile",
        code_family="COL",
        molecular_style="mutation_driven",
        cancer_keywords=["colon", "col"],
        preferred_section_codes=("COL-A", "COL-B", "COL-C", "COL-D", "COL-12", "COL-13", "COL-14", "COL-15", "COL-16"),
        catalog=COLORECTAL_CATALOG,
    ),
    "REC": ParserProfile(
        key="rectal",
        display_name="NCCN Rectal Molecular-Directed Profile",
        code_family="REC",
        molecular_style="mutation_driven",
        cancer_keywords=["rectal", "rec"],
        preferred_section_codes=("REC-A", "REC-B", "REC-C", "REC-D", "REC-12", "REC-14", "REC-15", "REC-17", "REC-18"),
        catalog=COLORECTAL_CATALOG,
    ),
    "PANC": ParserProfile(
        key="pancreatic",
        display_name="NCCN Pancreatic DNA-Repair Profile",
        code_family="PANC",
        molecular_style="dna_repair_driven",
        cancer_keywords=["pancreatic", "pancreas", "panc"],
        preferred_section_codes=("PANC-A", "PANC-B", "PANC-C", "PANC-D", "PANC-9", "PANC-10", "PANC-10A", "PANC-11", "PANC-12"),
        catalog=PANCREATIC_CATALOG,
    ),
    "LCOC": ParserProfile(
        key="ovarian",
        display_name="NCCN Ovarian HRD-Directed Profile",
        code_family="LCOC",
        molecular_style="subtype_driven",
        cancer_keywords=["ovarian", "fallopian", "primary peritoneal", "lcoc"],
        preferred_section_codes=("LCOC-A", "LCOC-B", "LCOC-9", "LCOC-12", "LCOC-13"),
        catalog=OVARIAN_CATALOG,
    ),
    "PROS": ParserProfile(
        key="prostate",
        display_name="NCCN Prostate DNA-Repair Profile",
        code_family="PROS",
        molecular_style="dna_repair_driven",
        cancer_keywords=["prostate", "pros"],
        preferred_section_codes=("PROS-J", "PROS-K", "PROS-L", "PROS-M", "PROS-N", "PROS-15", "PROS-16", "PROS-17", "PROS-18"),
        catalog=PROSTATE_CATALOG,
    ),
    "AML": ParserProfile(
        key="aml",
        display_name="NCCN AML Mutation-Directed Profile",
        code_family="AML",
        molecular_style="hematologic_marker_driven",
        cancer_keywords=["aml", "acute myeloid leukemia"],
        preferred_section_codes=("AML-A", "AML-B", "AML-C", "AML-D", "AML-E", "AML-F", "AML-G", "AML-H", "AML-I", "AML-J"),
        catalog=AML_CATALOG,
    ),
    "UTT": ParserProfile(
        key="bladder",
        display_name="NCCN Bladder Molecular-Directed Profile",
        code_family="UTT",
        molecular_style="pan_tumor",
        cancer_keywords=["bladder", "urothelial", "utt"],
        preferred_section_codes=("UTT-1", "UTT-2", "UTT-3", "UTT-4"),
        catalog=BLADDER_CATALOG,
    ),
    "BL": ParserProfile(
        key="bladder",
        display_name="NCCN Bladder Molecular-Directed Profile",
        code_family="BL",
        molecular_style="pan_tumor",
        cancer_keywords=["bladder", "urothelial", "bl"],
        preferred_section_codes=("BL-1", "BL-2", "PCU-1"),
        catalog=BLADDER_CATALOG,
    ),
    "KID": ParserProfile(
        key="kidney",
        display_name="NCCN Kidney Histology-Molecular Profile",
        code_family="KID",
        molecular_style="histology_molecular",
        cancer_keywords=["kidney", "renal", "kid"],
        preferred_section_codes=("KID-A", "KID-B", "KID-C", "KID-D", "KID-E", "GENE-1"),
        catalog=KIDNEY_CATALOG,
    ),
    "PAP": ParserProfile(
        key="thyroid",
        display_name="NCCN Thyroid Targeted-Therapy Profile",
        code_family="PAP",
        molecular_style="mutation_driven",
        cancer_keywords=["thyroid", "papillary thyroid", "pap"],
        preferred_section_codes=("PAP-1", "ANAP-A"),
        catalog=THYROID_CATALOG,
    ),
    "TI": ParserProfile(
        key="thyroid",
        display_name="NCCN Thyroid Targeted-Therapy Profile",
        code_family="TI",
        molecular_style="mutation_driven",
        cancer_keywords=["thyroid", "ti"],
        preferred_section_codes=("TI-1", "ANAP-A"),
        catalog=THYROID_CATALOG,
    ),
    "ENDO": ParserProfile(
        key="uterine",
        display_name="NCCN Uterine Molecular-Directed Profile",
        code_family="ENDO",
        molecular_style="pan_tumor",
        cancer_keywords=["uterine", "endometrial", "endo"],
        preferred_section_codes=("ENDO-A", "ENDO-B", "ENDO-C", "ENDO-D", "ENDO-10", "ENDO-11", "ENDO-12", "ENDO-13", "ENDO-14"),
        catalog=UTERINE_CATALOG,
    ),
    "UN": ParserProfile(
        key="uterine",
        display_name="NCCN Uterine Molecular-Directed Profile",
        code_family="UN",
        molecular_style="pan_tumor",
        cancer_keywords=["uterine", "endometrial", "un"],
        preferred_section_codes=("UN-1", "ENDO-A", "ENDO-B", "ENDO-C", "ENDO-D"),
        catalog=UTERINE_CATALOG,
    ),
    "GAST": ParserProfile(
        key="gastric",
        display_name="NCCN Gastric Molecular-Directed Profile",
        code_family="GAST",
        molecular_style="upper_gi_biomarker",
        cancer_keywords=["gastric", "stomach", "gast"],
        preferred_section_codes=("GAST-A", "GAST-B", "GAST-C", "GAST-D", "GAST-E", "GAST-F", "GAST-G", "GAST-H", "GAST-I", "GAST-J"),
        catalog=UPPER_GI_CATALOG,
    ),
    "ESOPH": ParserProfile(
        key="esophageal",
        display_name="NCCN Esophageal Molecular-Directed Profile",
        code_family="ESOPH",
        molecular_style="upper_gi_biomarker",
        cancer_keywords=["esophageal", "esophagus", "esoph"],
        preferred_section_codes=("ESOPH-A", "ESOPH-B", "ESOPH-C", "ESOPH-D", "ESOPH-E", "ESOPH-F", "ESOPH-G", "ESOPH-H", "ESOPH-I", "ESOPH-J"),
        catalog=UPPER_GI_CATALOG,
    ),
    "HCC": ParserProfile(
        key="hcc",
        display_name="NCCN HCC Pan-Tumor Biomarker Profile",
        code_family="HCC",
        molecular_style="pan_tumor",
        cancer_keywords=["hcc", "hepatocellular", "liver cancer"],
        preferred_section_codes=("HCC-A", "HCC-B", "HCC-C", "HCC-D", "HCC-E", "HCC-F", "HCC-G", "HCC-H", "HCC-I", "HCC-J"),
        catalog=HCC_CATALOG,
    ),
    "NE": ParserProfile(
        key="neuroendocrine",
        display_name="NCCN Neuroendocrine Pan-Tumor Profile",
        code_family="NE",
        molecular_style="pan_tumor",
        cancer_keywords=["neuroendocrine", "net", "ne"],
        preferred_section_codes=("NE-A", "NE-B", "NE-C", "NE-D", "NE-E", "NE-F", "NE-G", "NE-H", "NE-I", "NE-J", "NE-K", "NE-L"),
        catalog=NEUROENDOCRINE_CATALOG,
    ),
    "SCL": ParserProfile(
        key="sclc",
        display_name="NCCN Small Cell Lung Target Profile",
        code_family="SCL",
        molecular_style="emerging_target",
        cancer_keywords=["small cell lung", "sclc", "scl"],
        preferred_section_codes=("SCL-A", "SCL-B", "SCL-C", "SCL-D", "SCL-E", "SCL-F", "SCL-G"),
        catalog=SCLC_CATALOG,
    ),
    "ALL": ParserProfile(
        key="all",
        display_name="NCCN Acute Lymphoblastic Leukemia Starter Profile",
        code_family="ALL",
        molecular_style="hematologic_marker_driven",
        cancer_keywords=["acute lymphoblastic leukemia", "all"],
        preferred_section_codes=("ALL-1", "ALL-2", "ALL-3"),
        catalog=ALL_CATALOG,
    ),
    "AMP": ParserProfile(
        key="ampullary",
        display_name="NCCN Ampullary Pan-Tumor Profile",
        code_family="AMP",
        molecular_style="pan_tumor",
        cancer_keywords=["ampullary"],
        preferred_section_codes=("AMP-1", "AMP-2", "AMP-3"),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "ANAL": ParserProfile(
        key="anal",
        display_name="NCCN Anal Pan-Tumor Profile",
        code_family="ANAL",
        molecular_style="pan_tumor",
        cancer_keywords=["anal carcinoma", "anal cancer"],
        preferred_section_codes=("ANAL-1", "ANAL-2"),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "APP": ParserProfile(
        key="appendiceal",
        display_name="NCCN Appendiceal Pan-Tumor Profile",
        code_family="APP",
        molecular_style="pan_tumor",
        cancer_keywords=["appendiceal"],
        preferred_section_codes=("APP-1", "APP-2", "APP-3"),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "BCEL": ParserProfile(
        key="b_cell_lymphoma",
        display_name="NCCN B-Cell Lymphoma Starter Profile",
        code_family="BCEL",
        molecular_style="hematologic_marker_driven",
        cancer_keywords=["b-cell lymphoma", "b-cell lymphomas"],
        preferred_section_codes=("BCEL-1", "MANT-1", "FOLL-1", "MZL-1"),
        catalog=LYMPHOID_CATALOG,
    ),
    "BONE": ParserProfile(
        key="bone",
        display_name="NCCN Bone/Sarcoma Starter Profile",
        code_family="BONE",
        molecular_style="fusion_driven",
        cancer_keywords=["bone cancer"],
        preferred_section_codes=("BONE-1", "OSTEO-1", "EW-1"),
        catalog=SARCOMA_CATALOG,
    ),
    "BIL": ParserProfile(
        key="biliary",
        display_name="NCCN Biliary/Hepatobiliary Starter Profile",
        code_family="BIL",
        molecular_style="pan_tumor",
        cancer_keywords=["biliary tract", "hepatobiliary"],
        preferred_section_codes=("BIL-1", "GALL-1", "INTRA-1", "EXTRA-1"),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "CD": ParserProfile(
        key="castleman",
        display_name="NCCN Castleman Starter Profile",
        code_family="CD",
        molecular_style="inflammatory",
        cancer_keywords=["castleman"],
        preferred_section_codes=("CD-1", "HHV-1"),
        catalog=[],
    ),
    "GLIO": ParserProfile(
        key="cns",
        display_name="NCCN CNS Starter Profile",
        code_family="GLIO",
        molecular_style="fusion_driven",
        cancer_keywords=["central nervous system cancers", "cns cancers"],
        preferred_section_codes=("GLIO-1", "BRAIN-1", "EPEN-1"),
        catalog=CNS_CATALOG,
    ),
    "ME": ParserProfile(
        key="cutaneous_melanoma",
        display_name="NCCN Cutaneous Melanoma Starter Profile",
        code_family="ME",
        molecular_style="mutation_driven",
        cancer_keywords=["melanoma: cutaneous", "cutaneous melanoma"],
        preferred_section_codes=("ME-1", "ME-2"),
        catalog=SKIN_CATALOG,
    ),
    "GIST": ParserProfile(
        key="gist",
        display_name="NCCN GIST Targeted Profile",
        code_family="GIST",
        molecular_style="mutation_driven",
        cancer_keywords=["gastrointestinal stromal tumor", "gastrointestinal stromal tumors", "gist"],
        preferred_section_codes=("GIST-1", "GIST-2"),
        catalog=GIST_CATALOG,
    ),
    "GTN": ParserProfile(
        key="gtn",
        display_name="NCCN GTN Starter Profile",
        code_family="GTN",
        molecular_style="other",
        cancer_keywords=["gestational trophoblastic"],
        preferred_section_codes=("GTN-1", "HM-1"),
        catalog=[],
    ),
    "ORPH": ParserProfile(
        key="head_neck",
        display_name="NCCN Head and Neck Pan-Tumor Profile",
        code_family="ORPH",
        molecular_style="pan_tumor",
        cancer_keywords=["head and neck cancers", "head and neck"],
        preferred_section_codes=("ORPH-1", "NASO-1", "OCC-1", "SALI-1"),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "HIST": ParserProfile(
        key="histiocytic",
        display_name="NCCN Histiocytic Targeted Profile",
        code_family="HIST",
        molecular_style="mutation_driven",
        cancer_keywords=["histiocytic neoplasms"],
        preferred_section_codes=("HIST-1", "ECD-1", "LCH-1"),
        catalog=HISTIOCYTIC_CATALOG,
    ),
    "KS": ParserProfile(
        key="kaposi",
        display_name="NCCN Kaposi Starter Profile",
        code_family="KS",
        molecular_style="viral",
        cancer_keywords=["kaposi sarcoma"],
        preferred_section_codes=("KS-1",),
        catalog=[],
    ),
    "MCC": ParserProfile(
        key="mcc",
        display_name="NCCN Merkel Cell Skin Profile",
        code_family="MCC",
        molecular_style="immunotherapy_driven",
        cancer_keywords=["merkel cell carcinoma"],
        preferred_section_codes=("MCC-1",),
        catalog=SKIN_CATALOG,
    ),
    "PEM": ParserProfile(
        key="peritoneal_mesothelioma",
        display_name="NCCN Peritoneal Mesothelioma Starter Profile",
        code_family="PEM",
        molecular_style="pan_tumor",
        cancer_keywords=["mesothelioma: peritoneal", "peritoneal mesothelioma"],
        preferred_section_codes=("PEM-1",),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "NEUROB": ParserProfile(
        key="neuroblastoma",
        display_name="NCCN Neuroblastoma Starter Profile",
        code_family="NEUROB",
        molecular_style="pediatric_targeted",
        cancer_keywords=["neuroblastoma"],
        preferred_section_codes=("NEUROB-1", "HIGH-1"),
        catalog=PEDIATRIC_SOLID_CATALOG,
    ),
    "BCC": ParserProfile(
        key="bcc",
        display_name="NCCN Basal Cell Skin Starter Profile",
        code_family="BCC",
        molecular_style="skin_targeted",
        cancer_keywords=["basal cell skin cancer"],
        preferred_section_codes=("BCC-1",),
        catalog=SKIN_CATALOG,
    ),
    "OCC": ParserProfile(
        key="occult_primary",
        display_name="NCCN CUP Pan-Tumor Profile",
        code_family="OCC",
        molecular_style="pan_tumor",
        cancer_keywords=["occult primary", "cancer of unknown primary", "cup"],
        preferred_section_codes=("OCC-1", "TUMOR-1", "EVAL-1"),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "PEDALL": ParserProfile(
        key="ped_all",
        display_name="NCCN Pediatric ALL Starter Profile",
        code_family="PEDALL",
        molecular_style="hematologic_marker_driven",
        cancer_keywords=["pediatric acute lymphoblastic leukemia"],
        preferred_section_codes=("PEDALL-1", "ALL-1"),
        catalog=ALL_CATALOG,
    ),
    "PGLIO": ParserProfile(
        key="ped_cns",
        display_name="NCCN Pediatric CNS Starter Profile",
        code_family="PGLIO",
        molecular_style="fusion_driven",
        cancer_keywords=["pediatric central nervous system cancers"],
        preferred_section_codes=("PGLIO-1", "PMB-1", "HIGH-1"),
        catalog=CNS_CATALOG,
    ),
    "PHL": ParserProfile(
        key="ped_hodgkin",
        display_name="NCCN Pediatric Hodgkin Starter Profile",
        code_family="PHL",
        molecular_style="hematologic_marker_driven",
        cancer_keywords=["pediatric hodgkin lymphoma"],
        preferred_section_codes=("PHL-1", "FNP-1"),
        catalog=HODGKIN_CATALOG,
    ),
    "HODG": ParserProfile(
        key="hodgkin",
        display_name="NCCN Hodgkin Starter Profile",
        code_family="HODG",
        molecular_style="hematologic_marker_driven",
        cancer_keywords=["hodgkin lymphoma"],
        preferred_section_codes=("HODG-1",),
        catalog=HODGKIN_CATALOG,
    ),
    "PRMS": ParserProfile(
        key="ped_sts",
        display_name="NCCN Pediatric Soft Tissue Sarcoma Starter Profile",
        code_family="PRMS",
        molecular_style="fusion_driven",
        cancer_keywords=["pediatric soft tissue sarcoma"],
        preferred_section_codes=("PRMS-1", "SRF-1"),
        catalog=SARCOMA_CATALOG,
    ),
    "PN": ParserProfile(
        key="penile",
        display_name="NCCN Penile Pan-Tumor Profile",
        code_family="PN",
        molecular_style="pan_tumor",
        cancer_keywords=["penile cancer"],
        preferred_section_codes=("PN-1",),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "SARC": ParserProfile(
        key="sarcoma",
        display_name="NCCN Soft Tissue Sarcoma Starter Profile",
        code_family="SARC",
        molecular_style="fusion_driven",
        cancer_keywords=["soft tissue sarcoma"],
        preferred_section_codes=("SARC-1", "EXTSARC-1", "RETSARC-1"),
        catalog=SARCOMA_CATALOG,
    ),
    "SBA": ParserProfile(
        key="small_bowel",
        display_name="NCCN Small Bowel Pan-Tumor Profile",
        code_family="SBA",
        molecular_style="pan_tumor",
        cancer_keywords=["small bowel adenocarcinoma", "small bowel"],
        preferred_section_codes=("SBA-1",),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "SCC": ParserProfile(
        key="squamous_skin",
        display_name="NCCN Squamous Skin Starter Profile",
        code_family="SCC",
        molecular_style="skin_targeted",
        cancer_keywords=["squamous"],
        preferred_section_codes=("SCC-1",),
        catalog=SKIN_CATALOG,
    ),
    "TEST": ParserProfile(
        key="testicular",
        display_name="NCCN Testicular Starter Profile",
        code_family="TEST",
        molecular_style="other",
        cancer_keywords=["testicular cancer"],
        preferred_section_codes=("TEST-1", "SEM-1", "NSEM-1"),
        catalog=[],
    ),
    "THYM": ParserProfile(
        key="thymic",
        display_name="NCCN Thymic Starter Profile",
        code_family="THYM",
        molecular_style="pan_tumor",
        cancer_keywords=["thymomas and thymic carcinomas", "thymic carcinoma", "thymoma"],
        preferred_section_codes=("THYM-1",),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "UM": ParserProfile(
        key="uveal_melanoma",
        display_name="NCCN Uveal Melanoma Starter Profile",
        code_family="UM",
        molecular_style="mutation_driven",
        cancer_keywords=["melanoma: uveal", "uveal melanoma"],
        preferred_section_codes=("UM-1",),
        catalog=SKIN_CATALOG,
    ),
    "VAG": ParserProfile(
        key="vaginal",
        display_name="NCCN Vaginal Pan-Tumor Profile",
        code_family="VAG",
        molecular_style="pan_tumor",
        cancer_keywords=["vaginal cancer"],
        preferred_section_codes=("VAG-1",),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "VULVA": ParserProfile(
        key="vulvar",
        display_name="NCCN Vulvar Pan-Tumor Profile",
        code_family="VULVA",
        molecular_style="pan_tumor",
        cancer_keywords=["vulvar cancer"],
        preferred_section_codes=("VULVA-1",),
        catalog=PAN_TUMOR_SOLID_CATALOG,
    ),
    "WILMS": ParserProfile(
        key="wilms",
        display_name="NCCN Wilms Tumor Starter Profile",
        code_family="WILMS",
        molecular_style="pediatric_targeted",
        cancer_keywords=["wilms tumor", "nephroblastoma"],
        preferred_section_codes=("WILMS-1",),
        catalog=PEDIATRIC_SOLID_CATALOG,
    ),
}


def infer_code_family(guideline_name: str, cancer_type: str, section_codes: list[str]) -> str:
    for section_code in section_codes:
        if "-" in section_code:
            prefix = section_code.split("-", 1)[0].upper()
            if prefix in PROFILES:
                return prefix

    haystack = f"{guideline_name} {cancer_type}".lower()
    for prefix, profile in PROFILES.items():
        if any(keyword in haystack for keyword in profile.cancer_keywords):
            return prefix

    return ""


def get_parser_profile(guideline_name: str, cancer_type: str, section_codes: list[str]) -> ParserProfile | None:
    code_family = infer_code_family(guideline_name, cancer_type, section_codes)
    return PROFILES.get(code_family)
