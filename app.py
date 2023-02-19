import datetime as dt
import pytz
import json

import requests
from flask import Flask, jsonify, request

# reads json file
def read_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


CONFIG_PATH = "config.json"
config = read_json(CONFIG_PATH)
# create your API token, and set it up in Postman collection as part of the Body section
API_TOKEN = config["api_token"]
# you can get API keys for free here - https://api-docs.pgamerx.com/
RSA_API_KEY = config["rsa_api_key"]
X_RAPID_API_KEY = config["x_rapid_api_key"]

app = Flask(__name__)


def generate_joke(exclude: str):
    url_base_url = "https://v6.rsa-api.xyz/"
    url_api = "joke"
    url_endpoint = "random"
    url_exclude = ""

    if exclude:
        url_exclude = f"?exclude={exclude}"

    url = f"{url_base_url}/{url_api}/{url_endpoint}{url_exclude}"

    payload = {}
    headers = {"Authorization": RSA_API_KEY}

    response = requests.request("GET", url, headers=headers, data=payload)
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


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

#
# Root endpoint
#

@app.route("/")
def home_page():
    return "<p><h2>KMA L2: Python Saas.</h2></p>"
#
# Joke endpoint
#

@app.route(
    "/content/api/v1/integration/generate",
    methods=["POST"],
)
def joke_endpoint():
    start_dt = dt.datetime.now()
    json_data = request.get_json()

    if json_data.get("token") is None:
        raise InvalidUsage("token is required", status_code=400)

    token = json_data.get("token")

    if token != API_TOKEN:
        raise InvalidUsage("wrong API token", status_code=403)

    exclude = ""
    if json_data.get("exclude"):
        exclude = json_data.get("exclude")

    joke = generate_joke(exclude)

    end_dt = dt.datetime.now()

    result = {
        "event_start_datetime": start_dt.isoformat(),
        "event_finished_datetime": end_dt.isoformat(),
        "event_duration": str(end_dt - start_dt),
        "joke": joke,
    }

    return result

#
# Weather private variables
#

KEY_TOKEN = "token"
KEY_REQUESTER_NAME = "requester_name"
KEY_LOCATION = "location"
KEY_DATE = "date"
X_RAPID_API_HOST = "ai-weather-by-meteosource.p.rapidapi.com"
weather_base_url = "https://ai-weather-by-meteosource.p.rapidapi.com"
headers = {
    "Authorization": RSA_API_KEY,
    "X-RapidAPI-Key": X_RAPID_API_KEY,
    "X-RapidAPI-Host": X_RAPID_API_HOST,    
}
#
# Weather Helper methods
#

# get_place_id requests to API in order to get place id, which can be used
# in getting weather method 
def get_place_id(location: str) -> str:
    url = f"{weather_base_url}/find_places"
    query_params = {"text":location}
    payload = {}

    response = requests.request("GET", url, headers=headers, data=payload, params=query_params)
    if response.status_code != 200:
        raise InvalidUsage("Bad location", status_code=response.status_code)

    body = json.loads(response.text)
    if len(body) == 0:
        raise InvalidUsage("Could not find location", status_code=404)

    place_id = body[0].get("place_id")
    if place_id is None:
        raise InvalidUsage("Could not find location", status_code=404)

    return place_id

def get_weather(location: str, date_time: str):
    url = f"{weather_base_url}/historical_weather"
    query_params = {
        "place_id": get_place_id(location),
        "date": date_time,
        "units":"metric"
    }

    payload = {}
    response = requests.request("GET", url, headers=headers, data=payload, params=query_params)
    return json.loads(response.text)


def check_missing_fields(body, key: str) -> str:
    value = body.get(key)
    if value is None:
        raise InvalidUsage(f"{key} is missing", status_code=400)
    return value

    
def validate_weather_body(body) -> tuple:
    token = check_missing_fields(body, KEY_TOKEN)
    if token != API_TOKEN:
        raise InvalidUsage("wrong API token", status_code=403)
    
    name = check_missing_fields(body, KEY_REQUESTER_NAME)
    if len(name.split()) != 2:
        raise InvalidUsage("Enter full name", status_code=400)
    
    location = check_missing_fields(body, KEY_LOCATION)

    date = check_missing_fields(body, KEY_DATE)
    try:
        dt.datetime.strptime(date, '%Y-%m-%d')
    except ValueError as ve1:
        raise InvalidUsage("Wrong date format", status_code=400)
    return name, location, date


#
# Endpoint
#

@app.route(
    "/weather",
    methods=["POST"],
)
def weather_endpoint():
    json_data = request.get_json()

    name, location, date = validate_weather_body(json_data)

    weather = get_weather(location, date)

    result = {
        KEY_REQUESTER_NAME: name,
        "timestamp": dt.datetime.now(tz=pytz.UTC).isoformat(),
        KEY_LOCATION: location,
        KEY_DATE: date,
        "weather": weather
    }

    return result