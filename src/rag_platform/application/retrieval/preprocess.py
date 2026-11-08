import re

_WS = re.compile(r"\s+")


def preprocess_question(question: str) -> str:
    collapsed = _WS.sub(" ", question.strip())
    return collapsed[:4000]
