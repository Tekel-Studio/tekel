# Getting Started

## Installation

```bash
# From source
git clone https://github.com/youruser/tekeldb.git
cd tekeldb
pip install -e .

# Verify
tekeldb --version
```

## Create Your First Database

```bash
mkdir my-project && cd my-project

# Initialize with the built-in project management schema
tekeldb init --schema pm
```

This creates:

```
.tekeldb/
├── schema.yaml     # defines collections, field types, rules
├── config.yaml     # database settings
└── data/
    ├── tasks/
    ├── milestones/
    └── contacts/
```

## Add Documents

tekeldb doesn't write data — you do. Create YAML files directly:

```yaml
# .tekeldb/data/tasks/TASK-0001.yaml
id: TASK-0001
title: Design landing page
status: open
priority: high
assignee: elif
tags:
  - design
  - website
```

Or use any tool you like — vim, scripts, AI agents, `yq`, `sed`, whatever writes text files.

## Validate

```bash
tekeldb validate
# All documents valid.

# Auto-fix missing defaults
tekeldb validate --fix
```

## Query

```bash
# List all tasks
tekeldb list tasks

# Filter
tekeldb list tasks status:open priority:high

# Sort and limit
tekeldb list tasks --sort -priority --limit 5

# Output as JSON
tekeldb list tasks status:!done --format json

# Full-text search
tekeldb find "landing page"

# Count with grouping
tekeldb count tasks --group-by status
```

## View a Document

```bash
tekeldb show TASK-0001
```

## Export

```bash
tekeldb export --collection tasks --format json --output tasks.json
tekeldb export --collection tasks --format csv --output tasks.csv
```

## What's Next

- [Schema Guide](schema.md) — define your own collections and field types
- [CLI Reference](cli.md) — all commands and options
- [CI/CD Integration](ci-cd.md) — validate in your pipeline
