# **Robot Framework Gherkin Parser (Extended)**: Quick Overview

The **Robot Framework Gherkin Parser (Extended)** enables seamless integration of Gherkin feature files with the **Robot Framework**, facilitating behavior-driven development (BDD) with enhanced IDE support. This extended version adds **Go to Definition** and **Hover** functionality for Gherkin steps in VS Code, allowing you to navigate directly from Gherkin steps to their Robot Framework keyword implementations.

## 🆕 New Features in Extended Version

- **Go to Definition**: Ctrl+Click or F12 on any Gherkin step to jump to its keyword implementation in `.resource` files
- **Hover Information**: Hover over steps to see keyword signatures, documentation, arguments, and file locations
- **Variable Support**: Handles Robot Framework variables (`${variable}`) in step definitions
- **Smart Matching**: Supports exact matches, pattern matching, and fuzzy matching for keyword discovery

[**📖 Read detailed documentation about Go to Definition features**](./GOTO_DEFINITION.md)

---

The **Robot Framework Gherkin Parser** enables seamless integration of Gherkin feature files with the **Robot Framework**, facilitating behavior-driven development (BDD) with ease. This integration not only allows for the flexible execution of Gherkin feature files alongside **Robot Framework** test files but also highlights the complementary strengths of both approaches. Gherkin feature files, with their less technical and more scenario-focused syntax, emphasize the behavioral aspects of what is being tested, rather than the how. In contrast, **Robot Framework** test files tend to be more technical, focusing on the step-by-step implementation of test scenarios through keyword sequences.

