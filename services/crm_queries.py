"""
crm_queries.py — CRM / lead-tracking queries.

Kept separate from airtable_queries.py (which is already big) to keep the
CRM surface easy to find and maintain. All functions here treat leads as
Projects with Status='Lead' (no separate Leads table).

Public surface:
  get_crm_leads()                  — list view data for the CRM tab
  create_lead(form_data)           — creates Author (or reuses) + Project(Lead)
  log_interaction(...)             — creates a row in the Interactions table
  get_interactions_for_project(id) — newest-first history for a lead/project
  get_overdue_followups()          — subset of leads past their follow-up date
"""

from datetime import date, datetime, timedelta

from airtable_helpers import get_record, get_records, create_record, update_record
from config import (
    PROJECTS_TABLE, AUTHORS_TABLE, INTERACTIONS_TABLE,
    PROJ_NAME, PROJ_AUTHOR, PROJ_SERVICE, PROJ_STATUS, PROJ_START_DATE,
    PROJ_LEAD_SOURCE, PROJ_REFERRED_BY, PROJ_BOOK_TOPIC,
    PROJ_BUDGET_RANGE, PROJ_FIT_SCORE, PROJ_NEXT_FOLLOWUP, PROJ_LEAD_NOTES,
    AUTHOR_NAME, AUTHOR_EMAIL, AUTHOR_PHONE,
    INT_NAME, INT_PROJECT, INT_DATE, INT_TYPE, INT_DIRECTION,
    INT_SUMMARY, INT_LOGGED_BY,
)


# ============================================================
# Lead list — powers the CRM tab
# ============================================================

def get_crm_leads():
    """
    Return all leads (Projects where Status = 'Lead') enriched with
    author contact info, follow-up urgency, and last-interaction date.

    PERFORMANCE: uses the bulk pre-fetch pattern — 3 Airtable calls total,
    regardless of how many leads/authors/interactions exist. See the
    Command Center perf notes in airtable_queries.get_all_tasks for context.

    Each lead dict:
      {
        "id": "recXXX",
        "name": "Smith — Lead — 2026-04-14",
        "author_id": "recYYY" or None,
        "author_name": "...",
        "author_email": "...",
        "author_phone": "...",
        "service": "Full Concierge" or "",
        "source": "Referral" or "",
        "referred_by": "...",
        "book_topic": "...",
        "budget": "$5K–$15K" or "",
        "fit_score": "4 — Good" or "",
        "next_followup": "2026-04-20" or "",  # ISO date string
        "next_followup_date": date(2026, 4, 20) or None,  # python date
        "is_overdue": bool,  # follow-up past today
        "is_due_this_week": bool,
        "notes": "...",
        "last_interaction_date": "2026-04-10" or "",
        "interaction_count": int,
      }
    """
    # Only fetch leads (filter in Airtable, not Python)
    formula = "{Status}='Lead'"
    lead_records = get_records(PROJECTS_TABLE, formula=formula)

    # Pre-fetch all authors once, build id→fields dict
    all_authors = get_records(AUTHORS_TABLE)
    authors_by_id = {a.get("id"): a.get("fields", {}) for a in all_authors}

    # Pre-fetch all interactions, group by project_id
    all_interactions = get_records(INTERACTIONS_TABLE)
    interactions_by_project = {}
    for rec in all_interactions:
        f = rec.get("fields", {})
        for pid in f.get(INT_PROJECT, []) or []:
            interactions_by_project.setdefault(pid, []).append(f)

    today = date.today()
    week_from_now = today + timedelta(days=7)

    leads = []
    for r in lead_records:
        f = r.get("fields", {})
        pid = r.get("id")

        # Resolve author from pre-fetched dict
        author_links = f.get(PROJ_AUTHOR, []) or []
        author_id = author_links[0] if author_links else None
        author_fields = authors_by_id.get(author_id, {}) if author_id else {}

        # Resolve next follow-up date
        next_followup = f.get(PROJ_NEXT_FOLLOWUP, "")
        next_followup_date = None
        is_overdue = False
        is_due_this_week = False
        if next_followup:
            try:
                next_followup_date = datetime.strptime(next_followup, "%Y-%m-%d").date()
                if next_followup_date < today:
                    is_overdue = True
                elif next_followup_date <= week_from_now:
                    is_due_this_week = True
            except ValueError:
                pass

        # Last-interaction date + count (from pre-fetched index)
        project_interactions = interactions_by_project.get(pid, [])
        last_interaction_date = ""
        if project_interactions:
            dates = [pi.get(INT_DATE, "") for pi in project_interactions if pi.get(INT_DATE)]
            if dates:
                last_interaction_date = max(dates)

        leads.append({
            "id": pid,
            "name": f.get(PROJ_NAME, "(unnamed)"),
            "author_id": author_id,
            "author_name": author_fields.get(AUTHOR_NAME, ""),
            "author_email": author_fields.get(AUTHOR_EMAIL, ""),
            "author_phone": author_fields.get(AUTHOR_PHONE, ""),
            "service": f.get(PROJ_SERVICE, ""),
            "source": f.get(PROJ_LEAD_SOURCE, ""),
            "referred_by": f.get(PROJ_REFERRED_BY, ""),
            "book_topic": f.get(PROJ_BOOK_TOPIC, ""),
            "budget": f.get(PROJ_BUDGET_RANGE, ""),
            "fit_score": f.get(PROJ_FIT_SCORE, ""),
            "next_followup": next_followup,
            "next_followup_date": next_followup_date,
            "is_overdue": is_overdue,
            "is_due_this_week": is_due_this_week,
            "notes": f.get(PROJ_LEAD_NOTES, ""),
            "last_interaction_date": last_interaction_date,
            "interaction_count": len(project_interactions),
        })

    # Sort: overdue first, then due-this-week, then everyone else by follow-up date
    def sort_key(lead):
        if lead["is_overdue"]:
            return (0, lead["next_followup_date"] or date(1900, 1, 1))
        if lead["is_due_this_week"]:
            return (1, lead["next_followup_date"] or date(9999, 12, 31))
        if lead["next_followup_date"]:
            return (2, lead["next_followup_date"])
        return (3, date(9999, 12, 31))

    leads.sort(key=sort_key)
    return leads


