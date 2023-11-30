"""Backend logic."""
import logging
import os
import time
from datetime import datetime

import openai
from approaches.retrieve_read import RetrieveReadApproach
from approaches.retrieve_read_read import RetrieveReadReadApproach
from approaches.retrieve_read_retry import RetrieveReadRetryApproach
from approaches.retrieve_reformulate_retrieve_read import RetrieveReformulateRetrieveReadApproach
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from constants import ACSIndex
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from requests import get
from rich import print

load_dotenv()

# Replace these with your own values, either in environment variables or directly here
AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE")
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX")
print("@@@@@@@@@@@")
print(AZURE_SEARCH_INDEX)
AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE")
AZURE_OPENAI_GPT_DEPLOYMENT_DEFAULT = "gpt-35-turbo"

KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT") or "content"
KB_FIELDS_CATEGORY = os.environ.get("KB_FIELDS_CATEGORY") or "category"
KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE") or "sourcepage"

# Use current user identity to authenticate with Azure OpenAI and Cognitive Search.
# No secrets needed, just use 'az login' locally, and managed identity when deployed on Azure.
# If you need to use keys, use separate AzureKeyCredential instances
# with the keys for each service.
# If you encounter a blocking error during a DefaultAzureCredntial resolution,
# you can exclude the problematic credential by using a parameter
# (ex. exclude_shared_token_cache_credential=True)
azure_credential = DefaultAzureCredential()

# Used by the OpenAI SDK
openai.api_type = "azure_ad"
openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
openai.api_version = "2023-03-15-preview"

# Comment these two lines out if using keys, set your API key in the
# OPENAI_API_KEY environment variable instead
openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
openai.api_key = openai_token.token

# Set up clients for Cognitive Search
SEARCH_CLIENTS = {
    ACSIndex.SEARCH_ALL: SearchClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        index_name=AZURE_SEARCH_INDEX,
        credential=azure_credential
    )
}

app = Flask(__name__)


def proxy(host, path):
    """Finalize HTTP response for serving static files."""
    response = get(f"{host}{path}")
    excluded_headers = [
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    ]
    headers = {
        name: value
        for name, value in response.raw.headers.items()
        if name.lower() not in excluded_headers
    }
    return (response.content, response.status_code, headers)


@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def static_file(path: str):
    """Send target file to the user."""
    print(f"[DEBUG] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | static_file")
    if os.environ.get("FLASK_DEBUG"):
        return proxy("http://localhost:5173", request.path)
    return app.send_static_file(path)


@app.route("/ask", methods=["POST"])
def ask():
    """Respond user questions."""
    print(f"[DEBUG] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ask")
    ensure_openai_token()
    approach = request.json.get("approach", RetrieveReadApproach.KEY)
    deployment = request.json.get("deployment", AZURE_OPENAI_GPT_DEPLOYMENT_DEFAULT)
    index = ACSIndex.SEARCH_ALL

    # Create approach instance
    if approach == RetrieveReadApproach.KEY:
        prompting_strategy = RetrieveReadApproach(SEARCH_CLIENTS[index], deployment)
    elif approach == RetrieveReformulateRetrieveReadApproach.KEY:
        prompting_strategy = RetrieveReformulateRetrieveReadApproach(SEARCH_CLIENTS[index], deployment)
    elif approach == RetrieveReadReadApproach.KEY:
        prompting_strategy = RetrieveReadReadApproach(SEARCH_CLIENTS[index], deployment)
    elif approach == RetrieveReadRetryApproach.KEY:
        prompting_strategy = RetrieveReadRetryApproach(SEARCH_CLIENTS[index], deployment)
    else:
        return jsonify({"error": "unknown approach"}), 400

    try:
        r = prompting_strategy.run(request.json["question"], request.json.get("overrides") or {})
        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /ask")
        return jsonify({"error": str(e)}), 500


def ensure_openai_token():
    """Refresh OpenAI token if necessary."""
    global openai_token
    if openai_token.expires_on < int(time.time()) - 60:
        openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
        openai.api_key = openai_token.token


if __name__ == "__main__":
    app.run()
