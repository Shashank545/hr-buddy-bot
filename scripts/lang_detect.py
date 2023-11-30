import spacy
from spacy_langdetect import LanguageDetector
from spacy.language import Language


def create_lang_detector(nlp, name):
    return LanguageDetector()

Language.factory("language_detector", func=create_lang_detector)


# Load SpaCy model with language detection component
nlp = spacy.load("en_core_web_sm")
nlp.add_pipe('language_detector', last=True)


def detect_language(text):
    doc = nlp(text)

    # Access the language detected
    detected_language = doc._.language["language"]

    return detected_language

# Example usage
text_to_detect = """
In Tokyo, the bustling metropolis, life is a dynamic blend of tradition and modernity. 毎日 (Every day), people navigate the crowded streets, 忙しい (busy) with their daily routines. Salarymen in their impeccable suits rush to catch the 電車 (train) as cherry blossoms bloom along the Sumida River. The traditional 深夜ラーメン屋 (late-night ramen shops) stand alongside trendy カフェ (cafes) serving matcha lattes. Families gather for お花見 (hanami) picnics under sakura trees, sharing delicious お弁当 (bento) boxes. As the sun sets, neon lights illuminate izakayas, inviting patrons to enjoy 酒 (sake) and 美味しい (delicious) 焼き鳥 (yakitori). From the serene 神社 (shrines) in Kyoto to the bustling 魚市場 (fish markets) in Osaka, Japan's rich tapestry of culture and daily life is a harmonious dance between the past and the present."""
detected_language = detect_language(text_to_detect)

print(f"The detected language is: {detected_language}")
