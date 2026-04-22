import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const [, , inputPath, outputPath] = process.argv;

if (!inputPath || !outputPath) {
  console.error("Usage: node build_marketing_plan_xlsx.mjs <input.json> <output.xlsx>");
  process.exit(1);
}

const rawInput = await fs.readFile(inputPath, "utf8");
const payload = JSON.parse(rawInput.replace(/^\uFEFF/, ""));
const workbook = Workbook.create();

function columnName(index) {
  let value = index + 1;
  let label = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    label = String.fromCharCode(65 + remainder) + label;
    value = Math.floor((value - 1) / 26);
  }
  return label;
}

function headerRange(rows) {
  if (!rows?.length || !rows[0]?.length) {
    return null;
  }
  return `A1:${columnName(rows[0].length - 1)}1`;
}

function bodyRange(rows) {
  if (!rows?.length || !rows[0]?.length) {
    return null;
  }
  return `A1:${columnName(rows[0].length - 1)}500`;
}

function addSheet(name) {
  return workbook.worksheets.add(name);
}

function writeTable(sheet, startCell, rows) {
  if (!rows || !rows.length) {
    return;
  }
  sheet.getRange(startCell).write(rows);
}

const summarySheet = addSheet("Plan Summary");
summarySheet.showGridLines = false;
writeTable(summarySheet, "A1", [
  [payload.reportKind === "final_marketing_report" ? "Final Report" : "Marketing Plan", payload.title || "Untitled Plan"],
  ["Plan Type", payload.planTypeLabel || payload.planType || ""],
  ["Geography", payload.geography || ""],
  ["Disease Focus", payload.diseaseFocus || ""],
  ["LLM Model", payload.llmModel || ""],
  ["Summary", payload.summary || ""],
  ["Planning Horizon", payload.salesExpectation?.planning_horizon || ""],
  ["Expected Monthly Samples", payload.salesExpectation?.expected_monthly_samples || ""],
  ["Expected Quarterly Revenue (BDT)", payload.salesExpectation?.expected_quarterly_revenue_bdt || ""],
  ["Expected Year-One Revenue (BDT)", payload.salesExpectation?.expected_year_one_revenue_bdt || ""],
  ["Revenue Guardrail Note", payload.salesExpectation?.revenue_guardrail_note || ""],
]);
summarySheet.getRange("A1:A11").format = {
  fill: "#0B4A72",
  font: { bold: true, color: "#FFFFFF" },
};
summarySheet.getRange("B1:B11").format.wrapText = true;
summarySheet.getRange("A1:B11").format.autofitColumns();
summarySheet.freezePanes.freezeRows(1);

if (payload.chronologyRows?.length) {
  const chronologySheet = addSheet("Chronology");
  writeTable(chronologySheet, "A1", payload.chronologyRows);
  const range = headerRange(payload.chronologyRows);
  const fullRange = bodyRange(payload.chronologyRows);
  if (range) {
    chronologySheet.getRange(range).format = {
      fill: "#EAF2F8",
      font: { bold: true, color: "#0B4A72" },
    };
  }
  if (fullRange) {
    chronologySheet.getRange(fullRange).format.wrapText = true;
    chronologySheet.getRange(fullRange).format.autofitColumns();
  }
  chronologySheet.freezePanes.freezeRows(1);
}

if (payload.kpiRows?.length) {
  const kpiSheet = addSheet("KPI Summary");
  writeTable(kpiSheet, "A1", payload.kpiRows);
  const range = headerRange(payload.kpiRows);
  const fullRange = bodyRange(payload.kpiRows);
  if (range) {
    kpiSheet.getRange(range).format = {
      fill: "#EAF2F8",
      font: { bold: true, color: "#0B4A72" },
    };
  }
  if (fullRange) {
    kpiSheet.getRange(fullRange).format.wrapText = true;
    kpiSheet.getRange(fullRange).format.autofitColumns();
  }
  kpiSheet.freezePanes.freezeRows(1);
}

if (payload.timelineRows?.length) {
  const timelineSheet = addSheet("Executive Timeline");
  writeTable(timelineSheet, "A1", payload.timelineRows);
  const range = headerRange(payload.timelineRows);
  const fullRange = bodyRange(payload.timelineRows);
  if (range) {
    timelineSheet.getRange(range).format = {
      fill: "#EAF2F8",
      font: { bold: true, color: "#0B4A72" },
    };
  }
  if (fullRange) {
    timelineSheet.getRange(fullRange).format.wrapText = true;
    timelineSheet.getRange(fullRange).format.autofitColumns();
  }
  timelineSheet.freezePanes.freezeRows(1);
}

const sectionsSheet = addSheet("Sections");
writeTable(sectionsSheet, "A1", payload.sectionRows || [["section", "item", "value"]]);
const sectionsHeader = headerRange(payload.sectionRows || [["section", "item", "value"]]);
const sectionsBody = bodyRange(payload.sectionRows || [["section", "item", "value"]]);
if (sectionsHeader) {
  sectionsSheet.getRange(sectionsHeader).format = {
    fill: "#EAF2F8",
    font: { bold: true, color: "#0B4A72" },
  };
}
if (sectionsBody) {
  sectionsSheet.getRange(sectionsBody).format.wrapText = true;
  sectionsSheet.getRange(sectionsBody).format.autofitColumns();
}
sectionsSheet.freezePanes.freezeRows(1);

const modelSheet = addSheet("Spreadsheet Model");
writeTable(modelSheet, "A1", payload.spreadsheetRows || [["row_type", "label", "period", "formula_logic", "numeric_value", "notes"]]);
const modelHeader = headerRange(payload.spreadsheetRows || [["row_type", "label", "period", "formula_logic", "numeric_value", "notes"]]);
const modelBody = bodyRange(payload.spreadsheetRows || [["row_type", "label", "period", "formula_logic", "numeric_value", "notes"]]);
if (modelHeader) {
  modelSheet.getRange(modelHeader).format = {
    fill: "#EAF2F8",
    font: { bold: true, color: "#0B4A72" },
  };
}
if (modelBody) {
  modelSheet.getRange(modelBody).format.wrapText = true;
  modelSheet.getRange(modelBody).format.autofitColumns();
}
modelSheet.freezePanes.freezeRows(1);

const ganttSheet = addSheet("Gantt Data");
writeTable(ganttSheet, "A1", payload.ganttRows || [["task", "phase", "owner", "start_period", "end_period", "dependency", "status_signal"]]);
const ganttHeader = headerRange(payload.ganttRows || [["task", "phase", "owner", "start_period", "end_period", "dependency", "status_signal"]]);
const ganttBody = bodyRange(payload.ganttRows || [["task", "phase", "owner", "start_period", "end_period", "dependency", "status_signal"]]);
if (ganttHeader) {
  ganttSheet.getRange(ganttHeader).format = {
    fill: "#EAF2F8",
    font: { bold: true, color: "#0B4A72" },
  };
}
if (ganttBody) {
  ganttSheet.getRange(ganttBody).format.wrapText = true;
  ganttSheet.getRange(ganttBody).format.autofitColumns();
}
ganttSheet.freezePanes.freezeRows(1);

const output = await SpreadsheetFile.exportXlsx(workbook);
await fs.mkdir(path.dirname(outputPath), { recursive: true });
await output.save(outputPath);
