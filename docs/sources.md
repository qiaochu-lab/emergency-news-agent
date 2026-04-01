# Professional Intelligence Sources Registry

Curated high-quality, actively updated sources for weekly reports in **AI (applied)**, **Drones/UAV**, **Communications (5G/6G, satellite, access networks)**, and **Emergency/Disaster Response**.

Focus: technical depth, practical value, and low noise. This document is the analyst-facing companion to [data/source_registry.json](/Users/chuchu/Desktop/泛应急新闻agent/data/source_registry.json).

## Metadata Standard

Each source should track:

- Name
- URL
- Source type: `news`, `paper`, `blog`, `forum`, `official`, `company`
- Access method: `rss`, `api`, or `web`
- Suggested read depth: `headline`, `summary`, or `fulltext`
- Domain coverage
- Why valuable
- Update frequency
- Signal quality
- Language
- Stable access
- Requires auth

## 1. News / Industry Media

### The Rundown AI

- URL: <https://www.therundown.ai/>
- Domain: AI
- Why valuable: Daily concise summaries of breakthroughs, deployments, and business applications with low hype; useful for spotting deployable AI in drones, comms, and emergency systems.
- Access method: web
- Update frequency: Daily
- Signal quality: High

### DroneLife

- URL: <https://dronelife.com/>
- Domain: Drones
- Why valuable: Trusted coverage of commercial and public-safety UAV deployments, AI integration, wildfire and rescue use cases, and regulatory updates.
- Access method: web
- Update frequency: Multiple times per week
- Signal quality: High

### Commercial UAV News

- URL: <https://www.commercialuavnews.com/>
- Domain: Drones, Emergency Response
- Why valuable: In-depth reporting on BVLOS, autonomy, enterprise deployments, and weekly market insight relevant to public-safety integrators.
- Access method: web
- Update frequency: Weekly newsletter plus frequent articles
- Signal quality: High

### Unmanned Systems Technology

- URL: <https://www.unmannedsystemstechnology.com/>
- Domain: Drones
- Why valuable: Supplier-neutral technical breakdowns of platforms, sensors, autonomy, and integration details useful for engineering assessment.
- Access method: web
- Update frequency: Weekly eBrief plus ongoing posts
- Signal quality: High

### Light Reading (Wireless / 6G)

- URL: <https://www.lightreading.com/wireless/6g>
- Domain: Communications
- Why valuable: Operator- and vendor-level analysis of satellite-terrestrial integration and emergency communications deployments.
- Access method: web
- Update frequency: Multiple times per week
- Signal quality: High

## 2. Academic / Papers / Preprints

### arXiv (cs.AI + cs.RO + cs.NI)

- URL: <https://arxiv.org/list/cs.AI/recent>
- Domain: AI, Drones, Communications
- Why valuable: Primary feed for applied papers on autonomy, 6G protocols, AI sensing, and disaster response algorithms.
- Access method: api
- Update frequency: Daily
- Signal quality: High

### Import AI

- URL: <https://jack-clark.net/>
- Domain: AI, Policy
- Why valuable: High-signal weekly analysis of key papers with real-world implications for autonomy, resilience, and emergency technology.
- Access method: web
- Update frequency: Weekly
- Signal quality: High

### Papers With Code

- URL: <https://paperswithcode.com/>
- Domain: AI, Drones
- Why valuable: Connects papers to code, benchmarks, and implementations for faster validation of practical algorithms.
- Access method: web
- Update frequency: Daily
- Signal quality: High

## 3. Technical Blogs / Experts

### AlphaSignal

- URL: <https://alphasignal.ai/>
- Domain: AI
- Why valuable: Practical summaries of models, papers, GitHub repos, and edge/hardware developments.
- Access method: web
- Update frequency: Daily summaries and weekly deep dives
- Signal quality: High

### The Batch

- URL: <https://www.deeplearning.ai/the-batch/>
- Domain: AI
- Why valuable: Curated weekly developments with strong production-oriented commentary.
- Access method: web
- Update frequency: Weekly
- Signal quality: High

### Oscar Liang

- URL: <https://oscarliang.com/>
- Domain: Drones
- Why valuable: Hands-on teardowns, firmware, autonomy, and hardware integration guides useful for operator and integrator awareness.
- Access method: web
- Update frequency: Weekly+
- Signal quality: High

## 4. Forums / Communities

### r/MachineLearning

- URL: <https://www.reddit.com/r/MachineLearning/>
- Domain: AI
- Why valuable: Useful for high-signal paper discussions and implementation threads.
- Access method: web
- Update frequency: Daily
- Signal quality: High

