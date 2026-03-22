# CLI Reference

## Database Lifecycle

### `tekeldb init`

Create a new database in the current directory.

```bash
tekeldb init                    # schema-free mode
tekeldb init --schema pm        # built-in project management schema
tekeldb init --schema ./my.yaml # custom schema file
```

### `tekeldb status`

Show database summary: name, collections, document counts, status breakdowns.

```bash
tekeldb status
```

### `tekeldb validate`

Check documents against the schema.

```bash
tekeldb validate                              # all collections
tekeldb validate --collection tasks           # one collection
tekeldb validate --fix                        # auto-apply defaults
tekeldb validate --format json                # JSON output (for CI)
tekeldb validate --format junit               # JUnit XML output (for CI dashboards)
tekeldb validate --files path/to/doc.yaml     # validate specific files
```

Exit codes: `0` = valid, `1` = errors found.

## Querying

### `tekeldb show`

Display a single document.

```bash
tekeldb show TASK-0001
```

### `tekeldb list`

List and filter documents in a collection.

```bash
tekeldb list <collection> [filters...] [options]
```

**Filters** use `field:value` syntax:

| Syntax | Meaning |
|--------|---------|
| `field:value` | Exact match (case-insensitive) |
| `field:!value` | Not equal |
| `field:~value` | Contains (substring) |
| `field:>value` | Greater than |
| `field:<value` | Less than |
| `field:>=value` | Greater than or equal |
| `field:<=value` | Less than or equal |

Multiple filters are AND logic. For list fields, `field:value` checks membership.

**Dot notation** for JSON fields: `api_response.event:push`

**Options:**

| Option | Description |
|--------|-------------|
| `--sort <field>` | Sort ascending. Prefix with `-` for descending. |
| `--format table\|yaml\|json\|csv` | Output format (default: table) |
| `--limit <n>` | Limit results |

**Examples:**

```bash
tekeldb list tasks                                    # all tasks
tekeldb list tasks status:open priority:high          # open AND high priority
tekeldb list tasks assignee:elif tags:design          # elif's design tasks
tekeldb list tasks title:~landing                     # title contains "landing"
tekeldb list tasks status:!done --format json         # not-done as JSON
tekeldb list tasks --sort -priority --limit 5         # top 5 by priority
```

### `tekeldb count`

Count documents, optionally grouped.

```bash
tekeldb count tasks                           # total count
tekeldb count tasks status:open               # filtered count
tekeldb count tasks --group-by status         # count per status
tekeldb count tasks --group-by assignee       # count per person
```

### `tekeldb find`

Full-text search across string and text fields.

```bash
tekeldb find "landing page"                   # search all collections
tekeldb find "elif" --collection contacts     # search one collection
tekeldb find "bug" --format json              # JSON output
```

### `tekeldb deps`

Inspect document references and dependencies.

```bash
tekeldb deps TASK-0001                        # show all refs (forward + reverse)
tekeldb deps TASK-0001 --reverse              # only incoming references
```

### `tekeldb export`

Export documents from the database.

```bash
tekeldb export --format json                          # all collections to stdout
tekeldb export --collection tasks --format csv        # one collection as CSV
tekeldb export --collection tasks --output tasks.json # write to file
```

## Views

Saved views are named, reusable queries stored in `.tekeldb/views.yaml`.

```bash
# Save a query
tekeldb view save open-tasks "list tasks status:open --sort -priority"

# Run it
tekeldb view run open-tasks
tekeldb view run open-tasks --format json     # override format

# Manage
tekeldb view list                             # list all views
tekeldb view show open-tasks                  # print view definition
tekeldb view delete open-tasks                # remove
```

## Schema Management

```bash
tekeldb schema show                                            # print schema
tekeldb schema add-collection sprints --id-prefix SPR          # add collection
tekeldb schema add-field tasks estimate integer --min 0         # add field
tekeldb schema add-field tasks size enum --values S,M,L,XL     # add enum field
tekeldb schema migrate --dry-run                               # preview migration
tekeldb schema migrate --yes                                   # apply migration
tekeldb schema migrate --prune --yes                           # also remove unknown fields
```

## Git Hooks

```bash
tekeldb hook install      # install pre-commit hook
tekeldb hook uninstall    # remove pre-commit hook
```

The pre-commit hook runs `tekeldb validate` on staged YAML files in `.tekeldb/data/`. Invalid documents block the commit.
