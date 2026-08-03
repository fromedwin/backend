# Contributing

We love your input! We want to make contributing to FromEdwin Monitor as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## 🚀 Getting Started

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/monitor.git
   cd monitor
   ```
3. **Set up development environment** (requires [uv](https://docs.astral.sh/uv/)):
   ```bash
   uv sync
   ```
4. **Run the development server**:
   ```bash
   docker compose up -d
   ```

### Development Workflow

1. **Create a branch** for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes** and commit them:
   ```bash
   git commit -m "Add your descriptive commit message"
   ```
3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
4. **Open a Pull Request** on GitHub

## 🐛 Reporting Bugs

We use GitHub Issues to track bugs. Report a bug by [opening a new issue](https://github.com/fromedwin/monitor/issues/new).

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## 💡 Suggesting Features

We use GitHub Issues to track feature requests too! When suggesting a feature:

1. **Check existing issues** first to avoid duplicates
2. **Describe the problem** you're solving
3. **Describe the solution** you'd like
4. **Describe alternatives** you've considered

## 📝 Documentation

Documentation improvements are always welcome! You can:

- Fix typos or improve clarity
- Add examples
- Write tutorials
- Improve API documentation

Documentation is built with Sphinx and uses Markdown files in the `docs/` directory.

## 🧪 Testing

- Write tests for new features
- Ensure existing tests pass
- Run the test suite: `python manage.py test`

## 📋 Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions small and focused

## 🏷️ Pull Request Guidelines

1. **Reference related issues** in your PR description
2. **Include tests** for new functionality
3. **Update documentation** if needed
4. **Keep PRs focused** - one feature/fix per PR
5. **Write clear commit messages**

## ❓ Questions?

Feel free to ask questions by:
- Opening a GitHub Issue with the "question" label
- Starting a GitHub Discussion
- Reaching out to maintainers

## 🎉 Recognition

Contributors will be recognized in our [Contributors](contributors.md) page. Thank you for helping make FromEdwin Monitor better!

---

By contributing, you agree that your contributions will be licensed under the MIT License. 