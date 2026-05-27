#!/usr/bin/env python3
"""
WNBA CBA Daily Quiz
Generates 10 CBA questions, saves an interactive HTML quiz to your Desktop,
and emails you a notification with a summary.
Run manually or via cron job.
"""

import json
import os
import smtplib
import sys
import requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ── CONFIG ─────────────────────────────────────────────────────────────────
# Reads from environment variables (set as GitHub Actions secrets)
# For local runs, you can also hardcode them here
ANTHROPIC_API_KEY  = "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"   # get at console.anthropic.com
GMAIL_ADDRESS      = "benpickmanathletic@gmail.com"        # the gmail account you send FROM
GMAIL_APP_PASSWORD = "ciumloosxycvossl"   # 16-char app password
RECIPIENT_EMAIL    = "benpickman@yahoo.com"
QUIZ_SAVE_PATH     = os.path.expanduser("~/Desktop/wnba_quiz.html") if os.path.exists(os.path.expanduser("~/Desktop")) else "/tmp/wnba_quiz.html"
NETLIFY_TOKEN      = os.environ.get("NETLIFY_TOKEN", "YOUR_NETLIFY_TOKEN")
NETLIFY_SITE_ID    = None  # auto-saved after first deploy
# ───────────────────────────────────────────────────────────────────────────

CBA_SYSTEM = "You are a precise quiz generator. Output ONLY valid JSON. No markdown, no preamble, no explanation."

