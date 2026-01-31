# Contributing to Robotframework Gherkin Parser

## Fork Workflow for Contributing

This document outlines the workflow for maintaining a synced fork while adding features.

### Initial Setup (Already Done)
```bash
git remote add upstream https://github.com/robotcodedev/robotframework-gherkin-parser.git
git remote -v  # Should show 'origin' (your fork) and 'upstream' (original repo)
```

### Adding New Features - Step by Step

#### 1. Sync your main with upstream BEFORE starting new work
```bash
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
```

#### 2. Create feature branch from synced main
```bash
git checkout -b feature/your-feature-name
# Example: git checkout -b feature/syntax-highlighting
```

#### 3. Do your development work
```bash
# Make your changes
git add .
git commit -m "feat: add your feature description"
```

#### 4. Push feature branch and create PR
```bash
git push origin feature/your-feature-name
```
Then create PR: `your-fork:feature/your-feature-name` → `robotcodedev:main`

#### 5. Merge feature to your main (for personal use)
```bash
git checkout main
git merge feature/your-feature-name
git push origin main
```

#### 6. Clean up feature branch (optional)
```bash
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

### Regular Maintenance

#### Sync with upstream regularly
```bash
git checkout main
git fetch upstream
git merge upstream/main  # Should be clean since you're based on their commits
git push origin main
```

### Key Benefits of This Workflow
- ✅ Your main stays compatible with original repository
- ✅ Each PR shows only your specific feature changes  
- ✅ No merge conflicts when syncing with upstream
- ✅ You keep all your features in your fork's main branch
- ✅ Clean contribution history for the original project

### Emergency: If You Mess Up the History

If you accidentally rewrite history or get out of sync:

```bash
# Reset your main to match upstream exactly
git checkout main
git fetch upstream
git reset --hard upstream/main
git push --force-with-lease origin main

# Then re-apply your features from feature branches
git merge feature/gherkin-go-to-definition
git push origin main
```

### Current Repository Status
- **Origin**: https://github.com/PcGnCLwnCm9EgY56mAmL/robotframework-gherkin-parser.git (your fork)
- **Upstream**: https://github.com/robotcodedev/robotframework-gherkin-parser.git (original)
- **Current Features**: Go to Definition and Hover support for Gherkin steps

### Git Configuration
Your commits are configured to use:
- **Name**: PcGnCLwnCm9EgY56mAmL  
- **Email**: r.kaligis@gmail.com

To verify: `git config user.name && git config user.email`