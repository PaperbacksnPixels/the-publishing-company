"""
typeflow.py — Typeflow API integration for document generation & e-signatures.

HOW IT WORKS:
  1. You call send_document() with a flow ID, table ID, and record ID.
  2. Typeflow pulls data from that Airtable record.
  3. Typeflow generates the document (using the flow's Google Docs template).
  4. Typeflow sends it to the signer(s) for e-signature.
  5. Once signed, Typeflow saves the PDF back to the Airtable record.

We just need to trigger step 1 — Typeflow handles the rest.
"""

import os
import requests

from config import (
    TYPEFLOW_API_URL,
    TYPEFLOW_SOW_FLOW_ID,
    TYPEFLOW_SOW_TABLE_ID,
    TYPEFLOW_MSA_FLOW_ID,
    AUTHORS_TABLE,
    PARTNERS_TABLE,
)


def send_document(flow_id, table_id, record_id):
    """
    Call the Typeflow API to generate a document and send it for signature.

    Args:
        flow_id:   The Typeflow flow/template ID (which document to create)
        table_id:  The Airtable table ID (where to pull data from)
        record_id: The Airtable record ID (which row to use)

    Returns:
        dict with keys:
          - success (bool): whether the API call worked
          - pdf_url (str): URL of the generated PDF (if successful)
          - error (str): error message (if failed)
    """
    api_key = os.environ.get("TYPEFLOW_API_KEY")
    if not api_key:
        return {"success": False, "error": "TYPEFLOW_API_KEY not set in .env"}

    try:
        response = requests.get(
            TYPEFLOW_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            params={
                "flow_id": flow_id,
                "table_id": table_id,
                "record_id": record_id,
            },
            timeout=30,  # Typeflow may take a moment to generate the doc
        )

        if response.status_code == 200:
            data = response.json()
            # Typeflow returns {"success": "done", "pdfUrl": "...", ...}
            if data.get("success") == "done":
                return {
                    "success": True,
                    "pdf_url": data.get("pdfUrl", ""),
                    "file_name": data.get("fileNameAirtable", ""),
                }

            # API returned 200 but something unexpected in the body
            return {
                "success": False,
                "error": f"Unexpected response: {data}",
            }

        # Non-200 status code
        return {
            "success": False,
            "error": f"Typeflow API returned {response.status_code}: {response.text[:200]}",
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Typeflow API timed out (30s)"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Network error: {str(e)}"}


def send_sow(project_record_id):
    """
    Send a Statement of Work for a specific project.
    Pulls data from the Projects table.
    """
    return send_document(
        flow_id=TYPEFLOW_SOW_FLOW_ID,
        table_id=TYPEFLOW_SOW_TABLE_ID,
        record_id=project_record_id,
    )


def send_msa(record_id, recipient_type="author"):
    """
    Send a Master Service Agreement.

    Args:
        record_id: The Airtable record ID (author or partner)
        recipient_type: "author" or "partner" — determines which table to use

    The MSA can go to either:
      - An Author (from the Authors table)
      - A Channel Partner (from the Partners table)
    """
    if recipient_type == "partner":
        table_id = PARTNERS_TABLE
    else:
        table_id = AUTHORS_TABLE

    return send_document(
        flow_id=TYPEFLOW_MSA_FLOW_ID,
        table_id=table_id,
        record_id=record_id,
    )
