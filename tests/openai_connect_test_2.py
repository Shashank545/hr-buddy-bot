import openai
from azure.identity import AzureDeveloperCliCredential

azd_credential = AzureDeveloperCliCredential()

openai.api_type = "azure_ad"
openai_token = azd_credential.get_token("https://cognitiveservices.azure.com/.default")
openai.api_key = openai_token.token
openai.api_base = "https://jp-oai-jpe-dev-kit-chat-001.openai.azure.com/"
openai.api_version = "2023-05-15"

response = openai.Embedding.create(
    input="Your text string goes here",
    engine="text-embedding-ada-002"
)
embeddings = response['data'][0]['embedding']
print(embeddings)