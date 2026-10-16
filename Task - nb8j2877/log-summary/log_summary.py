logs = [
    "INFO: Application started",
    "WARNING: Disk space low",
    "ERROR: Connection failed",
    "INFO: User logged in",
    "ERROR: File not found",
]

info_count = 0
warning_count = 0
error_count = 0

for log in logs:
    if log.startswith("INFO"):
        info_count += 1

for log in logs:
    if log.startswith("WARNING"):
        warning_count += 1

for log in logs:
    if log.startswith("ERROR"):
        error_count += 1

print("INFO:", info_count)
print("WARNING:", warning_count)
print("ERROR:", error_count)

# Example without WARNING
logs_without_warning = [
    "INFO: Application started",
    "ERROR: Connection failed",
]

info_count = 0
warning_count = 0
error_count = 0

for log in logs_without_warning:
    if log.startswith("INFO"):
        info_count += 1
    elif log.startswith("WARNING"):
        warning_count += 1
    elif log.startswith("ERROR"):
        error_count += 1

print("INFO:", info_count)
print("WARNING:", warning_count)
print("ERROR:", error_count)

# Empty example
empty_logs = []

info_count = 0
warning_count = 0
error_count = 0

for log in empty_logs:
    if log.startswith("INFO"):
        info_count += 1
    elif log.startswith("WARNING"):
        warning_count += 1
    elif log.startswith("ERROR"):
        error_count += 1

print("INFO:", info_count)
print("WARNING:", warning_count)
print("ERROR:", error_count)