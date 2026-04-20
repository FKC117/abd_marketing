# MedStratix MVP Task List

Based on: [medstratix_full_project.md](f:\abd_marketing\marketing\.agents\medstratix_full_project.md)

## 1. Foundation Setup

- [ ] Confirm project settings for PostgreSQL, static files, templates, and environment variables
- [ ] Add dependency list for Django, PostgreSQL driver, LangChain, LangGraph, HTMX/Tailwind support, and Gemini integration
- [ ] Create a local `.env` strategy for database and API keys
- [ ] Decide MVP scope for first cancer type and guideline source
- [ ] Set up base app structure for services, selectors, and AI/agent modules

## 2. Database Models

- [ ] Create `Company` model with `name` and `type`
- [ ] Create `Panel` model with company relation, price, TAT, and timestamps
- [ ] Create `Gene` model with normalized `symbol`
- [ ] Create `PanelGene` join model linking panels and genes
- [ ] Create `ComparisonReport` model for overlap and unique counts
- [ ] Create `Guideline` model with name, version, and year
- [ ] Create `GuidelineEntry` model with cancer type, gene, mutation, therapy, line of treatment, evidence level, and source text
- [ ] Create `StrategyReport` model with your panel, competitor panel, and structured report output
- [ ] Add model constraints, indexes, and readable admin definitions
- [ ] Generate and apply initial migrations

## 3. Admin and Data Management

- [ ] Register all core models in Django admin
- [ ] Add list display, filters, and search fields for admin usability
- [ ] Support inline management for panel genes where helpful
- [ ] Prepare seed data workflow for companies, genes, and guidelines

## 4. Panel Upload Workflow

- [ ] Create upload UI for CSV/text panel submission
- [ ] Add price and TAT input fields to the upload form
- [ ] Build server-side form validation
- [ ] Parse uploaded CSV/text into raw panel data
- [ ] Create panel save flow that stores company, panel, and related genes
- [ ] Add success/error messaging for upload results
- [ ] Create tests for upload parsing and save behavior

## 5. Gene Normalization

- [ ] Define normalization rules for gene symbols
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

- [ ] Create guideline import workflow or admin data-entry path
- [ ] Build guideline matching service for panel genes
- [ ] Identify actionable genes found in a panel
- [ ] Identify critical genes missing from a panel
- [ ] Scope guideline logic to one cancer type for MVP
- [ ] Add review-friendly output showing matched entries and source text
- [ ] Add tests for guideline matching behavior

## 8. Strategy Engine

- [ ] Define structured prompt inputs from panel comparison and guideline matches
- [ ] Build `agent_strategy_generator` service using Gemini 2.5 Flash
- [ ] Generate positioning strategy output
- [ ] Generate sales pitch output
- [ ] Generate differentiation insights output
- [ ] Save generated output in `StrategyReport`
- [ ] Add a fallback or validation step for malformed model output
- [ ] Add tests around report generation boundaries where feasible

## 9. Agent Layer

- [ ] Create `agent_panel_parser`
- [ ] Create `agent_gene_normalizer`
- [ ] Create `agent_comparison_engine`
- [ ] Create `agent_guideline_matcher`
- [ ] Create `agent_strategy_generator`
- [ ] Decide where LangChain is useful versus simple Python services
- [ ] Decide where LangGraph is useful versus overkill for the MVP
- [ ] Keep agent interfaces simple so they can be upgraded later

## 10. Frontend Pages

- [ ] Upgrade homepage to reflect the actual MedStratix product, not just marketing copy
- [ ] Create panel upload page
- [ ] Create comparison results page
- [ ] Create guideline intelligence page or section
- [ ] Create strategy output page
- [ ] Add HTMX interactions for fast partial updates where useful
- [ ] Introduce Tailwind build/setup if we want utility-first styling in the app UI

## 11. Reporting and UX

- [ ] Show comparison metrics clearly: overlap, unique genes, missing genes, coverage
- [ ] Show matched guideline evidence in a readable structure
- [ ] Show AI strategy output in clearly separated sections
- [ ] Add loading, empty, and error states for key flows
- [ ] Keep export/report-download as a post-MVP option unless it becomes necessary

## 12. Testing and Quality

- [ ] Add model tests
- [ ] Add form tests
- [ ] Add service tests for parsing, normalization, comparison, and guideline matching
- [ ] Add integration tests for the main MVP flow
- [ ] Validate generated strategy output manually during early iterations

## 13. Deployment Readiness

- [ ] Move secrets and config into environment variables
- [ ] Lock production settings for PostgreSQL and static handling
- [ ] Add logging for uploads, parsing failures, and AI generation errors
- [ ] Write a short setup guide for local development

## 14. Suggested Build Order

- [ ] Phase 1: Models, admin, migrations
- [ ] Phase 2: Panel upload and gene normalization
- [ ] Phase 3: Comparison engine and results UI
- [ ] Phase 4: Guideline models, import flow, and matching engine
- [ ] Phase 5: Strategy generation with Gemini
- [ ] Phase 6: UI refinement, HTMX enhancements, testing, and deployment cleanup

## 15. First Sprint Recommendation

- [ ] Implement all database models
- [ ] Register models in admin
- [ ] Create initial migrations
- [ ] Build basic panel upload form and save flow
- [ ] Build gene normalization service
- [ ] Make uploaded panels visible in admin and a simple list view

