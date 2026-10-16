
# Faulty code: work items stored as tuples

work_items = [
    (101, "Fix login issue", "High"),
    (102, "Update documentation", "Low"),
    (103, "Repair payment bug", "Medium"),
]


def print_summary(items):
    for item in items:
        item_id = item[0]
        title = item[1]
        priority = item[2]

        print(
            f"ID: {item_id} | "
            f"Title: {title} | "
            f"Priority: {priority}"
        )


print_summary(work_items)
