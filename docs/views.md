# Saved Views

Views are named, reusable queries stored in `.tekeldb/views.yaml`. Instead of retyping long filter/sort combos, save them once and run by name.

## Save a View

Write a query, test it, then save it:

```bash
# Test
tekeldb list tasks status:open priority:high --sort -due

# Save
tekeldb view save urgent "list tasks status:open priority:high --sort -due"
```

## Run a View

```bash
tekeldb view run urgent

# Override the output format
tekeldb view run urgent --format json
```

## Manage Views

```bash
# List all saved views
tekeldb view list

# Show a view's definition
tekeldb view show urgent

# Delete a view
tekeldb view delete urgent
```

## View Definition Format

Views are stored in `.tekeldb/views.yaml`:

```yaml
views:
  urgent:
    collection: tasks
    filters:
      - status:open
      - priority:high
    sort: -due

  my-tasks:
    collection: tasks
    filters:
      - assignee:elif
      - status:!done
    sort: -priority
    limit: 20

  team-load:
    collection: tasks
    filters:
      - status:!done
    group_by: assignee
```

You can edit this file directly — it's just YAML.

## Examples

```bash
# Save a view for each team member
tekeldb view save elif-tasks "list tasks assignee:elif status:!done --sort -priority"
tekeldb view save mehmet-tasks "list tasks assignee:mehmet status:!done --sort -priority"

# Daily standup queries
tekeldb view save in-progress "list tasks status:in-progress"
tekeldb view save blocked "list tasks status:review"

# Export views
tekeldb view run urgent --format csv > urgent-tasks.csv
```
