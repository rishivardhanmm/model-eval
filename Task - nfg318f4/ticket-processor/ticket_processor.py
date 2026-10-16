tickets = [
    {"id": 101, "title": "Login issue", "status": "open"},
    {"id": 102, "title": "Payment delay", "status": "pending"},
    {"id": 103, "title": "Account locked", "status": "closed"},
]


def process_ticket(ticket):
    if ticket["status"] == "open":
        message = "Ticket is open"
    elif ticket["status"] == "pending":
        message = "Ticket is pending"
    elif ticket["status"] == "closed":
        message = "Ticket is closed"
    else:
        message = "Unknown ticket status"

    print(
        f"Ticket {ticket['id']}: {ticket['title']} "
        f"- {ticket['status']} ({message})"
    )


if __name__ == "__main__":
    for ticket in tickets:
        process_ticket(ticket)