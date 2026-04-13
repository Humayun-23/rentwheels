# Contributing

Thanks for your interest in contributing to RentWheels.

## Quick start

1. Fork the repository and create a new branch.
2. Make your changes with clear, focused commits.
3. Open a pull request with a concise description of what changed and why.

## Development setup

- Python 3.11+
- Docker + Docker Compose (for the local stack)

### Local run (Docker)

```bash
docker compose up -d --build
```

### Local run (Python)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Configuration

Create a `.env` file in the repository root with the required settings. See `.env.example` if available.

## Code style

- Keep changes small and focused.
- Prefer clear, descriptive names.
- Add tests for new behavior when feasible.

## Tests

If tests exist, run them before submitting a PR:

```bash
pytest
```

## Security

If you discover a security issue, please do not open a public issue. Email the maintainer instead.

## Pull request checklist

- [ ] The change is scoped and documented.
- [ ] New behavior has tests (or a note explains why not).
- [ ] The app starts locally.
