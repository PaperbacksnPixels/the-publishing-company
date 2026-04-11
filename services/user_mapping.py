"""
user_mapping.py — Map Supabase users to Airtable records.

THE MENTAL MODEL:
Supabase knows WHO someone is (email + password).
Airtable knows WHAT they are (Author? Partner? Admin?) and their data.
This module bridges the two.

When a user logs in:
  1. Supabase returns a user object with email + user_id
  2. We look up their email in the Portal Users table
  3. We get back their role + linked Airtable record ID
  4. Flask stores all of that in the session

From then on, every time a route needs to query Airtable for "the
current user's projects", it uses the linked_airtable_id from the session.
This is the ownership check that keeps users from seeing each other's data.
"""

from airtable_helpers import get_records
from config import (
    PORTAL_USERS_TABLE,
    PU_EMAIL,
    PU_SUPABASE_ID,
    PU_ROLE,
    PU_LINKED_AUTHOR,
    PU_LINKED_PARTNER,
    PU_LINKED_INTERNAL,
    PU_ACTIVE,
)


def get_portal_user(email):
    """
    Look up a Portal Users record by email.

    Returns a dict with the user's role and linked Airtable IDs:
        {
            "portal_user_id": "recXXX",
            "email": "user@example.com",
            "role": "Author",
            "linked_author_id": "recYYY",   # or None
            "linked_partner_id": "recZZZ",  # or None
            "linked_internal_id": "recAAA", # or None
            "active": True,
        }

    Returns None if no matching user exists or the account is inactive.
    """
    if not email:
        return None

    # Query the Portal Users table for this email
    # Email is the primary field so filtering is fast
    formula = f"LOWER({{{PU_EMAIL}}}) = '{email.lower()}'"
    records = get_records(PORTAL_USERS_TABLE, formula=formula)

    if not records:
        return None

    # Should only be one match (email should be unique)
    record = records[0]
    fields = record.get("fields", {})

    # Check if the account is active
    if not fields.get(PU_ACTIVE, False):
        return None

    # Airtable returns linked records as lists of IDs — grab the first one
    def first_link(field_id):
        links = fields.get(field_id)
        if isinstance(links, list) and links:
            return links[0]
        return None

    return {
        "portal_user_id": record.get("id"),
        "email": fields.get(PU_EMAIL),
        "role": fields.get(PU_ROLE),
        "linked_author_id": first_link(PU_LINKED_AUTHOR),
        "linked_partner_id": first_link(PU_LINKED_PARTNER),
        "linked_internal_id": first_link(PU_LINKED_INTERNAL),
        "active": True,
    }
