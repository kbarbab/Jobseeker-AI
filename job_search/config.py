import os

# Tailoring runs via the Claude Code CLI (`claude -p`) against the user's Claude
# subscription (see job_search/tailor.py) rather than metered API billing — no
# ANTHROPIC_API_KEY here by design. TAILOR_MODEL is optional; if unset, Claude
# Code uses its own default model.
TAILOR_MODEL = os.environ.get("TAILOR_MODEL", "")

ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
# Comma-separated Adzuna country codes to search (each is a separate API call).
# Default targets Australia + Europe per the user's actual relocation preference —
# not the US. Adzuna's supported European codes: at, de, fr, gb, it, nl, pl.
ADZUNA_COUNTRIES = [
    c.strip() for c in os.environ.get("ADZUNA_COUNTRIES", "au,gb,de,nl,at,fr,it,pl").split(",") if c.strip()
]

JOOBLE_API_KEY = os.environ.get("JOOBLE_API_KEY", "")

THEMUSE_API_KEY = os.environ.get("THEMUSE_API_KEY", "")

# Direct-company job boards — no API key needed, these are public JSON APIs the
# ATS vendors themselves publish for embedding a company's listings on their own
# careers page (not scraping). Add/remove board tokens (found in the company's
# careers page URL, e.g. boards.greenhouse.io/<token>, jobs.lever.co/<token>,
# jobs.ashbyhq.com/<token>) as a comma-separated list.
#
# The defaults below are a starter pool (sourced from github.com/santifer/career-ops's
# portals.example.yml — originally curated for AI/ML roles, so most of these are
# NOT .NET shops). That's harmless: the downstream .NET keyword filter excludes
# irrelevant postings automatically, and an occasional stale/renamed slug is
# logged and skipped per-company rather than breaking the run. Treat this as a
# volume-over-precision starting point — swap in companies you know use .NET.
_DEFAULT_GREENHOUSE = (
    "anthropic,polyai,parloa,intercom,humeai,speechmatics,airtable,vercel,temporal,"
    "arizeai,runpod,coreweave,gleanwork,boomilp,blackforestlabs,helsing,celonis,"
    "contentful,getyourguide,hellofresh,n26,traderepublicbank,sumup,scandit,templafy,"
    "amplemarket,wayve,isomorphiclabs,physicsx,stabilityai,planetscale,factorial,"
    "runwayml,hightouch"
)
_DEFAULT_LEVER = "mistral,palantir,qonto,forto,pigment,diabolocom,spotify,vinted,getir"
_DEFAULT_ASHBY = (
    "cohere,langchain,pinecone,elevenlabs,deepgram,vapi,bland,lindy,n8n,zapier,"
    "AlephAlpha,DeepL,attio,tinybird,clarity-ai,travelperk,lakera.ai,cradlebio,"
    "photoroom,lovable,legora,corti,pleo,perplexity,claylabs,workos,supabase,resend,"
    "clerk,inngest,synthesia,faculty,causaly"
)

# os.environ.get's default only applies when the var is unset, not when it's
# present-but-empty (e.g. the blank "GREENHOUSE_COMPANIES=" line in .env.example)
# — fall back to the starter pool explicitly, same fix as NOTIFY_TO above.
GREENHOUSE_COMPANIES = [c.strip() for c in (os.environ.get("GREENHOUSE_COMPANIES") or _DEFAULT_GREENHOUSE).split(",") if c.strip()]
LEVER_COMPANIES = [c.strip() for c in (os.environ.get("LEVER_COMPANIES") or _DEFAULT_LEVER).split(",") if c.strip()]
ASHBY_COMPANIES = [c.strip() for c in (os.environ.get("ASHBY_COMPANIES") or _DEFAULT_ASHBY).split(",") if c.strip()]

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
# os.environ.get's default only applies when the var is unset, not when it's
# present-but-empty (e.g. a blank "NOTIFY_TO=" line in .env) — fall back explicitly.
NOTIFY_TO = os.environ.get("NOTIFY_TO") or GMAIL_ADDRESS

# Set to "true" to enable the optional, lower-trust LinkedIn/Indeed public
# search-results check. Off by default — see job_search/sources/linkedin_indeed.py
# for the rules this module follows before turning it on.
ENABLE_LINKEDIN_INDEED = os.environ.get("ENABLE_LINKEDIN_INDEED", "false").lower() == "true"

# Search queries sent to sources that restrict results server-side by a
# free-text query (Adzuna, Remotive, Jooble — see main.py's QUERY_FILTERED_SOURCES).
# Company-board sources (Greenhouse/Lever/Ashby) and RemoteOK/The Muse ignore
# this entirely and fetch everything, relying on the local role filter below
# instead — for those, widening AGENTIC_AI_KEYWORDS is what matters, not this.
JOB_QUERY = os.environ.get("JOB_QUERY", ".NET developer")
AI_JOB_QUERY = os.environ.get("AI_JOB_QUERY", "Agentic AI Engineer")