CBA_PROMPT = """Using ONLY the 2026 WNBA CBA, generate exactly 10 quiz questions for an experienced WNBA front office professional who knows the old CBA well and is mastering the new 2026 provisions.

KEY CBA FACTS:

ARTICLE I – DEFINITIONS:
- "Bona Fide Exclusive Endorsement Agreement": player receives at least $5,000/year; submitted to WNBA Enterprises before January 1 of the applicable Season
- "Extension" = amendment adding 12-month periods (not an option exercise)
- "Mid Point of Regular Season" = total calendar days ÷ 2, rounded up

ARTICLE IV – MANAGEMENT RIGHTS:
- Teams retain all rights not expressly limited by the CBA

ARTICLE V – STANDARD PLAYER CONTRACTS:
- Supermax Salary = 20% of Salary Cap for that year
- Standard Maximum Salary = 17% of Salary Cap for that year
- Base Salary annual increases/decreases capped at 5% of year-1 salary
- Rookie Scale Pick 1: $500K / $520K / $572K / $646,360 (4 years)
- Rookie Scale Pick 2: $466,913 year 1; Pick 3: $436,016 year 1
- Training Camp Contracts: max = Minimum Player Salary; no base salary protection; max 1 season; not counted in Team Salary until first day of Regular Season
- Player Development Contracts: excluded from Team Salary entirely
- Pregnancy Disability: 100% of Base Salary for duration of disability

ARTICLE VI – FREE AGENCY:
- Core Player: max 1 per team; beginning 2027, only players with ≤6 Years of Service eligible
- Restricted Qualifying Offer window: January 30 – February 3
- Unrestricted Free Agents: free to negotiate starting February 4
- Restricted QO must stay open through March 21 unless player agrees to withdrawal; if withdrawn, player immediately becomes UFA
- No individually-negotiated Right of First Refusal permitted in any contract

ARTICLE VII – SALARY CAP:
- 2026 Salary Cap = $7,000,000
- Minimum Team Salary = 85% of Salary Cap ($5,950,000 in 2026)
- Cap change cap: ±13% for 2027; ±10% for all subsequent years
- Incomplete roster: <11 players in Team Salary between Jan 1 and day before Regular Season → Team Salary increased by (11 − actual) × minimum salary
- Hardship Exception: expires 7 days after granted
- Career-ending injury exclusion voided if player plays >5 games in any one season or ≥10 games across two seasons post-injury

ARTICLE VIII – ROOKIE SCALE:
- Pick 1: Y1 $500,000 | Y2 $520,000 | Y3 $572,000 | Y4 option $646,360
- 2026 minimum salary (0–3 YOS): $270,000

ARTICLE IX – MERIT BONUSES:
- WNBA Champion: $60,000/player | Runner-up: $20,000 | 2nd Round exit: $10,000 | 1st Round exit: $5,000
- MVP: $60,000 | Finals MVP: $30,000 | DPOY: $30,000
- All-WNBA 1st Team: $30,000 | 2nd Team: $15,000
- All-Star participant: $15,000 | All-Star MVP: $20,000
- Rookie of the Year: $15,000
- Total pool (team + individual): $3,000,000
- Post-2026 amounts scale with Salary Cap

ARTICLE X – BENEFITS:
- Medical 2026: in-network deductible $600 individual/$1,800 family; OOP max $3,000/person; out-of-network deductible $2,500/person
- Dependent coverage: player pays 33% of cost
- Mental Health HRA: WNBA contributes IRS maximum for excepted benefit HRA
- Veteran Recognition Payment: $30,000 (5–7 YOS) | $50,000 (8–11 YOS) | $100,000 (12+ YOS); by December 31, 2026; retired MVPs get 12+ YOS amount regardless of years
- Family Planning: up to $20,000/year for players with 2+ YOS
- Non-Birthing Parent Leave: 2 weeks paid at 100% Base Salary
- Childcare: reimbursed up to IRS annual max ÷ months with games

ARTICLE XIII – DRAFT ELIGIBILITY:
- Domestic: must be 22+ years old in Draft calendar year OR have graduated
- International players: eligible at 20+ years old
- Only women are eligible to play in the WNBA
- Eligibility renunciation: written notice at least 10 days before Draft

ARTICLE XIV – PLAYER CONDUCT:
- Sec. 6 (Holdouts): suspension allowed if player gives written notice of not playing; or fails to report within 14 days AND fails to give written intent; or fails to report within 21 days of Season start
- Sec. 9 (WNBA Prioritization): suspend without pay for season remainder if not reported by Season start or May 1 (2026) / April 15 (2027+), whichever is later; does NOT apply to players with 0, 1, or 2 YOS; significant life events exempt with 24-hour return
- Sec. 18 (Gaming): investment disclosure within 30 days; promotion/endorsement subject to restrictions
- Sec. 19 (Cannabis): products with >0.3% THC prohibited
- Sec. 20 (Dress Code): league-wide only; Teams CANNOT have their own dress code policies; WNBA must consult WNBPA before changes

ARTICLE XV – CIRCUMVENTION:
- 1st violation: up to $900,000 fine (50% WNBA, 50% WNBPA charity)
- 2nd+ violation: up to $1,500,000
- Unauthorized agreements: up to $3,000,000
- Diversity in Coaching Initiative: player must have 8+ YOS and 3+ YOS with affiliated team

ARTICLE XX – PHYSICAL/MEDICAL:
- Second opinions: player notifies team in writing first; team must CONSIDER (not necessarily follow) the opinion
- Wearables: players may decline certain wearables (Sec. 13)
- Fitness-to-Play: joint physician panels (Sec. 11)
- Vaccination: education and recommendations only (Sec. 14)

ARTICLE XXXIII – EXPANSION/ROSTERS:
- Required roster size: 12 players; if falls below 12, must restore within 72 hours
- Regular Season game caps: 44 in 2026 | 50 in 2027–2028 | 52 from 2029 onward
- Pre-season: max 4 games per team
- Expansion draft: WNBA controls process; expansion team may select 1 UFA who cannot be a Core Player

REQUIREMENTS:
- Exactly 10 questions: ~7 multiple choice, ~3 true/false
- Follow this exact question distribution every time:
  * Art. V (Standard Player Contracts): 2 questions
  * Art. VI (Free Agency): 2 questions
  * Art. VII (Salary Cap): 2 questions
  * Art. VIII (Rookie Scale): 1 question
  * Art. XIII (Draft Eligibility): 1 question
  * Remaining 2 questions: randomly drawn from Art. I, IV, IX, X, XIV, XV, XX, XXXIII
- Questions must test precise numbers, thresholds, timelines, and edge cases
- For MC: 4 options (A/B/C/D) with plausible wrong answers
- For T/F: clear declarative statement
- Include correct answer and 1-sentence explanation citing article/section

OUTPUT FORMAT (strict JSON, no other text):
{
  "questions": [
    {
      "num": 1,
      "type": "mc",
      "article": "Art. VII",
      "question": "...",
      "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
      "answer": "B",
      "explanation": "Art. VII, Sec. 1(a): ..."
    },
    {
      "num": 2,
      "type": "tf",
      "article": "Art. XIV",
      "question": "True or False: ...",
      "answer": "False",
      "explanation": "Art. XIV, Sec. 20: ..."
    }
  ]
}"""


