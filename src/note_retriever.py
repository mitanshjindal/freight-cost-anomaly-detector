"""Deterministic TF-IDF retrieval and candidate ranking for context notes.
"""

from datetime import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.evidence_validator import EvidenceValidator, NoteKnowledge, ValidationAudit

logger = logging.getLogger(__name__)


class NoteRetriever:
    """Retrieves and scores context notes for anomalous route-weeks using TF-IDF and domain scoring."""

    def __init__(self, notes_df: pd.DataFrame):
        self.notes_df = notes_df.copy()
        self.validator = EvidenceValidator(notes_df)
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))

        # Prepare corpus for TF-IDF
        self.corpus = []
        for _, row in self.notes_df.iterrows():
            text = f"{row['note_id']} {row['date']} {row['applies_to']} {row['note']}"
            self.corpus.append(text)

        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

    def retrieve_candidates(
        self,
        route: str,
        week_of: str,
        top_k: int = 5
    ) -> List[Tuple[str, float, int]]:
        """Retrieve and rank candidate notes using a hybrid of TF-IDF, temporal distance, and route match.

        Scoring function:
        - TF-IDF cosine similarity: 0.0 to 1.0
        - Route match bonus: +1.0 for exact route, +0.5 for 'All Routes'
        - Temporal decay: 1.0 / (1.0 + days_diff / 30.0)
        - Composite score = tfidf_sim * 0.3 + route_score * 0.4 + temporal_score * 0.3

        Returns:
            List of tuples: (note_id, composite_score, days_diff)
        """
        query_text = f"{route} {week_of} cost increase rate rise surcharge detour flood fuel diesel toll"
        query_vec = self.vectorizer.transform([query_text])
        sims = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        week_date = datetime.strptime(week_of, "%Y-%m-%d").date()

        scored_candidates = []
        for i, row in self.notes_df.iterrows():
            nid = row["note_id"]
            applies = row["applies_to"]
            note_date = datetime.strptime(str(row["date"]).strip(), "%Y-%m-%d").date()
            days_diff = abs((week_date - note_date).days)

            # Route match score
            if applies == route:
                route_score = 1.0
            elif applies == "All Routes":
                route_score = 0.5
            else:
                route_score = 0.0

            # Temporal proximity score
            temporal_score = 1.0 / (1.0 + (days_diff / 30.0))

            tfidf_sim = float(sims[i])
            composite_score = (tfidf_sim * 0.25) + (route_score * 0.45) + (temporal_score * 0.30)

            scored_candidates.append((nid, composite_score, days_diff))

        # Sort by composite score descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return scored_candidates[:top_k]

    def find_justification_or_closest(
        self,
        route: str,
        week_of: str,
        is_anomaly: bool,
        max_candidate_day_window: int = 45
    ) -> Tuple[Optional[NoteKnowledge], Optional[ValidationAudit], Optional[ValidationAudit]]:
        """Search notes for justification or identify the closest non-justifying note.

        Args:
            route: Route string (e.g. 'Mumbai-Pune')
            week_of: ISO Monday date (YYYY-MM-DD)
            is_anomaly: Whether route-week was flagged as numerical anomaly
            max_candidate_day_window: Max day gap to cite a rejected 'closest note' in explanations (default 45)

        Returns:
            Tuple: (justified_note_or_none, justified_audit_or_none, closest_rejected_audit_or_none)
        """
        if not is_anomaly:
            return None, None, None

        candidates = self.retrieve_candidates(route, week_of, top_k=len(self.notes_df))

        justified_match: Optional[NoteKnowledge] = None
        justified_audit: Optional[ValidationAudit] = None

        all_audits = []

        for rank, (nid, score, days_diff) in enumerate(candidates, start=1):
            audit = self.validator.validate_candidate(
                note_id=nid,
                route=route,
                week_of=week_of,
                retrieval_score=score,
                retrieval_rank=rank
            )
            all_audits.append((audit, days_diff))

            if audit.final_justified:
                justified_match = self.validator.notes[nid]
                justified_audit = audit
                break  # Top ranked justified match found

        if justified_match is not None:
            return justified_match, justified_audit, None

        # If not justified, find the closest rejected candidate (if within temporal window)
        # Prioritize candidates applicable to route or All Routes with closest days_diff
        filtered_rejected = [
            (a, d) for a, d in all_audits
            if d <= max_candidate_day_window and (a.applies_to == route or a.applies_to == "All Routes")
        ]

        if filtered_rejected:
            # Sort primarily by days_diff, then by retrieval score
            filtered_rejected.sort(key=lambda x: (x[1], -x[0].retrieval_score))
            closest_rejected_audit = filtered_rejected[0][0]
            return None, None, closest_rejected_audit

        return None, None, None
