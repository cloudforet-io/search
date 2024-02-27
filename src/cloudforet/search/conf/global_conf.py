# Pymongo Databases Settings
# PYMONGO_DATABASES = {
#     "default": {
#         "db_prefix": "dev2",
#         "username": "cloudforet",
#         "password": "password1234",
#         "host": "mongodb://localhost:27017",
#     },
#     "identity": {
#         "db": "identity",
#     },
# }

DATABASES = {
    "default": {
        "username": "cloudforet",
        "password": "password1234",
        "host": "mongodb://localhost:27017",
    }
}

# Cache Settings
CACHES = {
    "default": {},
    "local": {
        "backend": "spaceone.core.cache.local_cache.LocalCache",
        "max_size": 128,
        "ttl": 300,
    },
}

# Handler Settings
HANDLERS = {
    # "authentication": [{
    #     "backend": "spaceone.core.handler.authentication_handler:SpaceONEAuthenticationHandler"
    # }],
    # "authorization": [{
    #     "backend": "spaceone.core.handler.authorization_handler:SpaceONEAuthorizationHandler"
    # }],
    # "mutation": [{
    #     "backend": "spaceone.core.handler.mutation_handler:SpaceONEMutationHandler"
    # }],
    # "event": []
}

# Log Settings
LOG = {"filters": {"masking": {"rules": {}}}}

# Connector Settings
CONNECTORS = {
    "SpaceConnector": {
        "backend": "spaceone.core.connector.space_connector:SpaceConnector",
        "endpoints": {
            "identity": "grpc://localhost:50051",
        },
    },
}

# Endpoint Settings
ENDPOINTS = [
    # {
    #     "service": "identity",
    #     "name": "Identity Service",
    #     "endpoint": "grpc://<endpoint>>:<port>"
    # },
]

# System Token Settings
TOKEN = ""
