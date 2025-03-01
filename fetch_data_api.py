from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3


app = Flask(__name__, static_folder="ui", static_url_path="/")
CORS(app)


conn = sqlite3.connect('metrics.db', check_same_thread=False)
cursor = conn.cursor()


def fetch_last_100_records():
    cursor.execute('SELECT * FROM metric_history ORDER BY timestamp DESC LIMIT 1000')
    records = cursor.fetchall()
    return records


@app.route('/')
def serve_ui():
    return send_from_directory("ui", "index.html")


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    try:
        records = fetch_last_100_records()
        return jsonify(records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/metrics/clear', methods=['POST'])
def clear_metrics():
    try:
        cursor.execute('DELETE FROM metric_history')
        conn.commit()
        return jsonify({'message': 'Metrics cleared successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 