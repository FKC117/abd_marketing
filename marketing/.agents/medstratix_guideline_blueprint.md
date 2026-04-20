# MedStratix Guideline Intelligence Implementation Blueprint

## 1. Goal

Build a guideline-ingestion and intelligence layer that can support:

- 1 initial guideline: NSCLC
- 20+ future guideline PDFs
- different molecular architectures per cancer type
- structured biomarker-to-therapy intelligence
- PostgreSQL as the system of record

This blueprint assumes:

- guideline PDFs will be stored locally
- we will extract text from PDFs
- we will normalize guideline content into structured database records
- MedStratix will compare panel genes against guideline-defined molecular and treatment relevance

## 2. Core Design Principle

Do not treat each PDF as a single document blob.

Instead, split the system into:

1. `document ingestion`
2. `section extraction`
3. `molecular architecture definition`
4. `structured rule extraction`
5. `panel-to-guideline matching`
6. `strategy/report generation`

That gives us a reusable engine across many cancer guidelines.

## 3. Multi-Guideline Architecture

Each guideline will have its own molecular architecture.

Examples:

- NSCLC: EGFR, ALK, ROS1, BRAF, MET exon 14, RET, ERBB2, NTRK, KRAS, NRG1
- Breast cancer: ER, PR, HER2, PIK3CA, ESR1, BRCA1/2
- CRC: KRAS, NRAS, BRAF, HER2, MSI, NTRK
- AML: FLT3, NPM1, IDH1, IDH2, TP53, etc.

So the system should not hardcode one universal biomarker map.

Instead:

- one guideline belongs to one cancer domain
- one guideline has many biomarker definitions
- one guideline has many therapy rules
- one guideline can define its own testing methodology rules
- one guideline can define its own molecular subtypes and interpretation logic

## 4. Recommended App Structure

Inside `medstratix`, add modules like:

```text
medstratix/
  guidelines/
    raw/
    extracted/
  services/
    pdf_extractor.py
    section_splitter.py
    biomarker_parser.py
    therapy_parser.py
    panel_matcher.py
    report_builder.py
  selectors/
    guideline_selectors.py
    panel_selectors.py
  management/
    commands/
      import_guideline_pdf.py
      extract_guideline_sections.py
      build_guideline_rules.py
  agents/
    agent_panel_parser.py
    agent_gene_normalizer.py
    agent_guideline_matcher.py
    agent_strategy_generator.py
```

## 5. PostgreSQL Data Model

Use PostgreSQL for all structured guideline intelligence.

### 5.1 Guideline Source Models

#### GuidelineDocument

- `id`
- `name`
- `cancer_type`
- `version`
- `year`
- `source_file`
- `status`
- `published_at`
- `created_at`
- `updated_at`

Purpose:
- one record per uploaded PDF guideline

#### GuidelineSection

- `id`
- `guideline_document_id`
- `section_code`
- `title`
- `page_start`
- `page_end`
- `raw_text`
- `normalized_text`
- `section_type`
- `created_at`

Examples:
- `NSCL-H`
- `NSCL-J`
- `NSCL-K`

Purpose:
- store extracted and searchable sections

### 5.2 Molecular Architecture Models

#### MolecularProfile

- `id`
- `guideline_document_id`
- `cancer_type`
- `name`
- `description`
- `clinical_context`
- `is_active`

Examples:
- `Advanced NSCLC actionable biomarkers`
- `Resistant EGFR-mutated NSCLC`

Purpose:
- logical grouping of biomarker and therapy rules inside a guideline

#### BiomarkerDefinition

- `id`
- `guideline_document_id`
- `molecular_profile_id`
- `gene_symbol`
- `alias_json`
- `alteration_family`
- `description`
- `is_actionable`
- `priority_rank`

Examples of `alteration_family`:
- `mutation`
- `fusion`
- `amplification`
- `exon_skipping`
- `protein_overexpression`
- `copy_number_gain`

Purpose:
- define the biomarker universe for one guideline

#### BiomarkerVariantRule

- `id`
- `guideline_document_id`
- `biomarker_definition_id`
- `variant_label`
- `variant_type`
- `variant_details_json`
- `testing_context`
- `histology_context`
- `stage_context`
- `disease_setting`
- `line_of_therapy`
- `is_preferred`
- `evidence_level`
- `recommendation_category`
- `notes`
- `source_section_id`

Examples:
- `EGFR exon 19 deletion`
- `EGFR L858R`
- `MET exon 14 skipping`
- `ALK fusion`

