from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.paper_trading.training_dataset_audit import TrainingDatasetAuditResult, audit_training_dataset


@dataclass(frozen=True)
class TrainingDatasetCandidateResult:
    status: str
    run_id: str
    data_until: str
    safe_train_until: str
    train_until: str
    label_horizon: int
    output_root: str
    datasets: tuple[TrainingDatasetAuditResult, ...]
    manifest_path: str
    model_retraining_executed: bool = False
    inference_executed: bool = False
    order_plan_generation_executed: bool = False
    broker_order_api_called: bool = False
    virtual_fill_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["datasets"] = [item.to_dict() for item in self.datasets]
        return payload


def build_training_dataset_candidates(
    *,
    normalized_daily_quotes_path: Path | str,
    listed_info_path: Path | str,
    trading_calendar_path: Path | str,
    data_until: str,
    safe_train_until: str,
    train_until: str,
    label_horizon: int,
    output_root: Path | str = ".runtime/phase9/training_dataset_candidates",
    created_at: str | None = None,
) -> TrainingDatasetCandidateResult:
    created_at = created_at or _now()
    run_id = f"phase9l1_training_dataset_{created_at.replace(':', '').replace('+', 'Z')}"
    output_dir = Path(output_root) / train_until
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = output_dir / "candidate_ai_dataset.parquet"
    opportunity_path = output_dir / "opportunity_ai_dataset.parquet"
    manifest_path = output_dir / "training_dataset_manifest.json"
    source_refs = {
        "normalized_daily_quotes": str(normalized_daily_quotes_path),
        "listed_info": str(listed_info_path),
        "trading_calendar": str(trading_calendar_path),
        "source": "J-Quants canonical Phase9 data only",
    }
    quotes = _read_quotes(Path(normalized_daily_quotes_path), data_until=data_until)
    candidate = _build_candidate_dataset(quotes=quotes, train_until=train_until, label_horizon=label_horizon, created_at=created_at)
    opportunity = _build_opportunity_dataset(candidate=candidate, created_at=created_at)
    candidate.to_parquet(candidate_path, index=False)
    opportunity.to_parquet(opportunity_path, index=False)
    audits = (
        audit_training_dataset(
            ai_name="candidate",
            dataset_path=candidate_path,
            data_until=data_until,
            safe_train_until=safe_train_until,
            train_until=train_until,
            label_horizon=label_horizon,
            source_data_refs=source_refs,
            label_source_until=data_until,
        ),
        audit_training_dataset(
            ai_name="opportunity",
            dataset_path=opportunity_path,
            data_until=data_until,
            safe_train_until=safe_train_until,
            train_until=train_until,
            label_horizon=label_horizon,
            source_data_refs=source_refs,
            label_source_until=data_until,
        ),
    )
    status = "TRAINING_DATASETS_READY" if all(item.status == "TRAINING_DATASET_READY" for item in audits) else (
        "TRAINING_DATASET_BLOCKED" if any(item.status == "TRAINING_DATASET_BLOCKED" for item in audits) else "TRAINING_DATASET_REPAIR_REQUIRED"
    )
    result = TrainingDatasetCandidateResult(
        status=status,
        run_id=run_id,
        data_until=data_until,
        safe_train_until=safe_train_until,
        train_until=train_until,
        label_horizon=label_horizon,
        output_root=str(output_dir),
        datasets=audits,
        manifest_path=str(manifest_path),
    )
    manifest_path.write_text(json.dumps(result.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _read_quotes(path: Path, *, data_until: str) -> pd.DataFrame:
    frame = pd.read_parquet(path, columns=["date", "code", "close", "volume"])
    frame = frame[frame["date"].astype(str) <= data_until].copy()
    frame["target_date"] = frame["date"].astype(str)
    frame["code"] = frame["code"].astype(str)
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce")
    return frame.dropna(subset=["close", "volume"]).sort_values(["code", "target_date"])


def _build_candidate_dataset(*, quotes: pd.DataFrame, train_until: str, label_horizon: int, created_at: str) -> pd.DataFrame:
    frame = quotes.copy()
    grouped = frame.groupby("code", group_keys=False)
    frame["feature__price_momentum_return_5d"] = grouped["close"].pct_change(5)
    frame["feature__price_momentum_return_20d"] = grouped["close"].pct_change(20)
    returns = grouped["close"].pct_change()
    frame["feature__volatility_return_std_20d"] = returns.groupby(frame["code"]).rolling(20).std().reset_index(level=0, drop=True)
    ma20 = grouped["close"].rolling(20).mean().reset_index(level=0, drop=True)
    frame["feature__trend_close_over_ma_20d"] = frame["close"] / ma20 - 1.0
    avg_volume = grouped["volume"].rolling(20).mean().reset_index(level=0, drop=True)
    frame["feature__liquidity_avg_volume_20d"] = avg_volume
    frame["feature__volume_momentum_ratio_5d"] = grouped["volume"].rolling(5).mean().reset_index(level=0, drop=True) / avg_volume
    future_close = grouped["close"].shift(-label_horizon)
    frame["label__future_return_20d"] = future_close / frame["close"] - 1.0
    frame["label__momentum_candidate_label"] = frame["label__future_return_20d"] > 0.05
    frame["label__top_decile_20d"] = frame.groupby("target_date")["label__future_return_20d"].rank(pct=True) >= 0.90
    frame = frame[frame["target_date"].astype(str) <= train_until].copy()
    feature_columns = [column for column in frame.columns if column.startswith("feature__")]
    label_columns = [column for column in frame.columns if column.startswith("label__")]
    frame = frame.dropna(subset=["label__future_return_20d"])
    frame["split"] = _split_by_date(frame["target_date"].astype(str))
    frame["dataset_version"] = "phase9l1_candidate_dataset_v1"
    frame["created_at"] = created_at
    columns = ["target_date", "code", "split", "dataset_version", "created_at", *feature_columns, *label_columns]
    return frame[columns].reset_index(drop=True)


def _build_opportunity_dataset(*, candidate: pd.DataFrame, created_at: str) -> pd.DataFrame:
    frame = candidate.copy()
    frame["label__expected_edge_label_20d"] = pd.to_numeric(frame["label__future_return_20d"], errors="coerce")
    frame["dataset_version"] = "phase9l1_opportunity_dataset_v1"
    frame["created_at"] = created_at
    return frame.reset_index(drop=True)


def _split_by_date(dates: pd.Series) -> list[str]:
    unique = sorted(dates.unique())
    if not unique:
        return []
    train_cut = unique[int(len(unique) * 0.70)]
    validation_cut = unique[int(len(unique) * 0.85)]
    return ["train" if date <= train_cut else "validation" if date <= validation_cut else "test" for date in dates]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
