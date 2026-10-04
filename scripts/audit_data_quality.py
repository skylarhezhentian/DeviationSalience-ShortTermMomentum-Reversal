#!/usr/bin/env python3
"""Audit missing holdings/extremes and import a documented external rate proxy.

All source data remain local and unchanged. Classifications describe observations
in this data extract; they do not establish delisting or suspension status.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RF_SERIES = "IR3TTS01CNM156N"
RF_URL = "https://fred.stlouisfed.org/series/" + RF_SERIES
RF_DOWNLOAD = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IR3TTS01CNM156N&cosd=2020-12-01&coed=2025-11-30"
MISSING_COLUMNS = [
    "stock", "formation_month", "holding_month", "classification", "market_endpoint_date",
    "holding_month_daily_rows", "first_holding_observation", "last_holding_observation",
    "first_observation_after_endpoint", "last_observation_in_extract", "formation_equal_weight",
    "formation_value_weight", "ds_bin", "ret_bin", "cause_verified",
]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def normalize_rf(frame):
    """Annual quoted percentage -> approximate monthly simple carry; no filling.

    This is not a realized bill return or a point-in-time cash investment series.
    A missing source observation remains absent, rather than being imputed.
    """
    required = {"observation_date", RF_SERIES}
    if not required.issubset(frame.columns):
        raise ValueError(f"Required source columns: {sorted(required)}")
    months = pd.to_datetime(frame["observation_date"], errors="raise").dt.to_period("M")
    if months.isna().any() or months.duplicated().any():
        raise ValueError("Missing or duplicate source observation month")
    raw_rates = frame[RF_SERIES].mask(frame[RF_SERIES].eq("."), np.nan)
    rates = pd.to_numeric(raw_rates, errors="raise")
    if np.isinf(rates).any():
        raise ValueError("Infinite source rate")
    out = pd.DataFrame({"month": months.astype(str), "annual_yield_percent": rates})
    out = out.dropna(subset=["annual_yield_percent"]).sort_values("month").reset_index(drop=True)
    out["rf_monthly_proxy"] = out["annual_yield_percent"] / 100 / 12
    out["source_series"], out["source_url"] = RF_SERIES, RF_URL
    return out


def classify_missing(member, daily, calendar):
    """Classify one unknown holding from raw observations, without imputing it."""
    formation = pd.Period(member["formation_month"], "M")
    holding = pd.Period(member["holding_month"], "M")
    if holding != formation + 1:
        raise ValueError("Holding must be the next calendar month")
    endpoint = pd.Timestamp(calendar[str(holding)])
    d = daily.sort_values("date")
    months = d["date"].dt.to_period("M")
    in_month = d.loc[months.eq(holding)]
    after = d.loc[d["date"].gt(endpoint)]
    exact = d.loc[d["date"].eq(endpoint)]
    if len(exact):
        category = "endpoint_present_requires_investigation"
    elif not len(after):
        category = "terminal_disappearance_in_extract"
    elif len(in_month):
        category = "intramonth_endpoint_gap_later_resumption"
    else:
        category = "whole_month_gap_later_resumption"
    return {
        "stock": member["stock"], "formation_month": str(formation), "holding_month": str(holding),
        "classification": category, "market_endpoint_date": endpoint.date().isoformat(),
        "holding_month_daily_rows": len(in_month),
        "first_holding_observation": str(in_month.date.min().date()) if len(in_month) else None,
        "last_holding_observation": str(in_month.date.max().date()) if len(in_month) else None,
        "first_observation_after_endpoint": str(after.date.min().date()) if len(after) else None,
        "last_observation_in_extract": str(d.date.max().date()) if len(d) else None,
        "formation_equal_weight": float(member["weight_equal"]),
        "formation_value_weight": float(member["weight_value"]),
        "ds_bin": int(member["ds_bin"]), "ret_bin": int(member["ret_bin"]),
        "cause_verified": False,
    }


def audit_missing_holdings(members, raw, calendar):
    """Return a stable audit schema, including when every holding is observed."""
    missing = members.loc[members.future_ret.isna()]
    relevant = set(missing.stock)
    raw_groups = {stock: group for stock, group in raw.loc[raw.stock.isin(relevant)].groupby("stock")}
    result = pd.DataFrame([classify_missing(row, raw_groups[row["stock"]], calendar)
                           for row in missing.to_dict("records")], columns=MISSING_COLUMNS)
    result["holding_month_daily_rows"] = result["holding_month_daily_rows"].astype("int64")
    result["cause_verified"] = result["cause_verified"].astype(bool)
    verified_merger = result.stock.eq("600068.SH") & result.holding_month.eq("2021-09")
    result.loc[verified_merger, "cause_verified"] = True
    result["verified_event"] = ""
    result["event_source_url"] = ""
    result.loc[verified_merger, "verified_event"] = "Merger-related termination of listing; successor shares/payout not modeled"
    result.loc[verified_merger, "event_source_url"] = "https://www.sse.com.cn/disclosure/announcement/general/c/c_20210910_5587127.shtml"
    return result


def monthly_components(raw, calendar):
    """Separate raw close movement from vendor adjustment-factor movement."""
    d = raw.copy()
    d["month"] = d["date"].dt.to_period("M")
    endpoint_dates = {pd.Period(month, "M"): pd.Timestamp(date) for month, date in calendar.items()}
    end = d.loc[d.date.eq(d.month.map(endpoint_dates)), ["stock", "month", "date", "close", "factor"]].copy()
    previous = end[["stock", "month", "close", "factor"]].copy()
    previous["month"] += 1
    previous = previous.rename(columns={"close": "previous_close", "factor": "previous_factor"})
    result = end.merge(previous, on=["stock", "month"], how="left", validate="one_to_one")
    result["raw_close_return"] = result.close / result.previous_close - 1
    result["adjustment_factor_ratio"] = result.factor / result.previous_factor
    result["adjusted_return"] = (1 + result.raw_close_return) * result.adjustment_factor_ratio - 1
    result["month"] = result.month.astype(str)
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def atomic_write(path, contents):
    """Replace one owned output only after its complete contents are ready."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare_rf(out, rf_csv=None, fetch=False):
    """Import a read-only snapshot or fetch into an owned path; invalidate stale outputs."""
    if fetch and rf_csv is not None:
        raise ValueError("Choose either an input snapshot or --fetch-rf")
    out = Path(out)
    normalized, metadata = out / "rf_proxy_monthly.csv", out / "rf_source.json"
    raw = Path(rf_csv) if rf_csv is not None else out / f"fred_{RF_SERIES}.csv"
    if rf_csv is not None:
        if not raw.is_file():
            raise FileNotFoundError(f"Rate source does not exist: {raw}")
        if raw.resolve() in {normalized.resolve(), metadata.resolve()}:
            raise ValueError("Rate input must be separate from generated rate outputs")
    owned_paths = [normalized, metadata] + ([raw] if fetch else [])
    if any(path.is_symlink() for path in owned_paths):
        raise ValueError("Rate output paths must not be symbolic links")
    out.mkdir(parents=True, exist_ok=True)
    info = {"available": False, "source_url": RF_URL, "download_url": RF_DOWNLOAD,
            "definition": "OECD/FRED monthly quoted 3-month or90-day China Treasury rate; annual percentage divided by100 and12 gives approximate monthly simple carry.",
            "limitations": "Not actual bill holding-period returns, not a certified historical vintage or known-at-formation series. Series endsNov2023; no extrapolation or filling. Retain locally; source terms and attribution apply.",
            "citation": "OECD, Main Economic Indicators - complete database, https://doi.org/10.1787/data-00052-en, retrieved via FRED, accessed2026-10-04.",
            "license_note": "FRED flags copyrighted data/citation required and reproduces OECD permission notice. No assertion of unrestricted redistribution."}
    try:
        if fetch:
            with urlopen(RF_DOWNLOAD, timeout=30) as response:
                contents = response.read(2_000_001)
            if len(contents) > 2_000_000:
                raise ValueError("Rate download exceeds the expected small snapshot size")
            rf = normalize_rf(pd.read_csv(io.BytesIO(contents)))
            if rf.empty:
                raise ValueError("Rate source has no observed rates")
            atomic_write(raw, contents)
        elif raw.is_file():
            rf = normalize_rf(pd.read_csv(raw))
            if rf.empty:
                raise ValueError("Rate source has no observed rates")
        else:
            normalized.unlink(missing_ok=True)
            write_json(metadata, info)
            return info
        atomic_write(normalized, rf.to_csv(index=False, float_format="%.12g").encode())
        info.update(available=True, rows=len(rf), start=str(rf.month.min()), end=str(rf.month.max()),
                    raw_sha256=sha256(raw), normalized_sha256=sha256(normalized))
        write_json(metadata, info)
        return info
    except Exception as error:
        normalized.unlink(missing_ok=True)
        info.update(available=False, status="import_failed", error_type=type(error).__name__)
        write_json(metadata, info)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    rate_source = parser.add_mutually_exclusive_group()
    rate_source.add_argument("--rf-csv", type=Path)
    rate_source.add_argument("--fetch-rf", action="store_true", help="Download one small public FRED snapshot; no credentials")
    args = parser.parse_args()
    if args.rf_csv is not None and not args.rf_csv.is_file():
        parser.error(f"Rate source does not exist: {args.rf_csv}")
    data, base = args.data_dir.resolve(), args.output_dir.resolve()
    out = base / "data_quality"
    if out == data or data in out.parents:
        raise ValueError("Output must be outside the original data directory")
    out.mkdir(parents=True, exist_ok=True)
    source_paths = [data / name for name in ("close.parquet", "value.parquet", "industry.parquet")]
    original_hashes = {path.name: sha256(path) for path in source_paths}
    baseline_hashes = {path.name: sha256(path) for path in base.iterdir() if path.is_file() and path.suffix in (".csv", ".parquet")}
    calendar = json.loads((base / "diagnostics.json").read_text())["panel"]["calendar"]
    raw = pd.read_parquet(data / "close.parquet").rename(columns={
        "S_INFO_WINDCODE": "stock", "TRADE_DT": "date", "S_DQ_CLOSE": "close", "S_DQ_ADJFACTOR": "factor"})
    raw["date"] = pd.to_datetime(raw.date)
    raw = raw.sort_values(["stock", "date"]).reset_index(drop=True)
    if raw.duplicated(["stock", "date"]).any():
        raise ValueError("Duplicate raw close keys")
    actual_calendar = raw.groupby(raw.date.dt.to_period("M")).date.max()
    if {str(k): str(v.date()) for k, v in actual_calendar.items()} != calendar:
        raise ValueError("Saved calendar does not match raw market endpoints")
    members = pd.read_parquet(base / "memberships.parquet")
    missing_audit = audit_missing_holdings(members, raw, calendar)
    missing_audit.to_csv(out / "missing_holdings.csv", index=False, float_format="%.12g")

    components = monthly_components(raw, calendar)
    panel = pd.read_parquet(base / "monthly_panel.parquet")
    comparison = components.merge(panel[["stock", "month", "ret"]], on=["stock", "month"], validate="one_to_one")
    if not np.allclose(comparison.adjusted_return, comparison.ret, equal_nan=True, atol=1e-12, rtol=1e-10):
        raise ValueError("Raw close/factor decomposition disagrees with saved panel")
    extremes = comparison.loc[comparison.ret.ge(1) | comparison.ret.le(-0.5)].copy()
    extremes["absolute_return"] = extremes.ret.abs()
    extremes = extremes.sort_values(["absolute_return", "stock"], ascending=[False, True])
    extremes["factor_changed"] = ~np.isclose(extremes.adjustment_factor_ratio, 1, atol=1e-10, rtol=0)
    extremes.to_csv(out / "monthly_extremes_decomposed.csv", index=False, float_format="%.12g")
    top = extremes.head(20)[["stock", "month"]]
    candidate_rows = raw.loc[raw.stock.isin(top.stock)].copy()
    candidate_rows["month"] = candidate_rows.date.dt.to_period("M").astype(str)
    event_rows = candidate_rows.merge(top, on=["stock", "month"], how="inner", validate="many_to_one")
    event_rows["adjusted_close"] = event_rows.close * event_rows.factor
    event_rows.to_csv(out / "top20_extreme_daily_paths.csv", index=False, float_format="%.12g")

    event_reviews = [
        {"stock": "600068.SH", "month": "2021-09", "source_type": "Shanghai Stock Exchange notice",
         "source_url": "https://www.sse.com.cn/disclosure/announcement/general/c/c_20210910_5587127.shtml",
         "source_document": "SSE notice dated2021-09-10, number2021-1563",
         "finding": "The exchange confirms September13 termination of listing under the China Energy Engineering share-exchange merger. This missing holding is a corporate-action case, not evidence of a total loss.",
         "verification_scope": "Cause verified; successor-share returns/cash elections are not reconstructed or imputed."},
        {"stock": "688585.SH", "month": "2025-07", "source_type": "issuer announcement in designated disclosure newspaper",
         "source_url": "https://paper.cnstock.com/html/2025-08/05/content_2101561.htm",
         "source_document": "Issuer announcement 2025-063, dated 2025-08-05",
         "finding": "Issuer reports 1083.42 percent cumulative price increase over July9-July30, July31 suspension, August5 resumption, and 92.07 closing price as of August4. The local July monthly increase and price match; vendor factors still require separate verification.",
         "verification_scope": "Primary issuer text checked; no issuer PDF redistributed; announcement is retrospective and is not used as a formation-time filter."},
        {"stock": "688068.SH", "month": "2021-04", "source_type": "Shanghai Stock Exchange statistical bulletin",
         "source_url": "https://english.sse.com.cn/news/publications/monthly/c/10114327/files/6bedb1c35f7c4617a27661b38b5953f1.pdf",
         "source_document": "SSE April2021 monthly bulletin, printed page64",
         "finding": "Official indexed table reports close225.50 and April price increase425.64 percent, consistent with the local extreme.",
         "verification_scope": "Official search-index table text checked; direct PDF retrieval timed out, so this is not a visually verified PDF transcription."},
    ]
    write_json(out / "event_reviews.json", event_reviews)

    archive = data / "1222实习数据" / "data.rar"
    archive_info = {"present": archive.is_file(), "extracted": False}
    if archive.is_file():
        listing = subprocess.run(["bsdtar", "-tvf", str(archive)], capture_output=True, text=True, check=True).stdout
        (out / "archive_listing.txt").write_text(listing)
        archive_info.update(sha256=sha256(archive), listing=listing,
                            finding="Only close.parquet, industry.parquet, value.parquet; listed sizes match supplied files; content identity not proven without extraction.")

    rf_info = prepare_rf(out, args.rf_csv, args.fetch_rf)
    unchanged = all(sha256(data / name) == value for name, value in original_hashes.items())
    baseline_unchanged = all(sha256(base / name) == value for name, value in baseline_hashes.items())
    if not unchanged or not baseline_unchanged:
        raise ValueError("Original data or baseline numeric outputs changed during audit")
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "status": "passed",
               "raw_data_sha256": original_hashes, "raw_data_unchanged": unchanged,
               "baseline_numeric_outputs_unchanged": baseline_unchanged,
               "missing_holdings": len(missing_audit), "missing_classification_counts": missing_audit.classification.value_counts().to_dict(),
               "missing_holdings_with_any_intramonth_rows": int(missing_audit.holding_month_daily_rows.gt(0).sum()),
               "missing_holdings_with_primary_source_cause_verification": int(missing_audit.cause_verified.sum()),
               "extreme_screen": "monthly adjusted return>=100percent or<=-50percent, audit flags only; nothing dropped",
               "extreme_stock_months": len(extremes), "extremes_with_changed_factor": int(extremes.factor_changed.sum()),
               "all_monthly_components_match_panel": True, "archive": archive_info, "rf": rf_info,
               "limitations": "Terminal disappearance means no later row in the extract, not verified delisting. Neither absence nor flat prices establishes execution/suspension. No payout imputed; no extreme removed."}
    write_json(out / "summary.json", summary)
    print(json.dumps({key: summary[key] for key in ["status", "missing_holdings", "missing_classification_counts", "extreme_stock_months", "extremes_with_changed_factor"]}, indent=2))


if __name__ == "__main__":
    main()
