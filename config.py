"""
config.py — All Airtable table and field IDs in one place.

WHY field IDs instead of names?
Field names can be renamed in the Airtable UI and silently break your code.
Field IDs (like "fldxuqCmoKKivX72Z") never change. So we use IDs in the API
calls and give them readable names here.

All IDs verified against live base appj8IY8wQ6PhnNOi on April 8, 2026.
"""

# ============================================================
# TABLE IDs
# ============================================================

PROJECTS_TABLE = "tbl80NFeqIftRgA0O"
AUTHORS_TABLE = "tblFNE5t3G3COLOTF"
INVOICES_TABLE = "tblOlB7EL37E422aY"
MILESTONE_LIBRARY_TABLE = "tblIHtzq0wtiCoRew"
TASKS_TABLE = "tblC79tQh8tJGjA1c"
SERVICES_TABLE = "tblVc0gp3KOj4vuxi"
PORTAL_USERS_TABLE = "tbl6ny7bV34Lmjaw4"
PARTNERS_TABLE = "tblC5DXtCNBdj6oKs"
PROJECT_FILES_TABLE = "tblru3XyFKxbEjwxw"
INTERACTIONS_TABLE = "tblVu2pZdlD56Wzhg"  # CRM touchpoints (added April 14, 2026)

# ============================================================
# PORTAL USERS — Field IDs (new in Phase 1 rebuild)
# ============================================================
# Maps Supabase Auth users -> Airtable records (Author/Partner/Internal Team)

PU_EMAIL = "fld7zbTh1iU4KOBDz"              # Email (primary, singleLineText)
PU_SUPABASE_ID = "fldmmIFVor6OHiqIf"        # Supabase User ID (singleLineText)
PU_ROLE = "fldmSA9tb8Sw1T14y"               # Role (singleSelect)
PU_LINKED_AUTHOR = "fldaneBPi9GcDwTix"      # Linked Author (link to Authors)
PU_LINKED_PARTNER = "fld5DVlAzLfIcl0sd"     # Linked Partner (link to Partners)
PU_LINKED_INTERNAL = "fldybZzi8kjtYXQnD"    # Linked Internal Team (link to Internal Team)
PU_ACTIVE = "fldUWIMzseQk1tXkT"             # Active (checkbox)
PU_NOTES = "fldYGdd8bI1fWPRqU"              # Notes (multilineText)
PU_DISPLAY_NAME = "fldI0NFG7tyka9CFn"        # Display Name (singleLineText)

# ============================================================
# PROJECTS — Field IDs
# ============================================================

PROJ_NAME = "fldxuqCmoKKivX72Z"            # Project Name (singleLineText, primary field)
PROJ_AUTHOR = "fldNGhEZJuOBGv1lW"          # Author (link to Authors table)
PROJ_SERVICE = "fld1H2ygVSIr0rGRB"         # Service (singleLineText, e.g. "Full Concierge")
PROJ_START_DATE = "fldsslHHYKFHrBuFp"      # Start Date (date, YYYY-MM-DD)
PROJ_STATUS = "fld8kMFirKw4gLrPn"          # Status (singleSelect: Lead, Active, Complete, etc.)
PROJ_DEPOSIT_PAID = "fldXKN3e7lcy1Q0bd"    # Deposit Paid (checkbox)
PROJ_TASKS = "fldmSh1cp2I0uiG5m"          # Tasks (link to Tasks table)
PROJ_INVOICES = "fldL3TJWJKpNliI21"       # Invoices (link to Invoices table)

# Contract / documents — Typeflow writes the signed PDF link here
PROJ_CONTRACT_URL = "fld3myq3CnWsfSgFz"    # Google Drive PDF URL Typeflow (url)
PROJ_CONTRACT_STATUS = "fld1fEWmMnQ9hd6Qy" # Contract Status (Not Sent / Sent / Signed / Countersigned)
PROJ_CONTRACT_SENT_DATE = "fldNeo8oMJV2fM0d4"    # Contract Sent Date (date)
PROJ_CONTRACT_SIGNED_DATE = "fldZf6bL6rhcDL9qv"  # Contract Signed Date (date)

