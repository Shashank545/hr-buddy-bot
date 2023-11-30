"""Base class for prompting strategies."""
import re
import time

from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType, Vector
from constants import AnalysisPanelLabel, SearchOption
from rich import print
from utils import calculate_cost, generate_embeddings, nonewlines


class Approach:
    """Base class for prompting strategies."""

    KEY = ""

    def __init__(
        self, search_client: SearchClient,
        openai_deployment: str,
    ):
        """Initialize class."""
        self.search_client = search_client
        self.openai_deployment = openai_deployment

        self.item_prefix = ""
        self.item_suffix = ""

    def run(self, q: str, use_summaries: bool) -> any:
        """Orchestrate execution of the prompting strategy."""
        raise NotImplementedError

    def create_label(self, label: str) -> str:
        """Create a label."""
        return self.item_prefix + label + self.item_suffix

    def create_time_item(self, label: str, start_time) -> dict:
        """Create an item for monitoring.time."""
        return {"label": self.create_label(label), "value": round(time.time() - start_time, 2)}

    def create_cost_item(self, label: str, usage: dict) -> dict:
        """Create an item for monitoring.cost."""
        return {"label": self.create_label(label), "value": calculate_cost(self.openai_deployment, usage)}

    def create_usage_item(self, label: str, usage) -> dict:
        """Create an item for monitoring.usage."""
        return {"label": self.create_label(label), "value": usage}

    def create_thought_item(self, label: str, value = "") -> dict:
        """Create an item for monitoring.prompts."""
        return {"label": self.create_label(label), "value": value}

    def retrieve(self, question: str, overrides: dict) -> list:
        """Retreve documents from ACS."""
        top = overrides.get("top") or 3
        search_option = overrides.get("search_option", SearchOption.BM25)
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        exclude_category = overrides.get("exclude_category") or None
        filter_ = "category ne '{}'".format(
            exclude_category.replace("'", "''")
        ) if exclude_category else None

        monitoring = {"time": [], "cost": []}

        # Construct
        payload = {
            "filter": filter_,
            "top": top,
        }
        if search_option in {SearchOption.Semantic, SearchOption.VectorSemantic}:
            payload = {
                **payload,
                "query_type": QueryType.SEMANTIC,
                "query_language": "en-us",
                "semantic_configuration_name": "default",
                "query_caption": "extractive|highlight-false" if use_semantic_captions else None,
            }
        if search_option in {SearchOption.Vector, SearchOption.VectorBM25, SearchOption.VectorSemantic}:
            start_time_embeddings = time.time()
            payload["vectors"] = [
                Vector(
                    value=generate_embeddings(question),
                    k=top,
                    fields="content_embedding",
                )
            ]
            monitoring["time"].append(self.create_time_item(
                AnalysisPanelLabel.VECTORIZATION, start_time_embeddings)
            )

        if search_option == SearchOption.Vector:
            payload["search_text"] = None
            payload["search_fields"] = []
        else:
            payload["search_text"] = question
            payload["search_fields"] = ["content"]

        print(f"[DEBUG] search_option: '{search_option}' ({SearchOption(search_option).name})")
        print(f"[DEBUG] use_semantic_captions: {use_semantic_captions}")
        print(f"[DEBUG] payload: '{payload}'")
        print(f"[DEBUG] search_index: '{self.search_client._index_name}'")

        # Retrieve relevant documents from ACS
        start_time_retrieval= time.time()
        search_results = self.search_client.search(**payload)

        # Parse search results
        data_points = []
        contents = []
        for doc in search_results:
            data_points.append(
                {
                    "score": doc["@search.score"],
                    "id": doc["id"],
                    "parent_id": doc["parent_id"],
                    "title": doc.get("title", ""),
                    "content": doc.get("content", ""),
                    "source_path": doc.get("source_path", ""),
                    "lang": doc.get("lang", ""),
                    "page_num": doc.get("page_num", ""),
                    "num_tokens": doc.get("num_tokens", ""),
                    "modified_from_source": doc.get("modified_from_source", ""),
                }
            )
            if (
                use_semantic_captions
                and search_option in {SearchOption.Semantic, SearchOption.VectorSemantic}
            ):
                contents.append("- " + nonewlines("。".join([c.text for c in doc["@search.captions"]])))
            else:
                contents.append("- " + nonewlines(doc["content"]))

        monitoring["time"].append(self.create_time_item(AnalysisPanelLabel.RETRIEVAL, start_time_retrieval))

        # TODO: For now, limit the content length < 1750 to avoid the maximum-context-length error
        content = "\n".join(contents)[:1500]

        return data_points, content, monitoring

    def clean_text(self, text: str) -> str:
        """Clean up input text."""
        text = re.sub(r"^「(.*)」$", r"\1", text)
        return text

    def create_response(
        self,
        data_points: list,
        answer: str,
        thoughts: list,
        start_time: float,
        monitoring_time_items: list,
        monitoring_cost_items: list,
        usage: dict,
    ) -> dict:
        """Create response for /ask endpoint."""
        return {
            "approach": self.KEY,
            "data_points": data_points,
            "answer": self.clean_text(answer),
            "thoughts": thoughts,
            "monitoring": {
                "time": {
                    "total": round(time.time() - start_time, 2),
                    "items": sorted(monitoring_time_items, key=lambda item: item["value"], reverse=True),
                },
                "cost": {
                    "total": round(sum(item["value"] for item in monitoring_cost_items), 2),
                    "items": sorted(monitoring_cost_items, key=lambda item: item["value"], reverse=True)
                },
                "usage": usage,
            }
        }
