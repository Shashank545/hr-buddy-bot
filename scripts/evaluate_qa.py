"""Evaluate question-answering on Chat KOMEI."""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

import requests

from evaluate_utils import (
    ApproachOption,
    APPROACH_OPTIONS,
    extract_test_cases,
    LLMOption,
    LLM_OPTIONS,
    MAP_FROM_INT_TO_APPROACH,
    MAP_FROM_SEARCH_OPTION_TO_INT,
    SearchOption,
    SEARCH_OPTIONS,
    SEARCH_OPTIONS_VECTOR,
    to_csv,
    to_json,
)
from prepdocs import TEXT_EMBEDDING_ADA_002_DEPLOYMENT


MAX_RETRY = 5
RETRY_INTERVAL = 10


def process_args():
    """Process command line args."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--approach-options",
        default=1,
        help=(
            "Select approach options. Each option must be separated by a comma. "
            f"Available options: {APPROACH_OPTIONS}"
        )
    )
    parser.add_argument(
        "--llm-options",
        default=LLMOption.Gpt35Turbo,
        help=(
            "Select LLM options. Each option must be separated by a comma. "
            f"Available options: {LLM_OPTIONS}"
        )
    )
    parser.add_argument(
        "--top",
        default=3,
        type=int,
        help="The number of documents to return",
    )
    parser.add_argument(
        "--temperature",
        default=0,
        type=int,
        help="Temperature value used in chat.completion API",
    )
    parser.add_argument(
        "--search-option",
        default=SearchOption.BM25,
        choices=SEARCH_OPTIONS,
        help=f"Select a search option from {SEARCH_OPTIONS}"
    )
    parser.add_argument(
        "--num-of-test-cases",
        default=None,
        type=int,
        help="The number of test cases to run. If not provided, we use all the test cases.",
    )

    args = parser.parse_args()

    # Validate --approach-options
    approach_options = []
    for approach_option in args.approach_options.split(","):
        approach_option = int(approach_option)
        if approach_option in APPROACH_OPTIONS:
            approach_options.append(approach_option)
        else:
            print(f"[WARNING] --approach-options='{approach_option}' is invalid and ignored")
    if len(approach_options) == 0:
        print("[WARNING] No valid approach_option is provided.")
        exit(1)

    # Validate --llm-options
    llm_options = []
    for llm_option in args.llm_options.split(","):
        if llm_option in LLM_OPTIONS:
            llm_options.append(llm_option)
        else:
            print(f"[WARNING] --llm-options='{llm_option}' is invalid and ignored")
    if len(llm_options) == 0:
        print("[WARNING] No valid llm_option is provided.")
        exit(1)

    return (
        approach_options,
        llm_options,
        args.search_option,
        args.top,
        args.temperature,
        args.num_of_test_cases,
    )


def generate_answer(
    question: str,
    approach: ApproachOption,
    llm: LLMOption,
    search_option: SearchOption,
    top: int,
    temperature: int,
) -> dict:
    """Generate answer."""
    headers = {"Content-type": "application/json"}
    payload = {
        "question": question,
        "approach": approach,
        "deployment": llm,
        "overrides": {
            "semantic_captions": False,
            "top": top,
            "temperature": temperature,
            "search_option": MAP_FROM_SEARCH_OPTION_TO_INT[search_option]
        }
    }

    retry = 0
    while retry < MAX_RETRY:
        resp = requests.post(
            url="http://127.0.0.1:5000/ask",
            headers=headers,
            data=json.dumps(payload),
            timeout=120,
        )

        if resp.status_code == 200:
            return resp.json()
        else:
            retry += 1
            time.sleep(RETRY_INTERVAL)

    return None


def evaluate(
    test_cases: list,
    approach: int,
    llm: LLMOption,
    search_option: SearchOption,
    top: int,
    temperature: int,
    output_dir: Path,
    output_file_suffix: str,
):
    """Run evaluation."""
    eval_results = []
    responses = []
    acc_numerator = acc_denominator = evaluation_score = time_elapsed = estimated_cost = 0
    for test_case in tqdm(test_cases, desc =f"[INFO] approach{approach}, {llm}"):
        # Generate answer
        resp = generate_answer(
            question=test_case["query"],
            approach=MAP_FROM_INT_TO_APPROACH[approach],
            llm=llm,
            search_option=search_option,
            top=top,
            temperature=temperature,
        )

        responses.append({
            "test_id": test_case["id"],
            "question": test_case["query"],
            "response": resp,
        })

        if resp:
            num_of_expected_items = len(test_case["knowledge_id"])
            retrieved_knowledge_ids = {item["id"] for item in resp["data_points"]}
            num_of_matches = len(retrieved_knowledge_ids.intersection(test_case["knowledge_id"]))

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
                "expected_answer": test_case["answer"],
                "answer": resp["answer"],
                "acs_num_of_expected_items": num_of_expected_items,
                "acs_num_of_matches": num_of_matches,
                "acs_evaluation_score": evaluation_score,
                "time_elapsed": resp["monitoring"]["time"]["total"],
                "estimated_cost": resp["monitoring"]["cost"]["total"],
            })

            time_elapsed += resp["monitoring"]["time"]["total"]
            estimated_cost += resp["monitoring"]["cost"]["total"]
        
        else:
            print(f"[WARNING] Failed to generate an answer for test_id={test_case['id']}")
            eval_results.append({
                "test_id": test_case["id"],
                "query": test_case["query"],
                "answer": None,
                "acs_num_of_expected_items": None,
                "acs_num_of_matches": None,
                "acs_evaluation_score": None,
                "time_elapsed": None,
                "estimated_cost": None,
            })

    to_csv(eval_results, output_dir.joinpath(f"eval_results_approach{approach}_{llm}_{output_file_suffix}.csv"))
    to_json(responses, output_dir.joinpath(f"responses_approach{approach}_{llm}_{output_file_suffix}.json"))

    return {
        "approach": f"Approach{approach}, {MAP_FROM_INT_TO_APPROACH[approach]}",
        "llm": llm,
        "search_option": search_option,
        "vector_option": TEXT_EMBEDDING_ADA_002_DEPLOYMENT if search_option in SEARCH_OPTIONS_VECTOR else None,
        "top": top,
        "temperature": temperature,
        "time_elapsed[s]": round(time_elapsed, 2),
        "estimated_cost[JPY]": round(estimated_cost, 2),
        "acs_accuracy": f"{acc_numerator}/{acc_denominator}",
        "acs_accuracy[%]": round(acc_numerator/acc_denominator * 100, 2) if acc_denominator else "n/a",
    }


def main():
    """Orchestrate evaluation"""
    (
        approach_options,
        llm_options,
        search_option,
        top,
        temperature,
        num_of_test_cases,
    ) = process_args()

    # Extract test cases
    test_cases = extract_test_cases(max_count=num_of_test_cases)

    # Prepare output dir
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    num_of_approach_options = len(approach_options)
    num_of_llm_options = len(llm_options)
    if num_of_approach_options > 1 and num_of_llm_options == 1:
        output_dir = Path(f"data/eval_approach_{timestamp}")
    elif num_of_approach_options == 1 and num_of_llm_options > 1:
        output_dir = Path(f"data/eval_llm_{timestamp}")
    else:
        output_dir = Path(f"data/eval_approach_llm_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run evaluation
    eval_summary = []
    for approach in approach_options:
        for llm in llm_options:
            summary = evaluate(
                test_cases=test_cases,
                approach=approach,
                llm=llm,
                search_option=search_option,
                top=top,
                temperature=temperature,
                output_dir=output_dir,
                output_file_suffix=timestamp,
            )
            eval_summary.append(summary)

    # Save eval summary
    to_csv(eval_summary, output_dir.joinpath(f"_summary_{timestamp}.csv"))
    print(f"[INFO] Output files saved at {output_dir}")


if __name__ == "__main__":
    main()