# CRM / Lead tracking fields (added April 14, 2026)
PROJ_LEAD_SOURCE = "fld3WFj0e5mA2UA4p"     # Lead Source (singleSelect)
PROJ_REFERRED_BY = "fldPM4rlSjEoBodTS"     # Referred By (singleLineText)
PROJ_BOOK_TOPIC = "fldj9BjPqq8WJsqVZ"      # Book Topic (multilineText)
PROJ_BUDGET_RANGE = "flda3DaTz7WcdEzpP"    # Budget Range (singleSelect)
PROJ_FIT_SCORE = "fldLCO9GWxfNalA9G"       # Fit Score (singleSelect: 1-5)
PROJ_NEXT_FOLLOWUP = "fldKH983LhIxKyfEN"   # Next Follow-Up (date)
PROJ_LEAD_NOTES = "fldMWVCaEfJVfAHSV"      # Lead Notes (multilineText)
PROJ_INTERACTIONS = "fld4MTfKb9K2CY8qa"    # Interactions (link to Interactions table, reverse side)

# ============================================================
# AUTHORS — Field IDs
# ============================================================

AUTHOR_NAME = "fldQ8DO7efqeIqeob"          # Author Name (singleLineText, primary field)
AUTHOR_EMAIL = "fld0IWa2rFm4KfifS"         # Email (singleLineText)
AUTHOR_PHONE = "fldsIvwmSUjICsgpB"         # Phone (singleLineText)
AUTHOR_PROJECTS = "fldMPzZN7dXsRLUXq"      # Projects (link to Projects table)
AUTHOR_INVOICES = "fldJgSAK79f9EWFYr"      # Invoices (link to Invoices table)

# ============================================================
# INVOICES — Field IDs
# ============================================================

INV_NAME = "fldfeCxe5JJebuf5G"             # Invoice Name (singleLineText, primary field)
INV_AUTHOR = "fld1G61OGcpTuEfnA"          # Author (link to Authors table)
INV_TYPE = "fldWF9L3MpHth8NFE"            # Invoice Type (singleSelect: Deposit, Balance, etc.)
INV_DATE = "fld80mNfSgdHjaFV8"            # Invoice Date (date, YYYY-MM-DD)
INV_PROJECT = "fldAKLIauWoRpJGU3"         # Project (link to Projects table)
INV_AMOUNT = "fldCYKrf1OgFMTm6u"          # Amount (currency)
INV_AMOUNT_PAID = "fldhFcw9ZGAVaODXx"     # Amount Paid (currency)
INV_OUTSTANDING = "fld3BepKlABGOdOou"     # Outstanding Balance (formula)
INV_DUE_DATE = "fldOo1ez9RxHJiYE5"        # Due Date (date)
INV_PAYMENT_STATUS = "fldXXiUe4TQxQFI2f"  # Payment Status (singleSelect)
INV_STRIPE_URL = "fldWlkirmTavD7522"      # Stripe Invoice URL (url)
INV_VOIDED = "fld0HxuwpBsAuGPYV"          # Voided (checkbox)

# ============================================================
# MILESTONE LIBRARY — Field IDs
# ============================================================

