from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
import io
import re

app = Flask(__name__)

# URL of the public Google Sheet in CSV format
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1iqXW5F8b0LAyyTS6JzFkThfX8QxAxy0rFYhAhVSaVhQ/export?format=csv'

# Predefined user types to filter in column C (index 2)
VALID_USERS = ["mnair user", "199991 user"]

def fetch_sheet_data():
    try:
        response = requests.get(SHEET_URL)
        response.raise_for_status()
        # Read CSV data into a pandas DataFrame
        df = pd.read_csv(io.StringIO(response.text))
        return df
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Google Sheet: {e}")
        return None

def find_tracking_number(df, tracking_number):
    # Ensure the DataFrame has enough columns
    required_indices = [2, 3, 9]  # C (2), D (3), J (9)
    if df.shape[1] <= max(required_indices):
        print(f"DataFrame does not have enough columns. Expected at least {max(required_indices)+1} columns.")
        return None

    # Filter rows where column C (index 2) matches VALID_USERS
    try:
        # Convert column C to string and strip whitespace
        col_c = df.iloc[:, 2].astype(str).str.strip()
        matching_rows = df[col_c.isin(VALID_USERS)].copy()
    except Exception as e:
        print(f"Error filtering column C: {e}")
        return None

    if matching_rows.empty:
        print("No matching users found in column C.")
        return None

    # Compile regex pattern to match the tracking number as a whole word
    try:
        # Escape the tracking number to handle any special regex characters
        pattern = r'\b' + re.escape(tracking_number) + r'\b'
        # Convert column D to string and search using the regex pattern
        col_d = matching_rows.iloc[:, 3].astype(str)
        rows_with = matching_rows[col_d.str.contains(pattern, regex=True, na=False)]
    except Exception as e:
        print(f"Error searching in column D: {e}")
        return None

    if not rows_with.empty:
        # Get the last matching row
        last_row = rows_with.tail(1)
        try:
            # Extract value from column J (index 9)
            j_value = last_row.iloc[0, 9]
            return f"https://www.4tracking.net/en/tjax/track?nums={j_value}"
        except IndexError:
            print("Column J (index 9) does not exist in the matching row.")
            return None
    else:
        print("No rows found with the provided tracking number.")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/track', methods=['POST'])
def track():
    data = request.get_json()
    tracking_number = data.get('tracking_number', '').strip()

    if not tracking_number.isdigit():
        return jsonify({"error": "Invalid tracking number format."}), 400

    df = fetch_sheet_data()
    if df is None:
        return jsonify({"error": "Failed to fetch tracking data."}), 500

    track_url = find_tracking_number(df, tracking_number)

    if track_url:
        return jsonify({"track_url": track_url})
    else:
        return jsonify({"error": "Tracking number not found."}), 404

if __name__ == '__main__':
    app.run(debug=True)
