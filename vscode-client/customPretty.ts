import * as messages from "@cucumber/messages";
import { walkGherkinDocument } from "@cucumber/gherkin-utils";

export interface IndentationConfig {
  Feature: number;
  Background: number;
  Scenario: number;
  Step: number;
  Examples: number;
  example: number;
  given: number;
  when: number;
  then: number;
  and: number;
  but: number;
  "feature tag": number;
  "scenario tag": number;
}

/**
 * Gherkin Default: standard Cucumber indentation (2-space levels).
 */
export const gherkinDefaultIndentation: IndentationConfig = {
  Feature: 0,
  Background: 2,
  Scenario: 2,
  Step: 4,
  Examples: 4,
  example: 6,
  given: 4,
  when: 4,
  then: 4,
  and: 4,
  but: 4,
  "feature tag": 0,
  "scenario tag": 2,
};

/**
 * SCS Profile: aligned Given/When/Then/And/But for visual clarity.
 */
export const scsIndentation: IndentationConfig = {
  Feature: 0,
  Background: 2,
  Scenario: 2,
  Step: 4,
  Examples: 2,
  example: 4,
  given: 4,
  when: 5,
  then: 5,
  and: 6,
  but: 6,
  "feature tag": 0,
  "scenario tag": 2,
};

/** Alias - the SCS profile is the default for this extension. */
export const defaultIndentation: IndentationConfig = scsIndentation;

export type IndentationProfile = "gherkinDefault" | "scs" | "custom";

export function getProfileIndentation(profile: IndentationProfile): IndentationConfig {
  switch (profile) {
    case "gherkinDefault":
      return gherkinDefaultIndentation;
    case "scs":
      return scsIndentation;
    case "custom":
    default:
      return scsIndentation;
  }
}

function spaces(n: number): string {
  return " ".repeat(n);
}

function getStepIndent(keyword: string, config: IndentationConfig): number {
  const k = keyword.trim().toLowerCase();
  if (k === "given") return config.given;
  if (k === "when") return config.when;
  if (k === "then") return config.then;
  if (k === "and") return config.and;
  if (k === "but") return config.but;
  return config.Step;
}

function escapeCell(s: string): string {
  let e = "";
  for (const c of s.split("")) {
    switch (c) {
      case "\\":
        e += "\\\\";
        break;
      case "\n":
        e += "\\n";
        break;
      case "|":
        e += "\\|";
        break;
      default:
        e += c;
    }
  }
  return e;
}

function isNumeric(s: string): boolean {
  return !isNaN(parseFloat(s));
}

function formatTableRows(rows: readonly messages.TableRow[], indentLevel: number): string {
  if (rows.length === 0) return "";

  const maxWidths: number[] = new Array<number>(rows[0].cells.length).fill(0);
  for (const row of rows) {
    row.cells.forEach((cell, j) => {
      maxWidths[j] = Math.max(maxWidths[j], escapeCell(cell.value).length);
    });
  }

  let s = "";
  for (const row of rows) {
    const cells = row.cells.map((cell, j) => {
      const escaped = escapeCell(cell.value);
      const padding = " ".repeat(maxWidths[j] - escaped.length);
      return isNumeric(escaped) ? padding + escaped : escaped + padding;
    });
    s += `${spaces(indentLevel)}| ${cells.join(" | ")} |\n`;
  }
  return s;
}

function formatTags(tags: readonly messages.Tag[], indentLevel: number): string {
  if (!tags || tags.length === 0) return "";
  return spaces(indentLevel) + tags.map((t) => t.name).join(" ") + "\n";
}

function formatDescription(description: string | undefined, indentLevel: number): string {
  if (!description) return "";
  const lines = description.split("\n");
  return (
    lines
      .map((line) => {
        const trimmed = line.trim();
        return trimmed ? spaces(indentLevel) + trimmed : "";
      })
      .join("\n") + "\n"
  );
}

/**
 * Custom Gherkin pretty-printer with configurable per-keyword indentation.
 *
 * Default indentation follows the common BDD style:
 *   Feature: 0, Background/Scenario/Examples: 2, Given: 4, When/Then: 5, And/But: 6
 */
export function customPretty(
  gherkinDocument: messages.GherkinDocument,
  config: IndentationConfig = defaultIndentation,
): string {
  let currentStepIndent = config.Step;

  return walkGherkinDocument<string>(gherkinDocument, "", {
    comment(comment, content) {
      return content + comment.text + "\n";
    },

    feature(feature, content) {
      let result = content;

      // Add blank line after comments (e.g. copyright headers)
      if (result.length > 0 && !result.endsWith("\n\n")) {
        result += "\n";
      }

      // Language header (omit for English)
      if (feature.language && feature.language !== "en") {
        result += `# language: ${feature.language}\n`;
      }

      // Tags
      result += formatTags(feature.tags || [], config["feature tag"]);

      // Keyword line
      result += spaces(config.Feature) + feature.keyword + ": " + feature.name + "\n";

      // Description
      if (feature.description) {
        result += formatDescription(feature.description, config.Feature + 2);
      }

      return result;
    },

    rule(rule, content) {
      let result = content + "\n";
      if (rule.tags && rule.tags.length > 0) {
        result += formatTags(rule.tags, config.Background);
      }
      result += spaces(config.Background) + rule.keyword + ": " + rule.name + "\n";
      if (rule.description) {
        result += formatDescription(rule.description, config.Background + 2);
      }
      return result;
    },

    background(background, content) {
      let result = content + "\n";
      result += spaces(config.Background) + background.keyword + ": " + background.name + "\n";
      if (background.description) {
        result += formatDescription(background.description, config.Background + 2);
      }
      return result;
    },

    scenario(scenario, content) {
      let result = content + "\n";

      // Tags
      result += formatTags(scenario.tags || [], config["scenario tag"]);

      // Keyword line
      result += spaces(config.Scenario) + scenario.keyword + ": " + scenario.name + "\n";

      // Description
      if (scenario.description) {
        result += formatDescription(scenario.description, config.Scenario + 2);
      }

      return result;
    },

    examples(examples, content) {
      let result = content + "\n";

      // Tags
      result += formatTags(examples.tags || [], config.Examples);

      // Keyword line
      result += spaces(config.Examples) + examples.keyword + ": " + examples.name + "\n";

      // Description
      if (examples.description) {
        result += formatDescription(examples.description, config.Examples + 2);
      }

      // Table rows
      const tableRows = examples.tableHeader ? [examples.tableHeader, ...examples.tableBody] : [];
      result += formatTableRows(tableRows, config.example);

      return result;
    },

    step(step, content) {
      currentStepIndent = getStepIndent(step.keyword, config);
      return content + spaces(currentStepIndent) + step.keyword + step.text + "\n";
    },

    dataTable(dataTable, content) {
      return content + formatTableRows(dataTable.rows || [], currentStepIndent + 2);
    },

    docString(docString, content) {
      const docIndent = currentStepIndent + 2;
      const prefix = spaces(docIndent);
      const delimiter = (docString.delimiter || '"""').substring(0, 3);

      let docContent = docString.content.replace(/^/gm, prefix);
      if (delimiter === '"""') {
        docContent = docContent.replace(/"""/gm, '\\"\\"\\"');
      } else {
        docContent = docContent.replace(/```/gm, "\\`\\`\\`");
      }

      return (
        content +
        prefix +
        delimiter +
        (docString.mediaType || "") +
        "\n" +
        docContent +
        "\n" +
        prefix +
        delimiter +
        "\n"
      );
    },
  });
}