def get_overdue_followups():
    """
    Return just the overdue follow-ups, shaped for the priority banner.
    Each: {"id", "name", "author_name", "next_followup"}
    """
    leads = get_crm_leads()
    return [
        {
            "id": l["id"],
            "name": l["name"],
            "author_name": l["author_name"],
            "next_followup": l["next_followup"],
        }
        for l in leads if l["is_overdue"]
    ]


# ============================================================
# Create a new lead (Author + Project)
# ============================================================

def _find_author_by_email(email):
    """Look up an existing Author record by email (case-insensitive). Returns the record or None."""
    if not email:
        return None
    safe = email.strip().lower().replace("'", "\\'")
    formula = f"LOWER({{Email}})='{safe}'"
    records = get_records(AUTHORS_TABLE, formula=formula)
    return records[0] if records else None


def create_lead(form_data):
    """
    Create a new Author (or reuse existing by email) + a new Project in Lead status.

    Accepts a dict with keys:
      author_name (required)    — will create/reuse Author
      author_email              — used to dedupe against existing Authors
      author_phone
      service                   — "Full Concierge" etc. (or blank if unsure)
      lead_source               — "Referral" etc.
      referred_by
      book_topic
      budget_range
      fit_score                 — "4 — Good" etc.
      next_followup             — "YYYY-MM-DD"
      lead_notes

    Returns:
      { "success": True,  "project_id": "recXXX", "author_id": "recYYY" }
      { "success": False, "error":  "message" }
    """
    name = (form_data.get("author_name") or "").strip()
    if not name:
        return {"success": False, "error": "Author name is required"}

    email = (form_data.get("author_email") or "").strip()
    phone = (form_data.get("author_phone") or "").strip()

    # Reuse an Author by email if possible; otherwise create one
    author_id = None
    existing = _find_author_by_email(email) if email else None
    if existing:
        author_id = existing.get("id")
        # Patch missing phone if we have a new one — don't overwrite existing data
        existing_fields = existing.get("fields", {})
        patch = {}
        if phone and not existing_fields.get(AUTHOR_PHONE):
            patch[AUTHOR_PHONE] = phone
        if patch:
            update_record(AUTHORS_TABLE, author_id, patch)
    else:
        author_fields = {AUTHOR_NAME: name}
        if email:
            author_fields[AUTHOR_EMAIL] = email
        if phone:
            author_fields[AUTHOR_PHONE] = phone
        created = create_record(AUTHORS_TABLE, author_fields)
        if not created:
            return {"success": False, "error": "Could not create Author record"}
        author_id = created.get("id")

    # Build project name: "LastName — Lead — YYYY-MM-DD"
    last_name = name.split()[-1] if name else "Lead"
    today_str = date.today().isoformat()
    project_name = f"{last_name} — Lead — {today_str}"

    # Only include non-empty fields so we don't clobber defaults
    project_fields = {
        PROJ_NAME: project_name,
        PROJ_STATUS: "Lead",
        PROJ_AUTHOR: [author_id],
    }

    service = (form_data.get("service") or "").strip()
    if service:
        project_fields[PROJ_SERVICE] = service

    lead_source = (form_data.get("lead_source") or "").strip()
    if lead_source:
        project_fields[PROJ_LEAD_SOURCE] = lead_source

    referred_by = (form_data.get("referred_by") or "").strip()
    if referred_by:
        project_fields[PROJ_REFERRED_BY] = referred_by

    book_topic = (form_data.get("book_topic") or "").strip()
    if book_topic:
        project_fields[PROJ_BOOK_TOPIC] = book_topic

    budget_range = (form_data.get("budget_range") or "").strip()
    if budget_range:
        project_fields[PROJ_BUDGET_RANGE] = budget_range

    fit_score = (form_data.get("fit_score") or "").strip()
    if fit_score:
        project_fields[PROJ_FIT_SCORE] = fit_score

    next_followup = (form_data.get("next_followup") or "").strip()
    if next_followup:
        project_fields[PROJ_NEXT_FOLLOWUP] = next_followup

    lead_notes = (form_data.get("lead_notes") or "").strip()
    if lead_notes:
        project_fields[PROJ_LEAD_NOTES] = lead_notes

    project = create_record(PROJECTS_TABLE, project_fields)
    if not project:
        return {"success": False, "error": "Could not create Project record"}

    return {"success": True, "project_id": project.get("id"), "author_id": author_id}


