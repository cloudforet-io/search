RESOURCE_TYPES = {
    "identity.ServiceAccount": {
        "request": {"search": ["service_account_id", "name"]},
        "response": {
            "resource_id": "service_account_id",
            "name": "{service_account_id} ({name})",
        },
    },
    "identity.Project": {
        "request": {"search": ["name"]},
        "response": {"resource_id": "project_id", "name": "{name}"},
    },
    "identity.Workspace": {
        "request": {"search": ["name"], "filter": [{"state": "ENABLED"}]},
        "response": {"resource_id": "workspace_id", "name": "{name}"},
    },
    "inventory.CloudServiceType": {
        "request": {"search": ["name", "group", "provider"]},
        "response": {
            "resource_id": "cloud_service_type_id",
            "name": "{group} > {name}",
        },
    },
    "inventory.CloudService": {
        "request": {
            "search": [
                "name",
                "ip_addresses",
                "account",
            ],
            "filter": [{"state": "ACTIVE"}],
        },
        "response": {
            "resource_id": "cloud_service_id",
            "name": "{name}",
        },
    },
    "dashboard.PublicDashboard": {
        "request": {"search": ["name"]},
        "response": {
            "resource_id": "public_dashboard_id",
            "name": "{name}",
            "description": "{description}",
        },
    },
}
