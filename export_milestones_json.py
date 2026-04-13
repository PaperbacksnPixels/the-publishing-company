"""Export milestone data as JSON for the Word doc generator."""
import json
import os
from dotenv import load_dotenv
load_dotenv()

from airtable_helpers import get_records
from config import (
    MILESTONE_LIBRARY_TABLE,
    ML_NAME, ML_BUNDLE, ML_MODULE, ML_SEQUENCE,
    ML_DURATION_DAYS, ML_DEFAULT_OWNER, ML_TEMPLATE_ACTIVE,
    ML_DESCRIPTION, ML_AUTHOR_VISIBLE,
    SERVICE_TO_BUNDLE,
)

def export():
    records = get_records(MILESTONE_LIBRARY_TABLE)
    bundles = {}

    for rec in records:
        fields = rec.get("fields", {})
        bundle = fields.get(ML_BUNDLE, "")
        # Handle Bundle as list (multiple select field)
        if isinstance(bundle, list):
            bundle = bundle[0] if bundle else ""
        active = fields.get(ML_TEMPLATE_ACTIVE, False)
        if not bundle or not active:
            continue

        info = {
            "name": fields.get(ML_NAME, "(no name)"),
            "sequence": fields.get(ML_SEQUENCE, 999),
            "duration": fields.get(ML_DURATION_DAYS, None),
            "owner": fields.get(ML_DEFAULT_OWNER, ""),
            "author_visible": fields.get(ML_AUTHOR_VISIBLE, False),
            "description": fields.get(ML_DESCRIPTION, ""),
        }
        bundles.setdefault(bundle, []).append(info)

    # Sort each bundle by sequence
    for bundle in bundles:
        bundles[bundle].sort(key=lambda t: t["sequence"] if t["sequence"] is not None else 999)

    # Calculate cumulative days for each bundle
    for bundle_name, tasks in bundles.items():
        running = 0
        for t in tasks:
            dur = t["duration"]
            if dur:
                running += int(dur)
                t["cumulative"] = running
            else:
                t["cumulative"] = None
        # Store total
        for t in tasks:
            t["bundle_total_days"] = running

    # Build service mapping (which services map to which bundle)
    bundle_services = {}
    for svc, bun in SERVICE_TO_BUNDLE.items():
        bundle_services.setdefault(bun, []).append(svc)

    output = {
        "bundles": bundles,
        "bundle_services": bundle_services,
    }

    with open("milestones_data.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Exported {len(bundles)} bundles to milestones_data.json")

if __name__ == "__main__":
    export()
