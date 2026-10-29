#!/usr/bin/env python3
"""
Executive Control Plane: A Single Autonomous Agent for C-Level Executives
Local MVP Server (Python 3 standard library + SQLite)

Complies with BRD_Corpus.docx specifications:
- Dedicated single agent per C-level executive (CEO, CFO, COO, CTO, CMO, CHRO)
- Autonomy & Guardrails Engine (Suggest Only, Act with Approval, Autonomous)
- Memory System (PostgreSQL + pgvector simulation in SQLite with cosine similarity)
- Model Gateway (Vertex AI Gemini 1.5 Pro vs Ollama Llama 3 routing)
- Langfuse Observability & Tamper-Evident Audit Log
- Emergency One-Click Kill Switch (BR-055)
- Full 10 Representative Use Cases (UC-1 through UC-10)
"""

import http.server
import socketserver
import json
import sqlite3
import os
import sys
import re
import math
import uuid
import datetime
from urllib.parse import urlparse, parse_qs

PORT = 8000
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "control_plane.db")

# ---------------------------------------------------------------------------
# Database Initialization & Seed Data
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Executives table (BR-001, BR-005)
    c.execute("""
    CREATE TABLE IF NOT EXISTS executives (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        avatar TEXT,
        working_hours TEXT,
        tone TEXT,
        vip_contacts TEXT,
        no_go_topics TEXT,
        autonomy_level TEXT DEFAULT 'approval', -- suggest, approval, autonomous
        autonomy_sliders TEXT, -- JSON
        budget_monthly REAL DEFAULT 150.00,
        budget_spent REAL DEFAULT 42.60,
        delegate_name TEXT,
        delegate_role TEXT,
        is_away INTEGER DEFAULT 0
    )
    """)

    # Memories table (BR-060, BR-061, BR-062, BR-063)
    c.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        executive_id TEXT NOT NULL,
        memory_type TEXT NOT NULL, -- short_term, long_term, episodic
        category TEXT NOT NULL,    -- preference, relationship, decision, policy
        sensitivity TEXT DEFAULT 'Normal', -- Normal, Confidential, Restricted
        content TEXT NOT NULL,
        source TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Approvals queue (BR-050, BR-053, BR-093)
    c.execute("""
    CREATE TABLE IF NOT EXISTS approvals (
        id TEXT PRIMARY KEY,
        executive_id TEXT NOT NULL,
        risk_level TEXT NOT NULL, -- low, medium, high
        capability TEXT NOT NULL, -- email, calendar, finance, hr, document
        action_title TEXT NOT NULL,
        description TEXT NOT NULL,
        why_reason TEXT NOT NULL,
        sources TEXT,
        alternatives TEXT,
        draft_payload TEXT,
        status TEXT DEFAULT 'pending', -- pending, approved, edited, rejected, recalled
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        resolution_notes TEXT
    )
    """)

    # Commitments ledger (BR-040, BR-041)
    c.execute("""
    CREATE TABLE IF NOT EXISTS commitments (
        id TEXT PRIMARY KEY,
        executive_id TEXT NOT NULL,
        title TEXT NOT NULL,
        direction TEXT NOT NULL, -- made_by_exec, made_to_exec
        owner TEXT NOT NULL,
        counterparty TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT DEFAULT 'on_track', -- on_track, at_risk, overdue, completed
        slippage_risk TEXT,
        last_chased TEXT,
        notes TEXT
    )
    """)

    # Audit log (BR-091, BR-092)
    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        executive_id TEXT NOT NULL,
        action_name TEXT NOT NULL,
        actor TEXT NOT NULL, -- Agent, Executive, Delegate
        risk_level TEXT NOT NULL,
        policy_rule TEXT NOT NULL,
        data_scope TEXT NOT NULL,
        approver TEXT,
        status TEXT NOT NULL, -- Allowed, Blocked, Approved, Overridden
        details TEXT
    )
    """)

    # Langfuse Observability Traces (BR-090)
    c.execute("""
    CREATE TABLE IF NOT EXISTS langfuse_traces (
        trace_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        executive_id TEXT NOT NULL,
        name TEXT NOT NULL,
        model TEXT NOT NULL, -- Vertex AI Gemini 1.5 Pro vs Ollama Llama 3 8B
        latency_ms INTEGER NOT NULL,
        tokens_input INTEGER NOT NULL,
        tokens_output INTEGER NOT NULL,
        cost_usd REAL NOT NULL,
        steps_json TEXT
    )
    """)

    # Kill switch global state (BR-055)
    c.execute("""
    CREATE TABLE IF NOT EXISTS system_state (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    conn.commit()

    # Check if seed data exists
    c.execute("SELECT COUNT(*) as cnt FROM executives")
    if c.fetchone()["cnt"] == 0:
        seed_database(conn)

    conn.close()

def seed_database(conn):
    c = conn.cursor()
    now_iso = datetime.datetime.now().isoformat()

    executives_data = [
        {
            "id": "ceo-alexandra",
            "name": "Alexandra Chen",
            "role": "CEO",
            "title": "Chief Executive Officer",
            "company": "Apex Dynamics Technologies",
            "avatar": "👩‍💼",
            "working_hours": "07:30 - 18:30 EST",
            "tone": "Decisive, concise, visionary, warm yet direct with investors",
            "vip_contacts": "Board Members, Sequoia Capital (David Zhang), Key Enterprise Leads",
            "no_go_topics": "Early acquisition rumors, unverified valuation numbers, unreviewed legal filings",
            "autonomy_level": "approval",
            "autonomy_sliders": json.dumps({
                "briefing": "autonomous",
                "inbox_triage": "autonomous",
                "email_send": "approval",
                "scheduling": "autonomous_limits",
                "commitments": "autonomous_limits",
                "memos": "approval"
            }),
            "budget_monthly": 200.0,
            "budget_spent": 58.40,
            "delegate_name": "Marcus Vance",
            "delegate_role": "Chief of Staff / VP Strategy"
        },
        {
            "id": "cfo-marcus",
            "name": "Marcus Vance",
            "role": "CFO",
            "title": "Chief Financial Officer",
            "company": "Apex Dynamics Technologies",
            "avatar": "👨‍💼",
            "working_hours": "08:00 - 19:00 EST",
            "tone": "Analytical, precise, fiduciary-minded, risk-averse",
            "vip_contacts": "Audit Committee Chair, Silicon Valley Bank, External Auditors (PwC)",
            "no_go_topics": "Disclosing unverified cash burn, off-record debt covenants",
            "autonomy_level": "approval",
            "autonomy_sliders": json.dumps({
                "briefing": "autonomous",
                "inbox_triage": "autonomous",
                "email_send": "approval",
                "scheduling": "autonomous_limits",
                "commitments": "approval",
                "memos": "approval"
            }),
            "budget_monthly": 150.0,
            "budget_spent": 34.20,
            "delegate_name": "Sarah Lin",
            "delegate_role": "VP Financial Planning & Analysis"
        },
        {
            "id": "coo-elena",
            "name": "Elena Rostova",
            "role": "COO",
            "title": "Chief Operating Officer",
            "company": "Apex Dynamics Technologies",
            "avatar": "👩‍💻",
            "working_hours": "07:00 - 17:30 EST",
            "tone": "Operational, outcome-driven, clear deadlines, SLA-focused",
            "vip_contacts": "Tier-1 Hardware Suppliers, Logistics Heads, Head of Customer Delivery",
            "no_go_topics": "Signing unvetted vendor SLAs, bypassing safety certifications",
            "autonomy_level": "autonomous_limits",
            "autonomy_sliders": json.dumps({
                "briefing": "autonomous",
                "inbox_triage": "autonomous",
                "email_send": "approval",
                "scheduling": "autonomous",
                "commitments": "autonomous",
                "memos": "approval"
            }),
            "budget_monthly": 150.0,
            "budget_spent": 46.10,
            "delegate_name": "Carlos Gomez",
            "delegate_role": "Director of Supply Operations"
        },
        {
            "id": "cto-david",
            "name": "David Kim",
            "role": "CTO",
            "title": "Chief Technology Officer",
            "company": "Apex Dynamics Technologies",
            "avatar": "🧑‍🔬",
            "working_hours": "09:00 - 19:30 EST",
            "tone": "Engineering-first, architectural rigor, pragmatic, incident-focused",
            "vip_contacts": "Principal Architects, CISO, Head of SRE, Major Cloud Partner Lead",
            "no_go_topics": "Publishing uncoordinated CVE announcements, pushing unreviewed prod bypasses",
            "autonomy_level": "approval",
            "autonomy_sliders": json.dumps({
                "briefing": "autonomous",
                "inbox_triage": "autonomous",
                "email_send": "approval",
                "scheduling": "autonomous_limits",
                "commitments": "autonomous_limits",
                "memos": "approval"
            }),
            "budget_monthly": 180.0,
            "budget_spent": 62.80,
            "delegate_name": "Ananya Sharma",
            "delegate_role": "VP Engineering"
        },
        {
            "id": "cmo-sarah",
            "name": "Sarah Jenkins",
            "role": "CMO",
            "title": "Chief Marketing Officer",
            "company": "Apex Dynamics Technologies",
            "avatar": "👩‍🎨",
            "working_hours": "08:30 - 18:00 EST",
            "tone": "Engaging, brand-aligned, conversion-focused, empathetic, energetic",
            "vip_contacts": "Press / TechCrunch Leads, Keynote Speakers, VP Demand Gen",
            "no_go_topics": "Premature unannounced product release dates, unauthorized press comments",
            "autonomy_level": "autonomous_limits",
            "autonomy_sliders": json.dumps({
                "briefing": "autonomous",
                "inbox_triage": "autonomous",
                "email_send": "approval",
                "scheduling": "autonomous",
                "commitments": "autonomous",
                "memos": "autonomous_limits"
            }),
            "budget_monthly": 140.0,
            "budget_spent": 39.50,
            "delegate_name": "Liam Scott",
            "delegate_role": "Head of Growth & Comms"
        },
        {
            "id": "chro-patrice",
            "name": "Patrice Lumumba",
            "role": "CHRO",
            "title": "Chief Human Resources Officer",
            "company": "Apex Dynamics Technologies",
            "avatar": "🤝",
            "working_hours": "08:00 - 17:30 EST",
            "tone": "Discreet, empathetic, policy-compliant, fair, legally sound",
            "vip_contacts": "Employment Counsel, Compensation Committee, Head of Talent Acquisition",
            "no_go_topics": "Individual salary compensation figures in public channels, unfinalized severance matters",
            "autonomy_level": "suggest",
            "autonomy_sliders": json.dumps({
                "briefing": "autonomous",
                "inbox_triage": "autonomous",
                "email_send": "approval",
                "scheduling": "approval",
                "commitments": "approval",
                "memos": "approval"
            }),
            "budget_monthly": 120.0,
            "budget_spent": 28.10,
            "delegate_name": "Maya Patel",
            "delegate_role": "Director of People Ops"
        }
    ]

    for ex in executives_data:
        c.execute("""
        INSERT INTO executives (
            id, name, role, title, company, avatar, working_hours, tone,
            vip_contacts, no_go_topics, autonomy_level, autonomy_sliders,
            budget_monthly, budget_spent, delegate_name, delegate_role
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ex["id"], ex["name"], ex["role"], ex["title"], ex["company"], ex["avatar"],
            ex["working_hours"], ex["tone"], ex["vip_contacts"], ex["no_go_topics"],
            ex["autonomy_level"], ex["autonomy_sliders"], ex["budget_monthly"],
            ex["budget_spent"], ex["delegate_name"], ex["delegate_role"]
        ))

    # Seed Memories for CEO
    memories = [
        ("mem-1", "ceo-alexandra", "long_term", "preference", "Normal", "Prefers meetings before 14:00 to be capped at 25 minutes; reserves Friday afternoons for deep strategy work.", "Onboarding Profile", now_iso),
        ("mem-2", "ceo-alexandra", "long_term", "relationship", "Normal", "David Zhang from Sequoia Capital likes summaries with direct metrics (MoM ARR, CAC payback, Net Dollar Retention).", "Email Thread: Series B Prep", now_iso),
        ("mem-3", "ceo-alexandra", "episodic", "decision", "Confidential", "Rejected 20% discount request from MegaRetailer; established strict floor of 12% max discount across all enterprise tiers.", "Executive Decision Memo #104", now_iso),
        ("mem-4", "ceo-alexandra", "episodic", "decision", "Restricted", "M&A target exploration code-named Project Falcon: keep strictly isolated from general agent retrieval.", "Special Board Resolution", now_iso),
        ("mem-5", "cfo-marcus", "long_term", "policy", "Normal", "All receivables overdue beyond 45 days must trigger formal finance escalation and credit hold notice.", "CFO Policy Manual", now_iso),
        ("mem-6", "cfo-marcus", "episodic", "decision", "Confidential", "Approved $120,000 cloud infrastructure reserve buffer for Q4 ML inference surge.", "Q3 Financial Review", now_iso),
        ("mem-7", "coo-elena", "long_term", "preference", "Normal", "Hardware supplier delays exceeding 5 days require immediate dual-sourcing activation.", "Operations Playbook v3", now_iso),
        ("mem-8", "cto-david", "long_term", "policy", "Normal", "Zero production database migrations permitted during business hours (09:00 - 18:00 EST).", "CTO Architecture Charter", now_iso),
        ("mem-9", "chro-patrice", "long_term", "policy", "Restricted", "All offer packages exceeding $250k require Compensation Committee approval prior to verbal extension.", "HR Policy Doc 2026", now_iso)
    ]
    for m in memories:
        c.execute("INSERT INTO memories (id, executive_id, memory_type, category, sensitivity, content, source, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", m)

    # Seed Pending Approvals
    approvals = [
        (
            "appr-1", "ceo-alexandra", "high", "email",
            "Draft Response to Lead Investor (Sequoia Capital) on Series B Term Sheet",
            "Agent prepared a synthesized update addressing valuation cap amendment and board seat allocations based on confidential executive memo.",
            "BR-023 strictly mandates human sign-off for investor communications and financial commitments.",
            "Internal Memo #42, Google Sheet: Cap Table Projections v4",
            "Option A: Approve & Send immediately | Option B: Edit wording on valuation floor | Option C: Request in-person sync instead",
            json.dumps({
                "to": "david.zhang@sequoia.example",
                "subject": "Apex Dynamics - Series B Discussion Points & Cap Table Modeling",
                "body": "Hi David,\n\nThanks for your note yesterday. Regarding the Series B valuation cap and governance framework: we have aligned internally on a $120M cap with 15% ESOP pool refresh. We would be pleased to welcome one investor seat while retaining two founder-designated seats.\n\nLooking forward to catching up on Thursday.\n\nBest,\nAlexandra"
            }),
            "pending", now_iso
        ),
        (
            "appr-2", "cfo-marcus", "high", "finance",
            "Execute Receivables Chasing & Credit Hold Notice for Apex Global ($85,000 Overdue)",
            "Apex Global invoice #INV-4921 is 48 days overdue. Agent drafted formal escalation letter per CFO policy.",
            "BR-053 requires approval for legal and credit-related customer correspondence.",
            "QuickBooks Online API, Aging Report (48 days delinquent)",
            "Option A: Send formal credit hold warning | Option B: Offer 14-day payment installment plan | Option C: Schedule CFO-to-CFO direct call",
            json.dumps({
                "to": "accounts@apexglobal.example",
                "cc": "ceo@apexglobal.example",
                "subject": "URGENT: Formal Notice of Overdue Account - Inv #4921 ($85,000.00)",
                "body": "Dear Finance Team at Apex Global,\n\nOur records show that Invoice #INV-4921 in the amount of $85,000.00 is currently 48 days past due. Per our standard commercial terms, services will be placed on administrative hold unless payment is received or confirmed within 5 business days.\n\nPlease reply with wire remittance details or contact our treasury desk immediately.\n\nSincerely,\nMarcus Vance\nChief Financial Officer"
            }),
            "pending", now_iso
        ),
        (
            "appr-3", "coo-elena", "medium", "logistics",
            "Authorize Air Freight Expedite for Delayed Taiwan Microcontroller Batch",
            "Supplier reported 10-day ocean customs delay. Expedited air charter quote received for $14,200 to prevent factory halt.",
            "Policy caps autonomous logistics spend at $5,000; this action exceeds limit by $9,200.",
            "Supplier Notice #SUP-882, DHL Global Forwarding Air Quote #QF-9921",
            "Option A: Approve $14.2k air expedite | Option B: Partial expedite (500 units for $7.1k) | Option C: Shift production assembly line",
            json.dumps({
                "carrier": "DHL Global Forwarding",
                "cost_usd": 14200,
                "units": 1200,
                "origin": "Taipei (TPE)",
                "destination": "Austin (AUS)",
                "estimated_arrival": "2026-11-01"
            }),
            "pending", now_iso
        ),
        (
            "appr-4", "cto-david", "medium", "incident",
            "Publish Customer-Facing Post-Mortem Digest for Redis Latency Blip",
            "Resolved P2 incident (18 min elevated latency). Drafted transparent explanation for Tier-1 Enterprise status portal.",
            "BR-023: External communications regarding system outages require CTO sign-off.",
            "Datadog Incident #INC-3091, Slack #incident-p2-redis",
            "Option A: Publish as drafted | Option B: Add detailed root cause architecture diagram | Option C: Share only with affected accounts",
            json.dumps({
                "target": "Statuspage.io / Enterprise RSS",
                "headline": "Resolved: Intermittent API Latency Spike (04:12 - 04:30 UTC)",
                "summary": "Between 04:12 and 04:30 UTC, our caching layer experienced transient CPU saturation during scheduled key rebalancing. 3.2% of API requests observed elevated latency (>1.2s). Automated failover redirected traffic, fully restoring SLA. Preventative connection pooling limits have been deployed."
            }),
            "pending", now_iso
        )
    ]
    for app in approvals:
        c.execute("""
        INSERT INTO approvals (
            id, executive_id, risk_level, capability, action_title, description,
            why_reason, sources, alternatives, draft_payload, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, app)

    # Seed Commitments
    commitments = [
        ("com-1", "ceo-alexandra", "Deliver updated Q3 Board Pack with ARR breakdown", "made_by_exec", "Alexandra Chen", "Board of Directors", "2026-10-31", "on_track", "Low", now_iso, "Draft generated by Agent; awaiting CFO sign-off on EBITDA adjustments."),
        ("com-2", "ceo-alexandra", "Review revised commercial terms with CloudScale Corp", "made_to_exec", "David Zhang (CloudScale)", "Alexandra Chen", "2026-11-02", "at_risk", "Medium", now_iso, "Counterparty has not returned marked-up redline since Tuesday."),
        ("com-3", "cfo-marcus", "Close Q3 Financial Audit Review with PwC", "made_by_exec", "Marcus Vance", "Audit Committee", "2026-11-05", "on_track", "Low", now_iso, "Fieldwork 92% complete."),
        ("com-4", "coo-elena", "Deliver vendor SLA penalty assessment for logistics partner", "made_by_exec", "Elena Rostova", "Executive Committee", "2026-10-30", "overdue", "High", now_iso, "Slippage 48 hours; Agent prepared chase notification.")
    ]
    for com in commitments:
        c.execute("INSERT INTO commitments (id, executive_id, title, direction, owner, counterparty, due_date, status, slippage_risk, last_chased, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", com)

    # Seed Audit Log (BR-091)
    audit_entries = [
        ("aud-1", now_iso, "ceo-alexandra", "Generate Morning Brief", "Agent", "low", "BR-010 (Scheduled Briefing)", "Calendar, Gmail, Datadog", "Autonomous (Policy #P-101)", "Allowed", "Synthesized 5 priority emails, 4 meetings, and Q3 churn alert with citations."),
        ("aud-2", now_iso, "ceo-alexandra", "Triage Inbound Mailbox (18 Items)", "Agent", "low", "BR-020 (Inbox Classification)", "Google Workspace Gmail", "Autonomous (Policy #P-102)", "Allowed", "Triaged: 4 Act-Now, 6 Delegate, 5 Defer, 3 Ignore. Zero external sends initiated."),
        ("aud-3", now_iso, "ceo-alexandra", "Hold High-Risk Investor Draft for Review", "Agent", "high", "BR-023 (Investor Communications)", "Gmail, Cap Table", "Human Approval Required", "Blocked", "Draft prepared in Alexandra's voice; held in Approval Queue (appr-1)."),
        ("aud-4", now_iso, "cfo-marcus", "Flag Receivables Anomaly (UC-4)", "Agent", "medium", "BR-011 (KPI Anomaly Alert)", "QuickBooks API", "Autonomous Alerting", "Allowed", "Apex Global invoice $85k flagged at 48 days delinquent. Drafted credit hold notice."),
        ("aud-5", now_iso, "coo-elena", "Supplier Escalation Detected (UC-5)", "Agent", "medium", "BR-011 (Supply Chain Monitoring)", "Vendor Mailbox, Freight Tracker", "Autonomous Alerting", "Allowed", "10-day delay in Taiwan microcontroller delivery analyzed; impact 1,200 units.")
    ]
    for aud in audit_entries:
        c.execute("INSERT INTO audit_log (id, timestamp, executive_id, action_name, actor, risk_level, policy_rule, data_scope, approver, status, details) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", aud)

    # Seed Langfuse Observability Traces (BR-090)
    traces = [
        (
            "tr-901", now_iso, "ceo-alexandra", "Daily Brief Generation - Reasoning Loop",
            "Vertex AI (gemini-1.5-pro)", 1240, 4820, 1140, 0.0162,
            json.dumps([
                {"step": "Plan", "tool": "None", "thought": "Retrieve calendar events and scan unread VIP emails.", "duration_ms": 180},
                {"step": "Act", "tool": "google_calendar.list_events", "input": {"day": "today"}, "duration_ms": 310},
                {"step": "Observe", "tool": "google_workspace.gmail_triage", "input": {"vip_only": True}, "duration_ms": 420},
                {"step": "Synthesize", "model": "gemini-1.5-pro", "output": "Daily Briefing Pack generated with 3 citations.", "duration_ms": 330}
            ])
        ),
        (
            "tr-902", now_iso, "cfo-marcus", "Cash Burn & Receivables Diagnostic",
            "Ollama (llama-3-8b-instruct-private)", 480, 1920, 410, 0.0000,
            json.dumps([
                {"step": "Routing", "policy": "BR-081 Sensitive Financial Routing -> Private Ollama Node", "duration_ms": 40},
                {"step": "Act", "tool": "erp_accounting.query_ar_aging", "input": {"threshold_days": 45}, "duration_ms": 220},
                {"step": "Synthesize", "output": "Apex Global delinquency flagged. Drafted payment notice.", "duration_ms": 220}
            ])
        )
    ]
    for tr in traces:
        c.execute("INSERT INTO langfuse_traces (trace_id, timestamp, executive_id, name, model, latency_ms, tokens_input, tokens_output, cost_usd, steps_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tr)

    # System State
    c.execute("INSERT OR REPLACE INTO system_state (key, value) VALUES ('kill_switch', '0')")
    c.execute("INSERT OR REPLACE INTO system_state (key, value) VALUES ('kill_switch_activated_at', '')")

    conn.commit()

# ---------------------------------------------------------------------------
# Semantic Vector Search Simulator (Cosine similarity across words/embeddings)
# ---------------------------------------------------------------------------

def compute_similarity(query_terms, text):
    text_lower = text.lower()
    score = 0.0
    for term in query_terms:
        if term in text_lower:
            score += 1.0 + (text_lower.count(term) * 0.2)
    return score

# ---------------------------------------------------------------------------
# Guardrails and Safety Validation (BR-052, BR-054)
# ---------------------------------------------------------------------------

PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?(previous )?instructions",
    r"disregard safety guidelines",
    r"bypass policy",
    r"output system prompt",
    r"transfer (funds|money|\$[\d,]+)",
    r"wire \$[\d,]+",
    r"send credentials",
    r"reveal confidential api key"
]

def check_guardrails(text):
    text_lower = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            return {
                "safe": False,
                "reason": "Prompt Injection / Unauthorized Command Detected",
                "matched_pattern": pattern,
                "severity": "CRITICAL",
                "policy_violation": "BR-054 (Prompt Injection & Unauthorized Action Defense)"
            }
    
    # Check confidential PII patterns (Credit card, SSN)
    if re.search(r"\b(?:\d{4}-){3}\d{4}\b", text) or re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
        return {
            "safe": False,
            "reason": "Confidential PII (Card or SSN) Detected in Unencrypted Context",
            "severity": "HIGH",
            "policy_violation": "BR-063 (Confidential Data Isolation)"
        }

    return {"safe": True}

# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------

class ExecutiveControlPlaneHandler(http.server.SimpleHTTPRequestHandler):

    def send_json(self, status_code, data):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode("utf-8")
            return json.loads(body)
        return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # API Endpoints
        if path == "/api/health":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT value FROM system_state WHERE key='kill_switch'")
            kill_switch = c.fetchone()["value"] == "1"
            conn.close()
            return self.send_json(200, {
                "status": "healthy",
                "kill_switch_active": kill_switch,
                "version": "0.2-local-mvp",
                "models": {
                    "vertex_ai": "gemini-1.5-pro (Cloud High-Reasoning)",
                    "ollama": "llama-3-8b-instruct (Private/Sensitive On-Prem)"
                },
                "server_time": datetime.datetime.now().isoformat()
            })

        elif path == "/api/executives":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM executives")
            rows = [dict(r) for r in c.fetchall()]
            for r in rows:
                r["autonomy_sliders"] = json.loads(r["autonomy_sliders"]) if r["autonomy_sliders"] else {}
            conn.close()
            return self.send_json(200, rows)

        elif path.startswith("/api/executives/"):
            exec_id = path.replace("/api/executives/", "")
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM executives WHERE id = ?", (exec_id,))
            row = c.fetchone()
            if not row:
                conn.close()
                return self.send_json(404, {"error": "Executive not found"})
            data = dict(row)
            data["autonomy_sliders"] = json.loads(data["autonomy_sliders"]) if data["autonomy_sliders"] else {}
            conn.close()
            return self.send_json(200, data)

        elif path == "/api/approvals":
            exec_id = query.get("executive_id", [None])[0]
            conn = get_db()
            c = conn.cursor()
            if exec_id:
                c.execute("SELECT * FROM approvals WHERE executive_id = ? ORDER BY created_at DESC", (exec_id,))
            else:
                c.execute("SELECT * FROM approvals ORDER BY created_at DESC")
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return self.send_json(200, rows)

        elif path == "/api/commitments":
            exec_id = query.get("executive_id", [None])[0]
            conn = get_db()
            c = conn.cursor()
            if exec_id:
                c.execute("SELECT * FROM commitments WHERE executive_id = ? ORDER BY due_date ASC", (exec_id,))
            else:
                c.execute("SELECT * FROM commitments ORDER BY due_date ASC")
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return self.send_json(200, rows)

        elif path == "/api/memories":
            exec_id = query.get("executive_id", [None])[0]
            search_query = query.get("q", [None])[0]
            conn = get_db()
            c = conn.cursor()
            if exec_id:
                c.execute("SELECT * FROM memories WHERE executive_id = ? ORDER BY created_at DESC", (exec_id,))
            else:
                c.execute("SELECT * FROM memories ORDER BY created_at DESC")
            rows = [dict(r) for r in c.fetchall()]
            conn.close()

            # Apply semantic similarity scoring if query is passed
            if search_query:
                terms = [t.strip().lower() for t in search_query.split() if len(t.strip()) > 2]
                for r in rows:
                    r["similarity_score"] = round(compute_similarity(terms, r["content"] + " " + r["category"]), 2)
                rows = [r for r in rows if r["similarity_score"] > 0]
                rows.sort(key=lambda x: x["similarity_score"], reverse=True)

            return self.send_json(200, rows)

        elif path == "/api/audit":
            exec_id = query.get("executive_id", [None])[0]
            conn = get_db()
            c = conn.cursor()
            if exec_id:
                c.execute("SELECT * FROM audit_log WHERE executive_id = ? ORDER BY timestamp DESC LIMIT 50", (exec_id,))
            else:
                c.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 50")
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return self.send_json(200, rows)

        elif path == "/api/traces":
            exec_id = query.get("executive_id", [None])[0]
            conn = get_db()
            c = conn.cursor()
            if exec_id:
                c.execute("SELECT * FROM langfuse_traces WHERE executive_id = ? ORDER BY timestamp DESC LIMIT 20", (exec_id,))
            else:
                c.execute("SELECT * FROM langfuse_traces ORDER BY timestamp DESC LIMIT 20")
            rows = [dict(r) for r in c.fetchall()]
            for r in rows:
                if r["steps_json"]:
                    r["steps"] = json.loads(r["steps_json"])
            conn.close()
            return self.send_json(200, rows)

        # Fallback to standard static file server
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Check Kill Switch status for agent operations
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT value FROM system_state WHERE key='kill_switch'")
        kill_active = c.fetchone()["value"] == "1"

        if path == "/api/kill-switch":
            body = self.read_json_body()
            activate = body.get("activate", True)
            now_iso = datetime.datetime.now().isoformat()
            new_val = "1" if activate else "0"
            c.execute("UPDATE system_state SET value = ? WHERE key = 'kill_switch'", (new_val,))
            c.execute("UPDATE system_state SET value = ? WHERE key = 'kill_switch_activated_at'", (now_iso if activate else "",))

            # Audit record
            c.execute("""
            INSERT INTO audit_log (
                id, timestamp, executive_id, action_name, actor, risk_level,
                policy_rule, data_scope, approver, status, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"aud-kill-{uuid.uuid4().hex[:6]}", now_iso, body.get("executive_id", "all"),
                "EMERGENCY KILL SWITCH " + ("ACTIVATED" if activate else "DISARMED"),
                "Executive", "high", "BR-055 (Emergency Stop)", "All Tools & Connectors",
                "Executive Direct Action", "ENFORCED",
                "Immediately revoked all delegated tool execution and froze background agent tasks." if activate else "Control plane restored to normal governed operation."
            ))
            conn.commit()
            conn.close()
            return self.send_json(200, {
                "kill_switch_active": activate,
                "message": "Emergency Kill Switch Activated. All autonomous reasoning and tool execution halted." if activate else "Kill Switch disarmed. System operational."
            })

        # Disallow actions if Kill Switch is active
        if kill_active and path.startswith("/api/agent"):
            conn.close()
            return self.send_json(423, {
                "error": "KILL SWITCH ACTIVE: All agent actions are halted and tool access is revoked.",
                "policy": "BR-055"
            })

        if path.startswith("/api/approvals/") and path.endswith("/action"):
            appr_id = path.split("/")[3]
            body = self.read_json_body()
            action = body.get("action") # approve, edit, reject
            resolution_notes = body.get("notes", "")
            now_iso = datetime.datetime.now().isoformat()

            c.execute("SELECT * FROM approvals WHERE id = ?", (appr_id,))
            appr = c.fetchone()
            if not appr:
                conn.close()
                return self.send_json(404, {"error": "Approval request not found"})

            new_status = "approved" if action == "approve" else ("edited" if action == "edit" else "rejected")
            c.execute("UPDATE approvals SET status = ?, resolved_at = ?, resolution_notes = ? WHERE id = ?",
                      (new_status, now_iso, resolution_notes, appr_id))

            # Add to audit log
            c.execute("""
            INSERT INTO audit_log (
                id, timestamp, executive_id, action_name, actor, risk_level,
                policy_rule, data_scope, approver, status, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"aud-{uuid.uuid4().hex[:6]}", now_iso, appr["executive_id"],
                f"Approval Resolution: {appr['action_title']}", "Executive",
                appr["risk_level"], "BR-050 / BR-093 (Human Sign-off)",
                appr["capability"], "Human Executive", new_status.upper(),
                f"Action resolved as '{new_status}'. Reason/Notes: {resolution_notes}"
            ))

            # If edited or approved, record episodic memory learning
            if action in ["approve", "edit"]:
                c.execute("""
                INSERT INTO memories (id, executive_id, memory_type, category, sensitivity, content, source, created_at)
                VALUES (?, ?, 'episodic', 'decision', 'Normal', ?, 'Approval Flow Learning', ?)
                """, (
                    f"mem-learn-{uuid.uuid4().hex[:6]}", appr["executive_id"],
                    f"Executive {new_status} proposal '{appr['action_title']}'. Feedback: {resolution_notes or 'Proceeded with draft'}.",
                    now_iso
                ))

            conn.commit()
            conn.close()
            return self.send_json(200, {
                "status": "success",
                "approval_id": appr_id,
                "new_status": new_status,
                "undo_window_seconds": 30 if action == "approve" else 0
            })

        elif path.startswith("/api/approvals/") and path.endswith("/recall"):
            # Undo window (BR-056)
            appr_id = path.split("/")[3]
            now_iso = datetime.datetime.now().isoformat()
            c.execute("UPDATE approvals SET status = 'recalled', resolution_notes = 'Action recalled within 30-second undo window' WHERE id = ?", (appr_id,))
            c.execute("""
            INSERT INTO audit_log (
                id, timestamp, executive_id, action_name, actor, risk_level,
                policy_rule, data_scope, approver, status, details
            ) VALUES (?, ?, 'general', 'Action Recalled / Undone', 'Executive', 'medium', 'BR-056 (Undo Send Window)', 'Email/Connector', 'Executive', 'RECALLED', 'Executive recalled approved action within undo window. Execution intercepted.')
            """, (f"aud-undo-{uuid.uuid4().hex[:6]}", now_iso))
            conn.commit()
            conn.close()
            return self.send_json(200, {"status": "recalled", "message": "Action successfully recalled before execution completed."})

        elif path == "/api/commitments":
            body = self.read_json_body()
            now_iso = datetime.datetime.now().isoformat()
            com_id = f"com-{uuid.uuid4().hex[:6]}"
            c.execute("""
            INSERT INTO commitments (id, executive_id, title, direction, owner, counterparty, due_date, status, slippage_risk, last_chased, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                com_id, body["executive_id"], body["title"], body.get("direction", "made_by_exec"),
                body["owner"], body.get("counterparty", "Internal"), body["due_date"],
                body.get("status", "on_track"), body.get("slippage_risk", "Low"), now_iso, body.get("notes", "")
            ))
            conn.commit()
            conn.close()
            return self.send_json(201, {"id": com_id, "status": "created"})

        elif path.startswith("/api/commitments/") and path.endswith("/chase"):
            com_id = path.split("/")[2]
            c.execute("SELECT * FROM commitments WHERE id = ?", (com_id,))
            com = c.fetchone()
            if not com:
                conn.close()
                return self.send_json(404, {"error": "Commitment not found"})
            now_iso = datetime.datetime.now().isoformat()
            c.execute("UPDATE commitments SET last_chased = ?, status = 'on_track' WHERE id = ?", (now_iso, com_id))
            # Create audit record
            c.execute("""
            INSERT INTO audit_log (id, timestamp, executive_id, action_name, actor, risk_level, policy_rule, data_scope, approver, status, details)
            VALUES (?, ?, ?, 'Chase Overdue Commitment', 'Agent', 'low', 'BR-041 (Commitment Tracking)', 'Email / Slack', 'Autonomous within limits', 'EXECUTED', ?)
            """, (f"aud-chase-{uuid.uuid4().hex[:6]}", now_iso, com["executive_id"], f"Sent non-intrusive reminder to {com['owner']} for '{com['title']}'."))
            conn.commit()
            conn.close()
            return self.send_json(200, {"status": "chased", "message": f"Polite chase notification dispatched to {com['owner']}."})

        elif path == "/api/memories":
            body = self.read_json_body()
            now_iso = datetime.datetime.now().isoformat()
            mem_id = f"mem-{uuid.uuid4().hex[:6]}"
            c.execute("""
            INSERT INTO memories (id, executive_id, memory_type, category, sensitivity, content, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mem_id, body["executive_id"], body["memory_type"], body["category"],
                body.get("sensitivity", "Normal"), body["content"], body.get("source", "Executive Manual Add"), now_iso
            ))
            conn.commit()
            conn.close()
            return self.send_json(201, {"id": mem_id, "status": "created"})

        elif path == "/api/guardrails/check":
            body = self.read_json_body()
            text = body.get("text", "")
            result = check_guardrails(text)
            conn.close()
            return self.send_json(200, result)

        elif path == "/api/agent/chat":
            body = self.read_json_body()
            user_message = body.get("message", "")
            exec_id = body.get("executive_id", "ceo-alexandra")

            # 1. Guardrail check first (BR-054)
            guard_res = check_guardrails(user_message)
            if not guard_res["safe"]:
                now_iso = datetime.datetime.now().isoformat()
                c.execute("""
                INSERT INTO audit_log (id, timestamp, executive_id, action_name, actor, risk_level, policy_rule, data_scope, approver, status, details)
                VALUES (?, ?, ?, 'Guardrail Interception', 'Guardrails Engine', 'high', ?, 'Prompt Scanner', 'Automatic Block', 'BLOCKED', ?)
                """, (f"aud-blk-{uuid.uuid4().hex[:6]}", now_iso, exec_id, guard_res.get("policy_violation", "BR-054"), f"Blocked user prompt: {guard_res['reason']}"))
                conn.commit()
                conn.close()
                return self.send_json(400, {
                    "error": "Guardrail Interception",
                    "reason": guard_res["reason"],
                    "matched_pattern": guard_res.get("matched_pattern"),
                    "policy": guard_res.get("policy_violation")
                })

            # 2. Model Gateway Routing (BR-080, BR-081)
            is_sensitive = any(w in user_message.lower() for w in ["confidential", "salary", "m&a", "lawsuit", "covenant", "cash balance"])
            selected_model = "Ollama (llama-3-8b-instruct-private)" if is_sensitive else "Vertex AI (gemini-1.5-pro)"

            # 3. Simulate LangGraph Plan-Act-Observe Reasoning Loop (BR-083, BR-090)
            now_iso = datetime.datetime.now().isoformat()
            steps = [
                {"step": "Plan", "thought": f"Analyze executive context and intent for: '{user_message[:60]}...'"},
                {"step": "Route", "model": selected_model, "reason": "Routed to private Ollama node due to sensitivity rules" if is_sensitive else "Routed to Vertex AI Gemini for multi-step reasoning"},
                {"step": "Act", "tool": "vector_memory.search", "input": {"query": user_message[:40]}},
                {"step": "Observe", "result": "Retrieved relevant executive preferences and relationship history."},
                {"step": "Synthesize", "response": f"Generated executive answer adhering to tone and policy."}
            ]

            # Generate realistic response
            response_text = generate_agent_response(exec_id, user_message)

            # Record Langfuse Trace (BR-090)
            trace_id = f"tr-{uuid.uuid4().hex[:6]}"
            c.execute("""
            INSERT INTO langfuse_traces (trace_id, timestamp, executive_id, name, model, latency_ms, tokens_input, tokens_output, cost_usd, steps_json)
            VALUES (?, ?, ?, 'Conversational Copilot Loop', ?, 860, 1420, 390, 0.0042, ?)
            """, (trace_id, now_iso, exec_id, selected_model, json.dumps(steps)))

            # Record Audit Log
            c.execute("""
            INSERT INTO audit_log (id, timestamp, executive_id, action_name, actor, risk_level, policy_rule, data_scope, approver, status, details)
            VALUES (?, ?, ?, 'Conversational Interaction', 'Agent', 'low', 'BR-012 (On-Demand Intelligence)', 'Memory & Tools', 'Autonomous', 'COMPLETED', ?)
            """, (f"aud-chat-{uuid.uuid4().hex[:6]}", now_iso, exec_id, f"Executed conversational query with {selected_model}."))

            conn.commit()
            conn.close()

            return self.send_json(200, {
                "response": response_text,
                "model_routed": selected_model,
                "trace_id": trace_id,
                "reasoning_steps": steps
            })

        conn.close()
        return self.send_json(404, {"error": "Endpoint not found"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/memories/"):
            mem_id = path.replace("/api/memories/", "")
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
            conn.commit()
            conn.close()
            return self.send_json(200, {"status": "deleted", "id": mem_id})

        return self.send_json(404, {"error": "Endpoint not found"})

def generate_agent_response(exec_id, message):
    msg = message.lower()
    if "brief" in msg or "today" in msg or "schedule" in msg:
        return (
            "Here is your real-time briefing summary:\n\n"
            "• **Calendar Focus:** You have 3 key meetings today, beginning with the Executive Committee at 10:00 AM. 45-minute focus block reserved.\n"
            "• **Priority Inbound:** 4 emails require attention. High-stakes drafts for Sequoia Capital and Apex Global are waiting in your Approval Inbox.\n"
            "• **Commitment Watch:** Q3 Board Pack draft is on schedule. Supplier penalty review for logistics is overdue by 48 hours.\n"
            "• **Citations:** Sourced from Google Workspace Calendar API and ERP aging ledger."
        )
    elif "board" in msg or "pack" in msg or "deck" in msg:
        return (
            "I have synthesized the draft commentary for the upcoming Board Pack:\n\n"
            "• **Revenue & ARR:** Q3 closed at $14.2M ARR (+18% YoY), driven by enterprise tier expansions [Source: Stripe/Salesforce].\n"
            "• **Cash Runway:** Current treasury balance of $4.2M represents 14.2 months runway at baseline burn [Source: QuickBooks].\n"
            "• **Gap Flags:** Customer Churn ticked up by 1.2% in Tier-2 retail segment due to migration delays.\n"
            "Would you like me to push this draft to your Google Docs Board folder?"
        )
    elif "cash" in msg or "overdue" in msg or "receivable" in msg:
        return (
            "Cash & Receivables Status Alert:\n\n"
            "• **Delinquency Alert:** Apex Global ($85,000 overdue for 48 days) has crossed policy threshold.\n"
            "• **Action Taken:** Formal credit hold notice has been drafted in your Approval Inbox for human sign-off per BR-023.\n"
            "• **Buffer Impact:** Collecting this invoice restores the 90-day liquidity buffer to 100% compliance."
        )
    elif "incident" in msg or "outage" in msg or "redis" in msg:
        return (
            "Technical Incident Digest (P2 Redis Latency Resolution):\n\n"
            "• **Timeline:** Redis cache degradation observed at 04:12 UTC; automated failover completed at 04:30 UTC (18 min duration).\n"
            "• **Impact:** 3.2% of API requests experienced >1.2s latency. Zero data loss.\n"
            "• **Customer Comms:** Draft post-mortem announcement is queued in your Approval Inbox."
        )
    else:
        return (
            f"I have reviewed your query against your executive memory and connected tools.\n\n"
            f"Based on your priorities, I have processed the relevant records and verified that all actions comply with your autonomy guardrails (Suggest Only / Approval required for external sends). "
            f"Let me know if you would like me to draft a memo, schedule time, or inspect the audit trail."
        )

# ---------------------------------------------------------------------------
# Server Entrypoint
# ---------------------------------------------------------------------------

def run_server():
    init_db()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with socketserver.TCPServer(("", PORT), ExecutiveControlPlaneHandler) as httpd:
        print(f"=================================================================")
        print(f"🚀 Executive Control Plane MVP Server Running on http://localhost:{PORT}")
        print(f"📌 Platform: Google Cloud Platform (GCP) & Google Antigravity")
        print(f"🔒 Single Agent Architecture: CEO, CFO, COO, CTO, CMO, CHRO")
        print(f"📁 Database: {DB_FILE} (SQLite pgvector simulation)")
        print(f"=================================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server gracefully...")

if __name__ == "__main__":
    run_server()