# ============================================================
# Interactions — log + retrieve
# ============================================================

def log_interaction(project_id, interaction_type, summary,
                    direction="N/A", int_date=None, logged_by=""):
    """
    Create a new row in the Interactions table.

    Args:
      project_id       — Airtable ID of the Project this interaction belongs to
      interaction_type — one of: Call, Email, Meeting, Text, Note
      summary          — free-text description of what happened
      direction        — Inbound / Outbound / N/A (default N/A)
      int_date         — ISO date "YYYY-MM-DD" (default: today)
      logged_by        — who recorded it (name or email)

    Returns the created record dict, or None on failure.
    """
    if not project_id:
        return None

    when = int_date or date.today().isoformat()

    # Build a readable primary-field name: "2026-04-14 Call — Smith"
    short_label = ""
    project = get_record(PROJECTS_TABLE, project_id)
    if project:
        project_name = project.get("fields", {}).get(PROJ_NAME, "")
        # "Smith — Lead — 2026-04-14" -> take just the first segment
        short_label = project_name.split(" — ")[0] if project_name else ""
    name = f"{when} {interaction_type}"
    if short_label:
        name = f"{name} — {short_label}"

    fields = {
        INT_NAME: name,
        INT_PROJECT: [project_id],
        INT_DATE: when,
        INT_TYPE: interaction_type,
        INT_DIRECTION: direction or "N/A",
        INT_SUMMARY: summary or "",
    }
    if logged_by:
        fields[INT_LOGGED_BY] = logged_by

    return create_record(INTERACTIONS_TABLE, fields)


def get_interactions_for_project(project_id):
    """
    Return all Interactions linked to a project, newest first.
    Each item:
      {"id", "date", "type", "direction", "summary", "logged_by", "name"}
    """
    if not project_id:
        return []

    # Filter in Python: Airtable formulas on linked-record fields match the
    # display value, not the record ID — same reason get_files_for_task does it.
    all_records = get_records(INTERACTIONS_TABLE)

    items = []
    for rec in all_records:
        f = rec.get("fields", {})
        linked = f.get(INT_PROJECT, []) or []
        if project_id not in linked:
            continue
        items.append({
            "id": rec.get("id"),
            "name": f.get(INT_NAME, ""),
            "date": f.get(INT_DATE, ""),
            "type": f.get(INT_TYPE, ""),
            "direction": f.get(INT_DIRECTION, ""),
            "summary": f.get(INT_SUMMARY, ""),
            "logged_by": f.get(INT_LOGGED_BY, ""),
        })

    # Newest first (string sort works for ISO dates)
    items.sort(key=lambda i: i["date"] or "", reverse=True)
    return items
