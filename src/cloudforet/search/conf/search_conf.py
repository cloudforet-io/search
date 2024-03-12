RESOURCE_TYPES = {
    "identity.ServiceAccount": {
        "request": {
            "search": [
                "name",
                "data.account_id",
                "data.subscription_id",
                "data.tenant_id",
                "data.project_id",
            ]
        },
        "response": {
            "resource_id": "service_account_id",
            "name": "{account} ({name})",
            "aliases": [
                {"data.account_id": "account"},
                {"data.subscription_id": "account"},
                {"data.project_id": "account"},
                {"service_account_id": "account"},
            ],
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
            "aliases": [
                {"tags.spaceone:icon": "icon"},
            ],
            "tags": {
                "provider": "{provider}",
                "icon": "{icon}",
                "group": "{group}",
                "name": "{name}",
            },
        },
    },
    "inventory.CloudService": {
        "request": {
            "search": ["name", "ip_addresses", "account", "instance_type"],
            "filter": [{"state": "ACTIVE"}],
        },
        "response": {
            "resource_id": "cloud_service_id",
            "name": "{name}",
            "description": "{cloud_service_group} > {cloud_service_type}",
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
