# MedStratix MVP Task List

Based on: [medstratix_full_project.md](f:\abd_marketing\marketing\.agents\medstratix_full_project.md)

Legend:
- `[x]` done
- `[~]` partially done / needs refinement
- `[ ]` not done yet

## 1. Foundation Setup

- [x] Confirm project settings for PostgreSQL, static files, templates, and environment variables
- [x] Add dependency list for Django, PostgreSQL driver, LangChain, LangGraph, HTMX/Tailwind support, and Gemini integration
- [x] Create a local `.env` strategy for database and API keys
- [x] Decide MVP scope for first cancer type and guideline source
- [~] Set up base app structure for services, selectors, and AI/agent modules
  Current state: strong `services/` layer exists; dedicated `selectors/` and `agent_*` modules are still not built.

## 2. Database Models

- [x] Create `Company` model with `name` and `type`
- [x] Create `Panel` model with company relation, price, TAT, and timestamps
- [x] Create `Gene` model with normalized `symbol`
- [x] Create `PanelGene` join model linking panels and genes
- [x] Create `ComparisonReport` model for overlap and unique counts
- [x] Create `Guideline` model with name, version, and year
- [~] Create `GuidelineEntry` model with cancer type, gene, mutation, therapy, line of treatment, evidence level, and source text
  Current state: this was implemented as a richer model set:
  `GuidelineSection`, `MolecularProfile`, `BiomarkerDefinition`, `BiomarkerVariantRule`, `TestingMethodRule`, `GuidelineTherapyRule`.
- [x] Create `StrategyReport` model with your panel, competitor panel, and structured report output
- [x] Add model constraints, indexes, and readable admin definitions
- [x] Generate and apply initial migrations

## 3. Admin and Data Management

- [x] Register all core models in Django admin
- [x] Add list display, filters, and search fields for admin usability
- [x] Support inline management for panel genes where helpful
- [~] Prepare seed data workflow for companies, genes, and guidelines
  Current state: guideline bulk import is built; company/panel/gene seed flow is not finished.

## 4. Panel Upload Workflow

- [ ] Create upload UI for competitor panel submission
- [ ] Create upload UI for your own panel submission
- [ ] Capture panel details for both flows: company, panel name, price, TAT, and upload file/text
- [ ] Build server-side form validation
- [ ] Parse uploaded CSV/text into raw panel data
- [ ] Create competitor panel save flow that stores company, panel, price, TAT, and related genes
- [ ] Create your-panel save flow that stores company, panel, price, TAT, and related genes
- [ ] Add success/error messaging for upload results
- [ ] Create tests for upload parsing and save behavior

## 5. Gene Normalization

- [~] Define normalization rules for gene symbols
  Current state: uppercase normalization exists for `Gene.symbol`, but no full panel-upload normalization policy yet.
- [ ] Create a normalization dictionary or alias mapping
- [ ] Build a reusable normalization service
- [ ] Normalize genes during upload before saving
- [ ] Track unmatched or suspicious symbols for manual review
- [ ] Add tests for normalization edge cases

## 6. Comparison Engine

- [ ] Build comparison service using overlap, missing, and unique gene logic
- [ ] Calculate overlap count, unique counts, and coverage percentage
- [ ] Persist comparison results in `ComparisonReport`
- [ ] Create comparison UI to select two panels
- [ ] Display overlap genes, genes only in panel A, and genes only in panel B
- [ ] Add tests for comparison logic and report persistence

## 7. Guideline Intelligence

- [x] Create guideline import workflow or admin data-entry path
- [~] Build guideline matching service for panel genes
  Current state: guideline structuring exists; actual panel-vs-guideline matching is still not implemented.
- [x] Identify actionable genes found in a panel
  Current state: achieved inside guideline structuring/ontology for guideline records, not yet against uploaded panels.
- [x] Identify critical genes missing from a panel
  Current state: supported conceptually by structured guideline layer, but not yet exposed through a panel comparison flow.
- [x] Scope guideline logic to one cancer type for MVP
  Current state: exceeded; framework now supports many NCCN families.
- [x] Add review-friendly output showing matched entries and source text
- [~] Add tests for guideline matching behavior
  Current state: no formal automated tests yet.

## 8. Strategy Engine

- [x] Define structured prompt inputs from panel comparison and guideline matches
- [~] Build `agent_strategy_generator` service using Gemini 2.5 Flash
  Current state: Gemini service exists as `strategy_generator.py`; dedicated `agent_*` wrapper is still not built.
