"""
airtable_helpers.py — Reusable functions for talking to the Airtable API.

These 4 functions handle all the HTTP work so the rest of the code
can just say "get me this record" or "create that record" without
worrying about URLs, headers, or pagination.

Uses the same requests + Bearer token pattern as the P&P website app.
"""

import os
import requests
from dotenv import load_dotenv

# Load .env file so we can read AIRTABLE_PAT and AIRTABLE_BASE_ID
load_dotenv()

# Base URL for all Airtable API calls
AIRTABLE_API_URL = "https://api.airtable.com/v0"


def _get_headers():
    """
    Build the authorization headers for Airtable API calls.
    Reads the Personal Access Token from the .env file.
    """
    pat = os.environ.get("AIRTABLE_PAT", "")
    if not pat or pat == "paste_your_token_here":
        print("ERROR: No Airtable PAT found!")
        print("  1. Go to https://airtable.com/create/tokens")
        print("  2. Create a token with data.records:read and data.records:write")
        print("  3. Paste it in .env as AIRTABLE_PAT=pat_xxxxx")
        return None
    return {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
    }


def _get_base_url(table_id):
    """Build the full API URL for a table."""
    base_id = os.environ.get("AIRTABLE_BASE_ID", "")
    return f"{AIRTABLE_API_URL}/{base_id}/{table_id}"


# ============================================================
# 1. GET ONE RECORD
# ============================================================

def get_record(table_id, record_id):
    """
    Fetch a single record by its ID.

    Returns a dict like:
        {"id": "recXXXXX", "fields": {"Field Name": "value", ...}}

    Returns None if something goes wrong.
    """
    headers = _get_headers()
    if not headers:
        return None

    url = f"{_get_base_url(table_id)}/{record_id}"

    # returnFieldsByFieldId=true makes the response use field IDs as keys
    # instead of field names. This matches our config.py constants.
    params = {"returnFieldsByFieldId": "true"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code != 200:
            print(f"ERROR fetching record {record_id}: {resp.status_code}")
            print(f"  {resp.text[:200]}")
            return None

        return resp.json()

    except requests.RequestException as e:
        print(f"ERROR: Could not reach Airtable: {e}")
        return None


# ============================================================
# 2. GET MULTIPLE RECORDS (with pagination!)
# ============================================================

def get_records(table_id, formula=None, sort_field=None, sort_dir="asc"):
    """
    Fetch ALL matching records from a table.

    IMPORTANT: Airtable only returns 100 records at a time. If there are
    more, the response includes an "offset" token. We keep fetching
    until there's no more offset — that's pagination.

    Args:
        table_id: Which table to query
        formula: Optional Airtable formula to filter records
                 Example: "{Template Active}=TRUE()"
        sort_field: Optional field name to sort by
        sort_dir: "asc" or "desc"

    Returns a list of records (could be hundreds).
    """
    headers = _get_headers()
    if not headers:
        return []

    url = _get_base_url(table_id)
    all_records = []  # We'll collect records from every page here
    offset = None     # Tracks where we are in the pagination

    while True:
        # Build the query parameters for this page
        params = {"returnFieldsByFieldId": "true"}

        if formula:
            params["filterByFormula"] = formula

        if sort_field:
            params["sort[0][field]"] = sort_field
            params["sort[0][direction]"] = sort_dir

        # If we have an offset from a previous page, include it
        if offset:
            params["offset"] = offset

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)

            if resp.status_code != 200:
                print(f"ERROR fetching records: {resp.status_code}")
                print(f"  {resp.text[:200]}")
                break

            data = resp.json()

            # Add this page's records to our collection
            records = data.get("records", [])
            all_records.extend(records)

            # Check if there are more pages
            offset = data.get("offset")
            if not offset:
                # No more pages — we have everything
                break

        except requests.RequestException as e:
            print(f"ERROR: Could not reach Airtable: {e}")
            break

    return all_records


# ============================================================
# 3. UPDATE A RECORD
# ============================================================

def update_record(table_id, record_id, fields_dict):
    """
    Update specific fields on an existing record.

    Args:
        table_id: Which table the record is in
        record_id: The record to update (e.g. "recXXXXX")
        fields_dict: A dict of {field_id: new_value} pairs
                     Example: {"fldxuqCmoKKivX72Z": "Trelstad — Full Concierge — 2026"}

    Returns the updated record, or None on error.
    """
    headers = _get_headers()
    if not headers:
        return None

    url = f"{_get_base_url(table_id)}/{record_id}"

    try:
        resp = requests.patch(
            url,
            headers=headers,
            json={"fields": fields_dict},
            timeout=10,
        )

        if resp.status_code != 200:
            print(f"ERROR updating record {record_id}: {resp.status_code}")
            print(f"  {resp.text[:200]}")
            return None

        return resp.json()

    except requests.RequestException as e:
        print(f"ERROR: Could not reach Airtable: {e}")
        return None


# ============================================================
# 4. CREATE A RECORD
# ============================================================

def delete_record(table_id, record_id):
    """
    Delete a single record from a table.

    Args:
        table_id: Which table the record is in
        record_id: The record to delete (e.g. "recXXXXX")

    Returns True on success, False on error.
    """
    headers = _get_headers()
    if not headers:
        return False

    url = f"{_get_base_url(table_id)}/{record_id}"

    try:
        resp = requests.delete(url, headers=headers, timeout=10)

        if resp.status_code != 200:
            print(f"ERROR deleting record {record_id}: {resp.status_code}")
            print(f"  {resp.text[:200]}")
            return False

        return True

    except requests.RequestException as e:
        print(f"ERROR: Could not reach Airtable: {e}")
        return False


def create_record(table_id, fields_dict):
    """
    Create a new record in a table.

    Args:
        table_id: Which table to add the record to
        fields_dict: A dict of {field_id: value} pairs for the new record

    Returns the created record (with its new ID), or None on error.
    """
    headers = _get_headers()
    if not headers:
        return None

    url = _get_base_url(table_id)

    try:
        resp = requests.post(
            url,
            headers=headers,
            json={"fields": fields_dict},
            timeout=10,
        )

        if resp.status_code != 200:
            print(f"ERROR creating record: {resp.status_code}")
            print(f"  {resp.text[:200]}")
            return None

        return resp.json()

    except requests.RequestException as e:
        print(f"ERROR: Could not reach Airtable: {e}")
        return None