ML_NAME = "fldVv3R64CckxKv4x"              # Milestone Name (singleLineText)
ML_BUNDLE = "fldlaCzfR5ja7iRZx"            # Bundle (multipleSelect, e.g. ["Full Concierge"])
ML_MODULE = "fldCQ5KlURmNzHrLY"            # Module (singleLineText)
ML_SEQUENCE = "fldbuD55qRo6Sx8Rn"          # Sequence Order (number)
ML_DEFAULT_OWNER = "fldKaL79dEMzm2S4P"     # Default Owner (singleSelect)
ML_DURATION_DAYS = "fldPxolKU4LCJgYwN"     # Default Duration Days (number)
ML_REQUIRES_AUTHOR = "fldFlLz0G0DvkYD6V"   # Requires Author Approval (checkbox)
ML_REQUIRES_PM = "fldUYWdjPWl2JNg6B"       # Requires PM Approval (checkbox)
ML_SENSITIVE = "fld6yiexQp9rZMcg3"         # Sensitive Communication (checkbox)
ML_TRIGGERS_FEE = "fldyEoa7frPEmwc3n"      # Triggers Fee (checkbox)
ML_TRIGGERS_DOC = "fldbmHpxWuM0fDhhC"      # Triggers Document (checkbox)
ML_DESCRIPTION = "fldbJNiX0zC876U3m"        # Task Description (multilineText)
ML_TEMPLATE_ACTIVE = "fldVhaPrkLRcrw2UD"    # Template Active (checkbox)
ML_AUTHOR_VISIBLE = "fldUxyvyXJ284QtFx"     # Author Visible (checkbox)
ML_STAGE_DESC = "fldPjhNiaA0W7TjoO"        # Stage Description (multilineText)
ML_WORKFLOW_STAGE = "fldBGeDR8Z2DCY3tt"     # Workflow Stage (singleSelect) — partner cascade key

# ============================================================
# TASKS — Field IDs
# ============================================================

TASK_NAME = "fldmRze6fg15y8HtV"             # Task Name (singleLineText)
TASK_PROJECT = "fldj1YwlwJbfK956K"         # Project (link to Projects table)
TASK_MILESTONE_SOURCE = "fldgOATDg4qInH9ra" # Milestone Library (link — traces back to template)
TASK_MODULE = "fldNOnRqAuQlXRLEt"          # Module (singleLineText)
TASK_SEQUENCE = "fldtyvvJzWoGu68ie"        # Sequence Order (number)
TASK_BUNDLE = "fldoUn5h7WAJF0q7m"          # Bundle (singleSelect)
TASK_STATUS = "flduGjVdvDWAsmTdq"          # Status (singleSelect)
TASK_DUE_DATE = "flda3RT448yzLEWaV"         # Due Date (date)
TASK_COMPLETED_DATE = "fldFR28GxPlXzTftS"   # Completed Date (date)
TASK_REQUIRES_AUTHOR = "fldJrY5qcKJUdfQoV" # Requires Author Approval (checkbox)
TASK_REQUIRES_PM = "fldzymeSrKFWZy1Tr"     # Requires PM Approval (checkbox)
TASK_SENSITIVE = "fldvA06w0Z9ppcMUF"        # Sensitive Communication (checkbox)
TASK_TRIGGERS_FEE = "fldqyEyzEz3QXyzkG"    # Triggers Fee (checkbox)
TASK_TRIGGERS_DOC = "fld23wm2QMjvNUAGV"    # Triggers Document (checkbox)
TASK_INSTRUCTIONS = "fldB74YCkAJ055mis"     # Instructions (multilineText)
TASK_AUTHOR_VISIBLE = "fldujWJJl0rB9jnXq"  # Author Visible (checkbox)
TASK_STAGE_DESC = "fldQBQZxYI7kDr6Qd"      # Stage Description (multilineText)
TASK_ASSIGNED_PARTNER = "fldrcTUeG3ZYIrvsJ" # Assigned Partner (link to Partners table)
TASK_WORKFLOW_STAGE = "fldS0YCvUy0AEVRLb"   # Workflow Stage (singleSelect) — partner cascade key

# Auto-PM stages: tasks in these stages skip the partner-cascade logic because
# the assignee is always the project's PM (Julie today). Keep in sync with the
# stages where Default Owner = "Primary PM" on Milestone Library.
AUTO_PM_STAGES = {
    "Discovery", "Onboarding", "Story Development", "CX",
    "Ebook Distribution", "Project Closeout", "Navigator Handoff",
    "DTC Funnel Handoff", "ISBN",
}

# ============================================================
# PARTNERS — Field IDs
# ============================================================

