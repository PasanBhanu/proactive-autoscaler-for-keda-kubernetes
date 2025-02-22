from flask import Flask, jsonify
import sqlite3


app = Flask(__name__)


def fetch_last_100_records():
    conn = sqlite3.connect('metrics.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM metric_history ORDER BY timestamp DESC LIMIT 100')
    records = cursor.fetchall()
    conn.close()
    return records


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    try:
        records = fetch_last_100_records()
        return jsonify(records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 