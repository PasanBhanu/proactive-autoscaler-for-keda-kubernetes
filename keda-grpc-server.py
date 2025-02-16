from concurrent import futures
import grpc
import externalscaler_pb2
import externalscaler_pb2_grpc
from prometheus_api_client import PrometheusConnect
import logging


# Configure Logging
logging.basicConfig(level=logging.INFO)


# Get Prometheus Metric Value
def get_prometheus_metric(serverAddress, query):
    prom = PrometheusConnect(url=serverAddress, disable_ssl=True, retry=False, timeout=10)
    metric_data = prom.custom_query(query=query)
    if metric_data:
        prometheusValue = float(metric_data[0]['value'][1])
    else:
        prometheusValue = 0.0
    
    logging.info(f"Prometheus Value: {prometheusValue}")
    return prometheusValue
    

# gRPC Implementation for KEDA
class ExternalScalerServicer(externalscaler_pb2_grpc.ExternalScalerServicer):
    # IsActive Check
    # Should return 1 always
    def IsActive(self, request, context):
        return externalscaler_pb2.IsActiveResponse(result=1)


    # StreamIsActive
    # Should return 1 always
    def StreamIsActive(self, request, context):
        while True:
            yield externalscaler_pb2.IsActiveResponse(result=1)


    # GetMetricSpec
    # Should return the metric name, target size and target size float
    def GetMetricSpec(self, request, context):
        metric_spec = externalscaler_pb2.MetricSpec(
            metricName="custom_metric",
            targetSize=1,
            targetSizeFloat=1.0
        )
        return externalscaler_pb2.GetMetricSpecResponse(metricSpecs=[metric_spec])


    # GetMetrics
    # Should return the predicted pod count
    def GetMetrics(self, request, context):
        serverAddress = request.scaledObjectRef.scalerMetadata["serverAddress"]
        query = request.scaledObjectRef.scalerMetadata["query"]
        podLimit = request.scaledObjectRef.scalerMetadata["podLimit"]
        logging.info(f"Input Metadata [serverAddress: {serverAddress}, query: {query}, podLimit: {podLimit}]")

        prometheusValue = get_prometheus_metric(serverAddress, query)

        result = 1 # TODO: Get the predicted pod count
        
        metric_value = externalscaler_pb2.MetricValue(
            metricName="custom_metric",
            metricValue=int(result),
            metricValueFloat=float(result)
        )

        return externalscaler_pb2.GetMetricsResponse(metricValues=[metric_value])


# Start the gRPC Server
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    externalscaler_pb2_grpc.add_ExternalScalerServicer_to_server(ExternalScalerServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    logging.info("Server started, listening on port 50051")
    server.wait_for_termination()


# Main Function
if __name__ == '__main__':
    serve()
