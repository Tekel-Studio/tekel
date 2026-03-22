# CLI Reference

## Database Lifecycle

### `tekel init`

Create a new database in the current directory.

```bash
tekel init                    # schema-free mode
tekel init --schema pm        # built-in project management schema
tekel init --schema ./my.yaml # custom schema file
```

### `tekel status`

Show database summary: name, collections, document counts, status breakdowns.

```bash
tekel status
```

### `tekel validate`

Check documents against the schema.

```bash
tekel validate                              # all collections
tekel validate --collection tasks           # one collection
tekel validate --fix                        # auto-apply defaults
tekel validate --format json                # JSON output (for CI)
tekel validate --format junit               # JUnit XML output (for CI dashboards)
tekel validate --files path/to/doc.yaml     # validate specific files
```

Exit codes: `0` = valid, `1` = errors found.

## Querying

### `tekel show`

Display a single document.

```bash
tekel show TASK-0001
```

### `tekel list`

List and filter documents in a collection.

```bash
tekel list <collection> [filters...] [options]
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
tekel list tasks                                    # all tasks
tekel list tasks status:open priority:high          # open AND high priority
tekel list tasks assignee:elif tags:design          # elif's design tasks
tekel list tasks title:~landing                     # title contains "landing"
tekel list tasks status:!done --format json         # not-done as JSON
tekel list tasks --sort -priority --limit 5         # top 5 by priority
```

### `tekel count`

Count documents, optionally grouped.

```bash
tekel count tasks                           # total count
tekel count tasks status:open               # filtered count
tekel count tasks --group-by status         # count per status
tekel count tasks --group-by assignee       # count per person
```

### `tekel find`

Full-text search across string and text fields.

```bash
tekel find "landing page"                   # search all collections
tekel find "elif" --collection contacts     # search one collection
tekel find "bug" --format json              # JSON output
```

### `tekel deps`

Inspect document references and dependencies.

```bash
tekel deps TASK-0001                        # show all refs (forward + reverse)
tekel deps TASK-0001 --reverse              # only incoming references
```

### `tekel export`

Export documents from the database.

```bash
tekel export --format json                          # all collections to stdout
tekel export --collection tasks --format csv        # one collection as CSV
tekel export --collection tasks --output tasks.json # write to file
```

## Views

Saved views are named, reusable queries stored in `.tekel/views.yaml`.

```bash
# Save a query
tekel view save open-tasks "list tasks status:open --sort -priority"

# Run it
tekel view run open-tasks
tekel view run open-tasks --format json     # override format

# Manage
tekel view list                             # list all views
tekel view show open-tasks                  # print view definition
tekel view delete open-tasks                # remove
```

## Schema Management

```bash
tekel schema show                                            # print schema
tekel schema add-collection sprints --id-prefix SPR          # add collection
tekel schema add-field tasks estimate integer --min 0         # add field
tekel schema add-field tasks size enum --values S,M,L,XL     # add enum field
tekel schema migrate --dry-run                               # preview migration
tekel schema migrate --yes                                   # apply migration
tekel schema migrate --prune --yes                           # also remove unknown fields
```

## Git Hooks

```bash
tekel hook install      # install pre-commit hook
tekel hook uninstall    # remove pre-commit hook
```

The pre-commit hook runs `tekel validate` on staged YAML files in `.tekel/data/`. Invalid documents block the commit.
