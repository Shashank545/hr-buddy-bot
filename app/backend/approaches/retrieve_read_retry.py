"""
Steps:

1. Do Approach 1
2. If Approach 1 doesn't produce an answer, do Approach 2
"""
import re
import time

from approaches.approach import Approach
from approaches.retrieve_read import RetrieveReadApproach
from approaches.retrieve_reformulate_retrieve_read import RetrieveReformulateRetrieveReadApproach
from constants import AnalysisPanelLabel


class RetrieveReadRetryApproach(Approach):
    KEY = "rrrt"

    def is_sufficient_answer(self, answer: str) -> bool:
        """Return true if answer is sufficient."""
        return not bool(re.match(r"^わかりません.*", answer) or re.match(r".*わかりません。?$", answer))

    def run(self, q: str, overrides: dict) -> any:
        start_time = time.time()

        thoughts = []

        approach1 = RetrieveReadApproach(self.search_client, self.openai_deployment)
        approach1.item_prefix = "[Approach 1] "
        resp1 = approach1.run(q, overrides)

        if self.is_sufficient_answer(resp1["answer"]):
            resp1["thoughts"].append(self.create_thought_item(
                AnalysisPanelLabel.ANSWER_CONFIRMATION_RESULT,
                AnalysisPanelLabel.DO_NOT_PROCEEDS_WITH_APPROACH_2
            ))
            return resp1

        thoughts += resp1["thoughts"]
        thoughts.append(self.create_thought_item(AnalysisPanelLabel.ANSWER_FROM_APPROACH_1, resp1['answer']))
        thoughts.append(self.create_thought_item(
            AnalysisPanelLabel.ANSWER_CONFIRMATION_RESULT,
            AnalysisPanelLabel.PROCEEDS_WITH_APPROACH_2
        ))

        approach2 = RetrieveReformulateRetrieveReadApproach(self.search_client, self.openai_deployment)
        approach2.item_prefix = "[Approach 2] "
        resp2 = approach2.run(q, overrides)
        
        return self.create_response(
            data_points=resp2["data_points"],
            answer=resp2["answer"],
            thoughts=thoughts + resp2["thoughts"],
            start_time=start_time,
            monitoring_time_items=resp1["monitoring"]["time"]["items"] + resp2["monitoring"]["time"]["items"],
            monitoring_cost_items=resp1["monitoring"]["cost"]["items"] + resp2["monitoring"]["cost"]["items"],
            usage=resp1["monitoring"]["usage"] + resp2["monitoring"]["usage"],
        )
