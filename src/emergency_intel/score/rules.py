IMPORTANT_TERMS = {
    3: [
        # Original high-weight terms (all lowercase — text is lowercased before matching)
        "regulation", "standard", "deployment", "procurement",
        "emergency response", "search and rescue",
        # Emergency response additions
        "first responder", "public safety", "disaster relief",
        "critical infrastructure", "mass casualty", "incident command",
        "emergency management", "fema", "firstnet", "public safety broadband",
        "wildfire response", "flood response", "disaster recovery",
        "mission critical communications", "interoperable communications",
        # Official signals
        "executive order", "federal mandate", "budget allocation",
    ],
    2: [
        # Original medium-weight terms
        "partnership", "funding", "trial", "pilot", "research", "satellite",
        # Emergency & resilience additions
        "resilience", "continuity of operations", "interoperability",
        "mission critical", "command and control", "situational awareness",
        "disaster response", "humanitarian aid", "crisis management",
        "public safety network", "emergency broadband", "tactical network",
        "search rescue", "wildfire", "earthquake", "hurricane response",
        # Technology signals
        "autonomous system", "swarm", "network slicing", "private network",
        "non-terrestrial network", "ntn", "low-altitude",
        # AI / agent signals (lowercase)
        "large language model", "llm", "generative ai", "foundation model",
        "ai agent", "multimodal", "real-time ai", "ai-powered",
        "reasoning model", "agentic", "context window", "fine-tuning",
        "alignment", "safety research", "inference", "benchmark",
        "anthropic", "claude", "openai", "gemini", "deepmind",
        "gpt", "o3", "o4", "grok", "mistral", "llama",
        # Drone / airspace signals
        "unmanned aerial", "uas", "uav", "bvlos", "utm", "drone response",
        "counter-drone", "aerial survey", "low altitude",
        # Communications signals
        "5g", "6g", "spectrum", "broadband", "cellular", "satellite communication",
    ],
    1: [
        # Original low-weight terms
        "update", "launch", "paper", "release",
        # Additional signals
        "sensor", "detection", "autonomous", "communication system",
        "payload", "firmware", "protocol",
        # General AI/tech signals
        "artificial intelligence", "machine learning", "deep learning",
        "neural network", "robotics", "automation",
        # AI builder / developer signals
        "mcp", "tool use", "prompt", "token", "embedding", "rag",
        "agent loop", "chain of thought", "system prompt", "api",
    ],
}

HEAT_TERMS = {
    3: ["breaking", "major", "urgent", "critical alert", "emergency declared"],
    2: ["this week", "announced", "new", "deployed", "approved", "signed", "launches", "released"],
    1: ["report", "blog", "study", "analysis", "review"],
}
