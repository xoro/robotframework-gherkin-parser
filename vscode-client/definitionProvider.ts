import * as vscode from "vscode";

interface KeywordMatch {
  keyword: string;
  file: string;
  line: number;
  pattern?: RegExp;
  priority?: number;
}

export class GherkinDefinitionProvider implements vscode.DefinitionProvider {
  private keywordCache: Map<string, KeywordMatch[]> = new Map();
  private cacheTimestamp: number = 0;
  private readonly CACHE_TIMEOUT = 30000; // 30 seconds

  async provideDefinition(
    document: vscode.TextDocument,
    position: vscode.Position,
    token: vscode.CancellationToken,
  ): Promise<vscode.Definition | undefined> {
    // Check if we're in a Gherkin step
    const line = document.lineAt(position.line);
    const stepMatch = line.text.match(/^\s*(Given|When|Then|And|But)\s+(.+)$/i);

    if (!stepMatch) {
      return undefined;
    }

    const stepText = stepMatch[2].trim();
    console.log(`[GherkinDefinitionProvider] Looking for definition of: "${stepText}"`);

    // Refresh keyword cache if needed
    await this.refreshKeywordCache(document.uri);

    // Find matching keywords
    const matches = this.findMatchingKeywords(stepText);
    console.log(
      `[GherkinDefinitionProvider] Found ${matches.length} matches:`,
      matches.map((m) => `${m.keyword} (priority: ${m.priority})`),
    );

    if (matches.length === 0) {
      console.log(`[GherkinDefinitionProvider] No matches found for: "${stepText}"`);
      return undefined;
    }

    // Convert matches to VS Code locations
    const definitions: vscode.Location[] = [];
    for (const match of matches) {
      try {
        const uri = vscode.Uri.file(match.file);
        const location = new vscode.Location(uri, new vscode.Position(match.line, 0));
        definitions.push(location);
      } catch (error) {
        console.error(`Error creating location for ${match.file}:${match.line}`, error);
      }
    }

    return definitions.length > 0 ? definitions : undefined;
  }

  private async refreshKeywordCache(documentUri: vscode.Uri): Promise<void> {
    const now = Date.now();
    if (now - this.cacheTimestamp < this.CACHE_TIMEOUT && this.keywordCache.size > 0) {
      return;
    }

    this.keywordCache.clear();
    this.cacheTimestamp = now;

    // Find workspace folder
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(documentUri);
    if (!workspaceFolder) {
      return;
    }

    // Look for .resource files in steps directories
    const pattern = new vscode.RelativePattern(workspaceFolder, "**/steps/**/*.resource");
    const resourceFiles = await vscode.workspace.findFiles(pattern);

    // Also look for .resource files in the general workspace (as a fallback)
    const generalPattern = new vscode.RelativePattern(workspaceFolder, "**/*.resource");
    const allResourceFiles = await vscode.workspace.findFiles(generalPattern);

    // Combine and deduplicate
    const uniqueFiles = [...new Set([...resourceFiles, ...allResourceFiles])];

    // Parse each resource file
    for (const fileUri of uniqueFiles) {
      await this.parseResourceFile(fileUri);
    }
  }

