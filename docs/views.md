# Saved Views

Views are named, reusable queries stored in `.tekel/views.json`. Instead of retyping long filter/sort combos, save them once and run by name.

## Save a View

Write a query, test it, then save it:

```bash
# Test
tekel list tasks status:open priority:high --sort -due

# Save
tekel view save urgent "list tasks status:open priority:high --sort -due"
```

## Run a View

```bash
tekel view run urgent

# Override the output format
tekel view run urgent --format json
```

## Manage Views

```bash
# List all saved views
tekel view list

# Show a view's definition
tekel view show urgent

# Delete a view
tekel view delete urgent
```

## View Definition Format

Views are stored in `.tekel/views.json`:

```json
{
  "views": {
    "urgent": {
      "collection": "tasks",
      "filters": ["status:open", "priority:high"],
      "sort": "-due"
    },
    "my-tasks": {
      "collection": "tasks",
      "filters": ["assignee:elif", "status:!done"],
      "sort": "-priority",
      "limit": 20
    },
    "team-load": {
      "collection": "tasks",
      "filters": ["status:!done"],
      "group_by": "assignee"
    }
  }
}
```

You can edit this file directly — it's just JSON.

## Examples

```bash
# Save a view for each team member
tekel view save elif-tasks "list tasks assignee:elif status:!done --sort -priority"
tekel view save mehmet-tasks "list tasks assignee:mehmet status:!done --sort -priority"

# Daily standup queries
tekel view save in-progress "list tasks status:in-progress"
tekel view save blocked "list tasks status:review"

# Export views
tekel view run urgent --format csv > urgent-tasks.csv
```
