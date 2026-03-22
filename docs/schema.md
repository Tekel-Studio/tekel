# Schema Guide

The schema file (`.tekel/schema.yaml`) defines the structure of your data: what collections exist, what fields each document has, what values are valid, and what state transitions are allowed.

If no schema is provided, tekel runs in **schema-free mode** — any YAML document is accepted, no validation is performed.

## Anatomy of a Schema

```yaml
version: "1.0"
name: my-project

collections:
  tasks:
    id_prefix: TASK
    additional_fields: true     # allow fields not listed below (default: true)
    fields:
      title: { type: string, required: true }
      status:
        type: enum
        values: [open, in-progress, done]
        default: open
        required: true
      priority:
        type: enum
        values: [low, medium, high, critical]
        default: medium
      assignee: { type: string }
      due: { type: date }
      tags: { type: list, items: string }
      description: { type: text }
      points: { type: integer, min: 0, max: 100 }
      metadata: { type: any }
    refs:
      blocks: { collection: tasks, type: many }
      milestone: { collection: milestones, type: one }
    transitions:
      status:
        open: [in-progress]
        in-progress: [done, open]
        done: []
```

## Field Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Short text, single line | `"Design the homepage"` |
| `text` | Multi-line text | `"First line.\nSecond line."` |
| `integer` | Whole number | `42` |
| `float` | Decimal number | `3.14` |
| `boolean` | True or false | `true` |
| `date` | Calendar date (ISO 8601) | `2026-04-01` |
| `datetime` | Date and time (ISO 8601) | `2026-04-01T14:30:00` |
| `enum` | One of a defined set | `"high"` |
| `list` | Ordered list | `[design, website]` |
| `object` | Nested structure | `{key: value}` |
| `json` | Raw JSON string or object | `'{"event": "push"}'` |
| `any` | Any valid YAML value | Skips type validation |

## Field Options

| Option | Applies to | Description |
|--------|-----------|-------------|
| `required: true` | Any | Document is invalid without this field |
| `default: <value>` | Any | Applied by `validate --fix` if field is missing |
| `auto: true` | `datetime` | Set to current time |
| `min: <n>` | `integer`, `float` | Minimum value |
| `max: <n>` | `integer`, `float` | Maximum value |
| `format: email` | `string` | Validate as email address |
| `format: url` | `string` | Validate as URL |
| `values: [...]` | `enum` | Allowed values |
| `items: <type>` | `list` | Type constraint on list elements |
| `unique: true` | `string`, `integer` | Value must be unique across collection |

## Additional Fields

By default, documents can contain fields not listed in the schema. To enforce strict schemas:

```yaml
collections:
  contracts:
    additional_fields: false    # reject any field not defined below
    fields:
      title: { type: string, required: true }
      value: { type: float, required: true }
```

## References

References define relationships between documents in different collections:

```yaml
refs:
  blocks: { collection: tasks, type: many }      # list of IDs
  milestone: { collection: milestones, type: one } # single ID
```

In the document:

```yaml
blocks:
  - TASK-0010
  - TASK-0012
milestone: MS-0003
```

`tekel validate` checks that referenced IDs actually exist. Use `tekel deps <id>` to inspect relationships.

## Transitions

Define valid state changes for enum fields:

```yaml
transitions:
  status:
    open: [in-progress]           # from open, can go to in-progress
    in-progress: [done, open]     # from in-progress, can go to done or back to open
    done: []                      # done is a terminal state
```

If no transitions are defined, any value change is allowed. `tekel validate` checks transition rules when comparing documents against their previous state.

## Managing the Schema

```bash
# View current schema
tekel schema show

# Add a collection
tekel schema add-collection sprints --id-prefix SPR

# Add a field
tekel schema add-field tasks estimate integer --min 0 --max 100
tekel schema add-field tasks size enum --values S,M,L,XL

# After editing the schema, migrate existing documents
tekel schema migrate --dry-run     # preview changes
tekel schema migrate --yes         # apply
```

## Schema Migration

When you change the schema, existing documents may not match. `schema migrate` handles this:

| Change | What happens |
|--------|-------------|
| New field with default | Added to all docs automatically |
| New required field, no default | Reported as error (manual fix needed) |
| Type change (compatible) | Coerced automatically (`"42"` → `42`) |
| Type change (incompatible) | Reported as error |
| Enum value removed | Docs using old value flagged |
| New collection | Data directory created |
| Removed collection | Warning (directory not deleted) |

```bash
tekel schema migrate --dry-run          # preview
tekel schema migrate --yes              # apply fixable changes
tekel schema migrate --prune --yes      # also remove unknown fields
```

Backups are saved to `.tekel/.migrate-backup/` before any changes.
