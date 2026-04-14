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

from airtable_helpers import get_record, get_records, create_record
from datetime import date, datetime, timedelta

# ============================================================
# NEXT-STEP LOGIC
# ============================================================
# Computes what the user should do next for each task.
# Returns {"text": "...", "action": True/False}
# action=True means the user needs to do something (highlighted).
# action=False means they're waiting on someone else.

def compute_next_step(task, files, role, is_up_next=False):
    """
    Figure out the next step for a task based on its state, files, and
    who's looking at it (role).

    Args:
        task: dict with at least "status" key
        files: list of file dicts from get_files_for_task()
        role: "Task Partner", "Author", or "Admin"
        is_up_next: True if the previous task in sequence just completed
    """
    status = task.get("status", "Not Started")

    if status == "Complete":
        return {"text": "Complete", "action": False, "complete": True}
    if status == "Blocked":
        return {"text": "This task is on hold — Julie will follow up", "action": False, "complete": False}

    # Check what files exist and their directions
    has_source = any(f["direction"] == "To Partner" for f in files)
    has_deliverable = any(f["direction"] == "From Partner" for f in files)
    has_corrections = any(f["direction"] == "Author Review" for f in files)

    # Find the most recent file direction to know "who has the ball"
    latest_direction = ""
    if files:
        latest_direction = files[0]["direction"]  # files are sorted newest first

    # "Tag, you're it!" — this task just became active because the
    # previous one completed
    up_next_prefix = "You're up! " if is_up_next and status != "In Progress" else ""

    if role == "Task Partner":
        if has_corrections:
            return {"text": f"{up_next_prefix}Download the author's corrections and revise", "action": True, "complete": False, "up_next": is_up_next}
        if has_source and not has_deliverable:
            return {"text": f"{up_next_prefix}Download the source file and begin your work", "action": True, "complete": False, "up_next": is_up_next}
        if has_deliverable and latest_direction == "From Partner":
            return {"text": "Your deliverable is under review", "action": False, "complete": False, "up_next": False}
        if not has_source:
            if is_up_next:
                return {"text": "You're up next! Waiting for Julie to share the file", "action": False, "complete": False, "up_next": True}
            return {"text": "Waiting for Julie to share the file", "action": False, "complete": False, "up_next": False}
        return {"text": "Check with Julie for next steps", "action": False, "complete": False, "up_next": False}

    if role == "Author":
        if has_deliverable and latest_direction == "From Partner":
            return {"text": f"{up_next_prefix}Review the deliverable and upload corrections if needed", "action": True, "complete": False, "up_next": is_up_next}
        if status == "In Progress":
            return {"text": "In progress — your team is working on this", "action": False, "complete": False, "up_next": False}
        if is_up_next:
            return {"text": "Coming up next!", "action": False, "complete": False, "up_next": True}
        return {"text": "Coming up", "action": False, "complete": False, "up_next": False}

    if role == "Admin":
        is_overdue = task.get("is_overdue", False)
        requires_pm = task.get("requires_pm", False)
        partner_name = task.get("partner_name", "the partner")

        if is_overdue:
            return {"text": f"{up_next_prefix}Follow up — this task is overdue", "action": True, "complete": False, "up_next": is_up_next}
        if not has_source and partner_name:
            return {"text": f"{up_next_prefix}Upload the source file for {partner_name}", "action": True, "complete": False, "up_next": is_up_next}
        if has_deliverable and latest_direction == "From Partner":
            return {"text": f"{up_next_prefix}Review {partner_name}'s deliverable", "action": True, "complete": False, "up_next": is_up_next}
        if requires_pm:
            return {"text": f"{up_next_prefix}Approve this task", "action": True, "complete": False, "up_next": is_up_next}
        if status == "In Progress":
            return {"text": "In progress", "action": False, "complete": False, "up_next": False}
        if is_up_next:
            return {"text": "Up next!", "action": True, "complete": False, "up_next": True}
        return {"text": "Not started", "action": False, "complete": False, "up_next": False}

    return {"text": "", "action": False, "complete": False, "up_next": False}