# Coarse keyword pre-filters (case-insensitive substring match against title+description).
DOTNET_KEYWORDS = [
    ".net", "dotnet", "asp.net", "c#", "csharp", "entity framework",
    "blazor", "xamarin", ".net core", ".net framework",
]

# Second target role category, alongside .NET — a job matches if it hits EITHER
# category (still combined with the visa/relocation + region filters below).
# Added specifically because the AI/ML-heavy default company pool (career-ops'
# list) was producing zero real .NET matches — this makes that fetch volume
# actually useful, and is a real adjacent direction given hands-on experience
# building this very agentic pipeline (see base_resume.json's projects section).
AGENTIC_AI_KEYWORDS = [
    "agentic ai", "agentic", "ai agent", "ai agents", "llm agent",
    "autonomous agent", "multi-agent", "tool use", "tool calling",
    "llm engineer", "llm engineering", "applied ai engineer",
    "machine learning engineer", "ml engineer", "genai", "gen ai",
    "generative ai engineer", "prompt engineering", "rag pipeline",
    "retrieval augmented generation", "langchain", "langgraph",
]

VISA_RELOCATION_KEYWORDS = [
    "visa sponsorship", "visa sponsor", "will sponsor", "sponsorship available",
    "relocation assistance", "relocation package", "relocation support",
    "relocate", "work permit assistance", "h-1b", "h1b", "sponsor visa",
    "international candidates welcome", "provide sponsorship",
]

# Common negated phrasings that contain a VISA_RELOCATION_KEYWORDS hit but mean
# the opposite — e.g. "not eligible for visa sponsorship" contains "visa
# sponsorship". Checked as a veto after a keyword match, not a replacement for it.
VISA_NEGATION_PHRASES = [
    "not eligible for visa sponsorship", "not eligible for sponsorship",
    "no visa sponsorship", "not able to sponsor", "unable to sponsor",
    "cannot sponsor", "can not sponsor", "does not sponsor", "will not sponsor",
    "won't sponsor", "without the need for visa sponsorship",
    "not provide visa sponsorship", "does not provide visa sponsorship",
    "no sponsorship available", "not offer sponsorship", "not offer visa sponsorship",
    "without requiring sponsorship", "not require sponsorship",
    "unable to offer visa sponsorship", "unable to provide visa sponsorship",
    "unable to offer sponsorship",
]

# Coarse location allowlist — jobs must mention one of these to pass the region
# filter. Covers Australia + Europe broadly (not just the countries searched via
# Adzuna above) since sources like Greenhouse/Lever/Ashby surface listings from
# companies with offices anywhere in Europe, not a fixed country list.
TARGET_REGION_KEYWORDS = [
    "australia", "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra",
    "united kingdom", " uk", "uk,", "london", "manchester", "edinburgh", "belfast",
    "germany", "berlin", "munich", "hamburg", "frankfurt", "cologne", "stuttgart",
    "netherlands", "amsterdam", "rotterdam", "the hague", "eindhoven", "utrecht",
    "austria", "vienna",
    "france", "paris", "lyon", "toulouse",
    "italy", "milan", "rome", "turin",
    "poland", "warsaw", "krakow", "wroclaw",
    "ireland", "dublin", "cork",
    "spain", "madrid", "barcelona", "valencia",
    "portugal", "lisbon", "porto",
    "sweden", "stockholm", "gothenburg",
    "denmark", "copenhagen", "aarhus",
    "switzerland", "zurich", "geneva", "basel",
    "belgium", "brussels", "antwerp",
    "finland", "helsinki",
    "norway", "oslo",
    "czech republic", "czechia", "prague",
    "romania", "bucharest", "cluj",
    "hungary", "budapest",
    "greece", "athens",
    "bulgaria", "sofia",
    "croatia", "zagreb",
    "slovakia", "bratislava",
    "slovenia", "ljubljana",
    "estonia", "tallinn",
    "latvia", "riga",
    "lithuania", "vilnius",
    "luxembourg",
    "serbia", "belgrade",
    "iceland", "reykjavik",
    "malta",
    "cyprus",
    "europe", "eu ", "emea",
    # Fully remote/global roles impose no geographic restriction, so they're
    # compatible with being based in Australia or Europe even if not named.
    "remote", "worldwide", "anywhere",
]

SEEN_JOBS_PATH = os.path.join(os.path.dirname(__file__), "seen_jobs.json")
BASE_RESUME_PATH = os.path.join(os.path.dirname(__file__), "base_resume.json")
DRAFTS_DIR = os.path.join(os.path.dirname(__file__), "drafts")