Purpose:
- store the exact clinically meaningful biomarker condition

#### TestingMethodRule

- `id`
- `guideline_document_id`
- `biomarker_definition_id`
- `method_type`
- `preferred_rank`
- `is_required`
- `notes`
- `source_section_id`

Examples of `method_type`:
- `DNA_NGS`
- `RNA_NGS`
- `plasma_testing`
- `tissue_testing`
- `IHC`
- `FISH`
- `RT_PCR`

Purpose:
- store how a biomarker should be tested or confirmed

### 5.3 Treatment Intelligence Models

#### TherapyDefinition

- `id`
- `name`
- `therapy_class`
- `combination_json`
- `manufacturer`
- `is_systemic`
- `notes`

Examples:
- `osimertinib`
- `amivantamab-vmjw + lazertinib`
- `selpercatinib`

#### GuidelineTherapyRule

- `id`
- `guideline_document_id`
- `molecular_profile_id`
- `biomarker_variant_rule_id`
- `therapy_definition_id`
- `therapy_line`
- `therapy_role`
- `patient_context`
- `histology_context`
- `stage_context`
- `recommendation_strength`
- `evidence_level`
- `special_notes`
- `source_section_id`

Examples of `therapy_role`:
- `first_line`
- `subsequent`
- `maintenance`
- `useful_in_certain_circumstances`
- `preferred`

Purpose:
- link a biomarker state to a treatment recommendation

### 5.4 Panel Matching Models

#### PanelGuidelineMatch

- `id`
- `panel_id`
- `guideline_document_id`
- `cancer_type`
- `match_status`
- `matched_genes_count`
- `missing_actionable_genes_count`
- `coverage_percent`
- `summary_json`
- `created_at`

#### PanelGuidelineGeneMatch

- `id`
- `panel_guideline_match_id`
- `gene_symbol`
- `biomarker_definition_id`
- `match_type`
- `testing_relevance`
- `therapy_relevance`
- `notes_json`

Examples of `match_type`:
- `present_actionable`
- `present_non_actionable`
- `missing_actionable`
- `present_but_incomplete_for_variant_detection`

Purpose:
- support panel-vs-guideline intelligence

## 6. Why This Schema Scales

This design works for 20+ guidelines because:

- `GuidelineDocument` separates one PDF/version from another
- `BiomarkerDefinition` is cancer-specific
- `BiomarkerVariantRule` supports very different mutation/fusion architectures
- `TestingMethodRule` supports method differences across cancers
- `GuidelineTherapyRule` supports multiple therapies per biomarker and therapy line
- PostgreSQL JSON fields let us store nuanced rule metadata without blocking MVP speed

## 7. Guideline Ingestion Pipeline

### Stage 1: Store Raw Guideline

Input:
- one uploaded PDF

Process:
- save metadata in `GuidelineDocument`
- store source file path
- assign cancer type and version

Output:
- one persisted guideline document record

### Stage 2: Extract Text

Recommended first tool:
- `pdftotext -layout`

Store:
- full extracted text in file storage
- parsed sections in `GuidelineSection`

Output:
- clean searchable sections

### Stage 3: Split Into Logical Sections

For NCCN-like documents, split by anchors such as:

- `NSCL-H`
- `NSCL-J`
- `NSCL-K`
- disease-specific page blocks
- biomarker-specific headings

Store both:
- raw block text
- normalized block text

### Stage 4: Build Molecular Architecture

For each guideline, create:

- biomarker list
- variant rules
- testing rules
- therapy rules

This should be done in a semi-structured curated pipeline:

1. parser proposes candidates
2. review screen validates them
3. approved records are saved to PostgreSQL

### Stage 5: Panel Matching

Given panel genes:

1. normalize gene symbols
2. load cancer-specific biomarker universe
3. compare panel genes to actionable genes
4. identify missing genes
5. identify potential therapy relevance

### Stage 6: Strategy Layer

After structured matching is done:

- generate competitive intelligence
- summarize missing NCCN-relevant markers
- summarize possible therapy-linked differentiators

This layer should consume structured rows, not raw PDF text.

## 8. Parsing Strategy

Use a hybrid strategy:

### Deterministic Parsing

Use code for:

- section boundary detection
- page references
- biomarker heading detection
- therapy table extraction
- guideline code extraction
- gene symbol normalization

This should be the default approach.

### Assisted Parsing

Use AI or curated review for:

- summarizing long rationale sections
- converting ambiguous narrative text into structured notes
- resolving edge cases

But the core treatment rules should not depend on freeform AI output alone.

