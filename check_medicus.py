import http.cookiejar
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
FORM = {
    "action": "medicus_slots",
    "doc_id": "580",
    "idx_lekarza": "107",
    "idx_wariantu": "1514",
    "lang": "pl",
}

# Test doctor to see if it works.
# FORM = {
#     "action": "medicus_slots",
#     "nonce": "b062807f06",
#     "doc_id": "1293",
#     "idx_lekarza": "302",
#     "idx_wariantu": "3197",
#     "lang": "pl",
# }

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

# Keep cookies between loading the registration page
# and calling the AJAX endpoint.
cookie_jar = http.cookiejar.CookieJar()

opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cookie_jar)
)


# ---------------------------------------------------------
# Fetch Gawron's page and find the current nonce
# ---------------------------------------------------------

page_request = urllib.request.Request(
    BOOKING_URL,
    headers=HEADERS,
)

with opener.open(page_request, timeout=15) as response:
    page_html = response.read().decode("utf-8")

nonce_patterns = [
    r'["\'][^"\']*nonce[^"\']*["\']\s*:\s*["\']([a-f0-9]{10})["\']',
    r'data-nonce\s*=\s*["\']([a-f0-9]{10})["\']',
    r'\bnonce\s*[:=]\s*["\']([a-f0-9]{10})["\']',
]

nonce_candidates = []

for pattern in nonce_patterns:
    for nonce in re.findall(pattern, page_html, re.IGNORECASE):
        if nonce not in nonce_candidates:
            nonce_candidates.append(nonce)

if not nonce_candidates:
    raise RuntimeError("Could not find a nonce on the Medicus page.")

print(f"Found {len(nonce_candidates)} nonce candidate(s).")


# ---------------------------------------------------------
# Find which nonce Medicus accepts
# ---------------------------------------------------------

result = None

for nonce in nonce_candidates:
    form = {
        **FORM,
        "nonce": nonce,
    }

    request = urllib.request.Request(
        URL,
        data=urllib.parse.urlencode(form).encode(),
        headers={
            **HEADERS,
            "Referer": BOOKING_URL,
        },
    )

    with opener.open(request, timeout=15) as response:
        candidate_result = json.load(response)

    if candidate_result.get("success"):
        result = candidate_result
        print(f"Valid nonce found: {nonce}")
        break

    print(f"Nonce rejected: {nonce}")

if result is None:
    raise RuntimeError(
        "Found nonce candidates, but Medicus rejected all of them."
    )


# ---------------------------------------------------------
# Validate availability
# ---------------------------------------------------------

print("Medicus response:", result)

if not result["data"]["has_slots"]:
    print("No available slots.")
    exit()

print("SLOT AVAILABLE!")


# ---------------------------------------------------------
# Extract available dates and times
# ---------------------------------------------------------

timeslots_html = result["data"]["timeslots"]

slots = re.findall(
    r'data-date="([^"]+)" data-time="([^"]+)"',
    timeslots_html,
)

slots_text = "\n".join(
    f"{date} at {time[:5]}"
    for date, time in slots
)


# ---------------------------------------------------------
# Build email
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Send email
# ---------------------------------------------------------

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(
        os.environ["EMAIL"],
        os.environ["EMAIL_APP_PASSWORD"],
    )
    smtp.send_message(msg)

print("Email sent.")
