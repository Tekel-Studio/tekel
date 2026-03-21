# tekeldb

A schema-driven, flat-file document database.

Each document is a YAML file. Each collection is a directory. The `.tekeldb/` folder is the entire database. A CLI provides CRUD operations, structured queries, and schema validation. No server, no daemon, no dependencies beyond Python.

## Install

```bash
pip install -e .
```

## Quick Start

```bash
# Initialize with the built-in project management schema
tekeldb init --schema pm

# Create documents
tekeldb create tasks "Design landing page" --assignee elif --priority high
tekeldb create tasks "Fix login bug" --priority critical --assignee mehmet
tekeldb create contacts "Elif Yilmaz" --email elif@co.com --company "Acme Corp"

# View a document
tekeldb show TASK-0001

# List and filter
tekeldb list tasks                                    # all tasks
tekeldb list tasks status:open priority:high          # open AND high priority
tekeldb list tasks assignee:elif                      # elif's tasks
tekeldb list tasks title:~landing                     # title contains "landing"
tekeldb list tasks status:!done --format json         # not-done as JSON
tekeldb list tasks --sort -priority --limit 5         # top 5 by priority

# Edit with transition validation
tekeldb edit TASK-0001 --status in-progress
tekeldb edit TASK-0001 --assignee mehmet --priority critical

# Delete
tekeldb delete TASK-0001

# Validate all documents against the schema
tekeldb validate

# Database summary
tekeldb status
```

## How It Works

```
.tekeldb/
├── schema.yaml          # Entity definitions, field types, rules
├── config.yaml          # Database settings
├── counters.yaml        # Auto-increment state
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
    transitions:
      status:
        open: [in-progress, backlog]
        in-progress: [review, open]
        review: [done, in-progress]
        done: [archived]
```

**Field types:** `string`, `text`, `integer`, `float`, `boolean`, `date`, `datetime`, `enum`, `list`, `object`

**Field options:** `required`, `default`, `auto` (datetime), `min`/`max`, `format` (email/url), `values` (enum), `unique`

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
| `tekeldb create <collection> <title> [--field value ...]` | Create a document |
| `tekeldb show <id>` | Display a document |
| `tekeldb list <collection> [filters] [--sort field] [--format fmt] [--limit n]` | Query documents |
| `tekeldb edit <id> [--field value ...]` | Update a document |
| `tekeldb delete <id> [--yes]` | Delete a document |
| `tekeldb validate [--collection name] [--fix]` | Validate against schema |
| `tekeldb status` | Database summary |
| `tekeldb schema show` | Print the schema |

## License

MIT