### r/drones

- URL: <https://www.reddit.com/r/drones/>
- Domain: Drones
- Why valuable: Operator discussions on deployments, payloads, regulations, and field practices.
- Access method: web
- Update frequency: Daily
- Signal quality: High

### r/EmergencyManagement

- URL: <https://www.reddit.com/r/EmergencyManagement/>
- Domain: Emergency Response
- Why valuable: Practitioner feedback on what actually works in incidents and public-safety operations.
- Access method: web
- Update frequency: Daily
- Signal quality: High

### X (Jack Clark)

- URL: <https://x.com/jackclarkSF>
- Domain: AI
- Why valuable: Fast commentary on frontier papers and implications from a highly informed source.
- Access method: api
- Update frequency: Frequent
- Signal quality: High

## 5. Government / Institutions / Labs

### DARPA

- URL: <https://www.darpa.mil/>
- Domain: AI, Drones, Communications, Emergency Response
- Why valuable: Early signals on autonomy, resilient communications, and disaster technology programs before commercialization.
- Access method: web
- Update frequency: Ongoing program announcements
- Signal quality: High

### NIST Public Safety Communications Research (PSCR)

- URL: <https://www.nist.gov/public-safety-communications-research>
- Domain: Communications, Drones, Emergency Response
- Why valuable: Standards, testbeds, drone challenges, and validated performance data for public-safety systems.
- Access method: web
- Update frequency: Quarterly challenges plus reports
- Signal quality: High

### 3GPP

- URL: <https://www.3gpp.org/>
- Domain: Communications
- Why valuable: Official specifications and release information on NTN integration and emergency communications features.
- Access method: web
- Update frequency: Quarterly releases plus newsletters
- Signal quality: High

### PNNL – Rapid Analytics for Disaster Response (RADR)

- URL: <https://www.pnnl.gov/projects/rapid-analytics-disaster-response>
- Domain: AI, Drones, Communications, Emergency Response
- Why valuable: Open AI tools for multimodal imagery analysis and damage assessment used in real incidents.
- Access method: web
- Update frequency: Project-driven
- Signal quality: High

## 6. Companies / Product Blogs

### OpenAI Blog

- URL: <https://openai.com/blog>
- Domain: AI
- Why valuable: Direct announcements of model capabilities that may affect autonomy, multimodal reasoning, and command workflows.
- Access method: web
- Update frequency: Frequent
- Signal quality: High

### Skydio Blog / News

- URL: <https://www.skydio.com/blog>
- Domain: Drones, AI, Emergency Response
- Why valuable: Enterprise autonomy and public-safety case studies from a leading drone platform.
- Access method: web
- Update frequency: Monthly+
- Signal quality: High

### Ericsson Blog

- URL: <https://www.ericsson.com/en/blog>
- Domain: Communications
- Why valuable: Technical material on NTN, private networks, resilience, and operator-grade communications.
- Access method: web
- Update frequency: Monthly
- Signal quality: High

## Recommended Starting Set

If you want the first fully operational weekly pipeline to stay lean, start with:

- The Rundown AI
- DroneLife
- Commercial UAV News
- Light Reading
- arXiv
- Import AI
- NIST PSCR
- DARPA
- OpenAI Blog
- Skydio Blog

## Implementation Notes

- `rss` and `api` sources should be prioritized first for automation stability.
- `web` sources may need site-specific extraction rules later.
- Forums and X should be treated as secondary intelligence and low-trust evidence unless corroborated elsewhere.
- Newsletters can be ingested later through mailbox forwarding or manual copy-to-ingest workflows.

## Read Depth Guidance

To support research-note style output, not all sources should be read at the same depth.

### `headline`

Use for:

- hotlists
- forum threads
- X / social signals
- weak-signal discovery

Purpose:

- topic discovery
- trend detection
- auxiliary corroboration

### `summary`

Use for:

- RSS feeds with useful descriptions
- paper abstracts
- structured API feeds

Purpose:

- initial triage
- relevance scoring
- early-stage weekly candidate selection

### `fulltext`

Use for:

- official announcements
- company technical blogs
- deep industry analysis
- items selected into weekly report body

Purpose:

- extract the original argument and key claims
- support “event overview + analysis judgment” writing
- avoid title-only rewriting in final reports

Recommended rule:

- sources may default to `headline` or `summary`
- but any item entering the main report body should be eligible for `fulltext` enrichment

See also:

- `docs/content_ingestion_strategy.md`
