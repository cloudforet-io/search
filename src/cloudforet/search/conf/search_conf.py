RESOURCE_TYPES = {
    "identity.ServiceAccount": {
        "request": {"search": ["service_account_id", "name"]},
        "response": {"name": "{service_account_id} ({name})"},
    },
    "identity.Project": {
        "request": {"search": ["name", "project_id"]},
        "response": {"name": "{name}"},
    },
}
