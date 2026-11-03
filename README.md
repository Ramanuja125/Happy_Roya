# Roya Health AI Platform — Happy Kids Pediatrics
### Full Architecture & Documentation

> **How to use this file:** Each major feature has its own clearly labelled section. When something new is added, scroll to the relevant section and add to it — no need to rewrite anything else. The Table of Contents links to every section.

---

## Table of Contents

1. [What Is This?](#what-is-this)
2. [Feature List](#feature-list)
3. [Tech Stack](#tech-stack)
4. [System Architecture](#system-architecture)
5. [User Journey](#user-journey)
6. [How the AI Works](#how-the-ai-works)
7. [SMS Bill Reminder System](#sms-bill-reminder-system)
8. [AWS Setup — Auth & File Chat](#aws-setup--auth--file-chat)
9. [AWS Setup — SMS System](#aws-setup--sms-system)
10. [Firebase & EmailJS Setup](#firebase--emailjs-setup)
11. [Hosting & Subdomain Setup](#hosting--subdomain-setup)
12. [File Structure](#file-structure)
13. [Branding & UI](#branding--ui)
14. [Security Architecture](#security-architecture)
15. [How to Change Things](#how-to-change-things)

---

## What Is This?

The **Roya Health AI Platform** is a HIPAA-conscious, two-factor authenticated staff portal built specifically for Happy Kids Pediatrics. It is hosted on a subdomain of `kanikayears.com` at:

> **https://HappyRoya.kanikayears.com**

After logging in with email, password, and a one-time code sent to their inbox, staff can:

- **Upload** new patient files (Excel, PDF, Word, CSV) to secure cloud storage
- **Browse** files already in storage and load them instantly
- **Chat with files** using AI — ask questions about patient records across one or many files at once
- **Send SMS bill reminders** to patients directly from a patient Excel file — and receive two-way AI-powered replies

No backend server. No managed database for the web app. No AI framework. Everything runs on managed cloud services stitched together with clean, minimal code.

---

## Feature List

| # | Feature | How |
|---|---------|-----|
| 1 | User registration with email + password | Firebase Authentication |
| 2 | Email verification on sign-up | Firebase built-in |
| 3 | Two-factor login (password + OTP) | Firebase + EmailJS |
| 4 | Password reset via email | Firebase built-in |
| 5 | Secure session management | Browser sessionStorage |
| 6 | Mode selection — Upload or Load Stored | Vanilla JavaScript |
| 7 | Multi-file upload to AWS S3 | Pre-signed POST URLs via Lambda |
| 8 | Drag-and-drop file upload UI | Vanilla JavaScript |
| 9 | Load stored files with checkboxes | Lambda list_files + S3 list_objects_v2 |
| 10 | AI chat — Per File tab | s3-chat Lambda + OpenRouter + GPT-5.5 |
| 11 | Auto file summary when chat opens | Same Lambda, auto-triggered |
| 12 | Per-file independent conversation history | Browser memory (JavaScript) |
| 13 | Ask All Files — Combined Answer | All files merged in one Lambda call |
| 14 | Ask All Files — Ask Each File | Parallel per-file Lambda calls |
| 15 | Speech-to-text mic button | Browser Web Speech API |
| 16 | API key never exposed to browser | Lambda environment variable only |
| 17 | SMS bill reminders to patients | AWS End User Messaging via sms-send Lambda |
| 18 | Two-way SMS — AI replies to patient responses | sms-reply Lambda + GPT-5.5 |
| 19 | SMS Reminders tab in portal UI | dashboard.html SMS tab → s3-chat trigger_sms action |
| 20 | View patient replies in portal | dashboard.html → s3-chat get_sms_conversations → DynamoDB |
| 21 | Strict AI guardrails on SMS replies | Whitelist system prompt — redirects unknown questions to practice phone |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Hosting | GitHub Pages (via GoDaddy subdomain) | Serves all HTML/CSS/JS |
| Subdomain | `HappyRoya.kanikayears.com` (GoDaddy DNS) | Custom domain pointing to GitHub Pages |
| Authentication | Firebase Auth | Stores and verifies email + hashed password |
| OTP Delivery | EmailJS | Sends 6-digit code to user's inbox |
| Email Transport | Gmail SMTP (via EmailJS) | Actual email delivery |
| Upload backend | AWS Lambda — `s3-upload-lambda` (Python 3.12) | Generates temporary S3 upload permissions |
| Chat + List backend | AWS Lambda — `s3-chat` (Python 3.12) | Reads files, extracts text, lists bucket, calls AI, triggers SMS, reads SMS conversations |
| SMS sending | AWS Lambda — `sms-send` (Python 3.12) | Reads patient Excel, sends bill reminder SMS to each patient |
| SMS replies | AWS Lambda — `sms-reply` (Python 3.12) | Handles inbound patient SMS, calls GPT-5.5, sends AI reply |
| SMS routing | Amazon SNS | Routes inbound SMS from End User Messaging to sms-reply Lambda |
| SMS service | AWS End User Messaging (`pinpoint-sms-voice-v2`) | Two-way SMS — send and receive |
| SMS phone number | Toll-free number `+18557684735` | Registered in AWS End User Messaging |
| Conversation state | AWS DynamoDB — `sms-conversations` | Stores per-patient SMS conversation history |
| Python packages | AWS Lambda Layer — `s3-chat-layer` | openpyxl, pypdf, python-docx, xlrd |
| API layer | AWS API Gateway (HTTP API) | HTTPS endpoints for upload and chat |
| File storage | AWS S3 | All uploaded files stored under `uploads/` prefix |
| AI model | GPT-5.5 via OpenRouter | File chat + SMS reply AI |
| Voice input | Browser Web Speech API | Speech-to-text, built into Chrome/Edge |
| Frontend | HTML, CSS, Vanilla JS | All UI and browser-side logic |

---

## System Architecture

```
                  +------------------------------------------+
                  |            GitHub Pages                  |
                  |    HappyRoya.kanikayears.com             |
                  |                                          |
                  |  index.html      --> verify.html         |
                  |  register.html                           |
                  |  forgot-password.html                    |
                  |  dashboard.html  <-- main page after     |
                  |    Tab 1: Per File Chat                  |
                  |    Tab 2: Ask All Files                  |
                  |    Tab 3: SMS Reminders                  |
                  +-----+-----------------------------+------+
                        |                             |
          +-------------+----------+   +--------------+----------------------+
          |  Firebase + EmailJS    |   |  AWS API Gateway (HTTP API)         |
          |                        |   |  aoqop7lkph.execute-api.us-east-2   |
          |  - Auth (login/signup) |   |                                     |
          |  - OTP (email)         |   |  POST /get-upload-url               |
          |  - Password reset      |   |  POST /chat  (all actions)          |
          +------------------------+   +----+--------------------+-----------+
                                            |                    |
                               +------------+------+  +----------+----------+
                               |  s3-upload-lambda |  |  s3-chat Lambda     |
                               |                   |  |                     |
                               |  Generates        |  |  - list_files       |
                               |  pre-signed       |  |  - single file chat |
                               |  POST URL         |  |  - combined chat    |
                               +------------+------+  |  - trigger_sms      |
                                            |         |  - get_sms_convs    |
                                            |         +----+--------+--------+
                                            |              |        |
                               +------------+--------------+--+     |
                               |         AWS S3               |     |
                               |  uploads/*.xlsx, *.pdf etc   |     |
                               +------------------------------+     |
                                                                    |
                                              +---------------------+--------+
                                              |      sms-send Lambda         |
                                              |  Reads patient Excel from S3 |
                                              |  Sends bill reminder per row |
                                              +---------------------+--------+
                                                                    |
                                              +---------------------+--------+
                                              |  AWS End User Messaging      |
                                              |  Toll-free: +18557684735     |
                                              |  Two-way SMS                 |
                                              +---+---------+----------------+
                                                  |         |
                                          Outbound|         |Inbound replies
                                                  |         |
                                            Patient Phone   |
                                                            |
                                              +-------------+---------+
                                              |  Amazon SNS           |
                                              |  sms-inbound-replies  |
                                              +-------------+---------+
                                                            |
                                              +-------------+---------+
                                              |  sms-reply Lambda     |
                                              |  GPT-5.5 via OpenRtr  |
                                              |  Saves to DynamoDB    |
                                              +-------------+---------+
                                                            |
                                              +-------------+---------+
                                              |  DynamoDB             |
                                              |  sms-conversations    |
                                              |  (one row per patient)|
                                              +-----------------------+
```

---

## User Journey

### Step 1 — Login with Two Factors

```
index.html
  Staff enters email + password
  → Firebase checks the password
  → JavaScript generates a random 6-digit OTP, stores it in browser tab only
  → EmailJS sends the code to the user's email via Gmail SMTP
  → User goes to verify.html

verify.html
  Staff types the 6-digit code
  → Browser checks: does it match? Is it within 10 minutes?
  → Yes: session saved, user goes to dashboard.html
  → No: user must log in again
```

**Non-technical:** It's a double lock. Your password is the first key. A one-time code sent to your email is the second key. Even if someone steals your password, they can't get in without also accessing your email inbox.

---

### Step 2 — Upload or Load Files

**Upload Files** — choose files from your computer. Supports Excel (.xlsx, .xls), PDF, Word (.docx), CSV, TXT. Multiple files at once with drag-and-drop.

**Load Stored Files** — browse every file already in S3 as a scrollable checklist with file size and upload date. Select any combination and click Load.

Both modes feed into the same chat interface. You can mix both in one session.

---

### Step 3 — Chat With Your Files

#### Per File Chat
Select one file. The AI automatically summarises it, then you ask follow-up questions. Conversation history is remembered per file independently throughout your session.

#### Ask All Files
- **Combined Answer** — all files merged into one AI call. Best for cross-file questions like totals or trends.
- **Ask Each File** — same question sent to every file in parallel. Best for side-by-side comparisons.

#### Voice Input
Every question box has a mic button. Click, speak, and it types itself. Uses the browser's built-in speech recognition — no external service or microphone permission beyond the browser.

---

### Step 4 — SMS Bill Reminders

The SMS Reminders tab (third tab in the chat section):

1. Load your patient Excel file from S3 (Load Stored Files)
2. Switch to the SMS Reminders tab — the Excel file auto-populates the dropdown
3. Click **Send Reminders** → each patient gets a personalised text:
   > *"Hi John Smith, you have an outstanding bill amount due of $150.00. Call 480-776-3790 at your convenience. Reply STOP to opt out."*
4. Patients who reply get an instant AI response (GPT-5.5)
5. Click **↻ Refresh** to see all patient replies in the table

---

## How the AI Works

### File Chat — Three Steps, No Framework

```
1. boto3 s3.get_object()    → download file bytes from S3
2. extract_text()           → parse file to plain text
3. call_openrouter()        → send text + question to GPT-5.5, return answer
```

No LangChain, AutoGen, or AI agents framework. The intelligence comes entirely from GPT-5.5. The Lambda is the plumbing.

### File Text Extraction

| File Type | Library | Notes |
|-----------|---------|-------|
| `.xlsx` | openpyxl | Pure Python, reads modern Excel format |
| `.xls` | xlrd | Fallback for old Excel 97–2003 binary format |
| `.pdf` | pypdf | Pure Python. pdfplumber tried first but has compiled C extensions that fail on Lambda |
| `.docx` | python-docx | Reads Word document XML |
| `.csv` / `.txt` | built-in | Decode bytes as UTF-8 |

Context limits: single file 60,000 chars. Combined mode 120,000 chars total split equally across files.

### Multi-Turn Conversation

Full conversation history is re-sent with every message. The model itself is stateless — context is rebuilt on each call. History lives in browser memory per file for the duration of the session.

### API Key Security

```
Browser → API Gateway → s3-chat Lambda → OpenRouter (key stored here only)
```

The OpenRouter key is a Lambda environment variable. It never appears in any HTML, JS, or GitHub file, and never touches the browser.

---

## SMS Bill Reminder System

### Overview

Two-way SMS using AWS End User Messaging (the AWS successor to Pinpoint SMS, supported beyond Oct 2026).

- **Outbound:** portal triggers `sms-send` Lambda → reads patient Excel → sends personalised bill reminder to each mobile number
- **Inbound:** patient replies → End User Messaging → SNS → `sms-reply` Lambda → GPT-5.5 generates a guardrailed response → sends reply back to patient

### Patient Excel Format

The Excel file uploaded to S3 must have these column headers:

| First Name | Last Name | Middle Name | DOB | Gender | DOS | Amount Due | Mobile Number | HomeNumber | Email |
|------------|-----------|-------------|-----|--------|-----|------------|---------------|------------|-------|

Mobile Number can be `4805551234`, `(480) 555-1234`, or `+14805551234` — the Lambda normalises all formats automatically.

### DynamoDB — One Row Per Patient

Table: `sms-conversations` | Partition key: `phone_number` (String)

Each patient has exactly one row:

| Field | Content |
|-------|---------|
| `phone_number` | `+14805551234` (partition key) |
| `patient_name` | `John Smith` |
| `amount_due` | `150.00` |
| `last_outbound_message` | The bill reminder text we sent |
| `conversation_history` | Full JSON array of all messages |
| `opt_out` | `true` / `false` |

When a patient replies, the Lambda loads their row, appends the new exchange to `conversation_history`, and saves it back. 10 patients = 10 rows, fully independent.

### AI Guardrails on SMS Replies

The `sms-reply` Lambda uses a **whitelist system prompt** — GPT-5.5 can only answer from facts explicitly given to it. Anything outside that list redirects to the practice phone number. It is explicitly banned from speculating, guessing, or using phrases like "I believe" or "probably."

**What it knows:**
- Patient's own balance (from DynamoDB)
- Saturday hours: Chandler location 8 AM–12 Noon
- Practice phone: 480-776-3790

**For everything else:** *"For more information, please call us at 480-776-3790."*

**To add more facts the AI can answer** (e.g. weekday hours, payment methods, other locations): open `sms_reply_lambda.py`, add the new facts under the `FACTS YOU ARE ALLOWED TO SHARE` section in `SYSTEM_PROMPT`, paste into the `sms-reply` Lambda, click Deploy. No code changes needed.

### How the UI Connects to SMS

The SMS tab in `dashboard.html` uses the **existing `/chat` API endpoint** — no new API Gateway routes needed:

| UI Action | Calls | Lambda handles via |
|-----------|-------|--------------------|
| Send Reminders | `POST /chat` `{ action: "trigger_sms" }` | s3-chat invokes sms-send async |
| ↻ Refresh replies | `POST /chat` `{ action: "get_sms_conversations" }` | s3-chat reads DynamoDB |

The `trigger_sms` action uses `InvocationType='Event'` (fire and forget) — the API returns instantly and sms-send runs in the background for as long as needed.

---

## AWS Setup — Auth & File Chat

### Resources

| AWS Resource | Name | Purpose |
|-------------|------|---------|
| S3 Bucket | `emr-lab-bucket-699092321120-us-east-2-an` | All uploaded files under `uploads/` prefix |
| Lambda | `s3-upload-lambda` | Generates pre-signed upload URLs |
| Lambda | `s3-chat` | Chat, file listing, combined queries, SMS trigger, SMS conversations |
| Lambda Layer | `s3-chat-layer` | openpyxl, pypdf, python-docx, xlrd |
| API Gateway | HTTP API | `aoqop7lkph.execute-api.us-east-2.amazonaws.com` |
| IAM Role | `s3-upload-lambda-role` | Permissions for both file Lambdas |

### S3 Bucket CORS Policy

The CORS policy must list the subdomain so browsers allow cross-origin requests from the portal:

```json
[{
  "AllowedHeaders": ["*"],
  "AllowedMethods": ["PUT", "POST"],
  "AllowedOrigins": ["https://HappyRoya.kanikayears.com"],
  "ExposeHeaders": ["ETag"],
  "MaxAgeSeconds": 3000
}]
```

> If you also want the old `kanikayears.com` path to keep working, add it as a second object in the array.

### IAM Role — `s3-upload-lambda-role`

All policies are attached to this one role. Both file Lambdas use it.

**Inline Policy — `s3-put-emr-lab-bucket`**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::emr-lab-bucket-699092321120-us-east-2-an/*"
  }]
}
```

**Inline Policy — `s3-read-list-emr-lab-bucket`**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::emr-lab-bucket-699092321120-us-east-2-an/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::emr-lab-bucket-699092321120-us-east-2-an"
    }
  ]
}
```

> Note: `s3:GetObject` uses `/*` (targets objects inside the bucket). `s3:ListBucket` uses no `/*` (targets the bucket itself). Both are required. Missing `s3:ListBucket` causes Load Stored Files to fail with a 500 error even though upload and chat work fine.

**AWS Managed Policy:** `AmazonDynamoDBFullAccess`

**Inline Policy — `Invoke_function`** (allows s3-chat to trigger sms-send)
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "lambda:InvokeFunction",
    "Resource": "arn:aws:lambda:us-east-2:699092321120:function:sms-send"
  }]
}
```

### Lambda Layer (s3-chat-layer)

Built in AWS CloudShell — must use CloudShell because Lambda runs Amazon Linux Python 3.12, and packages with compiled C extensions must be built on a matching OS:

```bash
mkdir python
pip install openpyxl pypdf python-docx xlrd -t python/ --quiet
zip -r layer.zip python/
aws lambda publish-layer-version \
  --layer-name s3-chat-layer \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.12
```

### Lambda Functions — File Chat

**`s3-upload-lambda`** (`lambda_function.py`)
- Runtime: Python 3.12 | Role: `s3-upload-lambda-role` | Timeout: 30s
- Env vars: `BUCKET_NAME`, `BUCKET_REGION`, `ALLOWED_ORIGIN`
- Files stored at `uploads/<filename>` (not bucket root)

**`s3-chat`** (`chat_lambda_function.py`)
- Runtime: Python 3.12 | Role: `s3-upload-lambda-role` | Layer: `s3-chat-layer` | Timeout: 5 min
- Env vars:

| Variable | Value |
|----------|-------|
| `BUCKET_NAME` | `emr-lab-bucket-699092321120-us-east-2-an` |
| `BUCKET_REGION` | `us-east-2` |
| `ALLOWED_ORIGIN` | `https://HappyRoya.kanikayears.com` |
| `OPENROUTER_API_KEY` | `sk-or-...` — never put anywhere else |
| `DYNAMODB_TABLE` | `sms-conversations` |
| `SMS_SEND_FUNCTION` | `sms-send` |

Actions handled by s3-chat:

| `action` in request body | What it does |
|--------------------------|-------------|
| `list_files` | Lists all files in S3 `uploads/` prefix |
| *(none — has `s3_key`)* | Single file chat |
| *(none — has `s3_keys`)* | Combined multi-file chat |
| `trigger_sms` | Invokes sms-send Lambda asynchronously |
| `get_sms_conversations` | Reads all rows from DynamoDB |

### API Gateway Routes

| Route | Lambda | URL |
|-------|--------|-----|
| `POST /get-upload-url` | `s3-upload-lambda` | `https://aoqop7lkph.execute-api.us-east-2.amazonaws.com/get-upload-url` |
| `POST /chat` | `s3-chat` | `https://aoqop7lkph.execute-api.us-east-2.amazonaws.com/chat` |

---

## AWS Setup — SMS System

### Resources

| AWS Resource | Name / Value | Purpose |
|-------------|-------------|---------|
| DynamoDB Table | `sms-conversations` | Stores per-patient SMS conversation history |
| Lambda | `sms-send` | Reads patient Excel, sends bill reminders |
| Lambda | `sms-reply` | Handles inbound patient SMS, calls GPT-5.5 |
| SNS Topic | `sms-inbound-replies` | Routes inbound SMS to sms-reply Lambda |
| End User Messaging phone | `+18557684735` (toll-free) | Sends and receives SMS |
| IAM Role | `sms-lambda-role` | Permissions for sms-send and sms-reply |

### DynamoDB Table

- Table name: `sms-conversations`
- Partition key: `phone_number` (String)
- Capacity: On-demand
- Region: `us-east-2`

### IAM Role — `sms-lambda-role`

Attach these AWS managed policies:

| Policy | Why |
|--------|-----|
| `AmazonS3ReadOnlyAccess` | sms-send reads patient Excel from S3 |
| `AmazonDynamoDBFullAccess` | Both Lambdas read/write conversation history |
| `AmazonPinpointSMSVoiceV2FullAccess` | Sending SMS via End User Messaging |
| `AWSLambdaBasicExecutionRole` | CloudWatch logging |

### Lambda Functions — SMS

**`sms-send`** (`sms_send_lambda.py`)
- Runtime: Python 3.12 | Role: `sms-lambda-role` | Layer: `s3-chat-layer` | Timeout: 5 min
- Triggered manually via portal UI (or on a schedule via EventBridge)
- Env vars:

| Variable | Value |
|----------|-------|
| `BUCKET_NAME` | `emr-lab-bucket-699092321120-us-east-2-an` |
| `DYNAMODB_TABLE` | `sms-conversations` |
| `ORIGINATION_NUMBER` | `+18557684735` |

**`sms-reply`** (`sms_reply_lambda.py`)
- Runtime: Python 3.12 | Role: `sms-lambda-role` | Timeout: 30s
- Triggered automatically by SNS topic `sms-inbound-replies` whenever a patient replies
- Env vars:

| Variable | Value |
|----------|-------|
| `DYNAMODB_TABLE` | `sms-conversations` |
| `ORIGINATION_NUMBER` | `+18557684735` |
| `OPENROUTER_API_KEY` | `sk-or-...` — never put anywhere else |

### End User Messaging Setup

1. **Request toll-free number** — End User Messaging → Phone numbers → Request originator → Toll-free → US → SMS
2. **Enable two-way SMS** — click the number → Edit → Two-way SMS → enable → SNS topic → select `sms-inbound-replies`
3. **Register the number** (toll-free verification form) — company name, website (`hkpeds.com`), use case (medical billing reminders), opt-in method (patient intake), sample message
4. **Wait for Active status** — typically 24–72 hours. The number accepts API calls while Pending but the carrier does not deliver messages until Active.

### SNS → Lambda Connection

In `sms-reply` Lambda → Configuration → Triggers → Add trigger → SNS → select `sms-inbound-replies`.

Every patient reply automatically triggers sms-reply. No polling needed.

---

## Firebase & EmailJS Setup

### Firebase

Project: `hipaa-877ca`. Only Firebase Authentication is used — no Firestore or Realtime Database.

**Authorized Domains** (Firebase Console → Authentication → Settings):
- `localhost`
- `ramanuja125.github.io`
- `kanikayears.com`
- `HappyRoya.kanikayears.com`

> **Important:** the subdomain `HappyRoya.kanikayears.com` must be added to the Authorized Domains list or Firebase will block login attempts from it.

Firebase config in `auth.js` (apiKey, projectId, etc.) is safe to be public — access is controlled by the Authorized Domains list, not by keeping the config secret.

### EmailJS

| Value | ID |
|-------|-----|
| Account | kanikayears@gmail.com |
| Service ID | `service_xkqj0hk` |
| Template ID | `template_itledcu` |
| Public Key | `SZ8eY2te2zZP5bkQe` |

Template variables: `{{to_email}}` and `{{otp_code}}`. The Public Key is safe to expose — it only allows sending through your own pre-configured templates.

---

## Hosting & Subdomain Setup

The portal files are hosted on **GitHub Pages** under the `kanikayears` GitHub account. The custom subdomain `HappyRoya.kanikayears.com` is configured in GoDaddy DNS and points to GitHub Pages.

### GoDaddy DNS Setup

In the GoDaddy DNS management panel for `kanikayears.com`:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| CNAME | `HappyRoya` | `<your-github-pages-url>` | 1 hour |

### GitHub Pages Setup

In the GitHub repository settings → Pages:
- Source: Deploy from branch (or GitHub Actions)
- Custom domain: `HappyRoya.kanikayears.com`
- Enforce HTTPS: ✅ enabled

GitHub Pages automatically provisions an SSL certificate for the subdomain via Let's Encrypt.

### If You Need to Update the Domain

1. Update `ALLOWED_ORIGIN` in `s3-chat` and `s3-upload-lambda` Lambda env vars to the new domain
2. Update the S3 CORS policy `AllowedOrigins` to include the new domain
3. Add the new domain to Firebase Authorized Domains
4. Update the GitHub Pages custom domain setting

---

## File Structure

```
/
├── index.html                   → Login page (email + password)
├── register.html                → New user registration
├── verify.html                  → OTP entry (2FA step)
├── dashboard.html               → Main page: upload, load stored, AI chat, SMS tab
├── forgot-password.html         → Password reset
├── success.html                 → Post-login confirmation
├── styles.css                   → Shared styles (Inter font, HKPeds navy #184080, all pages)
├── auth.js                      → Firebase + EmailJS auth logic
├── happy.jpg                    → Happy Kids Pediatrics logo (used in all page headers + navbar)
│
├── lambda_function.py           → s3-upload-lambda: pre-signed upload URLs
├── chat_lambda_function.py      → s3-chat: file chat, listing, SMS trigger, SMS conversations
├── sms_send_lambda.py           → sms-send: reads Excel, sends bill reminder SMS
├── sms_reply_lambda.py          → sms-reply: handles inbound SMS, GPT-5.5 reply
│
├── cors_policy.json             → S3 bucket CORS configuration
├── sms_setup_guide.md           → Step-by-step SMS AWS setup reference
└── README.md                    → This file
```

---

## Branding & UI

The portal is fully branded for **Happy Kids Pediatrics** and the **Roya Health AI** platform.

| Element | Value |
|---------|-------|
| Brand color | `#184080` (HKPeds navy — pixel-matched from logo) |
| Dark variant | `#0f2d5e` |
| Light tint | `#e8eef8` |
| Page background | `#f0f4fb` |
| Font | Inter (Google Fonts) |
| Logo | `happy.jpg` — shown in every page header and the dashboard navbar |
| Navbar | HKPeds navy `#184080` with white text |
| Sign-in subtitle | "Access your Happy Kids Pediatrics and Roya Health AI platform" |
| HIPAA footer | "For any information please contact the Practice at 480-776-3790" |

### Pages and Their Titles

| File | Browser Title |
|------|--------------|
| `index.html` | Sign In — Happy Kids Pediatrics |
| `register.html` | Register — Happy Kids Pediatrics |
| `verify.html` | Two-Factor Verification — Happy Kids Pediatrics |
| `forgot-password.html` | Reset Password — Happy Kids Pediatrics |
| `success.html` | Access Granted — Happy Kids Pediatrics |
| `dashboard.html` | Dashboard — Happy Kids Pediatrics |

---

## Security Architecture

| Concern | How It Is Handled |
|---------|------------------|
| AWS credentials in browser | Never — Lambda generates temporary upload URLs |
| OpenRouter API key in browser | Never — key lives only in Lambda environment variables |
| OpenRouter key in SMS Lambda | Same — only in sms-reply Lambda env vars, never in any file |
| Password storage | Firebase hashes passwords — plaintext never stored anywhere |
| OTP storage | Lives only in sessionStorage (browser tab), expires in 10 minutes |
| Session persistence | sessionStorage — clears automatically when tab closes |
| Pre-signed URL abuse | Expires in 15 minutes, scoped to one specific file key |
| S3 files publicly readable | Block All Public Access enabled on bucket — files are private |
| Cross-origin attacks | CORS headers on Lambdas restrict to `HappyRoya.kanikayears.com` only |
| Patient SMS data | Stored only in DynamoDB (AWS-managed, encrypted at rest by default) |
| SMS AI hallucination | Whitelist system prompt — AI can only answer from explicitly listed facts |
| Patient data in SMS | Only patient's own name and balance sent to GPT-5.5 for their conversation |

---

## How to Change Things

**Change the AI model (file chat or SMS):**
- File chat: in `chat_lambda_function.py`, update `"model": "openai/gpt-5.5"` to any OpenRouter model. Redeploy s3-chat.
- SMS replies: in `sms_reply_lambda.py`, same field. Redeploy sms-reply.

**Add more information the SMS AI can answer:**
- Open `sms_reply_lambda.py`
- Find the `FACTS YOU ARE ALLOWED TO SHARE` section in `SYSTEM_PROMPT`
- Add the new facts (e.g. weekday hours, accepted insurances, payment portal URL)
- Paste into sms-reply Lambda → Deploy. No code changes needed.

**Change the practice phone number shown to patients:**
- Update it in the SMS guardrail `SYSTEM_PROMPT` in `sms_reply_lambda.py`
- Also update the HIPAA footer text in each HTML file

**Change the SMS phone number:**
- Update `ORIGINATION_NUMBER` env var on both `sms-send` and `sms-reply` Lambdas

**Change the S3 bucket:**
- Create new bucket, apply `cors_policy.json`, update IAM policy ARNs, update `BUCKET_NAME` on all Lambdas

**Rotate the OpenRouter API key:**
- openrouter.ai → Keys → new key → update `OPENROUTER_API_KEY` on `s3-chat` and `sms-reply`

**Rotate the EmailJS public key:**
- emailjs.com → Account → regenerate → update `EMAILJS_PUBLIC_KEY` in `auth.js`

**Add a scheduled SMS blast (e.g. every Monday morning):**
- Lambda → sms-send → Add trigger → EventBridge (CloudWatch Events) → Schedule expression: `cron(0 14 ? * MON *)` (9 AM Arizona time = 14:00 UTC)
- Pass `{ "excel_key": "uploads/patients.xlsx" }` as the event payload

**Add a new API Gateway route:**
- API Gateway → your HTTP API → Routes → Create → method + path → attach Lambda integration → auto-deploys

**Update the subdomain or move to a new domain:**
1. Update `ALLOWED_ORIGIN` in `s3-chat` and `s3-upload-lambda` env vars
2. Update S3 CORS policy `AllowedOrigins`
3. Add new domain to Firebase Authorized Domains
4. Update GitHub Pages custom domain setting
