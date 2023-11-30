"""
Steps:
1. Given a question, retrieve relevant documents from ACS
2. Based on the retrieved contents, reformulate the question to make the user question more specific
3. Retrieve relevant documents to the reformulated question from ACS
4. Based on the retrieved contents, generate an answer
"""
import time

import openai
from approaches.approach import Approach
from constants import (
    AnalysisPanelLabel,
    SYSTEM_PROMPT_GENERATE_ANSWER,
    USER_PROMPT_GENERATE_QUESTION,
    USER_PROMPT_GENERATE_ANSWER,
)


class RetrieveReformulateRetrieveReadApproach(Approach):
    KEY = "rrrr"

    def run(self, q: str, overrides: dict) -> any:
        start_time = time.time()
        temperature = overrides.get('temperature', 0.6)

        monitoring_time_items = []
        monitoring_cost_items = []
        monitoring_usage = []
        thoughts = []

        print(f"[DEBUG] openai_deployment={self.openai_deployment}")
        print(f"[DEBUG] {temperature=}")

        # Step 1: Retrieve contents based on the input question
        self.item_suffix = f" ({AnalysisPanelLabel.QUESTION_REFORMULATION})"
        _, content, monitoring = self.retrieve(q, overrides)
        monitoring_time_items += monitoring["time"]
        self.item_suffix = ""

        # Step 2: Generate/reformulate question based on the input question
        message = [
            {"role": "user", "content": USER_PROMPT_GENERATE_QUESTION.format(content=content, question=q)},
        ]
        start_time_question = time.time()
        completion = openai.ChatCompletion.create(
            engine=self.openai_deployment,
            messages=message,
            temperature=temperature,
            max_tokens=1024,
            n=1,
            stop=["\n"]
        )
        reformulated_question = self.clean_text(completion.choices[0].message.content)
        monitoring_time_items.append(self.create_time_item(AnalysisPanelLabel.QUESTION_REFORMULATION, start_time_question))
        monitoring_cost_items.append(self.create_cost_item(AnalysisPanelLabel.QUESTION_REFORMULATION, completion["usage"]))
        monitoring_usage.append(self.create_usage_item(AnalysisPanelLabel.QUESTION_REFORMULATION, completion["usage"]))
        thoughts = [
            self.create_thought_item(AnalysisPanelLabel.QUESTION_REFORMULATION_PROMPT, message),
            self.create_thought_item(AnalysisPanelLabel.REFORMULATED_QUESTION, reformulated_question)
        ]
        print(f"[DEBUG] {reformulated_question=}")

        # Step 3: Retrieve contents based on the reformulated question
        self.item_suffix = f" ({AnalysisPanelLabel.ANSWER_GENERATION})"
        data_points, retrieved, monitoring = self.retrieve(reformulated_question, overrides)
        monitoring_time_items += monitoring["time"]
        self.item_suffix = ""

        # Step 4: Generate answer based on the reformulated question
        start_time_answer = time.time()
        message = [
            {"role": "system", "content": SYSTEM_PROMPT_GENERATE_ANSWER},
            {
                "role": "user",
                "content": USER_PROMPT_GENERATE_ANSWER.format(
                    source=retrieved,
                    question=reformulated_question
                )
            },
        ]
        completion = openai.ChatCompletion.create(
            engine=self.openai_deployment,
            messages=message,
            temperature=temperature,
            max_tokens=1024,
            n=1,
        )
        monitoring_time_items.append(self.create_time_item(AnalysisPanelLabel.ANSWER_GENERATION, start_time_answer))
        monitoring_cost_items.append(self.create_cost_item(AnalysisPanelLabel.ANSWER_GENERATION, completion["usage"]))
        monitoring_usage.append(self.create_usage_item(AnalysisPanelLabel.ANSWER_GENERATION, completion["usage"]))
        thoughts.append(self.create_thought_item(AnalysisPanelLabel.ANSWER_GENERATION_PROMPT, message))
    
        return self.create_response(
            data_points=data_points,
            answer=self.clean_text(completion.choices[0].message.content),
            thoughts=thoughts,
            start_time=start_time,
            monitoring_time_items=monitoring_time_items,
            monitoring_cost_items=monitoring_cost_items,
            usage=monitoring_usage,
        )
