"""Retrieves documents from Azure Search and then uses OpenAI to read them and answer the question.

1. Retrieve top documents from search
2. Construct a prompt with them
3. Use OpenAI to generate a completion (answer) with that prompt
"""
import time

import openai
from approaches.approach import Approach
from constants import (
    AnalysisPanelLabel,
    SYSTEM_PROMPT_GENERATE_ANSWER,
    USER_PROMPT_GENERATE_ANSWER,
)


class RetrieveReadApproach(Approach):
    KEY = "rr"

    def run(self, q: str, overrides: dict) -> any:
        start_time = time.time()
        temperature = overrides.get('temperature', 0.6)

        monitoring_time_items = []
        monitoring_cost_items = []

        print(f"[DEBUG] openai_deployment={self.openai_deployment}")
        print(f"[DEBUG] {temperature=}")

        # Step 1: Retrieve contents based on the input question
        data_points, retrieved, monitoring = self.retrieve(q, overrides)
        monitoring_time_items += monitoring["time"]

        # Step 2: Generate answer based on the reformulated question
        message = [
            {"role": "system", "content": SYSTEM_PROMPT_GENERATE_ANSWER},
            {"role": "user", "content": USER_PROMPT_GENERATE_ANSWER.format(source=retrieved, question=q)},
        ]
        start_time_answer = time.time()
        completion = openai.ChatCompletion.create(
            engine=self.openai_deployment,
            messages=message,
            temperature=temperature,
            max_tokens=1024,
            n=1,
        )
        monitoring_time_items.append(self.create_time_item(AnalysisPanelLabel.ANSWER_GENERATION, start_time_answer))
        monitoring_cost_items.append(self.create_cost_item(AnalysisPanelLabel.ANSWER_GENERATION, completion["usage"]))
        thoughts = [self.create_thought_item(AnalysisPanelLabel.ANSWER_GENERATION_PROMPT, message)]
        usage = [self.create_usage_item(AnalysisPanelLabel.ANSWER_GENERATION, completion["usage"])]

        return self.create_response(
            data_points=data_points,
            answer=completion.choices[0].message.content,
            thoughts=thoughts,
            start_time=start_time,
            monitoring_time_items=monitoring_time_items,
            monitoring_cost_items=monitoring_cost_items,
            usage=usage,
        )