- [x] Generate positioning strategy output
- [x] Generate sales pitch output
- [x] Generate differentiation insights output
- [x] Save generated output in `StrategyReport`
- [x] Store LLM input, output, tokens, and estimated cost in a dedicated model
- [x] Add market-intelligence context as structured human input for strategy generation
- [x] Add a fallback or validation step for malformed model output
  Current state: JSON validation and empty-response handling are built.
- [ ] Add tests around report generation boundaries where feasible

## 9. Agent Layer

- [ ] Create `agent_panel_parser`
- [ ] Create `agent_gene_normalizer`
- [ ] Create `agent_comparison_engine`
- [ ] Create `agent_guideline_matcher`
- [ ] Create `agent_strategy_generator`
- [~] Decide where LangChain is useful versus simple Python services
  Current state: dependencies are installed, but no explicit implementation decision is encoded yet.
- [~] Decide where LangGraph is useful versus overkill for the MVP
  Current state: same as above.
- [~] Keep agent interfaces simple so they can be upgraded later
  Current state: services are relatively modular, but dedicated agent interfaces still need to be designed.

## 10. Frontend Pages

- [x] Upgrade homepage to reflect the actual MedStratix product, not just marketing copy
- [x] Create panel upload page
- [x] Create comparison results page
- [x] Create guideline intelligence page or section
  Current state: workspace, dashboard, detail page, biomarker catalog, testing panels, therapy rules pages are all in place.
- [x] Create strategy output page
- [x] Create market-intelligence input page
- [ ] Add HTMX interactions for fast partial updates where useful
- [~] Introduce Tailwind build/setup if we want utility-first styling in the app UI
  Current state: dependency installed, not actually used.

## 11. Reporting and UX

- [x] Show comparison metrics clearly: overlap, unique genes, missing genes, coverage
- [x] Show matched guideline evidence in a readable structure
- [x] Show AI strategy output in clearly separated sections
- [x] Add loading, empty, and error states for key flows
- [~] Keep export/report-download as a post-MVP option unless it becomes necessary
  Current state: not built, intentionally deferred.

## 12. Testing and Quality

- [ ] Add model tests
- [ ] Add form tests
- [ ] Add service tests for parsing, normalization, comparison, and guideline matching
- [ ] Add integration tests for the main MVP flow
- [~] Validate generated strategy output manually during early iterations
  Current state: this will matter once the LLM strategy layer exists.

## 13. Deployment Readiness

- [x] Move secrets and config into environment variables
- [~] Lock production settings for PostgreSQL and static handling
  Current state: basics are configured, but full production hardening still needs a pass.
- [ ] Add logging for uploads, parsing failures, and AI generation errors
- [ ] Write a short setup guide for local development

## 14. Suggested Build Order

- [x] Phase 1: Models, admin, migrations
- [ ] Phase 2: Panel upload and gene normalization
- [ ] Phase 3: Comparison engine and results UI
- [~] Phase 4: Guideline models, import flow, and matching engine
  Current state: import + structuring are done; true panel-guideline matching is still pending.
- [ ] Phase 5: Strategy generation with Gemini
- [~] Phase 6: UI refinement, HTMX enhancements, testing, and deployment cleanup
  Current state: UI refinement is strong; HTMX/testing/deployment cleanup remain.

## 15. First Sprint Recommendation

- [x] Implement all database models
- [x] Register models in admin
- [x] Create initial migrations
- [ ] Build basic panel upload form and save flow
- [ ] Build gene normalization service
- [ ] Make uploaded panels visible in admin and a simple list view

## 16. What Is Actually Done Now

- [x] PostgreSQL + `.env` setup
- [x] Authentication: signup, signin, logout
- [x] Guideline upload from UI
- [x] Bulk backend guideline import for local NCCN library
- [x] PDF extraction into `GuidelineSection`
- [x] Section classification
- [x] Universal NCCN profile framework
- [x] Expanded shared biomarker ontology
- [x] Ontology-driven biomarker seeding
- [x] Structured biomarker / variant / testing / therapy persistence
- [x] Workspace page
- [x] Coverage dashboard
- [x] Guideline detail page with source linking + highlighting
- [x] Testing panels page
- [x] Therapy rules page
- [x] Biomarker catalog page

## 17. Highest-Priority Remaining Core Work

- [x] Dual panel upload + gene normalization pipeline
  Scope: competitor panels with pricing/details and your own panels with pricing/details
- [x] Panel comparison engine
- [x] Panel-vs-guideline matching engine
- [x] Gemini strategy generation service
- [x] Strategy report UI
- [~] Pure strategic decision system
  Current state: SWOT, market gap, guideline advantages, 10+ campaigns, sales pitch, LLM audit log, saved strategy workspace, and market-intelligence input layer are built; export/report packaging and deeper prompt refinement remain.
- [ ] Automated test coverage
- [ ] Logging + deployment cleanup
