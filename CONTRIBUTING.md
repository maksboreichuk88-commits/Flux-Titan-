# Contributing to Flux-Titan

First off, thanks for taking the time to contribute! 🎉

The following is a set of guidelines for contributing to Flux-Titan. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## How Can I Contribute?

### Reporting Bugs
This section guides you through submitting a bug report.
* Ensure the bug was not already reported by searching on GitHub under Issues.
* If you're unable to find an open issue addressing the problem, open a new one. Be sure to include a title and clear description, as much relevant information as possible, and a code sample or an executable test case demonstrating the expected behavior that is not occurring.

### Suggesting Enhancements
* Determine which repository the enhancement should be suggested in.
* Perform a search to see if the enhancement has already been suggested. If it has, add a comment to the existing issue instead of opening a new one.

### Pull Requests
The process described here has several goals:
* Maintain Flux-Titan's quality.
* Fix problems that are important to users.
* Engage the community in working toward the best possible Flux-Titan.

Please follow these steps to have your contribution considered by the maintainers:
1. Fork the repo and create your branch from `main`.
    ```bash
    git checkout -b feature/my-new-feature
    ```
2. If you've added code that should be tested, add tests.
3. Make sure the test suite passes locally.
4. Issue that pull request!

## Local Development Setup

To set up the project locally:

1. Clone the repository locally.
2. Ensure you have Python 3.11+ installed.
3. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install the package in editable mode:
   ```bash
   pip install -e .
   ```
5. Copy `.env.example` to `.env` and configure your local environment variables.
6. Try running the entry point:
   ```bash
   flux-titan
   ```

## Development Guidelines

* **Keep changes small and focused.** A pull request should do one thing and do it well.
* **Write Tests.** If you modify the RSS parser or summarizer, add test cases to ensure edge cases are handled.
* **Keep Dependencies Minimal.** We favor using standard libraries or lightweight proven libraries (like `httpx`, `aiohttp`) over large frameworks.
* **Keep State Local.** Runtime state (`processed.db`) should never be committed to the repository.

Thank you for contributing!