Utilizing a slightly modified version of the official [Cucumber Gherkin Parser](https://github.com/cucumber/gherkin), this custom parser implementation ensures the direct execution of Gherkin scenarios within the **Robot Framework** environment. This supports efficient transitions to and from BDD practices, catering to both technical and non-technical stakeholders by bridging the gap between business requirements and technical implementation.

The **Robot Framework Gherkin Parser** simplifies test step implementation, allowing technical testers to implement test steps in the **Robot Framework**'s keyword-driven language. This is particularly beneficial when compared to the traditional BDD approach, which might require complex programming skills for step definitions in languages such as Java or C#. The parser thereby reduces the barrier to BDD test creation and maintenance, making it more accessible.

## Core Features

- **Focus on Behavioral Testing**: Gherkin feature files allow for specifying test scenarios in a less technical, more narrative form, focusing on what needs to be tested rather than how it is to be tested. This complements the more technically oriented **Robot Framework** test files, providing a balanced approach to defining and executing tests.
- **User-Friendly Test Implementation**: Technical testers can easily implement test steps in the **Robot Framework**'s intuitive language, avoiding the complexity of traditional programming languages for BDD step definitions.
- **Efficient Execution and Porting**: Enables direct execution and easy porting of Gherkin feature files, bridging the gap between Gherkin's scenario-focused syntax and the **Robot Framework**'s technical implementation.
- **Seamless Development Environment**: The inclusion of a plugin/extension for [RobotCode](https://robotcode.io) enhances the development and testing process within Visual Studio Code, offering integrated tools tailored for both BDD and automated testing.

Designed for teams leveraging the **Robot Framework** and looking to integrate or enhance their BDD methodology, the **Robot Framework Gherkin Parser** facilitates a comprehensive testing strategy. It encourages a collaborative testing environment by simplifying the creation of BDD tests and improving testing efficiency and flexibility.

Explore the subsequent sections for details on integrating this parser into your testing strategy, optimizing its usage, and contributing to its development.

## Requirements

Only the Parser

* Python 3.8 or above
* Robotframework 7.0 and above

For Support in VSCode

* VSCode version 1.82 and above

## Installation

The **Robot Framework Gherkin Parser** can be installed using the following methods:

- **Pip**: The parser can be installed using pip, the Python package manager. Run the following command to install the parser:

  ```bash
  pip install robotframework-gherkin-parser
  ```

If you are using the [RobotCode](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode) extension for VSCode as your IDE, you can install the [**RobotCode GherkinParser Support** extension](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode-gherkin) from the VSCode Marketplace.


## Usage

## On command line

To execute `.feature` files using the **Robot Framework Gherkin Parser** on command line, you need to use the `robot` command line option `--parser` to specify the parser to be used. The following command demonstrates how to execute a `.feature` file using the **Robot Framework Gherkin Parser**:

```bash
robot --parser GherkinParser path/to/your/feature/file.feature
```

## IDE

### Visual Studio Code with [RobotCode](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode) extension

If the plugin-extension for [**RobotCode GherkinParser Support** extension](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode-gherkin) is installed in VSCode

By creating a `robot.toml` file in your project root and adding the following configuration:

```toml
[parsers]
GherkinParser=[]
```

NOT IMPLEMENTED YET: ~~You can enable the GherkinParser by the VSCode Setting: `robotcode.robot.parsers`~~

## Security and Configuration

### ⚠️ Breaking Changes in v0.4.2+

For security reasons, **automatic resource import** and **hook execution** are now **disabled by default** to prevent arbitrary code execution vulnerabilities. These features must be explicitly enabled via environment variables in trusted environments only.

### Environment Variables

#### `GHERKIN_PARSER_ENABLE_HOOKS`

Controls whether keywords tagged with `hook:*` (e.g., `hook:before-suite`, `hook:before-test`) are automatically executed during test suite initialization.

- **Default**: `0` (disabled)
- **Values**: `1`, `true`, `yes`, `on` to enable
- **Security Impact**: When enabled, any keyword tagged with a hook prefix will execute automatically without explicit reference in feature files. Only enable in fully trusted test environments.

**Example:**
```bash
# Enable hook execution (trusted environment only)
export GHERKIN_PARSER_ENABLE_HOOKS=1
robot --parser GherkinParser features/
```

#### `GHERKIN_PARSER_AUTO_IMPORT_RESOURCES`

Controls whether `.resource` files are automatically discovered and imported from the feature file directory tree.

- **Default**: `0` (disabled)
- **Values**: `1`, `true`, `yes`, `on` to enable
- **Security Impact**: When enabled, all `.resource` files under the feature directory are automatically imported. Only enable in trusted project directories.

**Example:**
```bash
# Enable automatic resource import (trusted environment only)
export GHERKIN_PARSER_AUTO_IMPORT_RESOURCES=1
robot --parser GherkinParser features/
```

#### Combined Usage

```bash
# Enable both features (trusted environment only)
export GHERKIN_PARSER_ENABLE_HOOKS=1
export GHERKIN_PARSER_AUTO_IMPORT_RESOURCES=1
robot --parser GherkinParser features/
```

### Security Best Practices

1. **Default Behavior is Secure**: The parser is secure by default - dangerous features are opt-in only
2. **Trusted Environments Only**: Only enable these features in controlled, trusted test environments
3. **CI/CD Considerations**: Be cautious when enabling these features in CI/CD pipelines that process external contributions
4. **Explicit Resource Imports**: When auto-import is disabled, explicitly import resources in your feature files using Robot Framework's `Resource` setting
5. **Manual Hook Invocation**: When hooks are disabled, explicitly call setup/teardown keywords in your test suites

### Migration from v0.4.1 and Earlier

If you were relying on automatic resource import or hook execution:

1. **Review your test setup** to understand which features you were using
2. **Enable the required features** via environment variables in your test execution environment
3. **Consider refactoring** to use explicit imports and setup/teardown for better clarity and security

### Additional Security Improvements (v0.4.3+)

- **Symlink Protection**: Directory symlinks are skipped by default during file discovery to prevent infinite loop attacks via symlink cycles
- **Cycle Detection**: When symlink following is explicitly enabled, visited directories are tracked to prevent infinite loops
- **Depth Limiting**: Optional maximum recursion depth can be configured programmatically for additional safety

These protections ensure the parser can safely scan untrusted directory structures without risk of denial-of-service via crafted filesystem layouts.

## Examples

The following example demonstrates a simple Gherkin feature file that can be executed using the **Robot Framework Gherkin Parser**:

Create a folder named `features` in your project root.
Create a file named `calculator.feature` in the folder `features` with the following content:

```gherkin
Feature: Calculator
  As a user
  I want to use a calculator
  So that I can perform basic arithmetic operations

  Scenario: Add two numbers
    Given I have entered 50 into the calculator
    And I have entered 70 into the calculator
    When I press add
    Then the result should be 120 on the screen
```

To execute the `calculator.feature` file using the **Robot Framework Gherkin Parser** on command line, run the following command:

```bash
robot --parser GherkinParser features/calculator.feature
```

If your are using VSCode + RobotCode + RobotCode GherkinParser Support, you can run the test by clicking on the play buttons in the feature file.



## Contributing

TODO
