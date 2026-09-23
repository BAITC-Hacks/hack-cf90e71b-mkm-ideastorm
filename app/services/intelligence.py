"""Local text-intelligence abstraction. Ollama-compatible; no hosted API calls."""
import json
import urllib.request

from app.config import DEMO_MODE, OLLAMA_BASE_URL, OLLAMA_MODEL


class TextIntelligence:
    def extract_action_items(self, transcript: str, meeting_date: str) -> list[dict]:
        raise NotImplementedError

    def summarize(self, transcript: str) -> str:
        raise NotImplementedError


class DemoTextIntelligence(TextIntelligence):
    def extract_action_items(self, transcript: str, meeting_date: str) -> list[dict]:
        return []  # Illustrative action items are seeded with the demo meeting.

    def summarize(self, transcript: str) -> str:
        return "Демо-режим: пример краткого резюме встречи на русском языке."


class OllamaTextIntelligence(TextIntelligence):
    """Structured extraction through a self-hosted Ollama endpoint on localhost."""
    def _generate(self, prompt: str) -> str:
        payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                              "options": {"temperature": 0.1}}).encode("utf-8")
        request = urllib.request.Request(OLLAMA_BASE_URL + "/api/generate", data=payload,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))["response"]

    def extract_action_items(self, transcript: str, meeting_date: str) -> list[dict]:
        prompt = ("Extract actionable commitments from this Russian, Kazakh, or mixed-language transcript. "
                  "Resolve relative deadlines using meeting date " + meeting_date + ". Return only JSON array; "
                  "each item has task, responsible_person, deadline (ISO date/time or unknown), source, confidence (0-1).\n" + transcript)
        return json.loads(self._generate(prompt))

    def summarize(self, transcript: str) -> str:
        return self._generate("Summarize this Russian/Kazakh meeting transcript in Russian with decisions and next steps:\n" + transcript)


def get_text_intelligence():
    return DemoTextIntelligence() if DEMO_MODE else OllamaTextIntelligence()