def apply_next_steps(tasks, role):
    """
    Process a list of tasks (sorted by sequence) and apply next_step
    with auto-advance logic. When a task is Complete, the NEXT task
    in sequence gets is_up_next=True — "tag, you're it!"
    """
    for i, task in enumerate(tasks):
        files = task.get("files", [])

        # Check if the previous task in sequence is Complete
        is_up_next = False
        if i > 0:
            prev = tasks[i - 1]
            if prev.get("status") == "Complete" and task.get("status") != "Complete":
                is_up_next = True

        # First task that's not complete is "up" by default
        if i == 0 and task.get("status") != "Complete":
            is_up_next = True

        task["next_step"] = compute_next_step(task, files, role, is_up_next)

    return tasks


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
    AUTHOR_NAME,
    AUTHOR_PROJECTS,
    TASKS_TABLE,
    TASK_NAME,
    TASK_MODULE,
    TASK_SEQUENCE,
    TASK_STATUS,
    TASK_DUE_DATE,
    TASK_AUTHOR_VISIBLE,
    TASK_STAGE_DESC,
    TASK_ASSIGNED_PARTNER,
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
    PARTNERS_TABLE,
    PARTNER_NAME,
    PARTNER_TYPE,
    PARTNER_EMAIL,
    PARTNER_SPECIALTIES,
    PARTNER_STATUS,
    PARTNER_BIO,
    PARTNER_TASKS,
    PARTNER_PROJECTS,
    PROJ_DISBURSEMENTS,
    DISBURSEMENTS_TABLE,
    DISB_NAME,
    DISB_PARTNER,
    DISB_TYPE,
    DISB_AMOUNT_REQUESTED,
    DISB_AMOUNT_PAID,
    DISB_REQUESTED_DATE,
    DISB_PAID_DATE,
    DISB_PAYMENT_STATUS,
    DISB_PAYMENT_METHOD,
    DISB_PROJECT,
    DISB_NOTES,
    PROJECT_FILES_TABLE,
    PF_FILE_NAME,
    PF_FILE,
    PF_PROJECT,
    PF_TASK,
    PF_VERSION,
    PF_FILE_TYPE,
    PF_UPLOADED_BY,
    PF_UPLOAD_DATE,
    PF_NOTES,
    PF_DIRECTION,
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
        total_tasks = fields.get("fldtHh5z0Ciw3sJUR", 0) or 0
        completed_tasks = fields.get("fld2fuE6jFyvi5RcZ", 0) or 0

        projects.append({
            "id": project.get("id"),
            "name": fields.get(PROJ_NAME, "(unnamed project)"),
            "book_title": fields.get("fld2wXSVFxt3QHnX0", ""),
            "status": fields.get(PROJ_STATUS, ""),
            "service": fields.get(PROJ_SERVICE, ""),
            "start_date": fields.get(PROJ_START_DATE, ""),
            "total_tasks": int(total_tasks),
            "completed_tasks": int(completed_tasks),
            "progress_pct": int((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0),
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

    # Check if the project has a channel partner (hides billing from author)
    channel_partner_links = fields.get("fld5fGLcwvYNdPIdp", [])
    has_channel_partner = len(channel_partner_links) > 0

    return {
        "id": project.get("id"),
        "name": fields.get(PROJ_NAME, "(unnamed project)"),
        "status": fields.get(PROJ_STATUS, ""),
        "service": fields.get(PROJ_SERVICE, ""),
        "start_date": fields.get(PROJ_START_DATE, ""),
        "contract_url": fields.get(PROJ_CONTRACT_URL, ""),
        "contract_status": fields.get(PROJ_CONTRACT_STATUS, ""),
        "contract_sent_date": fields.get(PROJ_CONTRACT_SENT_DATE, ""),
        "contract_signed_date": fields.get(PROJ_CONTRACT_SIGNED_DATE, ""),
        "has_channel_partner": has_channel_partner,
        "fields": fields,
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

        task_record_id = task.get("id")
        task_files = get_files_for_task(task_record_id)
        milestone_dict = {
            "id": task_record_id,
            "name": fields.get(TASK_NAME, "(unnamed milestone)"),
            "module": fields.get(TASK_MODULE, ""),
            "sequence": fields.get(TASK_SEQUENCE, 999),
            "status": fields.get(TASK_STATUS, "Not Started"),
            "due_date": fields.get(TASK_DUE_DATE, ""),
            "stage_description": fields.get(TASK_STAGE_DESC, ""),
            "files": task_files,
        }
        milestones.append(milestone_dict)

    # Sort by sequence order, then apply auto-advance
    milestones.sort(key=lambda m: m.get("sequence") or 999)
    apply_next_steps(milestones, "Author")
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


# ============================================================
# PARTNER QUERIES
# ============================================================

def get_partner_name(partner_id):
    """Fetch the partner's display name from their Airtable record."""
    if not partner_id:
        return None
    partner = get_record(PARTNERS_TABLE, partner_id)
    if not partner:
        return None
    return partner.get("fields", {}).get(PARTNER_NAME)


def get_partner_type(partner_id):
    """Fetch the partner type (Task Partner or Channel Partner)."""
    if not partner_id:
        return None
    partner = get_record(PARTNERS_TABLE, partner_id)
    if not partner:
        return None
    return partner.get("fields", {}).get(PARTNER_TYPE)


# ---- Task Partner queries ----

def get_tasks_for_task_partner(partner_id):
    """
    Fetch all tasks assigned to a Task Partner, grouped by project.

    SECURITY: Follows the Partner -> Tasks link directly, so we only
    return tasks explicitly assigned to this partner.

    Returns a list of project dicts, each with a "tasks" list:
        [
            {
                "project_id": "recXXX",
                "project_name": "AuthorName — Service — Year",
                "project_status": "Active",
                "book_title": "My Great Book",
                "tasks": [
                    {"name": "Cover Design", "status": "In Progress", ...},
                ]
            },
        ]
    """
    if not partner_id:
        return []

    # Step 1: Get the partner record to find their assigned task IDs
    partner = get_record(PARTNERS_TABLE, partner_id)
    if not partner:
        return []

    task_ids = partner.get("fields", {}).get(PARTNER_TASKS, [])
    if not task_ids:
        return []

    # Step 2: Fetch each task and collect project info
    # We group tasks by project so the template can show them organized
    projects_map = {}  # project_id -> {project info + tasks list}

    for tid in task_ids:
        task = get_record(TASKS_TABLE, tid)
        if not task:
            continue

        fields = task.get("fields", {})

        # Get the project this task belongs to
        project_links = fields.get("fldj1YwlwJbfK956K", [])  # TASK_PROJECT
        if not project_links:
            continue
        project_id = project_links[0]

        # If we haven't seen this project yet, fetch its info
        if project_id not in projects_map:
            project = get_record(PROJECTS_TABLE, project_id)
            if not project:
                continue
            pfields = project.get("fields", {})

            # Get the author name for display
            author_links = pfields.get(PROJ_AUTHOR, [])
            author_name = ""
            if author_links:
                author = get_record(AUTHORS_TABLE, author_links[0])
                if author:
                    author_name = author.get("fields", {}).get(AUTHOR_NAME, "")

            projects_map[project_id] = {
                "project_id": project_id,
                "project_name": pfields.get(PROJ_NAME, "(unnamed project)"),
                "project_status": pfields.get(PROJ_STATUS, ""),
                "book_title": pfields.get("fld2wXSVFxt3QHnX0", ""),
                "author_name": author_name,
                "tasks": [],
            }

        # Add this task to the project's task list
        task_record_id = task.get("id")
        task_files = get_files_for_task(task_record_id)
        task_dict = {
            "id": task_record_id,
            "name": fields.get(TASK_NAME, "(unnamed task)"),
            "module": fields.get(TASK_MODULE, ""),
            "sequence": fields.get(TASK_SEQUENCE, 999),
            "status": fields.get(TASK_STATUS, "Not Started"),
            "due_date": fields.get(TASK_DUE_DATE, ""),
            "stage_description": fields.get(TASK_STAGE_DESC, ""),
            "instructions": fields.get("fldB74YCkAJ055mis", ""),
            "files": task_files,
        }
        projects_map[project_id]["tasks"].append(task_dict)

    # Sort tasks within each project by sequence, then apply auto-advance
    result = list(projects_map.values())
    for proj in result:
        proj["tasks"].sort(key=lambda t: t.get("sequence") or 999)
        apply_next_steps(proj["tasks"], "Task Partner")

    return result


# ---- Channel Partner queries ----

def get_projects_for_channel_partner(partner_id):
    """
    Fetch all projects linked to a Channel Partner.

    SECURITY: Follows the Partner -> Projects link directly.
    Only returns projects explicitly linked to this partner.
    """
    if not partner_id:
        return []

    partner = get_record(PARTNERS_TABLE, partner_id)
    if not partner:
        return []

    project_ids = partner.get("fields", {}).get(PARTNER_PROJECTS, [])
    if not project_ids:
        return []

    projects = []
    for pid in project_ids:
        project = get_record(PROJECTS_TABLE, pid)
        if not project:
            continue
        fields = project.get("fields", {})

        # Get author name
        author_links = fields.get(PROJ_AUTHOR, [])
        author_name = ""
        if author_links:
            author = get_record(AUTHORS_TABLE, author_links[0])
            if author:
                author_name = author.get("fields", {}).get(AUTHOR_NAME, "")

        total_tasks = fields.get("fldtHh5z0Ciw3sJUR", 0) or 0
        completed_tasks = fields.get("fld2fuE6jFyvi5RcZ", 0) or 0

        projects.append({
            "id": project.get("id"),
            "name": fields.get(PROJ_NAME, "(unnamed project)"),
            "book_title": fields.get("fld2wXSVFxt3QHnX0", ""),
            "author_name": author_name,
            "status": fields.get(PROJ_STATUS, ""),
            "service": fields.get(PROJ_SERVICE, ""),
            "start_date": fields.get(PROJ_START_DATE, ""),
            "total_tasks": int(total_tasks),
            "completed_tasks": int(completed_tasks),
            "progress_pct": int((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0),
        })

    return projects


def get_project_for_channel_partner(partner_id, project_id):
    """
    Fetch a single project, but ONLY if it's linked to the given Channel Partner.

    Returns the project dict (same shape as get_project_for_author), or None.
    """
    if not partner_id or not project_id:
        return None

    # Step 1: Verify this partner is linked to this project
    partner = get_record(PARTNERS_TABLE, partner_id)
    if not partner:
        return None

    linked_projects = partner.get("fields", {}).get(PARTNER_PROJECTS, [])
    if project_id not in linked_projects:
        return None  # Access denied — not their project

    # Step 2: Fetch the project
    project = get_record(PROJECTS_TABLE, project_id)
    if not project:
        return None

    fields = project.get("fields", {})
    return {
        "id": project.get("id"),
        "name": fields.get(PROJ_NAME, "(unnamed project)"),
        "status": fields.get(PROJ_STATUS, ""),
        "service": fields.get(PROJ_SERVICE, ""),
        "start_date": fields.get(PROJ_START_DATE, ""),
        "contract_url": fields.get(PROJ_CONTRACT_URL, ""),
        "contract_status": fields.get(PROJ_CONTRACT_STATUS, ""),
        "contract_sent_date": fields.get(PROJ_CONTRACT_SENT_DATE, ""),
        "contract_signed_date": fields.get(PROJ_CONTRACT_SIGNED_DATE, ""),
        "fields": fields,
    }


def get_milestones_for_channel_project(partner_id, project_id):
    """
    Fetch milestones for a Channel Partner's project.
    Same as author milestones but ownership check goes through the partner.
    """
    # Verify ownership through the channel partner
    project = get_project_for_channel_partner(partner_id, project_id)
    if not project:
        return []

    task_ids = project["fields"].get(PROJ_TASKS, [])
    if not task_ids:
        return []

    milestones = []
    for tid in task_ids:
        task = get_record(TASKS_TABLE, tid)
        if not task:
            continue
        fields = task.get("fields", {})

        # Channel Partners see all milestones (not filtered by Author Visible)
        milestones.append({
            "id": task.get("id"),
            "name": fields.get(TASK_NAME, "(unnamed milestone)"),
            "module": fields.get(TASK_MODULE, ""),
            "sequence": fields.get(TASK_SEQUENCE, 999),
            "status": fields.get(TASK_STATUS, "Not Started"),
            "due_date": fields.get(TASK_DUE_DATE, ""),
            "stage_description": fields.get(TASK_STAGE_DESC, ""),
        })

    milestones.sort(key=lambda m: m.get("sequence") or 999)
    return milestones


def get_invoices_for_channel_project(partner_id, project_id):
    """
    Fetch invoices for a Channel Partner's project.
    Same as author invoices but ownership check goes through the partner.
    """
    project = get_project_for_channel_partner(partner_id, project_id)
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

    invoices.sort(key=lambda i: i.get("invoice_date") or "", reverse=True)
    return invoices


# ============================================================
# FILE QUERIES (Project Files table)
# ============================================================

def get_files_for_task(task_id):
    """
    Fetch all file records linked to a specific task.
    Returns them sorted by version (newest first) so the latest
    version is always at the top.

    Each file record includes the Airtable attachment URL, which
    is a temporary signed URL valid for a few hours.

    WHY PYTHON FILTERING?
    Airtable formulas on linked record fields match on the DISPLAY
    value (e.g. "Developmental Edit"), not the record ID. So we
    can't use FIND('recXXX', {Task}) in a formula. Instead we fetch
    all file records and filter by the linked task ID in Python.
    For a table with hundreds of rows this is fast enough.
    """
    if not task_id:
        return []

    # Fetch all file records, then filter by task ID in Python
    all_records = get_records(PROJECT_FILES_TABLE)
    records = []
    for r in all_records:
        linked_tasks = r.get("fields", {}).get(PF_TASK, [])
        if task_id in linked_tasks:
            records.append(r)

    files = []
    for r in records:
        fields = r.get("fields", {})

        # Airtable attachments are a list of dicts with url, filename, size, type
        attachments = fields.get(PF_FILE, [])
        attachment = attachments[0] if attachments else None

        # Check if we have a locally stored file (fallback for localhost)
        notes_raw = fields.get(PF_NOTES, "")
        stored_filename = ""
        display_notes = notes_raw
        if "[stored:" in notes_raw:
            # Extract the stored filename from notes
            start = notes_raw.index("[stored:") + len("[stored:")
            end = notes_raw.index("]", start)
            stored_filename = notes_raw[start:end]
            # Remove the stored tag from display notes
            display_notes = notes_raw[end + 1:].strip()

        # Build download URL: prefer Airtable attachment, fall back to local
        if attachment:
            download_url = attachment.get("url", "")
        elif stored_filename:
            download_url = f"/uploads/{stored_filename}"
        else:
            download_url = ""

        files.append({
            "id": r.get("id"),
            "file_name": fields.get(PF_FILE_NAME, "(unnamed)"),
            "version": fields.get(PF_VERSION, 1),
            "file_type": fields.get(PF_FILE_TYPE, ""),
            "uploaded_by": fields.get(PF_UPLOADED_BY, ""),
            "upload_date": fields.get(PF_UPLOAD_DATE, ""),
            "notes": display_notes,
            "direction": fields.get(PF_DIRECTION, ""),
            "has_file": bool(attachment or stored_filename),
            "download_url": download_url,
            "original_filename": attachment.get("filename", "") if attachment else fields.get(PF_FILE_NAME, ""),
            "file_size": attachment.get("size", 0) if attachment else 0,
        })

    # Sort: newest version first
    files.sort(key=lambda f: f.get("version") or 0, reverse=True)
    return files


def get_all_files_by_task():
    """
    Bulk-fetch ALL project files in a SINGLE Airtable call, then group
    them by their linked task ID. Used by Command Center to avoid
    calling get_files_for_task() hundreds of times (once per task).

    Returns a dict: {task_id: [file_dict, ...]}
    Each file_dict has the same shape as get_files_for_task() returns.

    WHY THIS EXISTS:
      get_files_for_task() fetches the entire Project Files table every
      time it's called. If Command Center loops over 300 tasks, that's
      300 full-table fetches = 30+ seconds. This helper does ONE fetch
      and lets the caller look up files in-memory.
    """
    all_records = get_records(PROJECT_FILES_TABLE)

    files_by_task = {}
    for r in all_records:
        fields = r.get("fields", {})

        # Airtable attachments are a list of dicts with url, filename, size, type
        attachments = fields.get(PF_FILE, [])
        attachment = attachments[0] if attachments else None

        # Check if we have a locally stored file (fallback for localhost)
        notes_raw = fields.get(PF_NOTES, "")
        stored_filename = ""
        display_notes = notes_raw
        if "[stored:" in notes_raw:
            start = notes_raw.index("[stored:") + len("[stored:")
            end = notes_raw.index("]", start)
            stored_filename = notes_raw[start:end]
            display_notes = notes_raw[end + 1:].strip()

        if attachment:
            download_url = attachment.get("url", "")
        elif stored_filename:
            download_url = f"/uploads/{stored_filename}"
        else:
            download_url = ""

        file_dict = {
            "id": r.get("id"),
            "file_name": fields.get(PF_FILE_NAME, "(unnamed)"),
            "version": fields.get(PF_VERSION, 1),
            "file_type": fields.get(PF_FILE_TYPE, ""),
            "uploaded_by": fields.get(PF_UPLOADED_BY, ""),
            "upload_date": fields.get(PF_UPLOAD_DATE, ""),
            "notes": display_notes,
            "direction": fields.get(PF_DIRECTION, ""),
            "has_file": bool(attachment or stored_filename),
            "download_url": download_url,
            "original_filename": attachment.get("filename", "") if attachment else fields.get(PF_FILE_NAME, ""),
            "file_size": attachment.get("size", 0) if attachment else 0,
        }

        # A file may be linked to multiple tasks (rare but possible)
        # Add it to each task's bucket
        linked_tasks = fields.get(PF_TASK, []) or []
        for tid in linked_tasks:
            files_by_task.setdefault(tid, []).append(file_dict)

    # Sort each task's files: newest version first
    for tid in files_by_task:
        files_by_task[tid].sort(key=lambda f: f.get("version") or 0, reverse=True)

    return files_by_task


def get_files_for_project(project_id):
    """
    Fetch all file records linked to a project.
    Used for showing all files across all tasks on a project.
    """
    if not project_id:
        return []

    all_records = get_records(PROJECT_FILES_TABLE)
    records = []
    for r in all_records:
        linked_projects = r.get("fields", {}).get(PF_PROJECT, [])
        if project_id in linked_projects:
            records.append(r)

    files = []
    for r in records:
        fields = r.get("fields", {})
        attachments = fields.get(PF_FILE, [])
        attachment = attachments[0] if attachments else None

        files.append({
            "id": r.get("id"),
            "file_name": fields.get(PF_FILE_NAME, "(unnamed)"),
            "version": fields.get(PF_VERSION, 1),
            "file_type": fields.get(PF_FILE_TYPE, ""),
            "uploaded_by": fields.get(PF_UPLOADED_BY, ""),
            "upload_date": fields.get(PF_UPLOAD_DATE, ""),
            "notes": fields.get(PF_NOTES, ""),
            "direction": fields.get(PF_DIRECTION, ""),
            "has_file": attachment is not None,
            "download_url": attachment.get("url", "") if attachment else "",
            "original_filename": attachment.get("filename", "") if attachment else "",
            "file_size": attachment.get("size", 0) if attachment else 0,
        })

    files.sort(key=lambda f: f.get("version") or 0, reverse=True)
    return files


def get_next_version_for_task(task_id):
    """
    Figure out the next version number for a file on this task.
    Looks at existing file records and returns max + 1.
    """
    files = get_files_for_task(task_id)
    if not files:
        return 1
    max_version = max(f.get("version") or 0 for f in files)
    return max_version + 1


def create_file_record(task_id, project_id, file_name, file_url,
                       file_type, direction, uploaded_by, notes="",
                       stored_filename=""):
    """
    Create a new row in the Project Files table.

    Args:
        task_id: The task this file belongs to
        project_id: The project this file belongs to
        file_name: Display name (e.g., "Money Mindset Manuscript v2.docx")
        file_url: Public URL where Airtable can download the file
        file_type: One of: Manuscript, Edited Manuscript, Cover Design, etc.
        direction: "To Partner", "From Partner", or "Author Review"
        uploaded_by: Name of the uploader
        notes: Optional notes about this version
        stored_filename: The unique filename in uploads/ folder (for direct serving)

    Returns the created record, or None on error.
    """
    version = get_next_version_for_task(task_id)

    fields = {
        PF_FILE_NAME: file_name,
        PF_PROJECT: [project_id],
        PF_TASK: [task_id],
        PF_VERSION: version,
        PF_FILE_TYPE: file_type,
        PF_UPLOADED_BY: uploaded_by,
        PF_UPLOAD_DATE: date.today().isoformat(),
        PF_DIRECTION: direction,
    }

    # Try to attach the file via URL. This only works when Airtable
    # can reach the URL (i.e., in production on Render, not localhost).
    if file_url:
        fields[PF_FILE] = [{"url": file_url}]

    # Store notes. If we have a stored_filename, prepend it so we can
    # build a download link even when Airtable's attachment is empty.
    note_parts = []
    if stored_filename:
        note_parts.append(f"[stored:{stored_filename}]")
    if notes:
        note_parts.append(notes)
    if note_parts:
        fields[PF_NOTES] = "\n".join(note_parts)

    return create_record(PROJECT_FILES_TABLE, fields)


# ============================================================
# COMMAND CENTER QUERIES (unfiltered — Admin sees everything)
# ============================================================

def get_all_projects():
    """
    Fetch ALL projects across all authors. No ownership filter.
    Returns a list sorted by status (Active first, then Lead, then Complete).
    """
    records = get_records(PROJECTS_TABLE)

    projects = []
    for r in records:
        fields = r.get("fields", {})

        # Get author name
        author_links = fields.get(PROJ_AUTHOR, [])
        author_name = ""
        if author_links:
            author = get_record(AUTHORS_TABLE, author_links[0])
            if author:
                author_name = author.get("fields", {}).get(AUTHOR_NAME, "")

        # Count tasks
        task_ids = fields.get(PROJ_TASKS, [])
        total_tasks = len(task_ids)

        projects.append({
            "id": r.get("id"),
            "name": fields.get(PROJ_NAME, "(unnamed)"),
            "status": fields.get(PROJ_STATUS, ""),
            "service": fields.get(PROJ_SERVICE, ""),
            "start_date": fields.get(PROJ_START_DATE, ""),
            "author_name": author_name,
            "total_tasks": total_tasks,
            "deposit_paid": fields.get("fldXKN3e7lcy1Q0bd", False),
            "contract_status": fields.get(PROJ_CONTRACT_STATUS, ""),
            "project_fee": fields.get("fldH1ypvmL7uqN6kT", 0),
            "total_collected": fields.get("fldAnGjvDw5UEAc6M", 0),
            "fields": fields,
        })

    # Sort: Active first, then Lead, then everything else
    status_order = {
        "Lead": 0, "Discovery": 1, "Proposal": 2,
        "Contract Sent": 3, "Signed": 4, "Active": 5,
        "On Hold": 6, "Complete": 7,
    }
    projects.sort(key=lambda p: status_order.get(p["status"], 99))
    return projects


def get_project_detail_admin(project_id):
    """
    Fetch full details for a single project (admin view, no ownership filter).
    Returns project info + tasks + invoices + author info + contract status.
    """
    project = get_record(PROJECTS_TABLE, project_id)
    if not project:
        return None

    fields = project.get("fields", {})

    # Get author info
    author_links = fields.get(PROJ_AUTHOR, [])
    author_id = author_links[0] if author_links else ""
    author_name = ""
    author_email = ""
    if author_id:
        author = get_record(AUTHORS_TABLE, author_id)
        if author:
            from config import AUTHOR_EMAIL
            author_name = author.get("fields", {}).get(AUTHOR_NAME, "")
            author_email = author.get("fields", {}).get(AUTHOR_EMAIL, "")

    # Get tasks for this project
    task_ids = fields.get(PROJ_TASKS, [])
    tasks = []
    for tid in task_ids:
        t = get_record(TASKS_TABLE, tid)
        if t:
            tf = t.get("fields", {})
            # Get assigned partner name
            partner_links = tf.get(TASK_ASSIGNED_PARTNER, [])
            partner_name = ""
            if partner_links:
                partner = get_record(PARTNERS_TABLE, partner_links[0])
                if partner:
                    partner_name = partner.get("fields", {}).get(PARTNER_NAME, "")

            tasks.append({
                "id": t.get("id"),
                "name": tf.get(TASK_NAME, ""),
                "status": tf.get(TASK_STATUS, ""),
                "due_date": tf.get(TASK_DUE_DATE, ""),
                "sequence": tf.get(TASK_SEQUENCE, 0),
                "module": tf.get(TASK_MODULE, ""),
                "partner_name": partner_name,
            })

    # Sort tasks by sequence
    tasks.sort(key=lambda t: t.get("sequence", 0))

    # Get invoices for this project
    invoice_ids = fields.get(PROJ_INVOICES, [])
    invoices = []
    for iid in invoice_ids:
        inv = get_record(INVOICES_TABLE, iid)
        if inv:
            ivf = inv.get("fields", {})
            if ivf.get(INV_VOIDED):
                continue
            invoices.append({
                "id": inv.get("id"),
                "name": ivf.get(INV_NAME, ""),
                "type": ivf.get(INV_TYPE, ""),
                "amount": ivf.get(INV_AMOUNT, 0),
                "amount_paid": ivf.get(INV_AMOUNT_PAID, 0),
                "outstanding": ivf.get(INV_OUTSTANDING, 0),
                "status": ivf.get(INV_PAYMENT_STATUS, ""),
                "due_date": ivf.get(INV_DUE_DATE, ""),
                "stripe_url": ivf.get(INV_STRIPE_URL, ""),
            })

    # Get disbursements (money going OUT — partner payments, referral fees)
    disb_ids = fields.get(PROJ_DISBURSEMENTS, [])
    disbursements = []
    for did in disb_ids:
        d = get_record(DISBURSEMENTS_TABLE, did)
        if d:
            df = d.get("fields", {})
            # Get partner name for this disbursement
            partner_links = df.get(DISB_PARTNER, [])
            disb_partner_name = ""
            if partner_links:
                partner = get_record(PARTNERS_TABLE, partner_links[0])
                if partner:
                    disb_partner_name = partner.get("fields", {}).get(PARTNER_NAME, "")

            disbursements.append({
                "id": d.get("id"),
                "name": df.get(DISB_NAME, ""),
                "type": df.get(DISB_TYPE, ""),
                "partner_name": disb_partner_name,
                "amount_requested": df.get(DISB_AMOUNT_REQUESTED, 0),
                "amount_paid": df.get(DISB_AMOUNT_PAID, 0),
                "requested_date": df.get(DISB_REQUESTED_DATE, ""),
                "paid_date": df.get(DISB_PAID_DATE, ""),
                "status": df.get(DISB_PAYMENT_STATUS, ""),
                "payment_method": df.get(DISB_PAYMENT_METHOD, ""),
                "notes": df.get(DISB_NOTES, ""),
            })

    return {
        "id": project.get("id"),
        "name": fields.get(PROJ_NAME, "(unnamed)"),
        "status": fields.get(PROJ_STATUS, ""),
        "service": fields.get(PROJ_SERVICE, ""),
        "start_date": fields.get(PROJ_START_DATE, ""),
        "author_id": author_id,
        "author_name": author_name,
        "author_email": author_email,
        "contract_status": fields.get(PROJ_CONTRACT_STATUS, ""),
        "contract_url": fields.get(PROJ_CONTRACT_URL, ""),
        "contract_sent_date": fields.get(PROJ_CONTRACT_SENT_DATE, ""),
        "contract_signed_date": fields.get(PROJ_CONTRACT_SIGNED_DATE, ""),
        "deposit_paid": fields.get("fldXKN3e7lcy1Q0bd", False),
        "tasks": tasks,
        "invoices": invoices,
        "disbursements": disbursements,
    }


def get_all_tasks():
    """
    Fetch ALL tasks across all projects. No ownership filter.
    Includes project name and assigned partner name for display.

    Returns tasks sorted by urgency:
      1. Overdue (past due, not complete)
      2. Due this week
      3. Requires PM approval
      4. In Progress
      5. Not Started
      6. Complete (at bottom)
    """
    records = get_records(TASKS_TABLE)
    today = date.today()
    week_from_now = today + timedelta(days=7)

    # PERFORMANCE: pre-fetch everything we need in 3 bulk calls instead of
    # looking each record up inside the loop. Without this, a 200-task
    # page made ~200 sequential Airtable calls for files alone (see
    # get_all_files_by_task docstring), which blew past gunicorn's
    # 30-second worker timeout.
    all_projects = get_records(PROJECTS_TABLE)
    project_names = {
        p.get("id"): p.get("fields", {}).get(PROJ_NAME, "")
        for p in all_projects
    }

    all_partners = get_records(PARTNERS_TABLE)
    partner_names = {
        p.get("id"): p.get("fields", {}).get(PARTNER_NAME, "")
        for p in all_partners
    }

    files_by_task = get_all_files_by_task()

    tasks = []

    for r in records:
        fields = r.get("fields", {})

        # Get project name from pre-fetched dict
        project_links = fields.get("fldj1YwlwJbfK956K", [])
        project_id = project_links[0] if project_links else ""
        project_name = project_names.get(project_id, "") if project_id else ""

        # Get assigned partner name from pre-fetched dict
        partner_links = fields.get(TASK_ASSIGNED_PARTNER, [])
        partner_id = partner_links[0] if partner_links else ""
        partner_name = partner_names.get(partner_id, "") if partner_id else ""

        status = fields.get(TASK_STATUS, "Not Started")
        due_date_str = fields.get(TASK_DUE_DATE, "")
        requires_pm = fields.get("fldzymeSrKFWZy1Tr", False)

        # Calculate urgency for sorting
        due_date = None
        is_overdue = False
        is_due_soon = False
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                if status != "Complete" and due_date < today:
                    is_overdue = True
                elif due_date <= week_from_now:
                    is_due_soon = True
            except ValueError:
                pass

        # Urgency score (lower = more urgent, shows first)
        if is_overdue:
            urgency = 0
        elif is_due_soon and status != "Complete":
            urgency = 1
        elif requires_pm and status != "Complete":
            urgency = 2
        elif status == "In Progress":
            urgency = 3
        elif status == "Not Started":
            urgency = 4
        elif status == "Complete":
            urgency = 9
        else:
            urgency = 5

        task_id = r.get("id")
        task_files = files_by_task.get(task_id, [])
        task_dict = {
            "id": task_id,
            "name": fields.get(TASK_NAME, "(unnamed)"),
            "project_id": project_id,
            "project_name": project_name,
            "partner_name": partner_name,
            "module": fields.get(TASK_MODULE, ""),
            "status": status,
            "due_date": due_date_str,
            "completed_date": fields.get("fldFR28GxPlXzTftS", ""),
            "requires_pm": requires_pm,
            "requires_author": fields.get("fldJrY5qcKJUdfQoV", False),
            "instructions": fields.get("fldB74YCkAJ055mis", ""),
            "stage_description": fields.get(TASK_STAGE_DESC, ""),
            "is_overdue": is_overdue,
            "is_due_soon": is_due_soon,
            "urgency": urgency,
        }
        task_dict["next_step"] = compute_next_step(task_dict, task_files, "Admin")
        tasks.append(task_dict)

    tasks.sort(key=lambda t: t["urgency"])
    return tasks


def get_all_invoices():
    """
    Fetch ALL non-voided invoices across all projects.
    Sorted by urgency: overdue first, then upcoming, then paid.
    """
    records = get_records(INVOICES_TABLE)
    today = date.today()

    # Cache project lookups
    project_cache = {}

    invoices = []
    for r in records:
        fields = r.get("fields", {})

        if fields.get(INV_VOIDED, False):
            continue

        # Get project name
        project_links = fields.get("fldAKLIauWoRpJGU3", [])
        project_id = project_links[0] if project_links else ""
        project_name = ""
        if project_id:
            if project_id not in project_cache:
                proj = get_record(PROJECTS_TABLE, project_id)
                project_cache[project_id] = proj
            proj = project_cache.get(project_id)
            if proj:
                project_name = proj.get("fields", {}).get(PROJ_NAME, "")

        payment_status = fields.get(INV_PAYMENT_STATUS, "")
        outstanding = fields.get(INV_OUTSTANDING, 0)
        due_date_str = fields.get(INV_DUE_DATE, "")

        # Check if overdue
        is_overdue = False
        if due_date_str and payment_status != "Paid":
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                if due_date < today:
                    is_overdue = True
            except ValueError:
                pass

        invoices.append({
            "id": r.get("id"),
            "name": fields.get(INV_NAME, "(unnamed)"),
            "project_name": project_name,
            "type": fields.get(INV_TYPE, ""),
            "amount": fields.get(INV_AMOUNT, 0),
            "amount_paid": fields.get(INV_AMOUNT_PAID, 0),
            "outstanding": outstanding,
            "invoice_date": fields.get(INV_DATE, ""),
            "due_date": due_date_str,
            "payment_status": payment_status,
            "stripe_url": fields.get(INV_STRIPE_URL, ""),
            "is_overdue": is_overdue,
        })

    # Sort: overdue first, then unpaid, then paid
    def sort_key(inv):
        if inv["is_overdue"]:
            return 0
        if inv["payment_status"] != "Paid" and inv["outstanding"] > 0:
            return 1
        return 2
    invoices.sort(key=sort_key)
    return invoices


def get_task_detail(task_id):
    """
    Fetch a single task with all fields for editing.
    Returns a dict with everything the Command Center needs.
    """
    if not task_id:
        return None

    task = get_record(TASKS_TABLE, task_id)
    if not task:
        return None

    fields = task.get("fields", {})

    # Get project info
    project_links = fields.get("fldj1YwlwJbfK956K", [])
    project_id = project_links[0] if project_links else ""
    project_name = ""
    if project_id:
        proj = get_record(PROJECTS_TABLE, project_id)
        if proj:
            project_name = proj.get("fields", {}).get(PROJ_NAME, "")

    # Get assigned partner info
    partner_links = fields.get(TASK_ASSIGNED_PARTNER, [])
    partner_id = partner_links[0] if partner_links else ""
    partner_name = ""
    if partner_id:
        partner = get_record(PARTNERS_TABLE, partner_id)
        if partner:
            partner_name = partner.get("fields", {}).get(PARTNER_NAME, "")

    # Get files
    files = get_files_for_task(task_id)

    return {
        "id": task.get("id"),
        "name": fields.get(TASK_NAME, "(unnamed)"),
        "project_id": project_id,
        "project_name": project_name,
        "partner_id": partner_id,
        "partner_name": partner_name,
        "module": fields.get(TASK_MODULE, ""),
        "status": fields.get(TASK_STATUS, "Not Started"),
        "due_date": fields.get(TASK_DUE_DATE, ""),
        "completed_date": fields.get("fldFR28GxPlXzTftS", ""),
        "requires_pm": fields.get("fldzymeSrKFWZy1Tr", False),
        "requires_author": fields.get("fldJrY5qcKJUdfQoV", False),
        "instructions": fields.get("fldB74YCkAJ055mis", ""),
        "stage_description": fields.get(TASK_STAGE_DESC, ""),
        "notes": fields.get("fldGlObVe6dyOSZci", ""),
        "files": files,
    }


def get_all_partners():
    """
    Fetch ALL partners with their task counts and active project info.
    """
    records = get_records(PARTNERS_TABLE)

    partners = []
    for r in records:
        fields = r.get("fields", {})
        task_ids = fields.get(PARTNER_TASKS, [])
        project_ids = fields.get(PARTNER_PROJECTS, [])

        partners.append({
            "id": r.get("id"),
            "name": fields.get(PARTNER_NAME, "(unnamed)"),
            "type": fields.get(PARTNER_TYPE, ""),
            "email": fields.get(PARTNER_EMAIL, ""),
            "specialties": fields.get(PARTNER_SPECIALTIES, []),
            "status": fields.get(PARTNER_STATUS, ""),
            "bio": fields.get(PARTNER_BIO, ""),
            "task_count": len(task_ids),
            "project_count": len(project_ids),
        })

    # Sort: active first, then by name
    partners.sort(key=lambda p: (0 if p["status"] == "Active" else 1, p["name"]))
    return partners


def get_partner_detail_admin(partner_id):
    """
    Fetch full details for a single partner (admin view).
    Returns partner info + their projects + their disbursements.
    """
    from config import (
        PARTNER_PREFERRED_NAME, PARTNER_HOURLY_RATE, PARTNER_PORTFOLIO,
        PARTNER_NOTES, PARTNER_DISBURSEMENTS,
    )

    partner = get_record(PARTNERS_TABLE, partner_id)
    if not partner:
        return None

    fields = partner.get("fields", {})

    # Get projects this partner is linked to
    # Task Partners: get projects via their tasks
    # Channel Partners: get projects via the direct link
    task_ids = fields.get(PARTNER_TASKS, [])
    project_ids_from_tasks = set()
    tasks = []
    for tid in task_ids:
        t = get_record(TASKS_TABLE, tid)
        if t:
            tf = t.get("fields", {})
            proj_links = tf.get("fldj1YwlwJbfK956K", [])
            proj_id = proj_links[0] if proj_links else ""
            if proj_id:
                project_ids_from_tasks.add(proj_id)
            tasks.append({
                "id": t.get("id"),
                "name": tf.get(TASK_NAME, ""),
                "status": tf.get(TASK_STATUS, ""),
                "due_date": tf.get(TASK_DUE_DATE, ""),
                "project_id": proj_id,
            })

    # Build projects list — combine task-linked and direct-linked projects
    direct_project_ids = fields.get(PARTNER_PROJECTS, [])
    all_project_ids = project_ids_from_tasks | set(direct_project_ids)

    projects = []
    for pid in all_project_ids:
        p = get_record(PROJECTS_TABLE, pid)
        if p:
            pf = p.get("fields", {})
            # Get author name
            author_links = pf.get(PROJ_AUTHOR, [])
            author_name = ""
            if author_links:
                a = get_record(AUTHORS_TABLE, author_links[0])
                if a:
                    author_name = a.get("fields", {}).get(AUTHOR_NAME, "")

            projects.append({
                "id": p.get("id"),
                "name": pf.get(PROJ_NAME, ""),
                "status": pf.get(PROJ_STATUS, ""),
                "service": pf.get(PROJ_SERVICE, ""),
                "author_name": author_name,
            })

    # Sort projects: Active first
    status_order = {
        "Lead": 0, "Discovery": 1, "Proposal": 2,
        "Contract Sent": 3, "Signed": 4, "Active": 5,
        "On Hold": 6, "Complete": 7,
    }
    projects.sort(key=lambda p: status_order.get(p["status"], 99))

    # Get disbursements for this partner
    disb_ids = fields.get(PARTNER_DISBURSEMENTS, [])
    disbursements = []
    total_paid = 0
    total_pending = 0
    for did in disb_ids:
        d = get_record(DISBURSEMENTS_TABLE, did)
        if d:
            df = d.get("fields", {})
            amt_paid = df.get(DISB_AMOUNT_PAID, 0) or 0
            amt_requested = df.get(DISB_AMOUNT_REQUESTED, 0) or 0
            status = df.get(DISB_PAYMENT_STATUS, "")

            total_paid += amt_paid
            if status != "Paid":
                total_pending += amt_requested - amt_paid

            # Get project name for this disbursement
            proj_links = df.get(DISB_PROJECT, [])
            disb_project_name = ""
            if proj_links:
                proj = get_record(PROJECTS_TABLE, proj_links[0])
                if proj:
                    disb_project_name = proj.get("fields", {}).get(PROJ_NAME, "")

            disbursements.append({
                "id": d.get("id"),
                "name": df.get(DISB_NAME, ""),
                "type": df.get(DISB_TYPE, ""),
                "project_name": disb_project_name,
                "amount_requested": amt_requested,
                "amount_paid": amt_paid,
                "requested_date": df.get(DISB_REQUESTED_DATE, ""),
                "paid_date": df.get(DISB_PAID_DATE, ""),
                "status": status,
                "payment_method": df.get(DISB_PAYMENT_METHOD, ""),
            })

    return {
        "id": partner.get("id"),
        "name": fields.get(PARTNER_NAME, "(unnamed)"),
        "preferred_name": fields.get(PARTNER_PREFERRED_NAME, ""),
        "type": fields.get(PARTNER_TYPE, ""),
        "email": fields.get(PARTNER_EMAIL, ""),
        "specialties": fields.get(PARTNER_SPECIALTIES, []),
        "hourly_rate": fields.get(PARTNER_HOURLY_RATE, 0),
        "portfolio_url": fields.get(PARTNER_PORTFOLIO, ""),
        "status": fields.get(PARTNER_STATUS, ""),
        "bio": fields.get(PARTNER_BIO, ""),
        "notes": fields.get(PARTNER_NOTES, ""),
        "projects": projects,
        "tasks": tasks,
        "disbursements": disbursements,
        "total_paid": total_paid,
        "total_pending": total_pending,
    }


def get_available_services():
    """
    Get the list of services for the project startup dropdown.
    Returns the keys from SERVICE_TO_BUNDLE mapping.
    """
    from config import SERVICE_TO_BUNDLE
    # Return unique service names (not the Chapters variants)
    return sorted(SERVICE_TO_BUNDLE.keys())


def get_all_authors():
    """Fetch all authors for the project startup dropdown."""
    records = get_records(AUTHORS_TABLE)
    authors = []
    for r in records:
        fields = r.get("fields", {})
        authors.append({
            "id": r.get("id"),
            "name": fields.get(AUTHOR_NAME, "(unnamed)"),
        })
    authors.sort(key=lambda a: a["name"])
    return authors


def get_lead_projects():
    """Fetch projects with Lead status for the 'activate existing' flow."""
    formula = "{Status}='Lead'"
    records = get_records(PROJECTS_TABLE, formula=formula)

    projects = []
    for r in records:
        fields = r.get("fields", {})
        # Get author name
        author_links = fields.get(PROJ_AUTHOR, [])
        author_name = ""
        if author_links:
            author = get_record(AUTHORS_TABLE, author_links[0])
            if author:
                author_name = author.get("fields", {}).get(AUTHOR_NAME, "")

        projects.append({
            "id": r.get("id"),
            "name": fields.get(PROJ_NAME, "(unnamed)"),
            "service": fields.get(PROJ_SERVICE, ""),
            "author_name": author_name,
        })
    return projects


def inject_milestones(project_id, service_name, start_date=None):
    """
    Create tasks for a project by copying from the Milestone Library.

    HOW IT WORKS:
      1. Look up the bundle name from SERVICE_TO_BUNDLE mapping
      2. Fetch all active milestone templates for that bundle
      3. Create a task for each one, linked to the project

    DUE DATE LOGIC (sequential):
      Each task's due date = previous task's due date + this task's duration.
      So if Task 1 takes 5 days and Task 2 takes 3 days:
        Task 1 due = start + 5 days
        Task 2 due = Task 1 due + 3 days = start + 8 days
      Tasks with no duration get no due date and don't push the timeline.

    Args:
        project_id: Airtable record ID for the project
        service_name: Service name (mapped to bundle via SERVICE_TO_BUNDLE)
        start_date: Optional date object for when the project starts.
                    Defaults to today if not provided.

    Returns the count of tasks created.
    """
    from config import (
        SERVICE_TO_BUNDLE,
        MILESTONE_LIBRARY_TABLE,
        ML_NAME, ML_BUNDLE, ML_MODULE, ML_SEQUENCE,
        ML_DEFAULT_OWNER, ML_DURATION_DAYS,
        ML_REQUIRES_AUTHOR, ML_REQUIRES_PM,
        ML_SENSITIVE, ML_TRIGGERS_FEE, ML_TRIGGERS_DOC,
        ML_DESCRIPTION, ML_TEMPLATE_ACTIVE,
        ML_AUTHOR_VISIBLE, ML_STAGE_DESC,
    )
    from airtable_helpers import create_record

    # Step 1: Map service name to bundle name
    bundle = SERVICE_TO_BUNDLE.get(service_name)
    if not bundle:
        print(f"WARNING: No bundle mapping for service '{service_name}'")
        return 0

    # Step 2: Fetch matching milestone templates
    # Bundle is a multiple select field — use FIND to match
    formula = f"AND(FIND('{bundle}', ARRAYJOIN({{Bundle}})), {{Template Active}}=TRUE())"
    templates = get_records(MILESTONE_LIBRARY_TABLE, formula=formula)

    if not templates:
        print(f"WARNING: No active templates for bundle '{bundle}'")
        return 0

    # Chapters — Foundation = Full Concierge minus Launch module (seq 2190-2260)
    if service_name == "Chapters — Foundation":
        templates = [
            t for t in templates
            if not (2190 <= (t.get("fields", {}).get(ML_SEQUENCE, 0) or 0) <= 2260)
        ]

    # Sort by sequence so tasks are created in order
    templates.sort(key=lambda t: t.get("fields", {}).get(ML_SEQUENCE, 999))

    # Step 3: Create a task for each template
    created = 0

    # Sequential due dates: each task starts where the previous one ended
    # Use the provided start_date, or fall back to today
    current_date = start_date if start_date else date.today()

    # Parallel modules: get due dates but don't push the main timeline.
    # Launch runs alongside production, forking after Cover Design Approved.
    # Map: module name → sequence number it forks from
    PARALLEL_MODULES = {
        "Launch": 2110,  # Fork after Cover Design Approved (seq 2110)
    }
    parallel_date = None       # Tracks timeline within the parallel branch
    date_at_sequence = {}      # Saves current_date after each milestone for fork lookups

    for tmpl in templates:
        tf = tmpl.get("fields", {})
        duration = tf.get(ML_DURATION_DAYS, 0) or 0
        module = tf.get(ML_MODULE, "")
        sequence = tf.get(ML_SEQUENCE, 0) or 0

        if module in PARALLEL_MODULES:
            # First parallel task: branch from the fork point
            if parallel_date is None:
                fork_seq = PARALLEL_MODULES[module]
                parallel_date = date_at_sequence.get(fork_seq, current_date)
            due_date = None
            if duration:
                due_date = (parallel_date + timedelta(days=int(duration))).isoformat()
                parallel_date = parallel_date + timedelta(days=int(duration))
        else:
            # When leaving a parallel branch, resume from whichever is later
            if parallel_date is not None:
                current_date = max(current_date, parallel_date)
                parallel_date = None
            due_date = None
            if duration:
                due_date = (current_date + timedelta(days=int(duration))).isoformat()
                current_date = current_date + timedelta(days=int(duration))
            # Save checkpoint so parallel branches can fork from here
            date_at_sequence[sequence] = current_date

        task_fields = {
            TASK_NAME: tf.get(ML_NAME, ""),
            "fldj1YwlwJbfK956K": [project_id],       # TASK_PROJECT
            "fldgOATDg4qInH9ra": [tmpl.get("id")],    # TASK_MILESTONE_SOURCE
            TASK_MODULE: tf.get(ML_MODULE, ""),
            TASK_SEQUENCE: tf.get(ML_SEQUENCE, 0),
            # Bundle comes as a list from multiple select — extract first value
            "fldoUn5h7WAJF0q7m": (tf.get(ML_BUNDLE, []) or [""])[0] if isinstance(tf.get(ML_BUNDLE), list) else tf.get(ML_BUNDLE, ""),  # TASK_BUNDLE
            TASK_STATUS: "Not Started",
            TASK_AUTHOR_VISIBLE: tf.get(ML_AUTHOR_VISIBLE, False),
            TASK_STAGE_DESC: tf.get(ML_STAGE_DESC, ""),
            "fldJrY5qcKJUdfQoV": tf.get(ML_REQUIRES_AUTHOR, False),
            "fldzymeSrKFWZy1Tr": tf.get(ML_REQUIRES_PM, False),
            "fldvA06w0Z9ppcMUF": tf.get(ML_SENSITIVE, False),
            "fldqyEyzEz3QXyzkG": tf.get(ML_TRIGGERS_FEE, False),
            "fld23wm2QMjvNUAGV": tf.get(ML_TRIGGERS_DOC, False),
            "fldB74YCkAJ055mis": tf.get(ML_DESCRIPTION, ""),
        }

        if due_date:
            task_fields[TASK_DUE_DATE] = due_date

        result = create_record(TASKS_TABLE, task_fields)
        if result:
            created += 1

    return created


def create_invoice(project_id, author_id, invoice_type, amount, project_name=""):
    """
    Create an invoice record in Airtable.

    Args:
        project_id: Link to the project
        author_id: Link to the author
        invoice_type: "Deposit" or "Balance" or custom string
        amount: Dollar amount
        project_name: Used to build the invoice name

    Returns the created record, or None on error.
    """
    from airtable_helpers import create_record

    today = date.today()

    # Build a descriptive name: "Mitchell — Deposit — 2026-04-12"
    short_name = project_name.split(" — ")[0] if " — " in project_name else project_name
    invoice_name = f"{short_name} — {invoice_type} — {today.isoformat()}"

    # Due date: 14 days for deposits, 30 days for everything else
    if invoice_type == "Deposit":
        due_date = (today + timedelta(days=14)).isoformat()
    else:
        due_date = (today + timedelta(days=30)).isoformat()

    # The Invoice Type field is a singleSelect — only "Deposit" and "Balance"
    # are valid. For anything else, we skip the type and put it in the name.
    valid_types = {"Deposit", "Balance"}
    airtable_type = invoice_type if invoice_type in valid_types else None

    fields = {
        INV_NAME: invoice_name,
        INV_AMOUNT: amount,
        INV_DATE: today.isoformat(),
        INV_DUE_DATE: due_date,
        INV_PAYMENT_STATUS: "Invoice Sent",
        "fldAKLIauWoRpJGU3": [project_id],   # INV_PROJECT
    }

    if airtable_type:
        fields[INV_TYPE] = airtable_type

    if author_id:
        fields["fld1G61OGcpTuEfnA"] = [author_id]  # INV_AUTHOR

    return create_record(INVOICES_TABLE, fields)


def create_deposit_invoice(project_id):
    """
    Auto-create a deposit invoice when a project starts.
    Reads the project fee and calculates 50% (or uses the deposit amount
    if already set on the project).
    """
    project = get_record(PROJECTS_TABLE, project_id)
    if not project:
        return None

    fields = project.get("fields", {})
    project_name = fields.get(PROJ_NAME, "")

    # Get deposit amount — prefer the calculated field, fall back to 50% of fee
    deposit_amount = fields.get("fldjIDncmB6pIiPtX", 0)  # Deposit Amount field
    if not deposit_amount:
        project_fee = fields.get("fldH1ypvmL7uqN6kT", 0) or 0
        deposit_amount = project_fee * 0.5

    if deposit_amount <= 0:
        return None  # No fee set, skip

    # Get the author
    author_links = fields.get(PROJ_AUTHOR, [])
    author_id = author_links[0] if author_links else ""

    return create_invoice(project_id, author_id, "Deposit", deposit_amount, project_name)


def create_balance_invoice(project_id):
    """
    Auto-create a balance invoice when the trigger milestone completes.
    Reads the balance due from the project.
    """
    project = get_record(PROJECTS_TABLE, project_id)
    if not project:
        return None

    fields = project.get("fields", {})
    project_name = fields.get(PROJ_NAME, "")

    balance_due = fields.get("fldgximxFCWg7bmv7", 0) or 0  # Balance Due field
    if balance_due <= 0:
        return None

    author_links = fields.get(PROJ_AUTHOR, [])
    author_id = author_links[0] if author_links else ""

    return create_invoice(project_id, author_id, "Balance", balance_due, project_name)


def update_task(task_id, updates):
    """
    Update fields on a task. Used by the Command Center for
    inline status changes, due date edits, etc.

    Args:
        task_id: The task record ID
        updates: Dict of {field_id: new_value} pairs

    Returns the updated record, or None on error.
    """
    from airtable_helpers import update_record
    return update_record(TASKS_TABLE, task_id, updates)
