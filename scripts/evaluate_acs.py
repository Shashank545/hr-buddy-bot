"""Evaluate ACS."""
import argparse
from datetime import datetime
from pathlib import Path

import openai
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType, Vector

from prepdocs import generate_embeddings, TEXT_EMBEDDING_ADA_002_DEPLOYMENT

from evaluate_utils import (
    extract_test_cases,
    SearchOption,
    SEARCH_OPTIONS,
    SEARCH_OPTIONS_VECTOR,
    to_csv,
)


def process_args():
    """Process command line args."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--search-service",
        required=True,
        help="ACS instance name",
    )
    parser.add_argument(
        "--index",
        required=True,
        help="ACS index name",
    )
    parser.add_argument(
        "--search-options",
        default=SearchOption.BM25,
        help=(
            "Select search options. Each option must be separated by a comma. "
            f"Available options: {SEARCH_OPTIONS}"
        )
    )
    parser.add_argument(
        "--top",
        default=3,
        type=int,
        help="The number of documents to return",
    )
    parser.add_argument(
        "--openai-service",
        default=None,
        help="OpenAI instance name",
    )
    parser.add_argument(
        "--num-of-test-cases",
        default=None,
        type=int,
        help="The number of test cases to run. If not provided, we use all the test cases.",
    )

    args = parser.parse_args()

    # Validate --search-options
    search_options = []
    for search_option in args.search_options.split(","):
        if search_option in SEARCH_OPTIONS:
            search_options.append(search_option)
            if search_option in SEARCH_OPTIONS_VECTOR and args.openai_service is None:
                print(f"[ERROR] Set --openai-service when using --search-options='{search_option}'")
                exit(1)
        else:
            print(f"[WARNING] --search-options='{search_option}' is invalid and ignored")
    if len(search_options) == 0:
        print("[WARNING] No valid search_option is provided.")
        exit(1)

    return args.search_service, args.index, search_options, args.top, args.openai_service, args.num_of_test_cases


def retrieve(
    search_client: SearchClient,
    query: str,
    search_option: SearchOption,
    top: int,
) -> list:
    """Retrieve documents from ACS."""
    payload = {"top": top}

    if search_option in {SearchOption.Semantic, SearchOption.VectorSemantic}:
        payload = {
            **payload,
            "query_type": QueryType.SEMANTIC,
            "query_language": "ja-jp",
            "semantic_configuration_name": "default",
        }
    if search_option in SEARCH_OPTIONS_VECTOR:
        payload["vectors"] = [Vector(
            value=generate_embeddings(query),
            k=top,
            fields="contentEmbeddings",
        )]
    if search_option == SearchOption.Vector:
        payload["search_text"] = None
        payload["search_fields"] = []
    else:
        payload["search_text"] = query
        payload["search_fields"] = ["content"]

    search_results_iter = search_client.search(**payload)

    search_results = []
    for doc in search_results_iter:
        search_results.append({
            "id": doc["id"],
            "score": doc["@search.score"],
            "category": doc["category"],
            "content": doc["content"],
        })

    return search_results


def _evaluate(
    search_service: str,
    index: str,
    search_option: SearchOption,
    test_cases: list,
    top: int,
    openai_service: str = None,
) -> list:
    """Get search results for test_cases."""
    
    azd_credential = DefaultAzureCredential()

    # Set up ACS client
    search_client = SearchClient(
        endpoint=f"https://{search_service}.search.windows.net/",
        index_name=index,
        credential=azd_credential,
    )

    # Set up Azure OpenAI
    if openai_service:
        openai_token = azd_credential.get_token("https://cognitiveservices.azure.com/.default")
        openai.api_type = "azure_ad"
        openai.api_version = "2023-03-15-preview"
        openai.api_base = f"https://{openai_service}.openai.azure.com"
        openai.api_key = openai_token.token

    acc_denominator = 0
    acc_numerator = 0
    eval_results = []
    search_results = []
    for test_case in test_cases:
        search_result = retrieve(
            search_client=search_client,
            query=test_case["query"],
            search_option=search_option,
            top=top,
        )
        retrieved_knowledge_ids = {doc["id"] for doc in search_result}
        num_of_expected_items = len(test_case["knowledge_id"])
        num_of_matches = len(retrieved_knowledge_ids.intersection(test_case["knowledge_id"]))
        evaluation_score = 0 if num_of_expected_items else -1
        
        if num_of_expected_items:
            acc_denominator += 1
            if num_of_matches:
                evaluation_score = 1
                acc_numerator += 1
            else:
                evaluation_score = 0
        else:
            evaluation_score = -1
        
        eval_results.append({
            "test_id": test_case["id"],
            "query": test_case["query"],
            "num_of_expected_items": num_of_expected_items,
            "num_of_matches": num_of_matches,
            "evaluation_score": evaluation_score,
        })

        for idx, doc in enumerate(search_result):
            search_results.append({
                "test_id": test_case["id"],
                "query": test_case["query"],
                "rank": idx + 1,
                **doc,
                "evaluation_score": 1 if doc["id"] in test_case["knowledge_id"] else 0,
            })

    summary = {
        "search_option": search_option,
        "vector_option": TEXT_EMBEDDING_ADA_002_DEPLOYMENT if search_option in SEARCH_OPTIONS_VECTOR else None,
        "top": top,
        "accuracy": f"{acc_numerator}/{acc_denominator}",
        "accuracy[%]": round(acc_numerator/acc_denominator * 100, 2) if acc_denominator else "n/a",
    }

    print(f"[INFO] Accuracy ({search_option}): {summary['accuracy']} ({summary['accuracy[%]']})")

    return eval_results, search_results, summary


def evaluate(
    search_service: str,
    index: str,
    search_option: SearchOption,
    test_cases: list,
    top: int,
    output_dir: Path,
    output_file_suffix: str,
    openai_service: str = None,
):
    """Run evaluation and save results."""
    eval_results, search_results, summary = _evaluate(
        search_service=search_service,
        index=index,
        search_option=search_option,
        test_cases=test_cases,
        top=top,
        openai_service=openai_service,
    )

    # Save results
    suffix = f"{search_option}_{output_file_suffix}"
    to_csv(eval_results, output_dir.joinpath(f"eval_results_{suffix}.csv"))
    to_csv(search_results, output_dir.joinpath(f"search_results_{suffix}.csv"))

    return summary


def main():
    """Orchestrate evaluation"""
    search_service, index, search_options, top, openai_service, num_of_test_cases = process_args()

    # Extract test cases
    test_cases = extract_test_cases(max_count=num_of_test_cases)

    # Prepare output dir
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_dir = Path(f"data/eval_acs_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run evaluation
    eval_summary = []
    for search_option in search_options:
        if search_option in SEARCH_OPTIONS_VECTOR:
            summary = evaluate(
                search_service=search_service,
                index=index,
                search_option=search_option,
                openai_service=openai_service,
                test_cases=test_cases,
                output_dir=output_dir,
                output_file_suffix=timestamp,
                top=top,
            )
            eval_summary.append(summary)
        else:
            summary = evaluate(
                search_service=search_service,
                index=index,
                search_option=search_option,
                test_cases=test_cases,
                output_dir=output_dir,
                output_file_suffix=timestamp,
                top=top,
            )
            eval_summary.append(summary)

    # Save eval summary
    to_csv(eval_summary, output_dir.joinpath(f"_summary_{timestamp}.csv"))
    print(f"[INFO] Output files saved at {output_dir}")

if __name__ == "__main__":
    main()
