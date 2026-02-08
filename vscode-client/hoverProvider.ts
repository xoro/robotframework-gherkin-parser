import * as vscode from "vscode";

interface KeywordInfo {
  keyword: string;
  file: string;
  line: number;
  documentation?: string;
  arguments?: string[];
  tags?: string[];
  priority?: number;
}

export class GherkinHoverProvider implements vscode.HoverProvider {
  private keywordCache: Map<string, KeywordInfo[]> = new Map();
  private cacheTimestamp: number = 0;
  private readonly CACHE_TIMEOUT = 30000; // 30 seconds

  async provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
    token: vscode.CancellationToken,
  ): Promise<vscode.Hover | undefined> {
    // Check if we're in a Gherkin step
    const line = document.lineAt(position.line);
    const stepMatch = line.text.match(/^\s*(Given|When|Then|And|But)\s+(.+)$/i);

    if (!stepMatch) {
      return undefined;
    }

    const stepText = stepMatch[2].trim();

    // Refresh keyword cache if needed
    await this.refreshKeywordCache(document.uri);

    // Find matching keywords
    const matches = this.findMatchingKeywords(stepText);

    if (matches.length === 0) {
      return undefined;
    }

    // Create hover content
    const markdownContent = new vscode.MarkdownString();
    markdownContent.isTrusted = true;

    for (let i = 0; i < matches.length; i++) {
      const match = matches[i];

      if (i > 0) {
        markdownContent.appendMarkdown("\n\n---\n\n");
      }

      // Keyword name
      markdownContent.appendCodeblock(match.keyword, "robotframework");

      // File location
      const relativePath = vscode.workspace.asRelativePath(match.file);
      markdownContent.appendMarkdown(
        `\n**Location:** [${relativePath}:${match.line + 1}](${vscode.Uri.file(match.file)}#${match.line + 1})`,
      );

      // Arguments
      if (match.arguments && match.arguments.length > 0) {
        markdownContent.appendMarkdown(`\n\n**Arguments:** ${match.arguments.join(", ")}`);
      }

      // Tags
      if (match.tags && match.tags.length > 0) {
        markdownContent.appendMarkdown(`\n\n**Tags:** ${match.tags.join(", ")}`);
      }

      // Documentation
      if (match.documentation) {
        markdownContent.appendMarkdown(`\n\n**Documentation:**\n${match.documentation}`);
      }
    }

    return new vscode.Hover(markdownContent);
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
      let currentKeywordInfo: KeywordInfo | null = null;

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmedLine = line.trim();

        // Check for *** Keywords *** section
        if (trimmedLine.match(/^\*\*\*\s*Keywords\s*\*\*\*$/i)) {
          inKeywordsSection = true;
          continue;
        }

        // Check for other sections
        if (trimmedLine.match(/^\*\*\*.*\*\*\*$/)) {
          inKeywordsSection = false;
          if (currentKeywordInfo) {
            this.addKeywordToCache(currentKeywordInfo);
            currentKeywordInfo = null;
          }
          continue;
        }

        if (inKeywordsSection && trimmedLine) {
          // Check if this is a keyword definition
          if (!line.startsWith("    ") && !line.startsWith("\t") && trimmedLine !== "") {
            // Save previous keyword if exists
            if (currentKeywordInfo) {
              this.addKeywordToCache(currentKeywordInfo);
            }

            // Skip lines that are clearly not keyword definitions
            if (trimmedLine.startsWith("[") || trimmedLine.startsWith("#")) {
              continue;
            }

            // Start new keyword
            currentKeywordInfo = {
              keyword: trimmedLine,
              file: fileUri.fsPath,
              line: i,
              arguments: [],
              tags: [],
              documentation: "",
            };
          } else if (currentKeywordInfo) {
            // Parse keyword settings
            if (trimmedLine.startsWith("[Documentation]")) {
              const docMatch = trimmedLine.match(/\[Documentation\]\s*(.+)/);
              if (docMatch) {
                currentKeywordInfo.documentation = docMatch[1];
              }
            } else if (trimmedLine.startsWith("[Arguments]")) {
              const argsMatch = trimmedLine.match(/\[Arguments\]\s*(.+)/);
              if (argsMatch) {
                currentKeywordInfo.arguments = argsMatch[1].split(/\s+/);
              }
            } else if (trimmedLine.startsWith("[Tags]")) {
              const tagsMatch = trimmedLine.match(/\[Tags\]\s*(.+)/);
              if (tagsMatch) {
                currentKeywordInfo.tags = tagsMatch[1].split(/\s+/);
              }
            }
          }
        }
      }

      // Don't forget the last keyword
      if (currentKeywordInfo) {
        this.addKeywordToCache(currentKeywordInfo);
      }
    } catch (error) {
      console.error(`Error parsing resource file ${fileUri.fsPath}:`, error);
    }
  }

  private addKeywordToCache(keywordInfo: KeywordInfo): void {
    const normalizedKey = this.normalizeForMatching(keywordInfo.keyword);
    if (!this.keywordCache.has(normalizedKey)) {
      this.keywordCache.set(normalizedKey, []);
    }

    // Check if this exact keyword already exists (avoid true duplicates)
    const existingKeywords = this.keywordCache.get(normalizedKey)!;
    const isDuplicate = existingKeywords.some(
      (existing) =>
        existing.keyword === keywordInfo.keyword &&
        existing.file === keywordInfo.file &&
        existing.line === keywordInfo.line,
    );

    if (!isDuplicate) {
      existingKeywords.push(keywordInfo);
    }
  }

  private createKeywordPattern(keyword: string): RegExp {
    // Handle Robot Framework variable patterns like ${variable}
    let pattern = keyword
      .replace(/[.*+?^${}()|[\]\\]/g, "\\$&") // Escape regex special chars
      .replace(/\\\$\\\{[^}]+\\\}/g, "(.+?)"); // Convert ${var} to capture groups

    // Handle quoted strings with variables
    pattern = pattern.replace(/["'](.+?)["']/g, (match, content) => {
      if (content.includes("${")) {
        return `(?:["']${content}["']|${content})`;
      }
      return match;
    });

    // Make the pattern case-insensitive and allow for flexible whitespace
    pattern = pattern.replace(/\s+/g, "\\s+");

    return new RegExp(`^${pattern}$`, "i");
  }

  private findMatchingKeywords(stepText: string): KeywordInfo[] {
    const matches: KeywordInfo[] = [];

    // Clean and normalize the step text
    const cleanStepText = stepText.replace(/^["']|["']$/g, "").trim();
    const normalizedStep = this.normalizeForMatching(cleanStepText);

    // First, try direct lookup for exact matches (much faster)
    const directMatches = this.keywordCache.get(normalizedStep);
    if (directMatches) {
      matches.push(...directMatches.map((match) => ({ ...match, priority: 1 })));
    }

    // Then try pattern matching for keywords with variables
    for (const [normalizedKeyword, keywordInfos] of this.keywordCache) {
      // Skip if we already found exact matches for this normalized keyword
      if (normalizedKeyword === normalizedStep) {
        continue;
      }

      for (const keywordInfo of keywordInfos) {
        const pattern = this.createKeywordPattern(keywordInfo.keyword);
        if (pattern.test(cleanStepText)) {
          matches.push({ ...keywordInfo, priority: 2 });
        }
      }
    }

    // Sort by priority and remove duplicates
    return matches.sort((a, b) => (a.priority || 999) - (b.priority || 999)).slice(0, 2); // Limit to top 2 matches for hover
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
