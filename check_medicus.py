import json
import os
import re
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage

URL = "https://medicus.com.pl/wp-admin/admin-ajax.php"

BOOKING_URL = (
    "https://medicus.com.pl/rejestracja/"
    "?search=Dr%20hab.%20n.%20med.%20Wojciech%20Gawron"
)

# Gawron himself.
# FORM = {
#     "action": "medicus_slots",
#     "nonce": "040b56546a",
#     "doc_id": "580",
#     "idx_lekarza": "107",
#     "idx_wariantu": "1514",
#     "lang": "pl",
# }

# Test doctor to see if it works.
FORM = {
    "action": "medicus_slots",
    "nonce": "b062807f06",
    "doc_id": "1293",
    "idx_lekarza": "302",
    "idx_wariantu": "3197",
    "lang": "pl",
}

# Call Medicus
request = urllib.request.Request(
    URL,
    data=urllib.parse.urlencode(FORM).encode(),
    headers={"User-Agent": "Mozilla/5.0"},
)

with urllib.request.urlopen(request, timeout=15) as response:
    result = json.load(response)

print("Medicus response:", result)

# Validate response
if not result.get("success"):
    raise RuntimeError("Medicus returned success=false")

# Nothing available
if not result["data"]["has_slots"]:
    print("No available slots.")
    exit()

print("SLOT AVAILABLE!")

# Extract available dates and times
timeslots_html = result["data"]["timeslots"]

slots = re.findall(
    r'data-date="([^"]+)" data-time="([^"]+)"',
    timeslots_html,
)

slots_text = "\n".join(
    f"{date} at {time[:5]}"
    for date, time in slots
)

# Build email
msg = EmailMessage()

msg["Subject"] = "🚨 Gawron appointment available at Medicus"
msg["From"] = os.environ["EMAIL"]
msg["To"] = os.environ["EMAIL_DESTINATION"]

msg.set_content(
    f"""Gawron has available appointments at Medicus.

AVAILABLE SLOTS:

{slots_text}

BOOK HERE:
{BOOKING_URL}

Book quickly. The available slots may disappear.
"""
)

# Send email
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(
        os.environ["EMAIL"],
        os.environ["EMAIL_APP_PASSWORD"],
    )
    smtp.send_message(msg)

print("Email sent.")
