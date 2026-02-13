import * as vscode from "vscode";
import { parseGherkinDocument } from "./parseGherkinDocument";
import { walkGherkinDocument } from "@cucumber/gherkin-utils";
import * as messages from "@cucumber/messages";

interface StepReference {
  uri: vscode.Uri;
  line: number;
  stepText: string;
}

/**
 * Provides "Find All References" for Robot Framework keyword definitions
 * in .resource files, showing where they are used in .feature / .feature.md files.
 */
export class GherkinReferenceProvider implements vscode.ReferenceProvider {
  private referenceCache: StepReference[] = [];
  private cacheTimestamp: number = 0;
  private readonly CACHE_TIMEOUT = 30000; // 30 seconds

  async provideReferences(
    document: vscode.TextDocument,
    position: vscode.Position,
    context: vscode.ReferenceContext,
    token: vscode.CancellationToken,
  ): Promise<vscode.Location[] | undefined> {
    // Only works in resource files
    if (!document.fileName.endsWith(".resource")) {
      return undefined;
    }

    // Find the keyword name at the cursor position
    const keywordName = this.getKeywordAtPosition(document, position);
    if (!keywordName) {
      return undefined;
    }

    console.log(`[GherkinReferenceProvider] Looking for references of: "${keywordName}"`);

    // Refresh step cache from feature files
    await this.refreshStepCache(document.uri, token);

    if (token.isCancellationRequested) return undefined;

    // Match steps against the keyword name (only feature file references)
    let locations = this.findReferences(keywordName);

    // Filter to closest parent folder to avoid duplicates from repo copies
    if (locations.length > 1) {
      locations = this.filterClosest(locations, document.uri);
    }

    console.log(`[GherkinReferenceProvider] Found ${locations.length} references`);
    return locations.length > 0 ? locations : undefined;
  }

  /**
   * Determine if the cursor is on a keyword definition line and return the keyword name.
   * Keyword definitions are non-indented lines inside a *** Keywords *** section.
   */
  private getKeywordAtPosition(document: vscode.TextDocument, position: vscode.Position): string | undefined {
    const lines = document.getText().split(/\r?\n/);
    const cursorLine = position.line;

    // Walk backwards to check we're inside a *** Keywords *** section
    let inKeywordsSection = false;
    for (let i = cursorLine; i >= 0; i--) {
      const trimmed = lines[i].trim();
      if (trimmed.match(/^\*\*\*\s*Keywords\s*\*\*\*$/i)) {
        inKeywordsSection = true;
        break;
      }
      if (trimmed.match(/^\*\*\*.*\*\*\*$/)) {
        // Hit another section before Keywords
        break;
      }
    }

    if (!inKeywordsSection) {
      return undefined;
    }

    // The line under the cursor must be a keyword definition (not indented, not a comment/section)
    const line = lines[cursorLine];
    const trimmed = line.trim();
    if (!trimmed || line.startsWith("    ") || line.startsWith("\t")) {
      // Indented line = keyword body, not the definition itself.
      // Walk up to find the parent keyword definition.
      for (let i = cursorLine - 1; i >= 0; i--) {
        const l = lines[i];
        const t = l.trim();
        if (t.match(/^\*\*\*.*\*\*\*$/)) break;
        if (t && !l.startsWith("    ") && !l.startsWith("\t") && !t.startsWith("[") && !t.startsWith("#")) {
          return t;
        }
      }
      return undefined;
    }

    if (trimmed.startsWith("[") || trimmed.startsWith("#") || trimmed.match(/^\*\*\*.*\*\*\*$/)) {
      return undefined;
    }

    return trimmed;
  }

  /**
   * Scan all .feature and .feature.md files in the workspace to build a cache of steps.
   */
  private async refreshStepCache(documentUri: vscode.Uri, token: vscode.CancellationToken): Promise<void> {
    const now = Date.now();
    if (now - this.cacheTimestamp < this.CACHE_TIMEOUT && this.referenceCache.length > 0) {
      return;
    }

    this.referenceCache = [];
    this.cacheTimestamp = now;

    const workspaceFolder = vscode.workspace.getWorkspaceFolder(documentUri);
    if (!workspaceFolder) return;

    // Find all feature files
    const featurePattern = new vscode.RelativePattern(workspaceFolder, "**/*.feature");
    const mdPattern = new vscode.RelativePattern(workspaceFolder, "**/*.feature.md");
    const [featureFiles, mdFiles] = await Promise.all([
      vscode.workspace.findFiles(featurePattern),
      vscode.workspace.findFiles(mdPattern),
    ]);

    const allFiles = [...featureFiles, ...mdFiles];

    for (const fileUri of allFiles) {
      if (token.isCancellationRequested) return;
      await this.parseFeatureFile(fileUri);
    }
  }

