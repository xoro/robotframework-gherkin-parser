import * as vscode from "vscode";
import { parseGherkinDocument } from "./parseGherkinDocument";
import {
  customPretty,
  IndentationConfig,
  IndentationProfile,
  getProfileIndentation,
  scsIndentation,
} from "./customPretty";

interface CustomIndentationSettings {
  Feature?: number;
  Background?: number;
  Scenario?: number;
  Step?: number;
  Examples?: number;
  example?: number;
  given?: number;
  when?: number;
  then?: number;
  and?: number;
  but?: number;
  featureTag?: number;
  scenarioTag?: number;
}

function getIndentationConfig(): IndentationConfig {
  const cfg = vscode.workspace.getConfiguration("gherkinParser.format.indentation");
  const profile = cfg.get<IndentationProfile>("profile", "scs");

  // For named profiles, return the preset directly
  if (profile !== "custom") {
    return getProfileIndentation(profile);
  }

  // Custom profile: read from the single JSON object setting
  const custom = cfg.get<CustomIndentationSettings>("custom", {});
  const base = scsIndentation;

  return {
    Feature: custom.Feature ?? base.Feature,
    Background: custom.Background ?? base.Background,
    Scenario: custom.Scenario ?? base.Scenario,
    Step: custom.Step ?? base.Step,
    Examples: custom.Examples ?? base.Examples,
    example: custom.example ?? base.example,
    given: custom.given ?? base.given,
    when: custom.when ?? base.when,
    then: custom.then ?? base.then,
    and: custom.and ?? base.and,
    but: custom.but ?? base.but,
    "feature tag": custom.featureTag ?? base["feature tag"],
    "scenario tag": custom.scenarioTag ?? base["scenario tag"],
  };
}

export class GherkinFormattingEditProvider implements vscode.DocumentFormattingEditProvider {
  provideDocumentFormattingEdits(
    document: vscode.TextDocument,
    options: vscode.FormattingOptions,
    token: vscode.CancellationToken,
  ): vscode.ProviderResult<vscode.TextEdit[]> {
    const gherkinSource = document.getText();
    const { gherkinDocument } = parseGherkinDocument(gherkinSource);
    if (gherkinDocument === undefined) return [];
    const config = getIndentationConfig();
    const newText = customPretty(gherkinDocument, config);
    const lines = gherkinSource.split(/\r?\n/);
    const line = lines.length - 1;
    const character = lines[line].length;
    const textEdit: vscode.TextEdit = new vscode.TextEdit(new vscode.Range(0, 0, line, character), newText);
    return [textEdit];
  }
}
