import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

# Automatically load .env file if present
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ[_k.strip()] = _v.strip()


class ProjectPaths(BaseModel):
    """File and directory path configuration."""
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data")
    output_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "output")
    docs_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "docs")

    shipment_records: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "shipment_records.csv")
    context_notes: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "context_notes.csv")
    sample_output: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "sample_output_format_v2.csv")
    final_output: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "output" / "shipping_cost_analysis.csv")


class BaselineSettings(BaseModel):
    """Baseline calculation parameters matching case study specification."""
    history_window_weeks: int = Field(default=8, description="Trailing weeks for own-history rolling average")
    min_history_observations: int = Field(default=1, description="Minimum prior observations to compute history baseline")
    peer_grouping_field: str = Field(default="route_type", description="Field defining similar routes (Short/Medium/Long)")


class AnomalyThresholds(BaseModel):
    """Configurable anomaly detection thresholds with documented rationale.
    
    Rationale:
    - history_spike_threshold_pct (15.0%): In the empirical distribution of 728 route-weeks,
      the 98th percentile of trailing 8-week history change is +7.5%. An increase >= 15% is 
      a severe historical outlier (>3 standard deviations above mean of 0.42%).
    - min_rise_for_peer_anomaly_pct (5.0%): Prevents flagging routes that are merely cheaper
      or stable compared to their own history but higher than peers. Ensures cost is actually rising.
    - peer_spike_threshold_pct (20.0%): The 98th percentile of peer percentage difference is +22.7%.
      Routes that rise >= 5% vs own history and are >= 20% above peers represent genuine anomalies
      (e.g., Mumbai-Pune on 2025-09-15 with +9.2% vs history and +23.6% vs peers).
    """
    history_spike_threshold_pct: float = Field(default=15.0, description="Minimum % increase vs history to flag independently")
    peer_spike_threshold_pct: float = Field(default=20.0, description="Minimum % difference vs similar routes")
    min_rise_for_peer_anomaly_pct: float = Field(default=5.0, description="Minimum % increase vs own history required for peer comparison")


class NLGSettings(BaseModel):
    """Settings for natural language audit synthesis."""
    enabled: bool = Field(
        default_factory=lambda: (
            os.environ.get("NLG_ENABLED", os.environ.get("LLM_ENABLED", "false")).lower() == "true"
            and bool(os.environ.get("GEMINI_API_KEY"))
        )
    )
    provider: str = Field(default="gemini", description="Inference engine provider")
    model_name: str = Field(default_factory=lambda: os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"), description="Engine model identifier")
    temperature: float = Field(default=0.0, description="Deterministic temperature (0.0)")
    api_key_env_var: str = Field(default="GEMINI_API_KEY", description="Environment variable holding API credentials")
    api_key: str = Field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""), description="Active API credentials")
    max_output_tokens: int = Field(default=150, description="Token budget cap for audit explanation synthesis")
    batch_mode: bool = Field(default=True, description="Selective execution: only invoke for verified anomalous observations")


# Backwards compatibility alias
LLMSettings = NLGSettings


class AppConfig(BaseModel):
    """Root configuration object."""
    paths: ProjectPaths = Field(default_factory=ProjectPaths)
    baselines: BaselineSettings = Field(default_factory=BaselineSettings)
    thresholds: AnomalyThresholds = Field(default_factory=AnomalyThresholds)
    nlg: NLGSettings = Field(default_factory=NLGSettings)

    @property
    def llm(self) -> NLGSettings:
        """Compatibility property for legacy references."""
        return self.nlg


# Default singleton instance
config = AppConfig()
