# Contributing to Tax Commander

First off, thank you for considering contributing to Tax Commander! It's people like you that make this tool better for Tioga Township and beyond.

## 🤝 How to Contribute

### Reporting Bugs
This section guides you through submitting a bug report for Tax Commander. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

**Perform a search** to see if the problem has already been reported. If it has, add a comment to the existing issue instead of opening a new one.

### Suggesting Enhancements
This section guides you through submitting an enhancement suggestion for Tax Commander, including completely new features and minor improvements to existing functionality.

### Pull Requests
1.  **Fork the repo** and create your branch from `master`.
2.  **Test your changes**! Run the full simulation suite (`bash tests/simulation_run.sh`) to ensuring nothing broke.
3.  **Update documentation** if your change affects how the tool is used.
4.  **Issue that pull request!**

## 💻 Development Setup

We use `uv` for dependency management and tooling.

```bash
# Clone the repository
git clone git@github.com:charles-forsyth/tax-commander.git
cd tax-commander

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e .
```

## 🧪 Testing
The project includes a comprehensive simulation suite that mimics a full tax year ("The Gauntlet").

```bash
bash tests/simulation_run.sh
```
All tests must pass before a PR can be merged.

## 🎨 Coding Style
*   Follow PEP 8 conventions.
*   Keep functions small and focused.
*   Document complex logic (especially tax calculations).
*   **Safety First:** Never write code that could accidentally delete financial records. Use "Reversals" instead of deletions.
