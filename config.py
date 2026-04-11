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

# ============================================================
# AUTHORS — Field IDs
# ============================================================

AUTHOR_NAME = "fldQ8DO7efqeIqeob"          # Author Name (singleLineText, primary field)
AUTHOR_EMAIL = "fld0IWa2rFm4KfifS"         # Email (singleLineText)
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
ML_BUNDLE = "fldlaCzfR5ja7iRZx"            # Bundle (singleSelect, e.g. "Full Concierge")
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

# ============================================================
# SERVICE-TO-BUNDLE MAPPING
# ============================================================
# The Service field on Projects is plain text (e.g. "Full Concierge").
# The Bundle field on Milestone Library is a select with specific names.
# This mapping translates between them.

SERVICE_TO_BUNDLE = {
    # Direct P&P services
    "Full Concierge": "Full Concierge",
    "Full Concierge - Children's Book": "Full Concierge - Children's Book",
    "Publish-Ready Concierge": "Publish-Ready Concierge",
    "Publish Ready Concierge": "Publish-Ready Concierge",
    "Publishing Strategy Session": "Publishing Strategy Session",
    "Navigator AI": "Navigator AI",
    "Navigator": "Navigator AI",
    "Launch Buddy AI": "Launch Buddy AI",
    "Launch Buddy": "Launch Buddy AI",
    "DTC Funnel": "DTC Funnel",
    "Platform Studio": "Platform Studio",
    "AI Edition": "AI Edition",
    "Ebook Edition": "Ebook Edition",

    # Chapters services — map to the appropriate bundle
    "Chapters — Foundation": "Full Concierge",
    "Chapters — Signature": "Full Concierge",
    "Chapters — Audiobook Production": "Full Concierge",
    "Chapters — Launch Buddy": "Launch Buddy AI",
    "Chapters — Full Launch Package": "Full Concierge",
    "Chapters — AI Edition Chatbot": "AI Edition",
}
