"""Seed the database with 100 realistic notes and reminders."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db
from core.notes import create_note
from core.reminders import create_reminder
from datetime import datetime, timedelta
import random

init_db()

NOW = datetime.now()

def dt(delta_days=0, hour=9, minute=0):
    d = NOW + timedelta(days=delta_days)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)

# ── NOTES (60) ────────────────────────────────────────────────────────────────

notes = [
    # Meeting notes
    ("Meeting with Yaseen — LCSI Update",
     "Discussed the LCSI integration progress. Yaseen confirmed the API endpoints are ready. "
     "Next steps: test authentication flow and schedule a demo with the client by end of month.",
     "meeting, lcsi, yaseen", "High", "2026-04-15"),
    ("Yemen Brief — Q1 Review",
     "Covered humanitarian situation update, logistics challenges in Aden port, and coordination "
     "with local NGO partners. Follow up with field team on supply chain delays.",
     "yemen, brief, q1", "Urgent", "2026-04-10"),
    ("DIEM Project Kickoff",
     "Initial meeting with DIEM stakeholders. Project scope defined: data integration middleware "
     "for EU agencies. Timeline 6 months. Budget approved. Team of 4 engineers assigned.",
     "diem, project, kickoff", "High", "2026-03-20"),
    ("Lebanon Field Visit Notes",
     "Visited Beirut office and met with local coordinator Hassan. Infrastructure challenges noted. "
     "Proposed mobile-first solution for connectivity issues in remote areas.",
     "lebanon, field, beirut", "Normal", "2026-04-22"),
    ("AI Research — LLM Evaluation",
     "Compared GPT-4, Claude, and Gemini on structured output tasks. Claude scored highest on "
     "instruction following. Recommend Claude API for the intent parser module.",
     "ai, research, llm, claude", "High", "2026-05-01"),
    ("Report Workflow Improvements",
     "Current report generation takes 3 hours manually. Proposed automation using Python scripts "
     "and template engine. Could reduce to 20 minutes. Present to management next week.",
     "report, workflow, automation", "Normal", "2026-04-28"),
    ("Team Retrospective — April",
     "Sprint went well overall. Main blockers: deployment pipeline slow, test coverage low at 62%. "
     "Action items: add CI caching, write unit tests for parser module.",
     "team, retro, april", "Normal", "2026-04-30"),
    ("Budget Planning FY2027",
     "Initial draft for FY2027 budget. IT infrastructure: $240k. Personnel: $1.2M. R&D allocation "
     "increased by 15% following board approval. Review with CFO scheduled.",
     "budget, planning, finance", "Urgent", "2026-05-03"),
    ("Partnership Discussion — Nablus Office",
     "Call with Nablus regional director. Discussed expanding service coverage to 3 new districts. "
     "Requires 2 additional field staff and a vehicle. Proposal to be submitted by May 20.",
     "nablus, partnership, expansion", "High", "2026-05-05"),
    ("Technical Architecture Review",
     "Reviewed microservices architecture for the new platform. Decided on event-driven approach "
     "using message queues. Database: PostgreSQL for transactional, Redis for caching.",
     "architecture, technical, review", "High", "2026-04-18"),

    # Personal notes
    ("Watch Purchase Research",
     "Looking at the Seiko Presage and Orient Star. Seiko has better movement accuracy. Orient "
     "has nicer dial finish. Budget: $400-600. Check for deals on Chrono24.",
     "personal, watch, shopping", "Low", "2026-04-05"),
    ("Reading List — May",
     "Books to read this month: 'The Pragmatic Programmer', 'Deep Work' by Cal Newport, "
     "'Thinking in Systems' by Meadows. Target: 1 book per week.",
     "reading, personal, books", "Low", "2026-05-01"),
    ("Home Office Setup",
     "Need: better monitor arm, cable management solution, sound dampening panels. "
     "Current setup causes neck strain after 4 hours. Budget ~$300.",
     "home, office, setup", "Normal", "2026-04-12"),
    ("Gym Plan — June",
     "Starting strength program: 3x/week compound lifts. Monday: squat/bench. "
     "Wednesday: deadlift/press. Friday: accessory work. Track progress in journal.",
     "gym, fitness, health", "Normal", "2026-05-10"),
    ("Flight Research — Istanbul",
     "Comparing Turkish Airlines vs Emirates for Istanbul trip. TA has direct flight 4h10m. "
     "Emirates via Dubai adds 5 hours but better business class seats. Trip dates: July 14-21.",
     "travel, istanbul, flight", "Normal", "2026-04-25"),

    # Work notes
    ("API Documentation — v2.0",
     "Updating REST API docs for version 2.0. New endpoints: /search, /batch-create, /webhooks. "
     "Using OpenAPI 3.1 spec. Auto-generate SDK from spec.",
     "api, documentation, dev", "Normal", "2026-05-06"),
    ("Security Audit Findings",
     "Penetration test results: 2 medium vulnerabilities found. SQL injection in legacy endpoint "
     "(patched). Session token expiry too long (72h → 8h). No critical issues.",
     "security, audit, dev", "High", "2026-04-29"),
    ("Onboarding — New Developer",
     "Ahmad joining the team June 1. Prepare: access credentials, dev environment setup doc, "
     "codebase tour session scheduled. Assign to LCSI project initially.",
     "onboarding, team, hr", "Normal", "2026-05-08"),
    ("Client Feedback — Phase 2",
     "Client satisfied with Phase 1 delivery. Phase 2 requests: mobile app, offline mode, "
     "export to Excel. Timeline discussion needed — currently scoped at 4 months.",
     "client, feedback, phase2", "High", "2026-05-04"),
    ("Database Migration Plan",
     "Moving from SQLite to PostgreSQL for production. Migration steps: schema conversion, "
     "data export, connection string updates, index recreation. Zero-downtime approach required.",
     "database, migration, dev", "High", "2026-05-07"),

    # Research/ideas
    ("Ideas — Aria Feature Roadmap",
     "Future features for Aria: voice-triggered calendar sync, smart scheduling suggestions, "
     "integration with Outlook/Teams, sentiment analysis of meeting notes, weekly digest email.",
     "aria, roadmap, ideas", "Normal", "2026-05-09"),
    ("Competitive Analysis — Notion vs Obsidian",
     "Notion: better collaboration, worse offline. Obsidian: pure markdown, great plugins, "
     "local first. For personal knowledge management, Obsidian wins. For team use, Notion.",
     "research, tools, analysis", "Low", "2026-04-20"),
    ("Machine Learning Pipeline Notes",
     "Prototype pipeline: data ingestion → preprocessing → feature engineering → model training → "
     "evaluation → deployment. Using MLflow for experiment tracking. GPU cluster available.",
     "ml, pipeline, research", "Normal", "2026-04-17"),
    ("Gaza Coordination Update",
     "Coordination meeting with partner organizations. Access remains limited in northern areas. "
     "Medical supply convoy approved for next week. Communication protocols reviewed.",
     "gaza, coordination, field", "Urgent", "2026-04-08"),
    ("Brand Guidelines — 2026",
     "Updated color palette: primary blue #2563eb, accent cyan #00d4ff. "
     "New logo usage rules. Typography: Inter for headings, Source Sans for body.",
     "brand, design, guidelines", "Normal", "2026-03-15"),

    # Past notes
    ("Q4 2025 Performance Review",
     "Team exceeded targets by 12%. Key achievements: launched v2 platform, onboarded 3 enterprise "
     "clients, reduced incident response time by 40%. Areas for improvement: documentation.",
     "performance, review, q4", "Normal", "2025-12-20"),
    ("Year-End Planning Session",
     "2026 goals set: expand to 2 new markets, hire 5 engineers, achieve SOC2 compliance, "
     "launch mobile app. OKRs defined for each team. All hands meeting scheduled Jan 5.",
     "planning, goals, 2026", "High", "2025-12-15"),
    ("Conference Notes — DevConf 2025",
     "Key talks: serverless architecture patterns, WebAssembly in production, AI-assisted coding. "
     "Met with 3 potential partners. Follow up with Khalid from DataStream by end of week.",
     "conference, notes, 2025", "Normal", "2025-11-10"),
    ("Proposal — Knowledge Management System",
     "Proposed internal KMS to centralize documentation, meeting notes, and project artifacts. "
     "Estimated ROI: 2 hours/week per employee saved. Tool recommendation: Notion + Aria.",
     "proposal, kms, internal", "Normal", "2025-10-05"),
    ("Infrastructure Costs Analysis",
     "AWS monthly spend: $8,400. Breakdown: EC2 $3.2k, RDS $1.8k, S3 $400, CloudFront $600, "
     "other $2.4k. Reserved instances could save 35%. Recommendation: commit to 1-year plan.",
     "infrastructure, costs, aws", "High", "2025-09-20"),

    # Future-oriented notes
    ("Strategy Session — H2 2026",
     "Planned for July 15. Agenda: market expansion analysis, product roadmap prioritization, "
     "talent acquisition plan, partnership opportunities in MENA region.",
     "strategy, h2, planning", "High", "2026-06-01"),
    ("Conference Presentation Prep",
     "Presenting at TechMENA 2026 in September. Topic: AI-assisted productivity tools for NGOs. "
     "Draft slides due August 1. Need 3 case studies, live demo of Aria.",
     "conference, presentation, prep", "Normal", "2026-07-01"),
    ("Product Launch Checklist",
     "v3.0 launch checklist: beta testing complete, docs updated, marketing copy ready, "
     "press release drafted, support team trained, rollback plan in place.",
     "launch, checklist, product", "High", "2026-06-15"),
    ("Team Expansion Plan — Q3",
     "Hiring plan: 2 backend engineers, 1 UX designer, 1 DevOps. Roles posted June 1. "
     "Target start dates: September. Budget approved. Work with HR on screening criteria.",
     "hiring, team, q3", "Normal", "2026-06-20"),
    ("Annual Report Draft — 2026",
     "Structure: executive summary, program highlights, financial statements, impact metrics, "
     "stories from the field, acknowledgements. Draft due October 15 to board.",
     "annual, report, draft", "Normal", "2026-09-01"),
]

# Add more varied notes
extra_notes = [
    ("Quick Note — Yaseen Follow-up", "Need to send Yaseen the updated proposal by Thursday. He mentioned the client is waiting.", "yaseen, followup", "Normal", "2026-05-11"),
    ("Meeting with Abesh — Project Review", "Reviewed milestones. 3 items delayed. Rescheduled demo to next Tuesday. Abesh concerned about timeline.", "meeting, review", "High", "2026-05-08"),
    ("Reminder Ideas for Aria", "Voice shortcuts: 'hey aria remind me', 'schedule for tomorrow', 'find my note about X'. Natural language improvements needed.", "aria, ideas, voice", "Low", "2026-05-07"),
    ("Office Supplies Order", "Ordered: 2 mechanical keyboards, 4 USB-C hubs, whiteboard markers, printer paper. Delivery expected Friday.", "office, supplies", "Low", "2026-05-06"),
    ("Lunch with Team", "Organized team lunch at the Lebanese restaurant near office. 12 people confirmed. Budget $15/person from team fund.", "team, lunch, social", "Low", "2026-05-09"),
    ("Code Review Notes — Auth Module", "Auth module looks solid. Minor issues: missing rate limiting on login endpoint, password strength check too lenient. Fixed in PR #142.", "code, review, auth", "Normal", "2026-05-05"),
    ("Client Call — Jordan Team", "Jordan team needs Arabic language support in the UI. Timeline: 6 weeks. Will require i18n refactor. Discussed scope.", "client, jordan, arabic", "High", "2026-05-04"),
    ("Draft Email — Partnership", "Draft: Dear [Partner], Following our discussion on May 3rd, we'd like to formalize... (to be completed)", "email, draft, partnership", "Normal", "2026-05-03"),
    ("Server Maintenance Window", "Scheduled maintenance: May 25 2am-4am UTC. Services affected: API, dashboard. Notify customers 5 days in advance.", "maintenance, server, devops", "High", "2026-05-10"),
    ("Personal — Things to Buy", "Headphone stand, blue light glasses, desk pad (large), plant for office. Check Amazon deals.", "personal, shopping", "Low", "2026-05-08"),
    ("Aria Bug — Search Not Working", "Bug: voice search not routing correctly when user says 'look for'. Fixed in latest commit. Need regression test.", "aria, bug, search", "Normal", "2026-05-12"),
    ("Feedback from User Testing", "5 users tested Aria. Average score 4.2/5. Top request: dark/light mode toggle. Second: keyboard shortcuts for recording.", "feedback, testing, ux", "High", "2026-05-11"),
    ("Project Palestine — Update", "Field team confirmed access restored to 3 districts. Remote monitoring system now active. Weekly reports scheduled.", "palestine, project, field", "Urgent", "2026-05-10"),
    ("Weekly Goals — May 12", "1. Fix avatar rendering 2. Seed database 3. Improve greeting engine 4. Code review for Ahmad 5. Draft Q2 report intro.", "goals, weekly", "Normal", "2026-05-12"),
    ("Interview Notes — Backend Candidate", "Candidate: Omar Khalil. Strong in Python/Django. Weak on distributed systems. Good communicator. Recommend 2nd interview.", "interview, hiring, backend", "Normal", "2026-05-07"),
    ("Hardware Procurement", "Request for 3 laptops (Dev team), 2 monitors, 1 server rack expansion. Total budget: $12,400. Approval needed from finance.", "hardware, procurement, it", "Normal", "2026-05-06"),
    ("Research — Whisper Model Comparison", "Whisper tiny: fast, less accurate. Whisper base: good balance. Whisper small: best for production. Using base currently.", "research, whisper, ai", "Normal", "2026-04-30"),
    ("Design Review — Dashboard", "New dashboard mockups reviewed. Feedback: more whitespace, reduce visual noise, make stats more prominent. Revision due Monday.", "design, dashboard, review", "Normal", "2026-05-02"),
    ("Training Plan — New Staff", "3 new staff starting June. Training schedule: Week 1 orientation, Week 2 tools & systems, Week 3 shadowing, Week 4 solo.", "training, hr, onboarding", "Normal", "2026-05-05"),
    ("Data Backup Verification", "Monthly backup check complete. All backups healthy. Recovery time objective: 4 hours. Last tested: April 30.", "backup, devops, data", "Normal", "2026-05-01"),
    ("Meeting Minutes — Board Call", "Board approved Q2 budget. Expansion into Iraq market approved conditionally. Next board meeting: August 5.", "board, meeting, minutes", "High", "2026-04-15"),
    ("API Rate Limit Analysis", "Current limits: 1000 req/min per client. Peak usage: 340 req/min. Headroom sufficient. Monitor monthly.", "api, performance, analysis", "Low", "2026-04-22"),
    ("Field Report — Aden", "Security situation improved in Aden port area. Supply chain now operational. 3 convoys successfully delivered this month.", "aden, field, report", "High", "2026-04-18"),
    ("Password Manager Migration", "Moving team from LastPass to Bitwarden. Self-hosted option preferred for data sovereignty. Migration timeline: 2 weeks.", "security, passwords, tools", "Normal", "2026-04-14"),
    ("Conversation — AI Ethics", "Discussion with team about responsible AI use in humanitarian contexts. Key concern: bias in automated decisions. Document guidelines.", "ai, ethics, discussion", "High", "2026-04-11"),
]

all_notes = notes + extra_notes

print(f"Creating {len(all_notes)} notes...")
for title, content, tags, importance, note_date in all_notes:
    create_note(title, content=content, tags=tags, importance=importance, note_date=note_date)
print(f"Created {len(all_notes)} notes.")

# ── REMINDERS (40) ────────────────────────────────────────────────────────────

reminders = [
    # Overdue
    ("2 PM Meeting with Yaseen", dt(-30, 14, 0), "Video call — LCSI Phase 2 review", "High"),
    ("Submit Monthly Report", dt(-25, 17, 0), "Operations report for April", "Urgent"),
    ("Call with Jordan Office", dt(-20, 10, 30), "Discuss Arabic language support timeline", "High"),
    ("Review Security Audit", dt(-15, 9, 0), "Review and sign off penetration test findings", "Urgent"),
    ("Follow up with Khalid", dt(-10, 11, 0), "DataStream partnership follow-up from conference", "Normal"),
    ("Pay Server Invoice", dt(-7, 16, 0), "AWS invoice due — $8,400", "Urgent"),
    ("Team Check-in", dt(-5, 10, 0), "Weekly team standup — review Q2 progress", "Normal"),
    ("Dentist Appointment", dt(-3, 14, 30), "Annual checkup at city clinic", "Normal"),
    ("Send Yaseen Proposal", dt(-2, 12, 0), "Updated LCSI proposal document", "High"),
    ("Review Ahmad's PR", dt(-1, 15, 0), "Code review for auth module changes", "Normal"),

    # Today
    ("Team Standup", dt(0, 9, 30), "Daily standup — 15 minutes", "Normal"),
    ("Client Demo Prep", dt(0, 14, 0), "Prepare slides and demo environment for Friday", "High"),
    ("Pay Rent", dt(0, 12, 0), "", "Urgent"),

    # This week
    ("Project Status Email", dt(1, 10, 0), "Send weekly status update to all stakeholders", "Normal"),
    ("Database Migration Review", dt(1, 14, 0), "Review PostgreSQL migration plan with DevOps team", "High"),
    ("Interview — Omar Khalil", dt(2, 11, 0), "2nd interview for backend engineer position", "Normal"),
    ("Client Demo — Phase 2", dt(2, 15, 0), "Live demo of new features to Jordan client", "Urgent"),
    ("Gym Session", dt(2, 18, 30), "Strength training — squat day", "Low"),
    ("Board Prep Call", dt(3, 10, 0), "Prepare materials for August board meeting", "High"),
    ("Budget Submission Deadline", dt(3, 17, 0), "Submit FY2027 budget to finance", "Urgent"),
    ("Weekly Report", dt(4, 16, 0), "Compile and submit weekly operations report", "Normal"),
    ("Team Lunch", dt(4, 12, 30), "Lebanese restaurant — 12 people", "Low"),
    ("Server Backup Check", dt(5, 9, 0), "Monthly backup verification", "Normal"),
    ("Call with Nablus Office", dt(5, 11, 0), "Expansion proposal discussion", "High"),
    ("Review Brand Guidelines", dt(5, 14, 0), "Check final version before publishing", "Low"),

    # Next 2 weeks
    ("Product Launch Planning", dt(8, 10, 0), "v3.0 launch timeline and task assignment", "High"),
    ("New Staff Onboarding — Ahmad", dt(10, 9, 0), "Ahmad starts today — orientation schedule", "High"),
    ("Security Training", dt(10, 14, 0), "Annual team security awareness training", "Normal"),
    ("Quarterly Review — Q2", dt(12, 10, 0), "Q2 performance and OKR review with management", "High"),
    ("Istanbul Trip — Departure", dt(14, 6, 0), "Flight TK 123 departs 06:30. Check in online.", "Normal"),

    # Month ahead
    ("Conference Presentation Draft", dt(20, 9, 0), "First draft of TechMENA slides due", "Normal"),
    ("Server Maintenance Window", dt(25, 2, 0), "Scheduled maintenance 02:00-04:00 UTC", "High"),
    ("Strategy Session H2", dt(35, 10, 0), "Half-year strategy planning — full team", "High"),
    ("Team Expansion Hiring Deadline", dt(42, 17, 0), "All job postings must be live by this date", "Normal"),
    ("Annual Report First Draft", dt(60, 9, 0), "First draft to board review committee", "Normal"),
    ("Istanbul Return", dt(21, 20, 0), "Return flight TK 456 departs 20:15", "Normal"),

    # Future important
    ("Budget Review — Q3", dt(75, 10, 0), "Q3 budget review and reforecast", "High"),
    ("Performance Reviews — H1", dt(90, 9, 0), "Individual performance reviews for all staff", "Normal"),
    ("Conference — TechMENA 2026", dt(120, 8, 0), "Check in at venue, speaker registration", "High"),
    ("Year-End Planning", dt(200, 10, 0), "FY2027 planning session — full leadership team", "High"),
]

print(f"\nCreating {len(reminders)} reminders...")
for title, due, message, importance in reminders:
    create_reminder(title, due, message=message, importance=importance)
print(f"Created {len(reminders)} reminders.")

print(f"\nDatabase seeded: {len(all_notes)} notes + {len(reminders)} reminders = {len(all_notes) + len(reminders)} total records.")
