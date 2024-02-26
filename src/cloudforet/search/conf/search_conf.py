RESOURCE_TYPES = {
    "identity.ServiceAccount": {
        "request": {"search": ["service_account_id", "name"]},
        "response": {
            "resource_id": "service_account_id",
            "name": "{service_account_id} ({name})",
        },
    },
    "identity.Project": {
        "request": {"search": ["name", "project_id"]},
        "response": {"resource_id": "project_id", "name": "{name}"},
    },
    "identity.Workspace": {
        "request": {"search": ["name"]},
        "response": {"resource_id": "workspace_id", "name": "{name}"},
    },
}