PARTNER_NAME = "fldgA3QXhaIxptkTc"          # Partner Name (singleLineText, primary field)
PARTNER_PREFERRED_NAME = "fldbnkRwfYSesJByY" # Preferred Name (singleLineText)
PARTNER_TYPE = "fldcwyrXcWBGwh6QR"          # Partner Type (singleSelect: Task Partner, Channel Partner)
PARTNER_EMAIL = "fldCg0ghQu5dkDOnY"         # Email (singleLineText)
PARTNER_SPECIALTIES = "fldoDXfhqVd2kd7IY"   # Specialties (multipleSelects)
PARTNER_HOURLY_RATE = "fldIpoHz9Pnn02h4M"   # Hourly Rate (currency)
PARTNER_PORTFOLIO = "fldlUT4yPKpu7Nb3l"     # Portfolio URL (url)
PARTNER_STATUS = "fldGM7ZRk1QqtUlgL"        # Status (singleSelect: Active, Inactive)
PARTNER_BIO = "fld0O98uUqaWfrzSd"           # Bio / Notes (multilineText)
PARTNER_NOTES = "fldWGVlB37Tm3yywb"         # Notes (multilineText)
PARTNER_TASKS = "fldW47MRkQk9FOhtB"         # Tasks (link to Tasks — reverse of assigned partner)
PARTNER_PROJECTS = "fldJudaNkeCczs7Oh"       # Projects (link to Projects — used by Channel Partners)
PARTNER_DISBURSEMENTS = "fldW7EgDPZBeGpAZ2"  # Disbursements (link to Disbursements)

# ============================================================
# PROJECT FILES — Field IDs (created April 12, 2026)
# ============================================================
# Every file upload is a row. Version history = multiple rows for the same task.

PF_FILE_NAME = "fldiGlEFDC3qyVSlX"        # File Name (singleLineText, primary)
PF_FILE = "fldA8Gix4LZmnxpN4"             # File (attachment)
PF_PROJECT = "fldpwfReXoCLCgGLM"           # Project (link to Projects)
PF_TASK = "fld0HkpPP95sPTiQX"             # Task (link to Tasks)
PF_VERSION = "fldxdCYY9r96M6nQz"           # Version (number)
PF_FILE_TYPE = "fld158UT0mSyGCwRq"         # File Type (singleSelect)
PF_UPLOADED_BY = "flddx9TnGVFiR3DmL"       # Uploaded By (singleLineText)
PF_UPLOAD_DATE = "fldwVDaYoCsjXLig2"        # Upload Date (date)
PF_NOTES = "fldLpRj4iJ2xrnUWr"             # Notes (multilineText)
PF_DIRECTION = "fldO5dA0A4xg3pt3y"          # Direction (singleSelect: To Partner, From Partner, Author Review)

# ============================================================
# DISBURSEMENTS — Field IDs (partner/vendor payments)
# ============================================================
# Tracks money going OUT — payments to partners, vendors, referral fees.

DISBURSEMENTS_TABLE = "tblpv5XXX4p1EO9GT"

DISB_NAME = "fldTgKvLWY5ONFLBu"              # Disbursement Name (primary)
DISB_PARTNER = "fldTTF8euDVhUdPpt"            # Partners (link to Partners)
DISB_TYPE = "fld8dSYo5B8CIKyDV"              # Disbursement Type (singleSelect)
DISB_RECIPIENT_TYPE = "fldRQPIeJoDqD90vv"     # Recipient Type (singleSelect)
DISB_PROJECT = "fldx4HlhuoiqmGDDI"           # Project (link to Projects)
DISB_TASK = "fldRSrGuNF6uEYSwI"              # Related Task (link to Tasks)
DISB_REFERRAL = "fldLsQIFVWLlNgx3U"          # Referral (link to Referrals)
DISB_AMOUNT_REQUESTED = "fld6ukQWYo4BYjYbo"  # Amount Requested (currency)
DISB_AMOUNT_PAID = "fldsCNwLFVvG9OORg"        # Amount Paid (currency)
DISB_REQUESTED_DATE = "fldirBKY1y7DCXWiU"     # Requested Date (date)
DISB_PAID_DATE = "fldOClVVJQvSjaZrp"          # Paid Date (date)
DISB_PAYMENT_STATUS = "fldVJVW7YUZvaNox1"     # Payment Status (singleSelect)
DISB_PAYMENT_METHOD = "fldrGm3LL9lIHK0vj"     # Payment Method (singleSelect)
DISB_PAYMENT_REF = "fld8uL2CnRbVpnxMa"       # Payment Reference (singleLineText)
DISB_NOTES = "fldffERNmN5WZVuJy"              # Notes (multilineText)

