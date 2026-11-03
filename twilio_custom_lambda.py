"""
twilio_custom_lambda.py
Lambda: twilio-custom-send
Purpose: Send a custom SMS to one number OR bulk to all patients in an Excel file.
Runtime: Python 3.12
Layer: s3-chat-layer (needed only for Excel bulk mode)
Timeout: 5 min
Env vars: BUCKET_NAME, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, ALLOWED_ORIGIN
"""

import json
import os
import re
import base64
import urllib.request
import urllib.parse
import boto3

BUCKET_NAME    = os.environ["BUCKET_NAME"]
ACCOUNT_SID    = os.environ["TWILIO_ACCOUNT_SID"]
AUTH_TOKEN     = os.environ["TWILIO_AUTH_TOKEN"]
FROM_NUMBER    = os.environ["TWILIO_FROM_NUMBER"]
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

TWILIO_URL  = f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages.json"
CREDENTIALS = base64.b64encode(f"{ACCOUNT_SID}:{AUTH_TOKEN}".encode()).decode()

s3 = boto3.client("s3")

# ── Helpers ───────────────────────────────────────────────────────────────────
def cors(extra=None):
    h = {
        "Access-Control-Allow-Origin":  ALLOWED_ORIGIN,
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
    }
    if extra: h.update(extra)
    return h

def ok(body):
    return {"statusCode": 200, "headers": cors({"Content-Type": "application/json"}), "body": json.dumps(body)}

def err(msg, code=400):
    return {"statusCode": code, "headers": cors({"Content-Type": "application/json"}), "body": json.dumps({"message": msg})}

def normalise(raw):
    digits = re.sub(r"\D", "", str(raw or ""))
    if len(digits) == 10:               return "+1" + digits
    if len(digits) == 11 and digits[0] == "1": return "+" + digits
    return None

def twilio_send(to_number, body):
    data = urllib.parse.urlencode({"To": to_number, "From": FROM_NUMBER, "Body": body}).encode()
    req  = urllib.request.Request(TWILIO_URL, data=data, method="POST")
    req.add_header("Authorization", f"Basic {CREDENTIALS}")
    req.add_header("Content-Type",  "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return False, json.loads(e.read())

# ── Excel bulk mode (optional — used when excel_key is provided) ──────────────
def read_phones(excel_key):
    import openpyxl
    obj  = s3.get_object(Bucket=BUCKET_NAME, Key=excel_key)
    wb   = openpyxl.load_workbook(obj["Body"], read_only=True, data_only=True)
    rows = list(wb.active.iter_rows(values_only=True))
    if not rows: return []
    header = [str(c).strip().lower() if c else "" for c in rows[0]]
    def col(names):
        for n in names:
            for i, h in enumerate(header):
                if n in h: return i
        return None
    first_col  = col(["first"])
    last_col   = col(["last"])
    mobile_col = col(["mobile", "cell", "phone"])
    results = []
    for row in rows[1:]:
        if not any(row): continue
        first = str(row[first_col]  or "").strip() if first_col  is not None else ""
        last  = str(row[last_col]   or "").strip() if last_col   is not None else ""
        phone = normalise(row[mobile_col] if mobile_col is not None else None)
        if phone:
            results.append(((first + " " + last).strip() or "Patient", phone))
    return results

# ── Handler ───────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {"statusCode": 204, "headers": cors()}

    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        return err("Invalid JSON body")

    message = body.get("message", "").strip()
    if not message:
        return err("message is required")
    if len(message) > 1600:
        return err("Message too long (max 1600 characters)")

    # ── Mode 1: single number ─────────────────────────────────────────────────
    to_number = body.get("to_number", "").strip()
    if to_number:
        phone = normalise(to_number)
        if not phone:
            return err(f"Invalid phone number: {to_number}")
        success, resp = twilio_send(phone, message)
        if success:
            return ok({"message": f"✓ Message sent to {phone}"})
        error = resp.get("message", str(resp)) if isinstance(resp, dict) else str(resp)
        return err(f"Twilio error: {error}", 500)

    # ── Mode 2: bulk from Excel ───────────────────────────────────────────────
    excel_key = body.get("excel_key", "").strip()
    if not excel_key:
        return err("Provide either to_number or excel_key")

    try:
        patients = read_phones(excel_key)
    except Exception as e:
        return err(f"Could not read Excel file: {str(e)}", 500)

    if not patients:
        return err("No valid phone numbers found in the selected file")

    sent, failed = 0, []
    for name, phone in patients:
        success, resp = twilio_send(phone, message)
        if success:
            sent += 1
        else:
            failed.append({"name": name, "phone": phone,
                           "error": resp.get("message", str(resp)) if isinstance(resp, dict) else str(resp)})

    summary = f"✓ Sent to {sent} patient(s)."
    if failed:
        summary += f" {len(failed)} failed: " + ", ".join(f["name"] for f in failed)
    return ok({"message": summary, "sent": sent, "failed": failed})
