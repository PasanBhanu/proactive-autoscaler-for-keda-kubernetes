import subprocess

# Start both scripts in parallel
subprocess.Popen(["python", "keda-grpc-server.py"])
subprocess.Popen(["python", "fetch_data_api.py"])
