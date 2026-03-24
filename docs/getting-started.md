# Getting Started

## Installation

```bash
# From source
git clone https://github.com/Tekel-Studio/tekeldb.git
cd tekeldb
pip install -e .

# Verify
tekel --version
```

## Create Your First Database

```bash
mkdir my-project && cd my-project

# Initialize with the built-in project management schema
tekel init --schema pm
```

This creates:

```
.tekel/
├── schema.json     # defines collections, field types, rules
├── config.json     # database settings
└── data/
    ├── tasks/
    ├── milestones/
    └── contacts/
```

## Add Documents

tekel doesn't write data — you do. Create JSON files directly:

```json
// .tekel/data/tasks/TASK-0001.json
{
  "id": "TASK-0001",
  "title": "Design landing page",
  "status": "open",
  "priority": "high",
  "assignee": "elif",
  "tags": ["design", "website"]
}
```

Or use any tool you like — scripts, AI agents, `jq`, whatever writes JSON files.

## Validate

```bash
tekel validate
# All documents valid.

# Auto-fix missing defaults
tekel validate --fix
```

## Query

```bash
# List all tasks
tekel list tasks

# Filter
tekel list tasks status:open priority:high

# Sort and limit
tekel list tasks --sort -priority --limit 5

# Output as JSON
tekel list tasks status:!done --format json

# Full-text search
tekel find "landing page"

# Count with grouping
tekel count tasks --group-by status
```

## View a Document

```bash
tekel show TASK-0001
```

## Export

```bash
tekel export --collection tasks --format json --output tasks.json
tekel export --collection tasks --format csv --output tasks.csv
```

## What's Next

- [Schema Guide](schema.md) — define your own collections and field types
- [CLI Reference](cli.md) — all commands and options
- [CI/CD Integration](ci-cd.md) — validate in your pipeline
