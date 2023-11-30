import os

import openai
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

openai.api_type = "azure"
openai.api_key = os.environ.get("OPENAI_API_KEY")
openai.api_base = os.environ.get("OPENAI_API_ENDPOINT")
openai.api_version = "2023-05-15"

text = "東京に住んでいる"
response = openai.Embedding.create(input=text, engine="text-embedding-ada-002")