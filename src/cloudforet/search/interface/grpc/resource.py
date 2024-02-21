from spaceone.core.pygrpc import BaseAPI
from spaceone.api.search.v1 import resource_pb2, resource_pb2_grpc

from cloudforet.search.service.resource import ResourceService


class Resource(BaseAPI, resource_pb2_grpc.ResourceServicer):
    pb2 = resource_pb2
    pb2_grpc = resource_pb2_grpc

    def search(self, request, context):
        params, metadata = self.parse_request(request, context)
        resource_svc = ResourceService(metadata)
        response: dict = resource_svc.search(params)
        return self.dict_to_message(response)
