RESOURCE_TYPES = {
    "identity.ServiceAccount": {
        "request": {
            "search": [
                "name",
                "data.account_id",
                "data.subscription_id",
                "data.tenant_id",
                "data.project_id",
            ],
            "projection": {
                "name": 1,
                "data": 1,
                "service_account_id": 1,
                "domain_id": 1,
                "workspace_id": 1,
                "project_id": 1,
                "account": {
                    "$switch": {
                        "branches": [
                            {
                                "case": {"$ifNull": ["$data.account_id", None]},
                                "then": "$data.account_id",
                            },
                            {
                                "case": {"$ifNull": ["$data.subscription_id", None]},
                                "then": "$data.subscription_id",
                            },
                            {
                                "case": {"$ifNull": ["$data.project_id", None]},
                                "then": "$data.project_id",
                            },
                        ],
                        "default": "$service_account_id",
                    }
                },
            },
        },
        "response": {
            "resource_id": "service_account_id",
            "name": "{name} ({account})",
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
        "request": {
            "search": ["name", "group", "provider"],
            "projection": {
                "group": 1,
                "name": 1,
                "provider": 1,
                "cloud_service_type_id": 1,
                "workspace_id": 1,
                "domain_id": 1,
                "icon": "$tags.spaceone:icon",
            },
        },
        "response": {
            "resource_id": "cloud_service_type_id",
            "name": "{group} > {name}",
            "tags": {
                "provider": "provider",
                "icon": "icon",
                "group": "group",
                "name": "name",
            },
        },
    },
    "inventory.CloudService": {
        "request": {
            "search": ["name", "ip_addresses", "account"],
            "filter": [{"state": "ACTIVE"}],
            "projection": {
                "cloud_service_id": 1,
                "cloud_service_type": 1,
                "cloud_service_group": 1,
                "name": 1,
                "provider": 1,
                "ip_addresses": {
                    "$reduce": {
                        "input": "$ip_addresses",
                        "initialValue": "",
                        "in": {"$concat": ["$$value", "$$this", ","]},
                    }
                },
                "project_id": 1,
                "workspace_id": 1,
                "domain_id": 1,
                "ref_resource_id": "$reference.resource_id",
                "cloud_service_type_key": {
                    "$concat": ["$provider", ":", "$cloud_service_type", ":", "$cloud_service_group"]
                },
            },
        },
        "response": {
            "resource_id": "cloud_service_id",
            "name": "[{cloud_service_group} > {cloud_service_type}] {ref_resource_id} - {name}({ip_addresses})",
            "tags": {
                "cloud_service_type_key": "cloud_service_type_key",
                "ip_addresses": "ip_addresses",
                "provider": "provider",
                "group": "cloud_service_group",
                "name": "cloud_service_type",
                "resource_id": "ref_resource_id",
            },
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
