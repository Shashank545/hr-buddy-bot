"""Constants."""
from enum import Enum, IntEnum

# OpenAI deployment names
OPENAI_DEPLOYMENT_GPT_35_TURBO = "gpt-35-turbo"
OPENAI_DEPLOYMENT_GPT_4 = "gpt-4"
OPENAI_DEPLOYMENT_TEXT_EMBEDDING_ADA_002 = "text-embedding-ada-002"

# Azure OpenAI pricing
# https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/
OPENAI_PRICING_PER_TOKEN = {
    OPENAI_DEPLOYMENT_GPT_35_TURBO: {
        "prompt_tokens": 0.281e-3,
        "completion_tokens": 0.281e-3,
    },
    OPENAI_DEPLOYMENT_GPT_4: {
        "prompt_tokens": 4.215e-3,
        "completion_tokens": 8.430e-3,
    },
    OPENAI_DEPLOYMENT_TEXT_EMBEDDING_ADA_002: {
        "prompt_tokens": 0.014455e-3,
    }
}


# Azure Cognitive Search - Search options
class SearchOption(IntEnum):
    """ACS search options."""

    BM25 = 0
    Semantic = 1
    Vector = 2
    VectorBM25 = 3
    VectorSemantic = 4


# Prompt templates
SYSTEM_PROMPT_ENG_ENG = """
You are an AI assistant. Please output your answer in English based only on the information 
below.Answer "I don't know" if there is insufficient information for the question."""

SYSTEM_PROMPT_JP_JP = """
あなたは AI アシスタントです。以下の情報のみを基に、日本語で回答を出力してください。
質問に対して情報が不足している場合は「わかりません」と答えてください。"""


SYSTEM_PROMPT_ENG_JP = """
You are an AI assistant. Please output your answer in English even when some of the text below is 
in Japanese. Answer based only on the information below and output "I don't know" if there 
is insufficient information for the question."""

SYSTEM_PROMPT_JP_ENG = """
あなたは AI アシスタントです。以下の文章が英語の場合でも、回答は日本語で出力してください。
以下の情報のみに基づいて回答し、質問に対して情報が不足している場合は「わかりません」と出力します。"""



SYSTEM_PROMPT_GENERATE_ANSWER = """
You are an AI assistant. Please output your response in English based on the following 
information. Answer based on the information provided, and if there is insufficient 
information for your question, answer "I don't know"."""

USER_PROMPT_GENERATE_QUESTION = """
{content}
Based on the information above, output one Japanese question text that gives a more accurate answer 
to the question "{question}".
"""


USER_PROMPT_GENERATE_ANSWER = """
#Source
{source}
#Question: {question}
#Answer:
"""

USER_PROMPT_CONFIRMING_ANSWER_ENG = """
If the answer text "{answer}" is appropriate for the question text "{question}", please output "Yes".
If it is not appropriate, please rewrite the answer sentence into a more appropriate form and output it.
"""

USER_PROMPT_CONFIRMING_ANSWER_JP = """
回答テキスト「{answer}」が質問テキスト「{question}」に適切な場合は、余分なテキストを含まずに日本語のみで「はい」を出力してください。
不適切な場合は、回答文をより適切な形に書き直して出力してください。
"""


SELF_SERVED_MODELS_URL = "http://40.81.203.154:6000/embed/"


class AnalysisPanelLabel(str, Enum):
    """Labels used in the Analysis Panel."""

    ANSWER_CONFIRMATION_RESULT = "回答の確認結果"
    ANSWER_GENERATION = "回答の作成"
    ANSWER_GENERATION_PROMPT = "回答作成用のプロンプト"
    RETRIEVAL = "コンテントの検索"
    VECTORIZATION = "ベクトル化"
    TOKEN_COMPLETION = "完了トークン"
    TOKEN_PROMPTS = "プロンプトトークン"
    TOKEN_TOTAL = "合計トークン"

    # Approach 2
    QUESTION_REFORMULATION = "質問文の書き換え"
    QUESTION_REFORMULATION_PROMPT = "質問文書き換え用のプロンプト"
    REFORMULATED_QUESTION = "書き換え後の質問文"

    # Approach 3
    ANSWER_CONFIRMATION = "回答の確認・修正"
    ANSWER_CONFIRMATION_PROMPT = "回答確認用のプロンプト"
    ANSWER_CONFIRMATION_RESULT_NO = "回答が不十分なため、修正する。"
    ANSWER_CONFIRMATION_RESULT_YES = "十分な回答が作成されている。"
    ORIGINAL_ANSWER = "修正前の回答"

    # Approach 4
    ANSWER_FROM_APPROACH_1 = "Approach 1 の回答"
    DO_NOT_PROCEEDS_WITH_APPROACH_2 = "Approach 1 で十分な回答が得られたため、ここで終了する。"
    PROCEEDS_WITH_APPROACH_2 = "Approach 1 で十分な回答が得られなかったため、Approach 2 へ切り替える。"


# ACS Index options
class ACSIndex(str, Enum):
    """ACS index names."""
    
    SEARCH_ALL = "kitchat-searchindex-all"
    SEARCH_PDF = "kitchat-searchindex-pdf"
    SEARCH_HTML = "kitchat-searchindex-html"
