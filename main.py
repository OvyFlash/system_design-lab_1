import datetime as dt
import json

import requests
import yaml
from flask import Flask, jsonify, request

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# create your API token, and set it up in Postman collection as part of the Body section
API_TOKEN = config["api_token"]
# you can get API keys for free here - https://api-ninjas.com/api/jokes
WEATHER_API_KEY = config["weather_api_key"]

app = Flask(__name__)


def handle_weather(location: str, date):
    url_base_url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    query = f"key={WEATHER_API_KEY}&timezone=Europe%2FKyiv&contentType=json&lang=uk&unitGroup=metric&elements=datetime,temp,windspeed,pressure,humidity"
    url = f"{url_base_url}/{location}/{date}?{query}"
    
    response = requests.get(url)
    if response.status_code == requests.codes.ok:
        # print(response.text)
        ...
    else:
        print("Error:", response.status_code, response.text)
    
    return json.loads(response.text)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv
    

def get_json_data_item(json_data, key: str):
    item = json_data.get(key)
    if item is None:
        raise InvalidUsage(f"{key} is required", status_code=400)
    return item


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route("/")
def home_page():
    return "<p><h2>KMA L2: python Saas.</h2></p>"


@app.route(
    "/content/api/v1/integration/weather",
    methods=["POST"],
)
def weather_endpoint():
    json_data = request.get_json()

    items = {"token": None, "requester_name": None, "location": None, "date": None}
    for key in items:
        items[key] = get_json_data_item(json_data, key)
    items["datetime"] = dt.datetime.now().isoformat()

    if items["token"] != API_TOKEN:
        raise InvalidUsage("wrong API token", status_code=403)
    del items["token"]

    weather = handle_weather(items["location"], items["date"])

    result = items
    result["weather"] = weather

    return result
