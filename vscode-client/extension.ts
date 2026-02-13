import * as vscode from "vscode";
import { GherkinFormattingEditProvider } from "./formattingEditProvider";
import { GherkinDefinitionProvider } from "./definitionProvider";
import { GherkinHoverProvider } from "./hoverProvider";
import { GherkinReferenceProvider } from "./referenceProvider";

export async function activateAsync(context: vscode.ExtensionContext): Promise<void> {
  const robotcode = vscode.extensions.getExtension("d-biehl.robotcode");
  if (!robotcode) {
    return;
  }
  await robotcode.activate();
  // const robotcodeExtensionApi = robotcode.exports;
  // if (!robotcodeExtensionApi) {
  //   return;
  // }

  const definitionProvider = new GherkinDefinitionProvider();
  const hoverProvider = new GherkinHoverProvider();
  const referenceProvider = new GherkinReferenceProvider();

  context.subscriptions.push(
    vscode.languages.registerDocumentFormattingEditProvider("gherkin", new GherkinFormattingEditProvider()),
    vscode.languages.registerDefinitionProvider("gherkin", definitionProvider),
    vscode.languages.registerDefinitionProvider("markdown", definitionProvider),
    vscode.languages.registerHoverProvider("gherkin", hoverProvider),
    vscode.languages.registerHoverProvider("markdown", hoverProvider),
    vscode.languages.registerReferenceProvider("robotframework", referenceProvider),
  );
}

function displayProgress<R>(promise: Promise<R>): Thenable<R> {
  const progressOptions: vscode.ProgressOptions = {
    location: vscode.ProgressLocation.Window,
    title: "RobotCode Gherkin extension loading ...",
  };
  return vscode.window.withProgress(progressOptions, () => promise);
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  return displayProgress(activateAsync(context));
}

export async function deactivate(): Promise<void> {
  return Promise.resolve();
}
