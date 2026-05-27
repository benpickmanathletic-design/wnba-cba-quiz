#!/usr/bin/env python3
"""
WNBA CBA Daily Quiz
Generates 10 CBA questions via Anthropic API and emails them to your inbox.
Run manually or via cron job.
"""

import json
import smtplib
import sys
import random
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── CONFIG ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = "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"   # get at console.anthropic.com
GMAIL_ADDRESS     = "benpickmanathletic@gmail.com"        # the gmail account you send FROM
GMAIL_APP_PASSWORD = "ciumloosxycvossl"  # 16-char app password (not your login password)
RECIPIENT_EMAIL   = "benpickman@yahoo.com"
SEND_HOUR         = 7   # not used by the script itself — set this in cron instead
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
- Mental Health HRA: WNBA contributes IRS maximum for excepted benefit HRA; for mental health expenses not covered by insurance
- Veteran Recognition Payment: $30,000 (5–7 YOS) | $50,000 (8–11 YOS) | $100,000 (12+ YOS); by December 31, 2026; retired MVPs get 12+ YOS amount regardless of years
- Family Planning: up to $20,000/year for players with 2+ YOS; covers adoption, surrogacy, oocyte cryopreservation, fertility treatment
- Non-Birthing Parent Leave: 2 weeks paid at 100% Base Salary
- Childcare: reimbursed up to IRS annual max ÷ months with games (tax-preferred)

ARTICLE XIII – DRAFT ELIGIBILITY:
- Domestic: must be 22+ years old in Draft calendar year OR have graduated (or class graduating within 3 months)
- International players: eligible at 20+ years old (lower threshold than domestic)
- Only women are eligible to play in the WNBA
- Eligibility renunciation: written notice at least 10 days before Draft

ARTICLE XIV – PLAYER CONDUCT:
- Sec. 6 (Holdouts): suspension allowed if player gives written notice of not playing; or fails to report within 14 days AND fails to give written intent; or fails to report within 21 days of Season start
- Sec. 9 (WNBA Prioritization): suspend without pay for season remainder if not reported by Season start or May 1 (2026) / April 15 (2027+), whichever is later; does NOT apply to players with 0, 1, or 2 YOS; significant life events exempt with 24-hour return
- Sec. 18 (Gaming): investment disclosure within 30 days of acquiring interest; promotion/endorsement subject to restrictions
- Sec. 19 (Cannabis): products with >0.3% THC prohibited; investment and promotion rules apply
- Sec. 20 (Dress Code): league-wide only; Teams CANNOT have their own dress code policies; WNBA must consult WNBPA before any changes

ARTICLE XV – CIRCUMVENTION:
- 1st violation: up to $900,000 fine (50% WNBA, 50% WNBPA charity)
- 2nd+ violation: up to $1,500,000
- Unauthorized agreements: up to $3,000,000
- Also: draft pick forfeiture; contract voiding
- Diversity in Coaching Initiative: player must have 8+ YOS and 3+ YOS with affiliated team; full-time off-season services; fair market compensation; WNBA approval required
- Retired player transactions challengeable if player retired within 5 years, was paid below market, and new deal exceeds $10,000 or includes investment opportunity

ARTICLE XX – PHYSICAL/MEDICAL:
- Second opinions: player notifies team in writing first; team must provide records; team must CONSIDER (not necessarily follow) the opinion; player may not miss games without team authorization
- Wearables: players may decline certain wearables (Sec. 13)
- Fitness-to-Play: joint physician panels (Sec. 11)
- Concussion/cardiac/emergency protocols: Sec. 7
- Vaccination: education and recommendations only (Sec. 14)

ARTICLE XXXIII – EXPANSION/ROSTERS:
- Required roster size: 12 players; if falls below 12, must restore within 72 hours
- Regular Season game caps: 44 in 2026 | 50 in 2027–2028 | 52 from 2029 onward
- Pre-season: max 4 games per team
- Expansion draft: WNBA controls process; expansion team may select 1 UFA who cannot be a Core Player
- Special competitions: WNBA discretion with WNBPA consultation; parties agree on prize pool

REQUIREMENTS:
- Exactly 10 questions: ~7 multiple choice, ~3 true/false
- Randomly vary which articles are covered each time (pick from all the above)
- Questions must test precise numbers, thresholds, timelines, and edge cases — not vague concepts
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
      "explanation": "Art. VII, Sec. 1(a): The 2026 Salary Cap is set at $7,000,000."
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
    """Call Anthropic API and return parsed questions list."""
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

    raw = data["content"][0]["text"].strip()
    # Strip any accidental markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)["questions"]


def build_html(questions: list[dict], date_str: str) -> str:
    """Build a clean HTML email body."""
    rows = ""
    for q in questions:
        type_label = "Multiple choice" if q["type"] == "mc" else "True / False"
        opts_html = ""
        if q["type"] == "mc" and "options" in q:
            for letter in ["A", "B", "C", "D"]:
                val = q["options"].get(letter, "")
                if val:
                    opts_html += f"""
                    <p style="font-size:14px;color:#555;margin:0 0 5px;padding-left:16px;">
                      <strong style="color:#999;">{letter}.</strong> {val}
                    </p>"""

        rows += f"""
        <div style="margin-bottom:28px;padding-bottom:28px;border-bottom:1px solid #e8e8e8;">
          <p style="font-size:11px;font-weight:600;color:#E25C1A;text-transform:uppercase;
                     letter-spacing:0.06em;margin:0 0 6px;">
            Q{q['num']} · {q.get('article','')} · {type_label}
          </p>
          <p style="font-size:15px;font-weight:500;margin:0 0 12px;line-height:1.5;">
            {q['question']}
          </p>
          {opts_html}
          <div style="margin-top:10px;padding:8px 12px;background:#f0faf5;
                       border-left:3px solid #2d9e6b;border-radius:0 4px 4px 0;">
            <p style="font-size:13px;color:#1a7a50;margin:0;">
              <strong>✓ Answer:</strong> {q['answer']}
            </p>
            <p style="font-size:12px;color:#4a9e7a;margin:4px 0 0;">
              {q.get('explanation','')}
            </p>
          </div>
        </div>"""

    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                max-width:620px;margin:0 auto;color:#1a1a1a;">
      <div style="background:#E25C1A;padding:24px 32px;border-radius:8px 8px 0 0;">
        <h1 style="color:#fff;margin:0;font-size:20px;font-weight:600;">
          🏀 WNBA CBA Daily Quiz
        </h1>
        <p style="color:rgba(255,255,255,0.85);margin:6px 0 0;font-size:14px;">
          {date_str} · 2026–2033 CBA · Front office edition
        </p>
      </div>
      <div style="background:#fafafa;padding:24px 32px;border:1px solid #e8e8e8;
                   border-top:none;border-radius:0 0 8px 8px;">
        {rows}
        <p style="font-size:12px;color:#aaa;text-align:center;margin:0;">
          Generated daily from the 2026 WNBA Collective Bargaining Agreement
        </p>
      </div>
    </div>"""


def send_email(html_body: str, date_str: str):
    """Send via Gmail SMTP using an App Password."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🏀 WNBA CBA Daily Quiz — {date_str}"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = RECIPIENT_EMAIL

    msg.attach(MIMEText(html_body, "html"))

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

    html = build_html(questions, date_str)

    try:
        send_email(html, date_str)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Email sent to {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"ERROR sending email: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
