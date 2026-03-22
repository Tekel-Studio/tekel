# tekeldb

structured, queryable, schema-validated data that lives in your repo and flows through your pipelines.

tekeldb gives any Git repository a built-in, schema-validated, queryable document database — no server, no driver, just files that flow through your existing pipelines.

Each document is a YAML file. Each collection is a directory. The `.tekeldb/` folder is the entire database. A CLI provides schema validation, structured queries, and formatted output. No server, no daemon, no dependencies beyond Python.

tekeldb does not write your data. You write it — by hand, by script, by agent. tekeldb validates it, queries it, and gates it in CI/CD.

## Install

```bash
pip install -e .
```

## Quick Start

```bash
# Initialize with the built-in project management schema
tekeldb init --schema pm

# Documents are written by you — YAML files in .tekeldb/data/<collection>/
# Use any tool: vim, scripts, AI agents, sed, yq, etc.

# View a document
tekeldb show TASK-0001

# List and filter
tekeldb list tasks                                    # all tasks
tekeldb list tasks status:open priority:high          # open AND high priority
tekeldb list tasks assignee:elif                      # elif's tasks
tekeldb list tasks title:~landing                     # title contains "landing"
tekeldb list tasks status:!done --format json         # not-done as JSON
tekeldb list tasks --sort -priority --limit 5         # top 5 by priority

# Validate all documents against the schema
tekeldb validate
tekeldb validate --fix                                # auto-correct fixable issues

# Database summary
tekeldb status
```

## How It Works

```
.tekeldb/
├── schema.yaml          # Entity definitions, field types, rules
├── config.yaml          # Database settings
└── data/
    ├── tasks/
    │   ├── TASK-0001.yaml
    │   └── TASK-0002.yaml
    └── contacts/
        └── CONT-0001.yaml
```

The files *are* the data. Copy the folder and you've copied the database. Edit a file in vim and you've updated a record. Put it in Git and every change is versioned, diffable, and mergeable.

## Schema

The schema defines collections, field types, validation rules, and state transitions:

```yaml
version: "1.0"
name: project-management

collections:
  tasks:
    id_prefix: TASK
    fields:
      title: { type: string, required: true }
      status:
        type: enum
        values: [backlog, open, in-progress, review, done, archived]
        default: open
      priority:
        type: enum
        values: [low, medium, high, critical]
        default: medium
      assignee: { type: string }
      due: { type: date }
      tags: { type: list, items: string }
      payload: { type: any }
    transitions:
      status:
        open: [in-progress, backlog]
        in-progress: [review, open]
        review: [done, in-progress]
        done: [archived]
```

**Field types:** `string`, `text`, `integer`, `float`, `boolean`, `date`, `datetime`, `enum`, `list`, `object`, `any`

**Field options:** `required`, `default`, `auto` (datetime), `min`/`max`, `format` (email/url), `values` (enum), `unique`, `additional_fields` (per collection, default: true)

Run `tekeldb init` without `--schema` for schema-free mode (any YAML, no validation).

## Filter Operators

| Syntax | Meaning |
|--------|---------|
| `field:value` | Exact match (case-insensitive) |
| `field:!value` | Not equal |
| `field:~value` | Contains (substring) |
| `field:>value` | Greater than |
| `field:<value` | Less than |
| `field:>=value` | Greater than or equal |
| `field:<=value` | Less than or equal |

Multiple filters are combined with AND logic. For list fields, `field:value` checks membership.

## Output Formats

```bash
tekeldb list tasks --format table   # default, fixed-width columns
tekeldb list tasks --format yaml    # YAML documents
tekeldb list tasks --format json    # JSON array
tekeldb list tasks --format csv     # CSV with headers
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `tekeldb init [--schema name\|path]` | Create a new database |
| `tekeldb show <id>` | Display a document |
| `tekeldb list <collection> [filters] [--sort field] [--format fmt] [--limit n]` | Query documents |
| `tekeldb validate [--collection name] [--fix]` | Validate against schema |
| `tekeldb status` | Database summary |
| `tekeldb schema show` | Print the schema |

## Works with Unix Tools

Because documents are plain YAML files in directories, every standard tool already works:

```bash
# grep — search across all documents
grep -rl "assignee: elif" .tekeldb/data/tasks/
grep -l "priority: critical" .tekeldb/data/tasks/*

# find — locate by file metadata
find .tekeldb/data/ -name "*.yaml" -mtime -1       # modified today
find .tekeldb/data/contacts/ -name "*.yaml" | wc -l # count contacts

# yq — YAML-aware queries
yq '.assignee' .tekeldb/data/tasks/*.yaml | sort -u
yq '.tags[]' .tekeldb/data/tasks/*.yaml | sort | uniq -c | sort -rn

# sed — bulk edits
sed -i 's/assignee: elif/assignee: mehmet/' .tekeldb/data/tasks/*.yaml

# xargs — batch operations
grep -l "status: archived" .tekeldb/data/tasks/* | xargs rm

# git — full audit trail for free
git log -p .tekeldb/data/tasks/TASK-0001.yaml
git blame .tekeldb/data/tasks/TASK-0001.yaml

# cat — no CLI needed to read a record
cat .tekeldb/data/tasks/TASK-0001.yaml
```

The CLI adds schema validation, typed queries, transition enforcement, and formatted output. For everything else, the file format is the API.

## License

MIT

#### Note: I don't know how i got here, i just wanted to make games. It's all downhill from here. May god help us all