## 9. NSCLC First Implementation

For `nscl.pdf`, first scope should be:

### Extract first

- `NSCL-H`
- `NSCL-J`
- advanced/metastatic testing and treatment pages

### Store first biomarker architecture

- `EGFR exon 19 deletion`
- `EGFR L858R`
- `EGFR uncommon mutations`
- `EGFR exon 20 insertion`
- `ALK fusion`
- `ROS1 fusion`
- `BRAF V600E`
- `KRAS G12C`
- `MET exon 14 skipping`
- `RET fusion`
- `ERBB2 mutation`
- `NTRK1/2/3 fusion`
- `NRG1 fusion`

### Store first testing rules

- broad molecular profiling recommended
- DNA NGS vs RNA NGS notes
- plasma and tissue testing notes
- IHC-specific notes where relevant

### Store first therapy rules

For each actionable biomarker:

- first-line options
- subsequent therapy options
- special warnings
- progression notes where clearly stated

## 10. Generalization for 20 More Guidelines

When more guidelines are added, do not build separate codepaths for each cancer.

Instead:

- same ingestion pipeline
- same storage schema
- guideline-specific parser config

### Recommended Parser Config Model

Create a config per guideline family:

#### GuidelineParserProfile

- `id`
- `name`
- `cancer_type`
- `section_patterns_json`
- `biomarker_patterns_json`
- `therapy_patterns_json`
- `testing_patterns_json`
- `is_active`

Example:
- NSCLC parser profile knows `NSCL-H`, `NSCL-J`
- Breast parser profile may know different section markers
- AML parser profile may focus on mutation-risk-stratification sections

This keeps the code generic while the parsing behavior stays disease-aware.

## 11. Recommended PostgreSQL Choices

- Use `JSONField` for parser metadata, aliases, combination therapies, and extraction traces
- Add indexes on:
  - `GuidelineDocument(cancer_type, version)`
  - `GuidelineSection(guideline_document_id, section_code)`
  - `BiomarkerDefinition(gene_symbol)`
  - `BiomarkerVariantRule(stage_context, line_of_therapy)`
  - `GuidelineTherapyRule(biomarker_variant_rule_id, therapy_line)`
- Add unique constraints where appropriate:
  - one biomarker definition per guideline/profile/gene family
  - one therapy rule per biomarker/therapy/line/source section combination

## 12. Django Implementation Order

### Phase 1: Core Models

Build:

- `GuidelineDocument`
- `GuidelineSection`
- `MolecularProfile`
- `BiomarkerDefinition`
- `BiomarkerVariantRule`
- `TestingMethodRule`
- `TherapyDefinition`
- `GuidelineTherapyRule`

### Phase 2: Ingestion Commands

Build management commands:

- `import_guideline_pdf`
- `extract_guideline_sections`
- `build_guideline_rules`

### Phase 3: Admin Review Tools

Build Django admin for:

- viewing extracted sections
- approving biomarker definitions
- approving therapy rules
- reviewing testing methodology notes

### Phase 4: Panel Matching

Build:

- guideline-aware panel matcher
- missing actionable gene detection
- therapy relevance summarizer

### Phase 5: Strategy Reports

Build:

- competitive intelligence summary
- treatment-linked differentiation insights
- sales strategy narrative from structured matches

## 13. MVP Decision Boundaries

To keep the build realistic:

### For MVP, do

- one cancer guideline fully structured
- one parser profile
- one approved biomarker architecture
- one panel-to-guideline comparison flow

### For MVP, do not do yet

- full automation for all PDFs without review
- fully autonomous extraction approval
- complex knowledge graph infrastructure
- deeply nested treatment pathway simulation

## 14. First Buildable Deliverables

The first concrete milestones should be:

### Milestone 1

- PostgreSQL connected to Django
- all guideline intelligence models created
- admin registered

### Milestone 2

- `nscl.pdf` imported as `GuidelineDocument`
- text extracted and split into `GuidelineSection`

### Milestone 3

- NSCLC biomarker universe stored in database
- NSCLC therapy rules stored in database

### Milestone 4

- panel gene list matched against NSCLC rules
- report shows:
  - actionable genes covered
  - missing actionable genes
  - possible treatment relevance

## 15. Recommended Next Build Step

Next, implement:

1. PostgreSQL settings
2. guideline intelligence models
3. admin registration
4. `import_guideline_pdf` command
5. `extract_guideline_sections` command for `nscl.pdf`

That gives us the right base for the 20 additional guidelines later.

