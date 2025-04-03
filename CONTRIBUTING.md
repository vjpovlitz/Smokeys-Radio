# Contributing to Smokey's Radio

Thank you for considering contributing to Smokey's Radio! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How Can I Contribute?

### Reporting Bugs

When reporting bugs, please include:

1. A clear and descriptive title
2. Steps to reproduce the bug
3. Expected behavior
4. Actual behavior
5. Screenshots if applicable
6. Your environment details (OS, Python version, etc.)

### Suggesting Features

We welcome feature suggestions! Please provide:

1. A clear description of the feature
2. Why this feature would be useful to most users
3. Any implementation ideas you have

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature or fix
3. Implement your changes
4. Add or update tests as needed
5. Ensure your code follows the project's style
6. Submit a pull request

## Development Setup

1. Fork and clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   python setup_audio.py
   ```
3. Create a `.env` file with your test bot token
4. Run tests before submitting changes

## Style Guidelines

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Comment complex sections of code
- Keep functions focused on a single responsibility

## Adding New Bypass Methods

When adding new bypass methods:

1. Add your method to the `try_extraction_methods` function
2. Update the statistics tracking to include your method
3. Document the method in the README
4. Provide testing evidence that it works with restricted content

## Testing

Before submitting a pull request:

1. Test with multiple song types (restricted and non-restricted)
2. Test all commands to ensure they still work
3. Check for any performance issues

## Questions?

If you have questions about contributing, please open an issue with your question.

Thank you for helping improve Smokey's Radio! 