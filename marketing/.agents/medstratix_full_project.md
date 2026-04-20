# MedStratix (NGS MVP)

## AI-Powered NGS Panel Intelligence & Strategy Engine

------------------------------------------------------------------------

# 1. OBJECTIVE

Build an AI-driven system that transforms NGS panel data and clinical
guidelines into actionable competitive intelligence and strategy.

------------------------------------------------------------------------

# 2. CORE FLOW

NGS Panels (Genes + Price) + Clinical Guidelines → Intelligence →
Comparison → Strategy

------------------------------------------------------------------------

# 3. CORE CAPABILITIES

## 3.1 Panel Intelligence

-   Upload NGS panels (CSV/Text)
-   Normalize gene lists
-   Store structured panel data

## 3.2 Comparison Engine

-   Gene overlap detection
-   Missing gene detection
-   Coverage %

## 3.3 Guideline Intelligence

-   Map genes to clinical relevance
-   Detect actionable genes
-   Identify missing critical genes

## 3.4 Strategy Engine

-   Generate positioning strategy
-   Generate sales pitch
-   Generate differentiation insights

------------------------------------------------------------------------

# 4. SYSTEM ARCHITECTURE

## Flow

Upload Panel → Normalize → Store → Compare → Match Guidelines → Generate
Strategy → Display

## Stack

-   Django 5.x
-   PostgreSQL
-   LangChain
-   LangGraph
-   Gemini 2.5 Flash
-   HTMX + Tailwind

------------------------------------------------------------------------

# 5. DATABASE DESIGN

## Models

### Company

-   id
-   name
-   type

### Panel

-   id
-   name
-   company_id
-   price
-   tat
-   created_at

### Gene

-   id
-   symbol

### PanelGene

-   id
-   panel_id
-   gene_id

### ComparisonReport

-   id
-   panel_a_id
-   panel_b_id
-   overlap_count
-   unique_a_count
-   unique_b_count

### StrategyReport

-   id
-   your_panel_id
-   competitor_panel_id
-   report_json

------------------------------------------------------------------------

# 6. GUIDELINE MODELS

### Guideline

-   id
-   name
-   version
-   year

### GuidelineEntry

-   id
-   guideline_id
-   cancer_type
-   gene
-   mutation
-   therapy
-   line_of_treatment
-   evidence_level
-   source_text

------------------------------------------------------------------------

# 7. AGENT ARCHITECTURE

## agent_panel_parser

Input: CSV/Text\
Output: panel name + genes

## agent_gene_normalizer

Standardizes gene symbols

## agent_comparison_engine

Calculates overlap and differences

## agent_guideline_matcher

Matches panel genes with guideline DB

## agent_strategy_generator

Generates strategy and pitch

------------------------------------------------------------------------

# 8. CORE LOGIC

## Comparison Logic

common = set(A) & set(B)\
only_A = set(A) - set(B)\
only_B = set(B) - set(A)

## Guideline Matching

Check if panel genes exist in guideline entries

------------------------------------------------------------------------

# 9. UI DESIGN

## Panel Upload

-   Upload CSV
-   Input price

## Comparison View

-   Overlap genes
-   Missing genes

## Guideline Panel

-   Actionable genes
-   Missing critical genes

## Strategy Panel

-   Strategy output
-   Sales pitch

------------------------------------------------------------------------

# 10. RISKS

## Gene Naming Issues

→ Use normalization dictionary

## Guideline Misinterpretation

→ Manual validation

## Over-complexity

→ Start with one cancer type

------------------------------------------------------------------------

# 11. ROADMAP

Week 1: Models + Upload\
Week 2: Comparison Engine\
Week 3: Guideline Engine\
Week 4: Strategy Generator

------------------------------------------------------------------------

# 12. MVP FEATURES

-   Panel upload
-   Gene comparison
-   Guideline matching
-   Strategy generation

------------------------------------------------------------------------

# 13. POSITIONING

MedStratix: AI-powered NGS Panel Intelligence & Strategy Engine
