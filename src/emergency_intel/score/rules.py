# ---------------------------------------------------------------------------
# Source credibility scores (0–10).
# Matched against source_name (netloc, e.g. "itu.int", "techcrunch.com").
# Partial substring match: key must appear anywhere in source_name.
# Default for unknown sources: 5.0
# ---------------------------------------------------------------------------
SOURCE_CREDIBILITY: dict[str, float] = {
    # Tier 1 — Standards bodies & government agencies (10)
    "itu.int": 10.0,
    "3gpp.org": 10.0,
    "etsi.org": 10.0,
    "ietf.org": 10.0,
    "fcc.gov": 10.0,
    "fema.gov": 10.0,
    "cisa.gov": 10.0,
    "dhs.gov": 10.0,
    "nato.int": 10.0,
    "un.org": 10.0,
    "apco911.org": 10.0,
    "pscr.nist.gov": 10.0,
    # Tier 2 — Academic & major wire services (8–9)
    "ieee.org": 9.0,
    "acm.org": 9.0,
    "arxiv.org": 8.5,
    "reuters.com": 8.5,
    "apnews.com": 8.5,
    "bbc.com": 8.0,
    "bbc.co.uk": 8.0,
    "ft.com": 8.0,
    "wsj.com": 8.0,
    "economist.com": 8.0,
    # Tier 3 — Industry / trade press (6–7)
    "spacenews.com": 7.5,
    "lightreading.com": 7.5,
    "rcrwireless.com": 7.5,
    "aviationweek.com": 7.5,
    "janes.com": 7.5,
    "defensenews.com": 7.0,
    "c4isrnet.com": 7.0,
    "militaryaerospace.com": 7.0,
    "govtech.com": 7.0,
    "fiercelywireless.com": 7.0,
    "fiercewireless.com": 7.0,
    "telecomtv.com": 7.0,
    "sdxcentral.com": 7.0,
    "techcrunch.com": 6.5,
    "wired.com": 6.5,
    "arstechnica.com": 6.5,
    "theregister.com": 6.5,
    "theverge.com": 6.0,
    "zdnet.com": 6.0,
    # Tier 4 — Blogs / social aggregators (3–4)
    "medium.com": 4.0,
    "substack.com": 4.0,
    "reddit.com": 3.0,
    "twitter.com": 3.5,
    "x.com": 3.5,
}

IMPORTANT_TERMS = {
    3: [
        # Policy / procurement / regulatory actions
        "executive order", "federal mandate", "budget allocation",
        "contract awarded", "procurement approved", "regulatory approval",
        "spectrum allocation", "standard published", "standard ratified",

        # Disaster comms — core business (cross-domain phrases, not single words)
        "disaster communication", "post-disaster network", "network recovery",
        "communication recovery", "deployable network", "resilient network",
        "mission-critical communication", "interoperable communications",
        "public safety broadband", "firstnet", "fema", "incident command",
        "disaster recovery", "critical infrastructure protection",

        # AI × Emergency comms intersection — high-value cross-domain signals
        "ai-driven network recovery", "ai network optimization",
        "predictive disaster response", "autonomous network restoration",
        "ai situational awareness", "ai-powered emergency",

        # Satellite × Emergency
        "leo satellite emergency", "satellite communication disaster",
        "direct-to-device emergency", "ntn deployment",
        "direct-to-cell emergency",

        # Drone/Aviation × Comms
        "drone-mounted repeater", "uav communication relay",
        "airborne base station", "aerial communication relay",
        "haps deployment", "airship relay",
    ],
    2: [
        # Comms standards and systems — specific enough to be meaningful
        "mcptt", "mcx", "mcpd", "tetra", "p25", "lmr",
        "broadband lmr", "ng911", "next generation 911",
        "network slicing", "private network", "tactical network",
        "emergency broadband", "mission critical",
        "non-terrestrial network", "ntn", "haps", "aerostat",
        "low earth orbit", "geo satellite", "starlink",

        # Aviation — specific enough
        "bvlos", "uav relay", "autonomous aerial", "evtol",
        "unmanned aerial", "counter-drone", "swarm coordination",
        "high-altitude platform", "stratospheric platform",

        # Disaster / crisis — meaningful phrases
        "disaster response", "humanitarian aid", "crisis management",
        "search and rescue", "mass casualty", "emergency management",
        "continuity of operations", "situational awareness",
        "command and control",

        # AI signals — frontier models and labs worth tracking
        "large language model", "foundation model", "reasoning model",
        "generative ai", "ai agent", "multimodal", "agentic",
        "anthropic", "openai", "deepmind", "meta ai",
        "gpt", "claude", "gemini", "grok", "llama", "mistral",

        # General tech signals
        "partnership", "funding", "pilot program", "field trial",
    ],
    1: [
        # Broad domain signals — relevant but not specific enough alone
        "satellite", "5g", "6g", "spectrum", "broadband",
        "drone", "uav", "uas", "airship",
        "artificial intelligence", "machine learning", "deep learning",
        "neural network", "robotics", "autonomous",
        "wireless", "cellular", "mesh network", "lte", "telecom",
        "first responder", "public safety", "emergency",
        "wildfire", "earthquake", "hurricane", "flood",
        "sensor", "payload", "protocol", "firmware",
    ],
}

HEAT_TERMS = {
    3: [
        # Definitive this-week actions — something concrete happened
        "deployed", "went live", "goes live", "contract signed", "contract awarded",
        "officially launched", "approved by", "enacted", "ratified",
        "emergency declared", "activated", "awarded",
    ],
    2: [
        # In-progress or near-term signals
        "announced", "released", "published", "unveiled",
        "expanded", "upgraded", "filed", "submitted",
        "trial commenced", "pilot launched", "signed agreement",
        "new release",
    ],
    1: [
        # Background / analytical content — lower time urgency
        "analysis", "whitepaper", "survey", "study",
        "report", "review", "outlook", "forecast",
    ],
}
