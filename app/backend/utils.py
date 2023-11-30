"""Utility functions."""
import openai
import spacy
from constants import OPENAI_DEPLOYMENT_TEXT_EMBEDDING_ADA_002, OPENAI_PRICING_PER_TOKEN
from spacy.language import Language
from spacy_langdetect import LanguageDetector


def create_lang_detector(nlp, name):
    """Instatiate spacy language detector."""
    return LanguageDetector()

Language.factory("language_detector", func=create_lang_detector)

# Load SpaCy model with language detection component
nlp = spacy.load("en_core_web_sm")
nlp.add_pipe('language_detector', last=True)


def nonewlines(s: str) -> str:
    """Replace newline."""
    return s.replace("\n", " ").replace("\r", " ")


def generate_embeddings(text: str):
    """Generate text embeddings using Azure OpenAI text-embedding-ada-002."""
    response = openai.Embedding.create(
        input=text,
        engine=OPENAI_DEPLOYMENT_TEXT_EMBEDDING_ADA_002
    )
    embeddings = response["data"][0]["embedding"]
    return embeddings


def calculate_cost(model: str, usage: dict):
    """Calculate estimated cost based on the # of tokens."""
    cost = 0
    for key in OPENAI_PRICING_PER_TOKEN[model]:
        cost += OPENAI_PRICING_PER_TOKEN[model][key] * usage[key]
    return round(cost, 2)


def detect_language(text):
    """Detect language of input text."""
    Language.factory("language_detector", func=create_lang_detector)
    doc = nlp(text)

    # Access the language detected
    detected_language = doc._.language["language"]

    return detected_language
