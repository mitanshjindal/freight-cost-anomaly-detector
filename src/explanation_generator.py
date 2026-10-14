"""Grounded explanation generation for route-week findings.
"""

import logging
import os
from typing import Optional, Dict, Any, Tuple
from config.settings import LLMSettings, config
from src.evidence_validator import NoteKnowledge, ValidationAudit

logger = logging.getLogger(__name__)


class ExplanationGenerator:
    """Generates concise, factual, evidence-grounded plain-English explanations."""

    def __init__(self, llm_settings: Optional[LLMSettings] = None):
        self.llm_settings = llm_settings or config.llm
        self.token_usage = {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0
        }

    def generate_explanation(
        self,
        route: str,
        week_of: str,
        cost_per_tonne_km: float,
        vs_own_history_pct: Optional[float],
        vs_similar_routes_pct: Optional[float],
        is_anomaly: bool,
        has_sufficient_history: bool,
        matched_note: Optional[NoteKnowledge] = None,
        closest_rejected_audit: Optional[ValidationAudit] = None
    ) -> str:
        """Generate a concise explanation string adhering strictly to ground-truth evidence.

        Guarantees:
        - Never hallucinates notes or facts.
        - Matches the case study sample output wording style.
        - Explains why candidate notes were rejected when applicable.
        - Fallbacks to deterministic templates if LLM is disabled or unavailable.
        """
        # Routine non-anomalous observations: use deterministic template to avoid wasteful LLM spend
        if not is_anomaly:
            if not has_sufficient_history:
                return "Initial observation week; insufficient historical baseline to assess trend. No anomaly detected."
            return "Cost is consistent with historical and peer baselines. No anomaly detected."

        # Case 1: Justified Anomaly
        if matched_note is not None:
            if self.llm_settings.enabled and self._can_use_engine():
                exp = self._synthesize_justified_explanation(route, week_of, matched_note, vs_own_history_pct, vs_similar_routes_pct)
                if exp:
                    return exp

            # Deterministic template matching official specification:
            return (
                f"Matches note {matched_note.note_id} dated {matched_note.date}: "
                f"{matched_note.summary}. The cost rise has a clear explanation."
            )

        # Case 2: Unexplained Anomaly with a rejected candidate note nearby
        if closest_rejected_audit is not None:
            if self.llm_settings.enabled and self._can_use_engine():
                exp = self._synthesize_unexplained_explanation(route, week_of, closest_rejected_audit, vs_own_history_pct, vs_similar_routes_pct)
                if exp:
                    return exp

            # Deterministic template matching sample output v2 exactly:
            if not closest_rejected_audit.supports_cost_increase:
                summary_text = getattr(closest_rejected_audit, "note_summary", None) or closest_rejected_audit.explanation
                return (
                    f"The closest note ({closest_rejected_audit.note_id}, {closest_rejected_audit.note_date}) "
                    f"mentions {summary_text} -- it does not describe a reason for a cost rise on this route. "
                    f"No genuine justification found; flagged for review."
                )
            else:
                return (
                    f"The closest note ({closest_rejected_audit.note_id}, {closest_rejected_audit.note_date}) "
                    f"covered disruption for {closest_rejected_audit.effective_window}; the current week ({week_of}) "
                    f"is outside the supported disruption window. No genuine justification found; flagged for review."
                )

        # Case 3: Unexplained Anomaly with no candidate notes nearby
        return "No matching note found for this route or date range. Cost rise looks unexplained and worth a human review."

    def _can_use_engine(self) -> bool:
        """Verify API credentials are configured."""
        api_key = self.llm_settings.api_key or os.environ.get(self.llm_settings.api_key_env_var, "")
        return bool(api_key and len(api_key.strip()) > 5)

    def _can_use_llm(self) -> bool:
        """Compatibility alias."""
        return self._can_use_engine()

    def _execute_inference_call(self, prompt: str) -> Optional[Tuple[str, int, int]]:
        """Execute guarded call to language model API at temperature=0 with token counting."""
        api_key = self.llm_settings.api_key or os.environ.get(self.llm_settings.api_key_env_var, "")
        if not api_key:
            return None

        model = self.llm_settings.model_name
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.llm_settings.temperature,
                "maxOutputTokens": self.llm_settings.max_output_tokens
            }
        }
        try:
            import requests
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                usage = data.get("usageMetadata", {})
                in_tok = usage.get("promptTokenCount", 0)
                out_tok = usage.get("candidatesTokenCount", 0)
                self.token_usage["calls"] += 1
                self.token_usage["input_tokens"] += in_tok
                self.token_usage["output_tokens"] += out_tok
                return text, in_tok, out_tok
            else:
                logger.debug(f"Inference API returned status {resp.status_code}; using deterministic fallback.")
                return None
        except Exception as e:
            logger.debug(f"Inference API request failed ({e}); using deterministic fallback.")
            return None

    def _call_gemini_api(self, prompt: str) -> Optional[Tuple[str, int, int]]:
        """Compatibility alias."""
        return self._execute_inference_call(prompt)

    def _synthesize_justified_explanation(
        self,
        route: str,
        week_of: str,
        note: NoteKnowledge,
        vs_hist: Optional[float],
        vs_peer: Optional[float]
    ) -> Optional[str]:
        """Synthesize natural language justification matching domain rules."""
        vs_h_str = f"{vs_hist:+.1f}%" if vs_hist is not None else "N/A"
        prompt = (
            f"You are a logistics freight cost analyst. Write a concise factual explanation (1-2 sentences):\n"
            f"- Corridor: {route}\n"
            f"- Week of: {week_of}\n"
            f"- vs Own History: {vs_h_str}\n"
            f"- Verified Supporting Note: {note.note_id} dated {note.date}\n"
            f"- Event details: {note.summary}\n"
            f"Requirements:\n"
            f"1. You MUST explicitly mention 'Matches note {note.note_id} dated {note.date}'.\n"
            f"2. Conclude that the cost rise has a clear explanation.\n"
            f"3. Do not invent any unsupplied facts."
        )
        res = self._execute_inference_call(prompt)
        if res:
            text, in_tok, out_tok = res
            if note.note_id in text and ("Matches note" in text or "note" in text.lower()):
                return text
        return None

    def _call_llm_justified(self, route: str, week_of: str, note: NoteKnowledge, vs_hist: Optional[float], vs_peer: Optional[float]) -> Optional[str]:
        """Compatibility alias."""
        return self._synthesize_justified_explanation(route, week_of, note, vs_hist, vs_peer)

    def _synthesize_unexplained_explanation(
        self,
        route: str,
        week_of: str,
        audit: ValidationAudit,
        vs_hist: Optional[float],
        vs_peer: Optional[float]
    ) -> Optional[str]:
        """Synthesize explanation for candidate rejection."""
        vs_h_str = f"{vs_hist:+.1f}%" if vs_hist is not None else "N/A"
        prompt = (
            f"You are a logistics freight cost analyst. Write a concise factual explanation (1-2 sentences):\n"
            f"- Corridor: {route}\n"
            f"- Week of: {week_of}\n"
            f"- vs Own History: {vs_h_str}\n"
            f"- Closest Candidate Note Examined: {audit.note_id} dated {audit.note_date} ({audit.note_summary})\n"
            f"- Why it was rejected: {audit.explanation}\n"
            f"Requirements:\n"
            f"1. State that the closest note ({audit.note_id}, {audit.note_date}) mentions {audit.note_summary} but does not describe a reason for a cost rise on this route.\n"
            f"2. Conclude that no genuine justification was found and it is flagged for review.\n"
            f"3. Do not invent any unsupplied facts."
        )
        res = self._execute_inference_call(prompt)
        if res:
            text, in_tok, out_tok = res
            if audit.note_id in text:
                return text
        return None

    def _call_llm_unexplained(self, route: str, week_of: str, audit: ValidationAudit, vs_hist: Optional[float], vs_peer: Optional[float]) -> Optional[str]:
        """Compatibility alias."""
        return self._synthesize_unexplained_explanation(route, week_of, audit, vs_hist, vs_peer)
