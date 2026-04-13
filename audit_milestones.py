"""
Milestone Library Audit Script
================================
One-time script to review all milestone templates in Airtable.
Checks for: missing durations, duplicate sequences, inactive templates,
and prints a clean summary grouped by bundle.

Run with:
    cd the-publishing-company
    venv/Scripts/python audit_milestones.py
"""

import os
import sys

# Load .env so we can talk to Airtable
from dotenv import load_dotenv
load_dotenv()

# Import our existing helpers (reuse what we already have!)
from airtable_helpers import get_records
from config import (
    MILESTONE_LIBRARY_TABLE,
    ML_NAME, ML_BUNDLE, ML_MODULE, ML_SEQUENCE,
    ML_DURATION_DAYS, ML_DEFAULT_OWNER, ML_TEMPLATE_ACTIVE,
    ML_DESCRIPTION, ML_AUTHOR_VISIBLE,
    SERVICE_TO_BUNDLE,
)


def fetch_all_milestones():
    """Grab every record from the Milestone Library table."""
    # No formula = get everything (active AND inactive)
    records = get_records(MILESTONE_LIBRARY_TABLE)
    if not records:
        print("ERROR: Could not fetch milestone records. Check your .env settings.")
        sys.exit(1)
    return records


def audit_milestones():
    """Main audit: fetch, organize, and report on milestone templates."""
    print("=" * 70)
    print("MILESTONE LIBRARY AUDIT")
    print("=" * 70)

    records = fetch_all_milestones()
    print(f"\nTotal records in Milestone Library: {len(records)}\n")

    # Organize by bundle
    bundles = {}       # bundle_name -> list of templates
    no_bundle = []     # templates with no bundle assigned

    for rec in records:
        fields = rec.get("fields", {})
        bundle = fields.get(ML_BUNDLE, "")
        # Handle Bundle as list (Airtable sometimes returns single-select as list)
        if isinstance(bundle, list):
            bundle = bundle[0] if bundle else ""
        active = fields.get(ML_TEMPLATE_ACTIVE, False)

        info = {
            "id": rec.get("id", ""),
            "name": fields.get(ML_NAME, "(no name)"),
            "bundle": bundle,
            "module": fields.get(ML_MODULE, ""),
            "sequence": fields.get(ML_SEQUENCE, None),
            "duration": fields.get(ML_DURATION_DAYS, None),
            "owner": fields.get(ML_DEFAULT_OWNER, ""),
            "active": active,
            "author_visible": fields.get(ML_AUTHOR_VISIBLE, False),
            "has_description": bool(fields.get(ML_DESCRIPTION, "")),
        }

        if not bundle:
            no_bundle.append(info)
        else:
            bundles.setdefault(bundle, []).append(info)

    # --- Report: Each bundle ---
    for bundle_name in sorted(bundles.keys()):
        templates = bundles[bundle_name]
        # Sort by sequence
        templates.sort(key=lambda t: t["sequence"] if t["sequence"] is not None else 999)

        active_count = sum(1 for t in templates if t["active"])
        inactive_count = len(templates) - active_count

        print("-" * 70)
        print(f"BUNDLE: {bundle_name}")
        print(f"  Templates: {len(templates)} ({active_count} active, {inactive_count} inactive)")
        print()

        # Calculate what the timeline would look like with sequential dates
        running_days = 0

        print(f"  {'#':<4} {'Status':<8} {'Task Name':<40} {'Days':<6} {'Cumulative':<10} {'Owner'}")
        print(f"  {'—'*4} {'—'*8} {'—'*40} {'—'*6} {'—'*10} {'—'*15}")

        # Track issues for this bundle
        issues = []

        seen_sequences = {}  # sequence -> task name (to find duplicates)

        for t in templates:
            status = "ACTIVE" if t["active"] else "OFF"
            dur = t["duration"]
            seq = t["sequence"]

            # Only count active templates toward the timeline
            if t["active"] and dur:
                running_days += int(dur)

            dur_str = str(int(dur)) if dur else "—"
            cum_str = str(running_days) if (t["active"] and dur) else ""
            seq_str = str(int(seq)) if seq is not None else "?"

            print(f"  {seq_str:<4} {status:<8} {t['name'][:40]:<40} {dur_str:<6} {cum_str:<10} {t['owner']}")

            # --- Check for issues ---
            if t["active"] and dur is None:
                issues.append(f"  WARNING: MISSING DURATION: '{t['name']}' (seq {seq_str})")

            if t["active"] and seq is None:
                issues.append(f"  WARNING: MISSING SEQUENCE: '{t['name']}'")

            if seq is not None and seq in seen_sequences and t["active"]:
                issues.append(f"  WARNING: DUPLICATE SEQUENCE {int(seq)}: '{t['name']}' and '{seen_sequences[seq]}'")

            if t["active"] and seq is not None:
                seen_sequences[seq] = t["name"]

        if running_days > 0:
            print(f"\n  Total estimated timeline: {running_days} days ({running_days // 7} weeks, {running_days % 7} days)")

        if issues:
            print(f"\n  ISSUES FOUND:")
            for issue in issues:
                print(issue)
        print()

    # --- Report: Templates with no bundle ---
    if no_bundle:
        print("-" * 70)
        print(f"WARNING: TEMPLATES WITH NO BUNDLE ASSIGNED: {len(no_bundle)}")
        for t in no_bundle:
            status = "ACTIVE" if t["active"] else "OFF"
            print(f"  [{status}] {t['name']}")
        print()

    # --- Report: Service mapping coverage ---
    print("-" * 70)
    print("SERVICE-TO-BUNDLE MAPPING CHECK")
    print()

    # Which bundles have templates?
    bundles_with_templates = set(bundles.keys())
    # Which bundles are referenced by services?
    bundles_referenced = set(SERVICE_TO_BUNDLE.values())

    # Bundles referenced but have no templates
    missing = bundles_referenced - bundles_with_templates
    if missing:
        print(f"  WARNING: Services map to these bundles, but NO templates exist:")
        for b in sorted(missing):
            services = [s for s, bun in SERVICE_TO_BUNDLE.items() if bun == b]
            print(f"    - {b} (used by: {', '.join(services)})")
    else:
        print("  OK: All mapped bundles have templates")

    # Bundles with templates but no service maps to them
    orphaned = bundles_with_templates - bundles_referenced
    if orphaned:
        print(f"\n  NOTE: Bundles with templates but no service mapping:")
        for b in sorted(orphaned):
            print(f"    - {b}")

    print()
    print("=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    audit_milestones()