  private async parseResourceFile(fileUri: vscode.Uri): Promise<void> {
    try {
      const document = await vscode.workspace.openTextDocument(fileUri);
      const content = document.getText();
      const lines = content.split(/\r?\n/);

      let inKeywordsSection = false;
      let currentKeyword: string | null = null;

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmedLine = line.trim();

        // Check for *** Keywords *** section
        if (trimmedLine.match(/^\*\*\*\s*Keywords\s*\*\*\*$/i)) {
          inKeywordsSection = true;
          continue;
        }

        // Check for other sections (*** Settings ***, *** Variables ***, etc.)
        if (trimmedLine.match(/^\*\*\*.*\*\*\*$/)) {
          inKeywordsSection = false;
          continue;
        }

        if (inKeywordsSection && trimmedLine) {
          // Check if this is a keyword definition (not indented or minimally indented)
          if (!line.startsWith("    ") && !line.startsWith("\t") && trimmedLine !== "") {
            // Skip lines that are clearly not keyword definitions
            if (trimmedLine.startsWith("[") || trimmedLine.startsWith("#")) {
              continue;
            }

            currentKeyword = trimmedLine;

            // Store the keyword
            const filePath = fileUri.fsPath;
            const keywordMatch: KeywordMatch = {
              keyword: currentKeyword,
              file: filePath,
              line: i,
              pattern: this.createKeywordPattern(currentKeyword),
            };

            if (!this.keywordCache.has(currentKeyword.toLowerCase())) {
              this.keywordCache.set(currentKeyword.toLowerCase(), []);
            }
            this.keywordCache.get(currentKeyword.toLowerCase())!.push(keywordMatch);
          }
        }
      }
    } catch (error) {
      console.error(`Error parsing resource file ${fileUri.fsPath}:`, error);
    }
  }

  private createKeywordPattern(keyword: string): RegExp {
    // Handle Robot Framework variable patterns like ${variable}
    // Convert them to regex patterns that can match actual values

    // Escape special regex characters except ${} patterns
    let pattern = keyword
      .replace(/[.*+?^${}()|[\]\\]/g, "\\$&") // Escape regex special chars
      .replace(/\\\$\\\{[^}]+\\\}/g, "(.+?)"); // Convert ${var} to capture groups

    // Handle quoted strings with variables
    pattern = pattern.replace(/["'](.+?)["']/g, (match, content) => {
      // If the content has variables, make the quotes optional
      if (content.includes("${")) {
        return `(?:["']${content}["']|${content})`;
      }
      return match;
    });

    // Make the pattern case-insensitive and allow for flexible whitespace
    pattern = pattern.replace(/\s+/g, "\\s+");

    return new RegExp(`^${pattern}$`, "i");
  }

  private findMatchingKeywords(stepText: string): KeywordMatch[] {
    const matches: KeywordMatch[] = [];

    // Clean the step text - remove quotes and normalize
    const cleanStepText = stepText.replace(/^["']|["']$/g, "").trim();

    for (const [, keywordMatches] of this.keywordCache) {
      for (const keywordMatch of keywordMatches) {
        // Normalize both step and keyword for comparison
        const normalizedStep = this.normalizeForMatching(cleanStepText);
        const normalizedKeyword = this.normalizeForMatching(keywordMatch.keyword);

        console.log(`[GherkinDefinitionProvider] Comparing:`);
        console.log(`  Step: "${cleanStepText}" -> normalized: "${normalizedStep}"`);
        console.log(`  Keyword: "${keywordMatch.keyword}" -> normalized: "${normalizedKeyword}"`);

        // Exact match after normalization - highest priority
        if (normalizedStep === normalizedKeyword) {
          console.log(`  -> EXACT MATCH!`);
          matches.push({ ...keywordMatch, priority: 1 });
          continue;
        }

        // Pattern match with variables - high priority
        if (keywordMatch.pattern && keywordMatch.pattern.test(cleanStepText)) {
          console.log(`  -> PATTERN MATCH!`);
          matches.push({ ...keywordMatch, priority: 2 });
          continue;
        }

        console.log(`  -> No match`);
      }
    }

    // Sort by priority (lower number = higher priority)
    return matches.sort((a, b) => (a.priority || 999) - (b.priority || 999));
  }

  private normalizeForMatching(text: string): string {
    return (
      text
        .toLowerCase()
        // Remove Gherkin keywords at the start
        .replace(/^(given|when|then|and|but)\s+/i, "")
        // Replace variables with placeholder
        .replace(/\$\{[^}]+\}/g, "VAR")
        // Normalize whitespace and punctuation
        .replace(/[^\w\s]/g, " ")
        .replace(/\s+/g, " ")
        .trim()
    );
  }
}
