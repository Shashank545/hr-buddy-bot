"""
Steps.

1. Given a question, retrieve relevant documents from ACS
2. Based on the retrieved contents, generate an answer
3. Confirm that the generated answer is acceptable
"""

import time

import openai
from approaches.approach import Approach
from constants import (
    SYSTEM_PROMPT_ENG_ENG,
    SYSTEM_PROMPT_ENG_JP,
    SYSTEM_PROMPT_JP_ENG,
    SYSTEM_PROMPT_JP_JP,
    USER_PROMPT_CONFIRMING_ANSWER_ENG,
    USER_PROMPT_CONFIRMING_ANSWER_JP,
    USER_PROMPT_GENERATE_ANSWER,
    AnalysisPanelLabel
)
from utils import detect_language


class RetrieveReadReadApproach(Approach):
    """Implement a prompting strategy that we call as 'Retrieve -> Read -> Read'."""

    KEY = "rrr"

    def run(self, q: str, overrides: dict) -> any:
        """Orchestrate execution of the prompting strategy."""
        start_time = time.time()
        temperature = overrides.get('temperature', 0.6)

        monitoring_time_items = []
        monitoring_cost_items = []
        monitoring_usage = []
        thoughts = []

        print(f"[DEBUG] openai_deployment={self.openai_deployment}")
        print(f"[DEBUG] {temperature=}")


        # Step 0: Question language detection
        ques_lang = detect_language(q)
        print(f"[DEBUG] {ques_lang=}")



        # Step 1: Retrieve contents based on the input question
        data_points, retrieved, monitoring = self.retrieve(q, overrides)
        monitoring_time_items += monitoring["time"]
        context_lang = detect_language(retrieved)
        print(f"[DEBUG] {context_lang=}")
        print("\n\n")
        print(f"[DEBUG] {retrieved=}")

        # Step 2: Message selection of static prompts based on language detected

        if ques_lang == "en" and context_lang == "en":
            message = [
                {"role": "system", "content": SYSTEM_PROMPT_ENG_ENG}
            ]
        elif ques_lang == "en" and context_lang == "ja":
            message = [
                {"role": "system", "content": SYSTEM_PROMPT_ENG_JP}
            ]
        elif ques_lang == "ja" and context_lang == "en":
            message = [
                {"role": "system", "content": SYSTEM_PROMPT_JP_ENG}
            ]
        else:
            message = [
                {"role": "system", "content": SYSTEM_PROMPT_JP_JP}
            ]

        message.append({"role": "user", "content": USER_PROMPT_GENERATE_ANSWER.format(
            source=retrieved, question=q)}
        )
    
        start_time_answer = time.time()
        completion = openai.ChatCompletion.create(
            engine=self.openai_deployment,
            messages=message,
            temperature=temperature,
            max_tokens=1024,
            n=1,
        )
        answer = completion.choices[0].message.content
        print("\n\n")
        print(f"[DEBUG] {answer=}")
        monitoring_time_items.append(
            self.create_time_item(AnalysisPanelLabel.ANSWER_GENERATION, start_time_answer)
        )
        monitoring_cost_items.append(
            self.create_cost_item(AnalysisPanelLabel.ANSWER_GENERATION, completion["usage"])
        )
        monitoring_usage.append(
            self.create_usage_item(AnalysisPanelLabel.ANSWER_GENERATION, completion["usage"])
        )
        thoughts.append(
            self.create_thought_item(AnalysisPanelLabel.ANSWER_GENERATION_PROMPT, message)
        )

        # Step 3: Confirm that the generated answer is acceptable
        ans_lang = detect_language(answer)
        if ques_lang == "en" and ans_lang == "en":

            confirm_message = [
                {"role": "system", "content": USER_PROMPT_CONFIRMING_ANSWER_ENG.format(
                    answer=answer, question=q)}
            ]
        else:
            confirm_message = [
                {"role": "system", "content": USER_PROMPT_CONFIRMING_ANSWER_JP.format(
                    answer=answer, question=q)}
            ]
            
        start_time_answer = time.time()
        completion = openai.ChatCompletion.create(
            engine=self.openai_deployment,
            messages=confirm_message,
            temperature=temperature,
            max_tokens=1024,
            n=1,
        )
        confirmation_response = self.clean_text(completion.choices[0].message.content)
        monitoring_time_items.append(
            self.create_time_item(AnalysisPanelLabel.ANSWER_CONFIRMATION, start_time_answer)
            )
        monitoring_cost_items.append(
            self.create_cost_item(AnalysisPanelLabel.ANSWER_CONFIRMATION, completion["usage"])
            )
        monitoring_usage.append(
            self.create_usage_item(AnalysisPanelLabel.ANSWER_CONFIRMATION, completion["usage"])
            )
        thoughts.append(
            self.create_thought_item(AnalysisPanelLabel.ANSWER_CONFIRMATION_PROMPT, message)
            )
        print(f"[DEBUG] {confirmation_response=}")

        if confirmation_response == "Yes" or confirmation_response == "はい":
            thoughts.append(
                self.create_thought_item(
                    AnalysisPanelLabel.ANSWER_CONFIRMATION_RESULT,
                    AnalysisPanelLabel.ANSWER_CONFIRMATION_RESULT_YES
                )
            )
            return self.create_response(
                data_points=data_points,
                answer=answer,
                thoughts=thoughts,
                start_time=start_time,
                monitoring_time_items=monitoring_time_items,
                monitoring_cost_items=monitoring_cost_items,
                usage=monitoring_usage,
            )

        thoughts.append(
            self.create_thought_item(
                AnalysisPanelLabel.ANSWER_CONFIRMATION_RESULT,
                AnalysisPanelLabel.ANSWER_CONFIRMATION_RESULT_NO
            )
        )
        thoughts.append(self.create_thought_item(AnalysisPanelLabel.ORIGINAL_ANSWER, answer))

        return self.create_response(
            data_points=data_points,
            answer=completion.choices[0].message.content,
            thoughts=thoughts,
            start_time=start_time,
            monitoring_time_items=monitoring_time_items,
            monitoring_cost_items=monitoring_cost_items,
            usage=monitoring_usage,
        )