# Link field on Projects table pointing to Disbursements
PROJ_DISBURSEMENTS = "fldcTAMpW6UHzTvBq"

# ============================================================
# INTERACTIONS — CRM touchpoints (calls, emails, meetings, notes)
# ============================================================

INT_NAME = "fldOk6k5B2SADb595"            # Name (singleLineText, primary — auto-built like "2026-04-14 Call — Smith")
INT_PROJECT = "fldVbdkPYevS5rOVC"         # Project (link to Projects)
INT_DATE = "fldlQGIo8ZPi6eYNb"            # Date (date)
INT_TYPE = "fld5ALKnrM5jowSRZ"            # Type (singleSelect: Call, Email, Meeting, Text, Note)
INT_DIRECTION = "fldytJA9TpQJycFXD"       # Direction (singleSelect: Inbound, Outbound, N/A)
INT_SUMMARY = "fldmfjDX8MyRiaqgY"         # Summary (multilineText)
INT_LOGGED_BY = "fldk3HjzMM9QbvbLW"       # Logged By (singleLineText)

# ============================================================
# TYPEFLOW — Document generation & e-signatures
# ============================================================
# Each "flow" is a template in Typeflow. When triggered via API,
# Typeflow generates the document from Airtable data, sends it
# for e-signature, and saves the signed PDF back to Airtable.

TYPEFLOW_API_URL = "https://app.typeflow.us/api/generate-doc"

# SOW (Statement of Work) — lives on the Projects table
# One SOW per project, scoped to a specific service.
TYPEFLOW_SOW_FLOW_ID = "1ef0aec99c5f42b1b6f3b09052e93d8a"
TYPEFLOW_SOW_TABLE_ID = PROJECTS_TABLE  # tbl80NFeqIftRgA0O

# MSA (Master Service Agreement) — lives on Authors or Partners table
# One MSA per author/partner relationship.
TYPEFLOW_MSA_FLOW_ID = "33bbd513db99493ab3d2ec01566fead3"
# MSA can go to either Authors or Partners (Channel Partners),
# so the table ID is passed dynamically based on who we're sending to.

# ============================================================
# SERVICE-TO-BUNDLE MAPPING
# ============================================================
# The Service field on Projects is plain text (e.g. "Full Concierge").
# The Bundle field on Milestone Library is a select with specific names.
# This mapping translates between them.

SERVICE_TO_BUNDLE = {
    # Publishing packages
    "Full Concierge": "Full Concierge",
    "Chapters — Signature": "Full Concierge",          # Same milestones as FC
    "Chapters — Foundation": "Full Concierge",          # Same as FC minus Launch module (code filters)
    "Publish-Ready Concierge": "Publish-Ready Concierge",
    "Publish Ready Concierge": "Publish-Ready Concierge",
    "Children's Book Concierge": "Children's Book Concierge",

    # Consulting & marketing
    "Navigator": "Navigator",
    "Launch Buddy": "Launch Buddy",
    "DTC Funnel": "DTC Funnel",

    # Add-on services (loaded as separate service on project)
    "AI Edition": "AI Edition",
    "Audiobook": "Audiobook",
    "Ebook Edition": "Ebook Edition",
    "CX Bundle": "CX Bundle",

    # Add-ons (standalone)
    "Illustration": "Illustration",
    "Indexing": "Indexing",
    "Photo Editing": "Photo Editing",
    "Sensitivity Read": "Sensitivity Read",
}
