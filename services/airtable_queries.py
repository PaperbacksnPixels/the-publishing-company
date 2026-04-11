"""
airtable_queries.py — The data-isolation chokepoint.

THE ONE RULE THAT MATTERS:
Every function in this file takes the logged-in user's linked Airtable ID
as its FIRST argument and filters query results by that ID. This is the
entire multi-tenant security model of the portal.

Never fetch a record directly from a URL parameter without checking
ownership through this module. If you find yourself calling
airtable_helpers.get_record() from a route, stop and ask yourself whether
you should add a proper function here instead.
"""

from airtable_helpers import get_record, get_records
from config import (
    PROJECTS_TABLE,
    PROJ_AUTHOR,
    PROJ_NAME,
    PROJ_STATUS,
    PROJ_SERVICE,
    PROJ_START_DATE,
    PROJ_TASKS,
    PROJ_INVOICES,
    PROJ_CONTRACT_URL,
    PROJ_CONTRACT_STATUS,
    PROJ_CONTRACT_SENT_DATE,
    PROJ_CONTRACT_SIGNED_DATE,
    AUTHORS_TABLE,
    AUTHOR_PROJECTS,
    TASKS_TABLE,
    TASK_NAME,
    TASK_MODULE,
    TASK_SEQUENCE,
    TASK_STATUS,
    TASK_DUE_DATE,
    TASK_AUTHOR_VISIBLE,
    TASK_STAGE_DESC,
    INVOICES_TABLE,
    INV_NAME,
    INV_TYPE,
    INV_AMOUNT,
    INV_AMOUNT_PAID,
    INV_OUTSTANDING,
    INV_DATE,
    INV_DUE_DATE,
    INV_PAYMENT_STATUS,
    INV_STRIPE_URL,
    INV_VOIDED,
)


# ============================================================
# AUTHOR QUERIES
# ============================================================

def get_projects_for_author(author_id):
    """
    Fetch all projects for a specific author.

    Args:
        author_id: The Airtable record ID of the Author (from the session)

    Returns a list of project dicts, each with:
        id, name, status, service, start_date

    If the author has no projects, returns an empty list.

    SECURITY: This function follows the Author -> Projects link directly.
    It fetches the author's record, reads the list of linked project IDs,
    and then fetches each one. This guarantees we only return projects
    that belong to this author.

    WHY NOT A FORMULA FILTER?
    Airtable formulas on linked record fields return the PRIMARY field
    text of the linked records (e.g. "Tessa Testauthor"), not the record
    IDs. So FIND('recXXX', {Author}) doesn't work. Following the link
    from the author side is cleaner and more reliable.
    """
    if not author_id:
        return []

    # Step 1: Fetch the author record to get their list of project IDs
    author = get_record(AUTHORS_TABLE, author_id)
    if not author:
        return []

    project_ids = author.get("fields", {}).get(AUTHOR_PROJECTS, [])
    if not project_ids:
        return []

    # Step 2: Fetch each project by ID
    projects = []
    for pid in project_ids:
        project = get_record(PROJECTS_TABLE, pid)
        if not project:
            continue
        fields = project.get("fields", {})
        projects.append({
            "id": project.get("id"),
            "name": fields.get(PROJ_NAME, "(unnamed project)"),
            "status": fields.get(PROJ_STATUS, ""),
            "service": fields.get(PROJ_SERVICE, ""),
            "start_date": fields.get(PROJ_START_DATE, ""),
        })

    return projects


