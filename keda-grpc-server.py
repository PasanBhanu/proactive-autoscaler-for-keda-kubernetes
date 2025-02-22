from concurrent import futures
import grpc
import externalscaler_pb2
import externalscaler_pb2_grpc
from prometheus_api_client import PrometheusConnect
import logging
from sklearn.preprocessing import MinMaxScaler
from prophet.serialize import model_from_json
from keras.models import load_model
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


# Configure Logging
logging.basicConfig(level=logging.INFO)


# Load Models
with open('models/fbprophet-nasa-20240911_175323.json', 'r') as f:
    prophet_model = model_from_json(f.read())
lstm_model = load_model('models/lstm-nasa-20240911_175323.keras')


# Initialize the MinMaxScaler
scaler = MinMaxScaler(feature_range=(0, 1))
scaler.fit(np.array([[-118], [284]]))


# Predict Traffic using Hybrid Model
def hybrid_prediction(request_rate, prophet_model, lstm_model, scaler):
    try:
        timestamp = datetime.now()
        future = pd.DataFrame({"ds": [timestamp + timedelta(minutes=1)]})

        # FB Prophet Prediction
        forecast = prophet_model.predict(future)
        fb_prophet_prediction = forecast.iloc[-1]["yhat"]
        logging.info(f"Prophet Prediction: {fb_prophet_prediction}")

        # Residual Calculation
        residual = request_rate - fb_prophet_prediction
        logging.info(f"Residual: {residual}")

        scaled_residual = scaler.transform([[residual]])
        scaled_residual = np.reshape(scaled_residual, (1, 1, 1))

        # LSTM Residual Prediction
        lstm_residual_prediction = lstm_model.predict(scaled_residual)
        lstm_residual_prediction = scaler.inverse_transform(lstm_residual_prediction)[0, 0]
        logging.info(f"Residual Prediction: {lstm_residual_prediction}")

        final_prediction = fb_prophet_prediction + lstm_residual_prediction
        logging.info(f"Predicted Value: {final_prediction}")

        return final_prediction
    except Exception as e:
        raise ValueError(f"Prediction failed with error: {str(e)}")
    

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
        server_address = request.scaledObjectRef.scalerMetadata["serverAddress"]
        query = request.scaledObjectRef.scalerMetadata["query"]
        pod_limit = request.scaledObjectRef.scalerMetadata["podLimit"]
        logging.info(f"Input Metadata [serverAddress: {server_address}, query: {query}, podLimit: {pod_limit}]")

        prometheus_value = get_prometheus_metric(server_address, query)
        predicted_value = hybrid_prediction(prometheus_value, prophet_model, lstm_model, scaler)
        logging.info(f"Prometheus Value: {prometheus_value}, Predicted Value: {predicted_value}")
        
        pod_count = float(predicted_value) / int(pod_limit)
        logging.info(f"Pod Count: {pod_count}")

        metric_value = externalscaler_pb2.MetricValue(
            metricName="custom_metric",
            metricValue=int(pod_count),
            metricValueFloat=float(pod_count)
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