  /**
   * Parse a single feature file and extract all step texts with their locations.
   */
  private async parseFeatureFile(fileUri: vscode.Uri): Promise<void> {
    try {
      const document = await vscode.workspace.openTextDocument(fileUri);
      const source = document.getText();

      // For .feature.md files, the parseGherkinDocument may handle them differently,
      // but we can also do a simple regex scan as a reliable fallback.
      // First try Gherkin AST parsing:
      const { gherkinDocument } = parseGherkinDocument(source);

      if (gherkinDocument) {
        this.extractStepsFromAst(gherkinDocument, fileUri);
      } else {
        // Fallback: regex-based step extraction
        this.extractStepsWithRegex(source, fileUri);
      }
    } catch (error) {
      // Fallback to regex on any parse error
      try {
        const document = await vscode.workspace.openTextDocument(fileUri);
        this.extractStepsWithRegex(document.getText(), fileUri);
      } catch {
        console.error(`[GherkinReferenceProvider] Error parsing ${fileUri.fsPath}:`, error);
      }
    }
  }

  /**
   * Walk the Gherkin AST to extract step texts and line numbers.
   */
  private extractStepsFromAst(gherkinDocument: messages.GherkinDocument, fileUri: vscode.Uri): void {
    const cache = this.referenceCache;
    walkGherkinDocument<void>(gherkinDocument, undefined, {
      step(step) {
        if (step.location && step.text) {
          cache.push({
            uri: fileUri,
            line: step.location.line - 1, // VS Code is 0-based
            stepText: step.text.trim(),
          });
        }
      },
    });
  }

  /**
   * Regex fallback for extracting steps from feature file text (handles .feature.md too).
   */
  private extractStepsWithRegex(source: string, fileUri: vscode.Uri): void {
    const lines = source.split(/\r?\n/);
    // Match classic Gherkin steps and markdown-style steps (- Given ...)
    const stepRegex = /^\s*(?:-\s*)?(Given|When|Then|And|But)\s+(.+)$/i;

    for (let i = 0; i < lines.length; i++) {
      const match = lines[i].match(stepRegex);
      if (match) {
        this.referenceCache.push({
          uri: fileUri,
          line: i,
          stepText: match[2].trim(),
        });
      }
    }
  }

  /**
   * Match a keyword name against the cached steps.
   * Uses the same normalization logic as the definition provider.
   */
  private findReferences(keywordName: string): vscode.Location[] {
    const locations: vscode.Location[] = [];

    const keywordPattern = this.createKeywordPattern(keywordName);
    const normalizedKeyword = this.normalizeForMatching(keywordName);

    for (const ref of this.referenceCache) {
      const normalizedStep = this.normalizeForMatching(ref.stepText);

      // Exact match (after normalization)
      if (normalizedStep === normalizedKeyword) {
        locations.push(new vscode.Location(ref.uri, new vscode.Position(ref.line, 0)));
        continue;
      }

      // Pattern match (keyword has ${variables} that match step values)
      if (keywordPattern && keywordPattern.test(ref.stepText)) {
        locations.push(new vscode.Location(ref.uri, new vscode.Position(ref.line, 0)));
        continue;
      }
    }

    return locations;
  }

  /**
   * Keep only references from the feature files that share the longest common
   * path prefix with the resource file (i.e. the "closest" copy of the repo).
   */
  private filterClosest(locations: vscode.Location[], resourceUri: vscode.Uri): vscode.Location[] {
    const resourceDir = resourceUri.fsPath.replace(/\/[^\/]*$/, "");

    // Compute shared prefix length for each location
    const scored = locations.map((loc) => ({
      location: loc,
      commonLength: this.commonPrefixLength(resourceDir, loc.uri.fsPath),
    }));

    const maxLen = Math.max(...scored.map((s) => s.commonLength));
    return scored.filter((s) => s.commonLength === maxLen).map((s) => s.location);
  }

  /**
   * Return the length of the common directory prefix between two paths.
   */
  private commonPrefixLength(a: string, b: string): number {
    const aParts = a.split("/");
    const bParts = b.split("/");
    let len = 0;
    for (let i = 0; i < Math.min(aParts.length, bParts.length); i++) {
      if (aParts[i] === bParts[i]) {
        len += aParts[i].length + 1; // +1 for the separator
      } else {
        break;
      }
    }
    return len;
  }

  /**
   * Create a regex from a keyword name, converting ${variable} placeholders
   * into capture groups that match actual values in steps.
   */
  private createKeywordPattern(keyword: string): RegExp | null {
    // Only create a pattern if the keyword contains variables
    if (!keyword.includes("${")) {
      return null;
    }

    let pattern = keyword
      .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
      .replace(/\\\$\\\{[^}]+\\\}/g, "(.+?)");

    pattern = pattern.replace(/\s+/g, "\\s+");
    return new RegExp(`^${pattern}$`, "i");
  }

  /**
   * Normalize text for comparison — mirrors definitionProvider logic.
   */
  private normalizeForMatching(text: string): string {
    return text
      .toLowerCase()
      .replace(/^(given|when|then|and|but)\s+/i, "")
      .replace(/\$\{[^}]+\}/g, "VAR")
      .replace(/["'][^"']*["']/g, "VAR") // quoted strings → VAR to match ${var}
      .replace(/[^\w\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }
}
