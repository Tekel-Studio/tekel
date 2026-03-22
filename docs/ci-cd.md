# CI/CD Integration

tekel is designed to run in pipelines. `tekel validate` returns exit code `0` when all documents are valid and `1` when errors are found.

## GitHub Actions

### Validate on every push

```yaml
name: Validate tekel
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install .
      - run: tekel validate
```

### Validate only changed files (faster for large databases)

```yaml
      - name: Validate changed documents
        run: |
          CHANGED=$(git diff --name-only ${{ github.event.before }} ${{ github.sha }} | grep '.tekel/data/' || true)
          if [ -n "$CHANGED" ]; then
            tekel validate --files $CHANGED
          fi
```

### JUnit output for test dashboards

```yaml
      - run: tekel validate --format junit > test-results.xml
        continue-on-error: true
      - uses: dorny/test-reporter@v1
        with:
          name: tekel validation
          path: test-results.xml
          reporter: java-junit
```

### JSON output for custom processing

```yaml
      - run: tekel validate --format json > validation.json
      - run: |
          ERRORS=$(python -c "import json; data=json.load(open('validation.json')); print(sum(len(f['errors']) for r in data for f in r['files']))")
          echo "Validation errors: $ERRORS"
```

## Git Pre-Commit Hook

Block invalid commits locally before they reach CI:

```bash
tekel hook install
```

This writes a pre-commit hook to `.git/hooks/pre-commit` that validates staged YAML files. Invalid documents block the commit:

```
$ git commit -m "update tasks"
tekel: validating staged documents...
TASK-0012.yaml:
  - status "wip" is not a valid enum value
Commit aborted. Run 'tekel validate --fix' to auto-correct fixable issues.
```

Remove with:

```bash
tekel hook uninstall
```

## GitLab CI

```yaml
validate-data:
  image: python:3.12
  script:
    - pip install .
    - tekel validate --format junit > report.xml
  artifacts:
    reports:
      junit: report.xml
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All documents valid |
| `1` | Validation errors found |

## Validate Specific Files

For incremental validation in PRs, pass specific file paths:

```bash
tekel validate --files .tekel/data/tasks/TASK-0001.yaml .tekel/data/tasks/TASK-0002.yaml
```

This is faster than validating the entire database and is what the pre-commit hook uses internally.
