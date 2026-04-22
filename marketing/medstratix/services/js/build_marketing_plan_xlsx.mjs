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
  ["Marketing Plan", payload.title || "Untitled Plan"],
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

const sectionsSheet = addSheet("Sections");
writeTable(sectionsSheet, "A1", payload.sectionRows || [["section", "item", "value"]]);
sectionsSheet.getRange("A1:C1").format = {
  fill: "#EAF2F8",
  font: { bold: true, color: "#0B4A72" },
};
sectionsSheet.getRange("A:C").format.wrapText = true;
sectionsSheet.getRange("A1:C500").format.autofitColumns();
sectionsSheet.freezePanes.freezeRows(1);

const modelSheet = addSheet("Spreadsheet Model");
writeTable(modelSheet, "A1", payload.spreadsheetRows || [["row_type", "label", "period", "formula_logic", "numeric_value", "notes"]]);
modelSheet.getRange("A1:F1").format = {
  fill: "#EAF2F8",
  font: { bold: true, color: "#0B4A72" },
};
modelSheet.getRange("A1:F500").format.wrapText = true;
modelSheet.getRange("A1:F500").format.autofitColumns();
modelSheet.freezePanes.freezeRows(1);

const ganttSheet = addSheet("Gantt Data");
writeTable(ganttSheet, "A1", payload.ganttRows || [["task", "phase", "owner", "start_period", "end_period", "dependency", "status_signal"]]);
ganttSheet.getRange("A1:G1").format = {
  fill: "#EAF2F8",
  font: { bold: true, color: "#0B4A72" },
};
ganttSheet.getRange("A1:G500").format.wrapText = true;
ganttSheet.getRange("A1:G500").format.autofitColumns();
ganttSheet.freezePanes.freezeRows(1);

const output = await SpreadsheetFile.exportXlsx(workbook);
await fs.mkdir(path.dirname(outputPath), { recursive: true });
await output.save(outputPath);
