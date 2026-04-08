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