def generate_questions() -> list[dict]:
    import urllib.request
    payload = json.dumps({
        "model": "claude-sonnet-4-5",
        "max_tokens": 4000,
        "system": CBA_SYSTEM,
        "messages": [{"role": "user", "content": CBA_PROMPT}]
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    raw = data["content"][0]["text"].strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)["questions"]


def build_interactive_html(questions: list[dict], date_str: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'wnba_quiz_template.html')
    with open(template_path) as f:
        template = f.read()
    quiz_data = json.dumps({"date": date_str, "questions": questions}, ensure_ascii=False)
    return template.replace('__QUIZ_DATA__', quiz_data)

def upload_to_netlify(html_content: str, date_str: str) -> str:
    """Upload quiz HTML to Netlify and return the live URL."""
    import zipfile, io

    # Step 1: Create or reuse a site
    site_id = get_netlify_site_id()
    headers_json = {
        'Authorization': f'Bearer {NETLIFY_TOKEN}',
        'Content-Type': 'application/json',
    }

    if not site_id:
        # Create a new site
        resp = requests.post(
            'https://api.netlify.com/api/v1/sites',
            headers=headers_json,
            json={'name': 'wnba-cba-quiz'}
        )
        print(f"Create site status: {resp.status_code} {resp.text[:200]}")
        resp.raise_for_status()
        site_data = resp.json()
        site_id = site_data.get('id')
        site_url = site_data.get('ssl_url') or site_data.get('url', '')
        # Save site ID
        site_id_path = '/tmp/wnba_quiz_site_id.txt'
        with open(site_id_path, 'w') as f:
            f.write(site_id)
        print(f"Created site: {site_id} at {site_url}")
    else:
        site_url = None

    # Step 2: Deploy files using file digest method
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('index.html', html_content)
    zip_buffer.seek(0)
    zip_data = zip_buffer.read()

    headers_zip = {
        'Authorization': f'Bearer {NETLIFY_TOKEN}',
        'Content-Type': 'application/zip',
    }

    deploy_resp = requests.post(
        f'https://api.netlify.com/api/v1/sites/{site_id}/deploys',
        headers=headers_zip,
        data=zip_data
    )
    print(f"Deploy status: {deploy_resp.status_code} {deploy_resp.text[:300]}")
    deploy_resp.raise_for_status()
    deploy_data = deploy_resp.json()

    final_url = deploy_data.get('ssl_url') or deploy_data.get('deploy_ssl_url') or deploy_data.get('url') or site_url
    print(f"Quiz live at: {final_url}")
    return final_url


def get_netlify_site_id() -> str:
    """Read saved Netlify site ID if it exists."""
    for path in ['/tmp/wnba_quiz_site_id.txt', os.path.expanduser('~/Downloads/wnba_quiz_site_id.txt')]:
        if os.path.exists(path):
            with open(path) as f:
                val = f.read().strip()
                if val:
                    return val
    return None


def build_notification_email(date_str: str, quiz_path: str, quiz_url: str = None) -> str:
    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                max-width:520px;margin:0 auto;color:#1a1a1a;">
      <div style="background:#E25C1A;padding:28px 32px;border-radius:12px 12px 0 0;">
        <h1 style="color:#fff;margin:0;font-size:20px;font-weight:700;">🏀 Your WNBA CBA Quiz is Ready</h1>
        <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;">{date_str}</p>
      </div>
      <div style="background:#fafafa;padding:28px 32px;border:1px solid #e8e8e8;
                   border-top:none;border-radius:0 0 12px 12px;">
        <p style="font-size:15px;line-height:1.6;margin:0 0 20px;">
          Today's 10-question quiz is ready. Tap the button below to open it on any device.
        </p>
        <a href="QUIZ_URL_PLACEHOLDER" style="display:block;text-align:center;background:#E25C1A;color:white;
           padding:16px 32px;border-radius:8px;font-size:16px;font-weight:700;text-decoration:none;
           margin-bottom:24px;">&#127936; Take Today's Quiz</a>
        <div style="background:#fff;border:1px solid #e8e8e8;border-radius:8px;
                     padding:14px 16px;font-size:13px;color:#555;margin-bottom:24px;">
          <strong style="color:#333;">🔗 Link:</strong> QUIZ_URL_PLACEHOLDER<br>
          <strong style="color:#333;">💻 Desktop:</strong> Also saved to your Desktop as wnba_quiz.html
        </div>
        <p style="font-size:12px;color:#aaa;text-align:center;margin:0;">
          2026–2033 WNBA CBA · Front office edition
        </p>
      </div>
    </div>"""


def send_email(html_body: str, date_str: str, attachment_path: str = None):
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"🏀 WNBA CBA Quiz Ready — {date_str}"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html"))
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        filename = os.path.basename(attachment_path)
        part.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(part)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())


def main():
    date_str = datetime.now().strftime("%A, %B %-d, %Y")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating quiz for {date_str}…")

    try:
        questions = generate_questions()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ {len(questions)} questions generated")
    except Exception as e:
        print(f"ERROR generating questions: {e}", file=sys.stderr)
        sys.exit(1)

    # Save interactive HTML to Desktop
    html_quiz = build_interactive_html(questions, date_str)
    with open(QUIZ_SAVE_PATH, "w") as f:
        f.write(html_quiz)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Quiz saved to {QUIZ_SAVE_PATH}")

    # Upload to Netlify
    quiz_url = None
    try:
        global NETLIFY_SITE_ID
        NETLIFY_SITE_ID = get_netlify_site_id()
        quiz_url = upload_to_netlify(html_quiz, date_str)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Quiz live at {quiz_url}")
    except Exception as e:
        print(f"WARNING: Netlify upload failed: {e}")

    # Send notification email
    email_html = build_notification_email(date_str, QUIZ_SAVE_PATH, quiz_url)
    # Replace placeholder URL in email
    if quiz_url:
        email_html = email_html.replace('QUIZ_URL_PLACEHOLDER', quiz_url)
    try:
        send_email(email_html, date_str, QUIZ_SAVE_PATH)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Notification sent to {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"ERROR sending email: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
