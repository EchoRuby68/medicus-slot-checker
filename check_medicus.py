import json
import os
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage

URL = "https://medicus.com.pl/wp-admin/admin-ajax.php"

FORM = {
    "action": "medicus_slots",
    "nonce": "040b56546a",
    "doc_id": "580",
    "idx_lekarza": "107",
    "idx_wariantu": "1514",
    "lang": "pl",
}

request = urllib.request.Request(
    URL,
    data=urllib.parse.urlencode(FORM).encode(),
    headers={"User-Agent": "Mozilla/5.0"},
)

with urllib.request.urlopen(request, timeout=15) as response:
    result = json.load(response)

print("Medicus response:", result)

if not result.get("success"):
    raise RuntimeError("Medicus returned success=false")

if not result["data"]["has_slots"]:
    print("No available slots.")
    exit()

print("SLOT AVAILABLE!")

msg = EmailMessage()
msg["Subject"] = "🚨 Gawron appointment available at Medicus"
msg["From"] = os.environ["EMAIL"]
msg["To"] = os.environ["EMAIL"]
msg.set_content(
    "A slot for Gawron is available at Medicus.\n\n"
    "Check Medicus immediately.\n\n"
    + result["data"]["alert"]
)

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(
        os.environ["EMAIL"],
        os.environ["EMAIL_APP_PASSWORD"],
    )
    smtp.send_message(msg)

print("Email sent.")
