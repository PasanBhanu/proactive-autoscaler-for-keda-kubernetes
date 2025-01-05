from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from prophet.serialize import model_from_json
from keras.models import load_model

# Load Models
with open('models/fbprophet-nasa-20240911_175323.json', 'r') as f:
    prophet_model = model_from_json(f.read())

lstm_model = load_model('models/lstm-nasa-20240911_175323.keras')

# Initialize the MinMaxScaler
scaler = MinMaxScaler(feature_range=(0, 1))
scaler.fit(np.array([[-118], [284]]))

# Initialize FastAPI
app = FastAPI()

# Prediction
def hybrid_prediction(request_rate, prophet_model, lstm_model, scaler):
    try:
        timestamp = datetime.now()
        future = pd.DataFrame({"ds": [timestamp + timedelta(minutes=1)]})

        # FB Prophet Prediction
        forecast = prophet_model.predict(future)
        fb_prophet_prediction = forecast.iloc[-1]["yhat"]
        print(f"Prophet Prediction: {fb_prophet_prediction}")

        # Residual Calculation
        residual = request_rate - fb_prophet_prediction
        print(f"Residual: {residual}")

        scaled_residual = scaler.transform([[residual]])
        scaled_residual = np.reshape(scaled_residual, (1, 1, 1))

        # LSTM Residual Prediction
        lstm_residual_prediction = lstm_model.predict(scaled_residual)
        lstm_residual_prediction = scaler.inverse_transform(lstm_residual_prediction)[0, 0]
        print(f"Residual Prediction: {lstm_residual_prediction}")

        final_prediction = fb_prophet_prediction + lstm_residual_prediction

        return final_prediction
    except Exception as e:
        raise ValueError(f"Prediction failed with error: {str(e)}")

# FastAPI Endpoint
@app.get("/prediction")
def get_prediction(rate: float):
    """
    API endpoint for hybrid prediction.
    :param rate: The current request rate.
    :return: Predicted request rate for the next minute.
    """
    try:
        prediction = hybrid_prediction(rate, prophet_model, lstm_model, scaler)
        return {"input_rate": rate, "predicted_rate": prediction}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))