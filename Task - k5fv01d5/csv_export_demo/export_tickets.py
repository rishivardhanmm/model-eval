import json

with open("tickets.json", encoding="utf-8") as file:
    tickets = json.load(file)

with open("tickets.csv", "w", encoding="utf-8") as file:
    file.write("ticket_id,status,note\n")

    for ticket in tickets:
        # Fault: converts the string ID into an integer.
        ticket_id = int(ticket["ticket_id"])

        # Fault: joins fields without CSV escaping.
        row = ",".join([
            str(ticket_id),
            ticket["status"],
            ticket["note"]
        ])

        file.write(row + "\n")

print("Export complete: tickets.csv")

