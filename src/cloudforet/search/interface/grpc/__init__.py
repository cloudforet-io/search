from spaceone.core.pygrpc.server import GRPCServer
from cloudforet.search.interface.grpc.resource import Resource

_all_ = ["app"]

app = GRPCServer()
app.add_service(Resource)
