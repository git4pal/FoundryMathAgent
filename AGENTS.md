# Project Guidance

This project was built with the microsoft-foundry skill. Before working on or
answering questions about Foundry agents, read the microsoft-foundry skill first.
If you are in VS Code, read the vscode-microsoft-foundry skill first.

Keep the prompt-agent definition and client-side Python executor separate.
Never enable web search or return unvalidated model prose. Preserve strict
whole-query validation and the exact fallback string. Run
`python -m unittest discover -s tests -v` after behavior changes. Never commit
`.env`, credentials, or the virtual environment.