def get_project_for_author(author_id, project_id):
    """
    Fetch a single project, but ONLY if it belongs to the given author.

    Returns the project dict, or None if:
      - The project doesn't exist
      - The project exists but belongs to someone else (access denied)

    This is the chokepoint for project detail pages.
    """
    if not author_id or not project_id:
        return None

    project = get_record(PROJECTS_TABLE, project_id)
    if not project:
        return None

    fields = project.get("fields", {})
    author_links = fields.get(PROJ_AUTHOR, [])

    # The critical ownership check
    if author_id not in author_links:
        return None

    return {
        "id": project.get("id"),
        "name": fields.get(PROJ_NAME, "(unnamed project)"),
        "status": fields.get(PROJ_STATUS, ""),
        "service": fields.get(PROJ_SERVICE, ""),
        "start_date": fields.get(PROJ_START_DATE, ""),
        # Contract / documents (Typeflow writes the signed PDF link here).
        # These are surfaced so the template doesn't need to know field IDs.
        "contract_url": fields.get(PROJ_CONTRACT_URL, ""),
        "contract_status": fields.get(PROJ_CONTRACT_STATUS, ""),
        "contract_sent_date": fields.get(PROJ_CONTRACT_SENT_DATE, ""),
        "contract_signed_date": fields.get(PROJ_CONTRACT_SIGNED_DATE, ""),
        "fields": fields,  # full field dict for the detail page
    }


def get_milestones_for_project(author_id, project_id):
    """
    Fetch the author-visible milestones (tasks) for a project.

    This enforces TWO ownership checks:
      1. The project must belong to the author (via get_project_for_author)
      2. Only tasks where Author Visible = true are returned

    Returns a list of milestone dicts sorted by sequence order,
    or empty list if the project doesn't belong to the author or has no
    visible milestones.
    """
    # First: verify the author owns this project.
    project = get_project_for_author(author_id, project_id)
    if not project:
        return []

    # Get the list of task record IDs from the project
    task_ids = project["fields"].get(PROJ_TASKS, [])
    if not task_ids:
        return []

    # Fetch each task and keep only the author-visible ones
    milestones = []
    for tid in task_ids:
        task = get_record(TASKS_TABLE, tid)
        if not task:
            continue

        fields = task.get("fields", {})

        # Filter: only show tasks marked visible to the author
        if not fields.get(TASK_AUTHOR_VISIBLE, False):
            continue

        milestones.append({
            "id": task.get("id"),
            "name": fields.get(TASK_NAME, "(unnamed milestone)"),
            "module": fields.get(TASK_MODULE, ""),
            "sequence": fields.get(TASK_SEQUENCE, 999),
            "status": fields.get(TASK_STATUS, "Not Started"),
            "due_date": fields.get(TASK_DUE_DATE, ""),
            "stage_description": fields.get(TASK_STAGE_DESC, ""),
        })

    # Sort by sequence order
    milestones.sort(key=lambda m: m.get("sequence") or 999)
    return milestones


def get_invoices_for_project(author_id, project_id):
    """
    Fetch all non-voided invoices for a project.

    Same ownership check as milestones: the project must belong to
    the author first, then we follow the Project -> Invoices link.

    Returns a list of invoice dicts sorted by invoice date (newest first).
    """
    # Ownership check
    project = get_project_for_author(author_id, project_id)
    if not project:
        return []

    invoice_ids = project["fields"].get(PROJ_INVOICES, [])
    if not invoice_ids:
        return []

    invoices = []
    for iid in invoice_ids:
        invoice = get_record(INVOICES_TABLE, iid)
        if not invoice:
            continue

        fields = invoice.get("fields", {})

        # Skip voided invoices — author doesn't need to see those
        if fields.get(INV_VOIDED, False):
            continue

        invoices.append({
            "id": invoice.get("id"),
            "name": fields.get(INV_NAME, "(unnamed invoice)"),
            "type": fields.get(INV_TYPE, ""),
            "amount": fields.get(INV_AMOUNT, 0),
            "amount_paid": fields.get(INV_AMOUNT_PAID, 0),
            "outstanding": fields.get(INV_OUTSTANDING, 0),
            "invoice_date": fields.get(INV_DATE, ""),
            "due_date": fields.get(INV_DUE_DATE, ""),
            "payment_status": fields.get(INV_PAYMENT_STATUS, ""),
            "stripe_url": fields.get(INV_STRIPE_URL, ""),
        })

    # Sort by invoice date descending (newest first)
    invoices.sort(key=lambda i: i.get("invoice_date") or "", reverse=True)
    return invoices
