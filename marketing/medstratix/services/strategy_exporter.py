from io import BytesIO


def _add_bullets(document, values):
    if values:
        for value in values:
            document.add_paragraph(str(value), style="List Bullet")
    else:
        document.add_paragraph("None", style="List Bullet")


def _add_key_value(document, label: str, value: str):
    paragraph = document.add_paragraph()
    label_run = paragraph.add_run(f"{label}: ")
    label_run.bold = True
    paragraph.add_run(value or "N/A")


def build_strategy_docx(report, latest_log):
    try:
        from docx import Document
        from docx.enum.section import WD_SECTION
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Pt, RGBColor
    except ModuleNotFoundError as exc:
        raise ValueError("python-docx is not installed. Please install requirements.txt before exporting Word files.") from exc

    def shade_cell(cell, fill: str):
        cell_properties = cell._tc.get_or_add_tcPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), fill)
        cell_properties.append(shading)

    document = Document()
    section = document.sections[0]
    section.top_margin = Pt(54)
    section.bottom_margin = Pt(54)
    section.left_margin = Pt(54)
    section.right_margin = Pt(54)

    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10.5)
    styles["Title"].font.name = "Aptos Display"
    styles["Title"].font.size = Pt(24)
    styles["Title"].font.bold = True
    styles["Heading 1"].font.name = "Aptos Display"
    styles["Heading 1"].font.size = Pt(15)
    styles["Heading 2"].font.name = "Aptos Display"
    styles["Heading 2"].font.size = Pt(12)

    accent = RGBColor(11, 74, 114)
    muted = RGBColor(96, 96, 96)

    title = document.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title_run = title.add_run(report.title or "Untitled Strategy Report")
    title_run.font.color.rgb = accent

    eyebrow = document.add_paragraph()
    eyebrow.alignment = WD_ALIGN_PARAGRAPH.LEFT
    eyebrow_run = eyebrow.add_run("MedStratix Strategic Report")
    eyebrow_run.bold = True
    eyebrow_run.font.size = Pt(9)
    eyebrow_run.font.color.rgb = muted

    document.add_paragraph(report.executive_summary or "No executive summary available.")

    meta_table = document.add_table(rows=3, cols=2)
    meta_table.style = "Table Grid"
    meta_pairs = [
        ("Disease Focus", report.disease_focus or "All diseases"),
        ("Your Panel", f"{report.your_panel.company.name} - {report.your_panel.name}"),
        ("Competitor Panel", f"{report.competitor_panel.company.name} - {report.competitor_panel.name}"),
        ("Primary Market Account", report.market_account.name if report.market_account else "None linked"),
        ("LLM Provider", report.llm_provider or "N/A"),
        ("LLM Model", report.llm_model or "N/A"),
    ]
    for index, (label, value) in enumerate(meta_pairs):
        row = index // 2
        col = (index % 2) * 1
        cell = meta_table.cell(row, col)
        shade_cell(cell, "EAF2F8")
        paragraph = cell.paragraphs[0]
        label_run = paragraph.add_run(f"{label}\n")
        label_run.bold = True
        label_run.font.color.rgb = accent
        paragraph.add_run(value)

    document.add_paragraph("")

    your_panels = report.report_json.get("your_panels", [])
    competitor_panels = report.report_json.get("competitor_panels", [])
    if your_panels or competitor_panels:
        document.add_heading("Panel Sets", level=1)
        if your_panels:
            document.add_heading("Your Panel Set", level=2)
            for panel in your_panels:
                document.add_paragraph(
                    f"{panel.get('company', 'Unknown')} | {panel.get('name', 'Unknown')} | {panel.get('sample_type', 'N/A')}",
                    style="List Bullet",
                )
        if competitor_panels:
            document.add_heading("Competitor Panel Set", level=2)
            for panel in competitor_panels:
                document.add_paragraph(
                    f"{panel.get('company', 'Unknown')} | {panel.get('name', 'Unknown')} | {panel.get('sample_type', 'N/A')}",
                    style="List Bullet",
                )

    strategist_note = report.report_json.get("strategist_note", "")
    if strategist_note:
        document.add_heading("Strategist Note", level=1)
        document.add_paragraph(strategist_note)

    if report.report_json.get("market_accounts"):
        document.add_heading("Market Context", level=1)
        for account in report.report_json.get("market_accounts", []):
            account_paragraph = document.add_paragraph(style="List Bullet")
            account_run = account_paragraph.add_run(account.get("name", "Unknown account"))
            account_run.bold = True
            if account.get("city"):
                account_paragraph.add_run(f" | {account['city']}")
            if account.get("institution_type"):
                account_paragraph.add_run(f" | {account['institution_type']}")

    document.add_heading("SWOT", level=1)
    for title_text, items in (
        ("Strengths", report.swot_json.get("strengths", [])),
        ("Weaknesses", report.swot_json.get("weaknesses", [])),
        ("Opportunities", report.swot_json.get("opportunities", [])),
        ("Threats", report.swot_json.get("threats", [])),
    ):
        document.add_heading(title_text, level=2)
        _add_bullets(document, items)

    document.add_heading("Market Gap", level=1)
    _add_key_value(document, "Unmet Need", report.market_gap_json.get("unmet_need", "N/A"))
    _add_key_value(document, "Competitor Gap", report.market_gap_json.get("competitor_gap", "N/A"))
    _add_key_value(document, "Your Gap", report.market_gap_json.get("your_gap", "N/A"))
    _add_key_value(document, "Positioning Space", report.market_gap_json.get("positioning_space", "N/A"))

    document.add_heading("Guideline Coverage And Advantages", level=1)
    for title_text, items in (
        ("Your Advantages", report.guideline_advantages_json.get("your_advantages", [])),
        ("Competitor Advantages", report.guideline_advantages_json.get("competitor_advantages", [])),
        ("Clinical Watchouts", report.guideline_advantages_json.get("clinical_watchouts", [])),
    ):
        document.add_heading(title_text, level=2)
        _add_bullets(document, items)

    document.add_heading("Marketing Campaigns", level=1)
    campaigns = report.campaigns_json or []
    if campaigns:
        for index, campaign in enumerate(campaigns, start=1):
            document.add_heading(f"{index}. {campaign.get('name', 'Untitled Campaign')}", level=2)
            _add_key_value(document, "Audience", campaign.get("audience", "N/A"))
            _add_key_value(document, "Message", campaign.get("message", "N/A"))
            _add_key_value(document, "Channel Mix", campaign.get("channel_mix", "N/A"))
            _add_key_value(document, "Proof Point", campaign.get("proof_point", "N/A"))
            _add_key_value(document, "Call To Action", campaign.get("call_to_action", "N/A"))
    else:
        document.add_paragraph("No campaigns saved.")

    document.add_heading("Sales Pitch", level=1)
    document.add_paragraph(report.sales_pitch_text or "No sales pitch saved.")

    document.add_heading("Recommended Next Steps", level=1)
    _add_bullets(document, report.report_json.get("recommended_next_steps", []))

    if latest_log:
        document.add_section(WD_SECTION.CONTINUOUS)
        document.add_heading("LLM Audit", level=1)
        audit_table = document.add_table(rows=2, cols=3)
        audit_table.style = "Table Grid"
        audit_items = [
            ("Provider", latest_log.provider),
            ("Model", latest_log.model_name),
            ("Prompt Tokens", str(latest_log.prompt_tokens)),
            ("Response Tokens", str(latest_log.response_tokens)),
            ("Total Tokens", str(latest_log.total_tokens)),
            ("Estimated Cost USD", str(latest_log.estimated_cost_usd)),
        ]
        for index, (label, value) in enumerate(audit_items):
            cell = audit_table.cell(index // 3, index % 3)
            shade_cell(cell, "F4F7FA")
            paragraph = cell.paragraphs[0]
            label_run = paragraph.add_run(f"{label}\n")
            label_run.bold = True
            label_run.font.color.rgb = accent
            paragraph.add_run(value or "N/A")

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer


def build_comparison_run_docx(run):
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Pt, RGBColor
    except ModuleNotFoundError as exc:
        raise ValueError("python-docx is not installed. Please install requirements.txt before exporting Word files.") from exc

    def shade_cell(cell, fill: str):
        cell_properties = cell._tc.get_or_add_tcPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), fill)
        cell_properties.append(shading)

    document = Document()
    section = document.sections[0]
    section.top_margin = Pt(54)
    section.bottom_margin = Pt(54)
    section.left_margin = Pt(54)
    section.right_margin = Pt(54)

    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10.5)
    styles["Title"].font.name = "Aptos Display"
    styles["Title"].font.size = Pt(24)
    styles["Title"].font.bold = True
    styles["Heading 1"].font.name = "Aptos Display"
    styles["Heading 1"].font.size = Pt(15)
    styles["Heading 2"].font.name = "Aptos Display"
    styles["Heading 2"].font.size = Pt(12)

    accent = RGBColor(11, 74, 114)
    muted = RGBColor(96, 96, 96)

    title = document.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title_run = title.add_run(run.name or f"Comparison Run {run.pk}")
    title_run.font.color.rgb = accent

    eyebrow = document.add_paragraph()
    eyebrow.alignment = WD_ALIGN_PARAGRAPH.LEFT
    eyebrow_run = eyebrow.add_run("MedStratix Head-To-Head Comparison")
    eyebrow_run.bold = True
    eyebrow_run.font.size = Pt(9)
    eyebrow_run.font.color.rgb = muted

    summary = run.summary_json or {}
    document.add_paragraph(
        "This report captures the saved comparison run, including your selected panel set, "
        "the competitor panel set, and any summary metadata stored with the run."
    )

    meta_table = document.add_table(rows=2, cols=2)
    meta_table.style = "Table Grid"
    meta_pairs = [
        ("Run Name", run.name or f"Comparison Run {run.pk}"),
        ("Created By", getattr(run.created_by, "username", "System")),
        ("Disease Filter", run.disease_filter or "All diseases"),
        ("Linked Marketing Plans", str(run.marketing_plans.count())),
    ]
    for index, (label, value) in enumerate(meta_pairs):
        cell = meta_table.cell(index // 2, index % 2)
        shade_cell(cell, "EAF2F8")
        paragraph = cell.paragraphs[0]
        label_run = paragraph.add_run(f"{label}\n")
        label_run.bold = True
        label_run.font.color.rgb = accent
        paragraph.add_run(value)

    document.add_heading("Your Panels", level=1)
    for panel in run.your_panels.all():
        document.add_paragraph(
            f"{panel.company.name} | {panel.name} | {panel.get_sample_type_display()} | Price BDT: {panel.price or 'N/A'} | TAT: {panel.tat or 'N/A'}",
            style="List Bullet",
        )

    document.add_heading("Competitor Panels", level=1)
    for panel in run.competitor_panels.all():
        document.add_paragraph(
            f"{panel.company.name} | {panel.name} | {panel.get_sample_type_display()} | Price BDT: {panel.price or 'N/A'} | TAT: {panel.tat or 'N/A'}",
            style="List Bullet",
        )

    if summary:
        document.add_heading("Stored Summary", level=1)
        for key, value in summary.items():
            document.add_paragraph(f"{key}: {value}")

    if run.marketing_plans.exists():
        document.add_heading("Linked Marketing Plans", level=1)
        for plan in run.marketing_plans.all():
            document.add_paragraph(f"{plan.title} | {plan.output_style} | {plan.created_at}", style="List Bullet")

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer
