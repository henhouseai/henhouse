# Henhouse Distributed Knowledge Architecture

## Part I: General System Architecture

### Vision Overview

The Henhouse system is designed as a three-tier distributed knowledge management platform that enables federated content curation and aggregation. The architecture implements a **hybrid centralized-decentralized model** where individual domain authorities maintain canonical datasets while participants run independent aggregation nodes that selectively replicate and extend content from multiple sources.

This maps closely to **content-addressed storage** systems like IPFS, **federated social networks** like ActivityPub, and **selective replication** patterns from BitTorrent, but optimized for structured knowledge management rather than file sharing or social media.

## Three-Tier Architecture

### Tier 1: Authoritative Layer (MySQL Core) - **CURRENT**
- **Purpose**: Canonical source of truth for specific domains
- **Technology**: MySQL with full relational schema *(implemented)*
- **Features**: ACID transactions, complex queries, joins, constraints *(implemented)*
- **Access Control**: Four-tier system (Guest → Verified → Admin → Root) *(implemented)*
- **MCP Integration**: Core business logic accessible through MCP backend alongside other interfaces *(implemented)*
- **Authority Model**: Each domain expert maintains their own authoritative instance *(Phase 1 - planned)*

### Tier 2: Cache Layer (Flat JSON Store) - **CURRENT**
- **Purpose**: Denormalized snapshots for fast browsing performance
- **Technology**: Single-table MySQL *(implemented with daemon maintenance)*
- **Data Format**: Complete JSON objects containing all relational data needed for rehydration *(implemented)*
- **Function**: Separates read performance from write operations, prevents editing locks from affecting browsers *(implemented)*
- **Versioning**: Timestamp-based cache invalidation with last_modified and cache_generated_at tracking *(implemented)*

### Tier 3: Aggregator Layer (Federated Nodes) - **PLANNED**
- **Purpose**: Independent nodes that selectively replicate from multiple authorities *(Phase 1-2)*
- **Technology**: JSON blob consumption with local override capabilities *(Phase 2)*
- **Distribution Model**: Pull-based selective replication similar to BitTorrent's piece selection *(Phase 3-5)*
- **Local Autonomy**: Nodes can layer local modifications without affecting upstream sources *(Phase 2)*
- **Redundancy**: Automatic content mirroring with **reachability-based garbage collection** *(Phase 5)*

## MCP-Integrated Design

### Universal Business Logic Access - **CURRENT**
All interaction methods access the same core business logic engine through different backends:
- **Browser UI**: Fetch API → HTTP backend → Business logic → MySQL *(implemented)*
- **CLI Interface**: Direct access to business logic for scripting, testing, and local operations *(implemented)*
- **Agent Interface**: MCP backend → Business logic for autonomous curation and management *(implemented)*
- **Maintenance Backend**: Daemon-driven job processing for automated operations *(implemented)*

### Agent-Driven Curation - **MIXED**
- **Admin-tier agents**: Perform sandboxed operations *(current)*, create merge proposals *(Phase 2)*
- **Root-tier agents**: Approve/reject proposals *(Phase 2)*, manage authoritative state *(current)*
- **Consensus agents**: Cross-reference multiple sources to detect patterns *(Phase 3-4)*
- **Maintenance agents**: Handle namespace remapping when authorities disappear *(Phase 4-5)*

## Authority and Trust Model

### Four-Tier Access Control - **MIXED**
1. **Guest**: Read-only access to public data *(implemented)*
2. **Verified**: Placeholder tier for future authentication systems *(not implemented - low priority)*
   - Could use magic links, accounts, or other auth methods per-node
   - Database access scope would be configurable per installation
   - May feed into approval queues or admin agent review workflows
3. **Admin**: Can create/modify in sandbox *(implemented)*, proposals queue for approval *(Phase 2)*
4. **Root**: Full authority to approve changes and manage authoritative state *(implemented)*

### Unix-Level Security Integration - **CURRENT**
- File system permissions enforce sandboxing for agent operations *(implemented)*
- MySQL permissions layer provides database-level access control *(implemented)*
- SSH key-based identity for inter-node communication *(implemented for local, Phase 1 for distributed)*
- HTTPS with per-installation authentication for web access *(implemented)*

### Trust Token System - **BRAINSTORMING/FUTURE**
*Note: These are conceptual ideas, not finalized designs*
- **Provenance Tracking**: Every object maintains source chain and modification history *(Phase 2-3, design TBD)*
- **Consensus Detection**: Automatic identification when multiple independent sources agree *(Phase 3-4, approach uncertain)*
- **Trust Scoring**: Reputation system based on accepted contributions over time *(Phase 4+, may not implement)*
- **Evidence Counting**: Threshold-based acceptance when sufficient independent sources concur *(Phase 3-4, algorithm TBD)*

## Distribution and Redundancy

### Federated Resilience Without P2P Complexity
- **Selective Replication**: Nodes automatically cache content they reference (similar to BitTorrent's **opportunistic caching**)
- **Authority Succession**: When an authority becomes unavailable, the network can establish new canonical sources through **emergent consensus**
- **Data Reconstruction**: Any node can bootstrap replacement authority from cached replicas
- **Reachability-Based Garbage Collection**: Content persists only while nodes maintain references to it

### Namespace and Identity Management - **BRAINSTORMING**
*Note: These are open design questions needing expert input*

- **Global Unique IDs**: Combination of namespace + local ID (similar to web URLs) *(design TBD)*
  - Local IDs can start at 1 and increment naturally (like odometer pride in low numbers)
  - No need to reserve ID blocks or use unwieldy UUIDs for local operations
  - Global uniqueness achieved through namespace prefix (e.g., `puzzles.example.com/1234`)

- **Authority Namespaces**: Likely domain-based rather than inventing new protocol *(design TBD)*
  - Leverages existing DNS infrastructure and familiarity
  - **Risk**: Domain expiration could allow namespace hijacking
  - **Mitigation**: Consensus-based detection when authority changes hands unexpectedly
  - Agents could automatically handle legitimate domain migrations

- **Version Tracking**: Timestamp-based cache invalidation with last_modified and cache_generated_at tracking *(implemented)*

- **Source Attribution**: Complete provenance chain for every data element *(Phase 2-3)*

*Open questions: How to handle domain transfers? Should we use DNS TXT records for authority verification? Alternative namespace schemes?*

## Human-in-the-Loop Design

### Passive Curation Model
Rather than requiring explicit curation overhead, the system implements **implicit consensus** through natural usage patterns:
- **Selection Signals**: What nodes choose to replicate reveals content value
- **Local Modifications**: Node-level corrections indicate data quality issues  
- **Usage Patterns**: Access frequency and reference counts indicate content importance
- **Emergent Consensus**: Multiple independent similar modifications suggest canonical updates needed

### Automated Consensus Detection
- **Pattern Recognition**: Agents identify when multiple nodes make similar modifications (**convergent editing**)
- **Trust Weighting**: Contributions weighted by source reputation and independence (**web of trust** model)
- **Threshold-Based Acceptance**: Automatic promotion to canonical when sufficient consensus exists (**quorum-based decisions**)
- **Human Override**: Authority-tier users can always intervene in automated decisions

## Practical Implementation Strategy

### Current Henhouse Integration - **FOUNDATION READY**
The aggregator layer builds directly on existing Henhouse infrastructure:
- **Page System**: Leverage existing hierarchical page structure for content organization *(extensible via class inheritance)*
  - Authority nodes can define custom page types through derived Python classes
  - Custom database schemas only needed at the authoritative source
  - Aggregators consume flattened cache data regardless of source implementation details
- **Inter-Node Communication**: Primarily through MCP backend for both human and automated access *(Phase 1)*
  - Guest tier: Anonymous cross-node fetching via MCP Gateway dispatch
  - Verified tier: IP-whitelisted nodes with enhanced MCP privileges  
  - Trusted nodes: Hard-coded IP addresses in MySQL for full cross-node operations
- **User Management**: IP-based verification combined with existing tier system *(Phase 1)*
- **Transaction System**: Apply existing atomic operation patterns to multi-source updates *(Phase 2)*

### Development Phases
1. **Phase 1**: Extend cache system to support external source ingestion
2. **Phase 2**: Implement local override and merge proposal mechanisms
3. **Phase 3**: Add consensus detection and automated acceptance rules
4. **Phase 4**: Deploy agent-driven curation and maintenance systems
5. **Phase 5**: Enable peer discovery and redundancy management

---

## Part II: Puzzle Collection Application

### Domain-Specific Implementation

The puzzle collection ecosystem demonstrates how the general architecture serves a specific knowledge domain:

### Participant Roles and Authority Emergence
*Note: Roles are fluid and authority emerges through two distinct mechanisms*

#### Natural Authority
- **Individual Creators**: Designers & manufacturers gain automatic authority by establishing their own domain/node
- **Guild/Organization Hosting**: Creators can become verified/admin users on established nodes (e.g., puzzle makers guild)
  - Provides authority without requiring individual site maintenance
  - Guild becomes trusted repository and known source for multiple creators
  - Can scale from hosting service to comprehensive global database if desired
- **First-Mover Advantage**: Early participation allows creators to control how their work is presented
- **Quality Control**: Original sources can dictate the canonical representation of their portfolio/catalog

#### Surrogate Authority  
- **Collectors/Experts**: Fill voids when designers are inactive, deceased, or haven't joined the system
- **Pointer-Based Recognition**: Authority emerges when aggregators redirect their source pointers to new nodes
- **Organic Evolution**: No central authority or tokens - recognition happens through individual aggregator choices
- **Torch Passing**: Previous authorities can explicitly yield by redirecting their own pointers
- **Quality-Driven**: Nodes gain recognition by improving existing records with corrections, additions, or better organization
- **Unpoliced System**: Individual aggregators free to point to any source, even unreliable ones - caveat emptor

#### Evolutionary Dynamics
- **Positive Incentives**: System motivates designers to participate early rather than risk others defining their legacy
- **Quality-Based Override**: Late-joining designers must compete on contribution quality, not just identity
- **Virtuous Cycle**: Better data attracts more participants, which attracts better data
- **Community Benefit**: Late joiners find existing data to build upon rather than starting from scratch

### Multi-Domain Aggregation
The framework supports collectors with diverse interests across multiple domains:

- **Cross-Domain Collections**: Single aggregator can pull from puzzle authorities, baseball card authorities, coins, stamps, knives, etc.
- **Unified Management**: Same collection management tools work across all item types
- **Domain-Agnostic Framework**: Underlying system handles any content type through the flattened cache layer

### Privacy and Anonymity Options
Collectors can participate at different levels of public visibility:

- **Public Profiles**: Full showcase with collector identity and detailed collection display
- **Semi-Anonymous**: Participate in market intelligence without revealing personal identity
- **Anonymous Nodes**: Contribute to ecosystem data (e.g., "Collection Node 14A12") without personal attribution
- **Security Considerations**: Protect against targeting while still accessing market data and want-list functionality

### Value Proposition for Puzzle Community
- **Collectors**: Build comprehensive databases across multiple domains, manage inventory, showcase selectively
- **Designers**: Establish authoritative presence, receive community contributions, control their legacy
- **Manufacturers & Artisans**: Portfolio showcase, marketing channel, and sales platform in one system
- **Researchers**: Access distributed knowledge without depending on single sources
- **Community**: Preserves knowledge across domains through distributed redundancy

### Extended Value Applications
- **Market Intelligence**: Real-time visibility into item desirability across all domains
- **Transaction Facilitation**: Connect buyers and sellers through expressed interest while respecting privacy preferences
- **Dynamic Valuation**: Market-driven pricing through aggregated demand signals
- **Collection Analytics**: Understand rarity, trends, and market dynamics across the entire ecosystem

### Monetization and Sustainability Model *(Highly Speculative - Open Problems)*
**Disclaimer: This section represents hypothetical concepts with significant unsolved technical and practical challenges**

The decentralized nature of the system makes monetization extraction and distribution extremely complex. Current thinking around contribution-based attribution:

#### Content Creation Incentives
Transaction fees (e.g., 3% of sale price) distributed based on actual content contributions:

- **Designer**: ~25% for original design creation
- **Manufacturer**: ~25% for production and manufacturing
- **Content Contributors**: ~10% each for substantive additions:
  - First photographer/reviewer who documented an instance
  - Production run data contributor  
  - Condition assessment contributor
  - Custom photography/documentation
- **System Infrastructure**: Remaining percentage for node maintenance and operations

#### Contribution-Based Attribution
- **Active Contributors**: Only those who add original content (photos, data, reviews) receive revenue shares
- **Passive Aggregators**: Users who simply click "I have this" without adding content don't claim attribution
- **Cumulative Benefits**: Creators who provide comprehensive portfolios can claim multiple attribution tiers
- **Incentive Alignment**: System rewards content creation and quality documentation over passive consumption

#### Multi-Tier Recognition
Each hierarchical content level (design → production run → individual instance) can have separate attribution:
- Encourages detailed, structured content creation
- Rewards both broad portfolio development and specific instance documentation
- Creates sustainable incentives for ongoing content improvement

#### Unsolved Implementation Challenges
**Major open questions with no clear solutions:**

- **Payment Extraction**: How to collect transaction fees in a decentralized system?
- **Distribution Mechanism**: How to reliably distribute payments to multiple contributors across different nodes?
- **Verification**: How to prevent gaming of attribution claims?
- **Enforcement**: What incentivizes voluntary participation in payment systems?
- **Ownership Updates**: How pointer updates reflect ownership changes without central authority?

**Possible approaches (all problematic):**
- Guild-mediated transactions (introduces centralization)
- Voluntary "sales tax" system (relies on honor system)
- Reputation-based enforcement (unclear penalties for non-compliance)
- Blockchain/smart contracts (adds complexity, contradicts simplicity goals)

*This remains an open design problem requiring expert input on decentralized payment systems*

### Three Primary Workflows

#### Top-Down (Designer-Initiated)
1. **Designer Publication**: Creator establishes authoritative portfolio on their node
2. **Manufacturer Connection**: Producers link their reproductions to existing designer records
3. **Collector Aggregation**: Users click "I have this" or augment with personal data
4. **Deterministic Structure**: Clean hierarchy from design → production → ownership

#### Middle-Out (Manufacturer-Initiated)  
1. **Manufacturer Documentation**: Producer creates records for items they've made
2. **Designer Placeholder**: May create top-level designer records if none exist
3. **Authority Evolution**: Original designer may later claim/transfer ownership
4. **Legacy Stewardship**: Manufacturer may remain authority for deceased/inactive designers

#### Bottom-Up (Collector-Initiated)
1. **Collector Documentation**: User catalogs items with unknown or unconnected provenance
2. **Reverse Engineering**: Building designer/manufacturer records from physical items
3. **Due Diligence Challenge**: Responsibility to search for existing records before creating new ones
4. **Automatic Authority**: First documenter becomes de facto authority for that item/design
5. **Natural Evolution**: Better authorities may emerge over time, requiring collector migration decisions
6. **Consensus Through Migration**: Aggregate of individual pointer redirections creates emergent consensus
7. **Agent-Informed Decisions**: Curator agents observe network migration patterns to suggest authority updates to node operators

#### Workflow Characteristics
- **Top-Down**: Deterministic, clean hierarchies, clear attribution
- **Middle-Out**: Balanced, potential ownership transfers, stewardship roles
- **Bottom-Up**: Individual stability with network-level evolution

#### Data Stability vs. Authority Evolution
**Individual Collector Perspective**: Stable personal metadata with dynamic upstream updates
- Clicking "I have this" caches local copy for redundancy while maintaining live upstream connection
- Personal metadata (location, condition, price paid, acquisition details) remains stable
- Core item data continues updating from current upstream authority
- Collectors can retarget their upstream pointer to different authorities
- Like changing your GPS route - your destination stays the same, but the path updates

**Network Perspective**: Organic evolution with reachability-based garbage collection
- Authority convergence happens gradually through individual migration decisions
- When collectors retarget to new authorities, they stop caching/backing up old sources
- Old authorities naturally fade when no one points to them anymore (reachability-based garbage collection)
- New authorities gain redundancy as more collectors cache their data
- "Squishiness" only applies to which source becomes the accepted authority

*The system cannot force consolidation - it relies on individual aggregators doing due diligence and naturally migrating to better authorities as they emerge*

### Benefits Over Current Approaches
- **No Central Dependency**: System survives individual site failures
- **Distributed Curation**: Quality improves through community contributions
- **Personal Control**: Each participant controls their own data and presentation
- **Automatic Backup**: Community interest ensures data preservation
- **Flexible Organization**: Collectors can organize across multiple taxonomies

### Resilience Scenario
When an authority disappears:
1. Aggregators detect unavailability and mark cached data as potentially stale
2. Community agents scan for alternative sources with similar data
3. Consensus emerges around most complete/trusted replacement authority
4. Namespace remapping occurs automatically via agent negotiation
5. New authority bootstraps from aggregated community data
6. System continues operating with minimal disruption

## Technical Advantages

### Leverages Existing Infrastructure
- **No New Database**: Uses proven MySQL foundation with JSON caching layer
- **MCP Integration**: Builds on established protocol for agent interaction
- **Unix Security**: Leverages mature file system permissions for sandboxing
- **HTTP Transport**: Simple, reliable, debuggable communication

### Scales Naturally
- **Horizontal Distribution**: Each aggregator is independent and self-sufficient
- **Selective Participation**: Users choose which authorities to trust and follow
- **Organic Growth**: Network effects encourage quality authorities and active collectors
- **Graceful Degradation**: System remains functional even with partial connectivity

### Agent-Friendly Architecture
- **Uniform Business Logic**: Same core operations accessible through multiple backends for humans, scripts, and agents
- **Deterministic Operations**: CLI backend enables reliable local and remote automation
- **Sandboxed Execution**: Unix permissions contain agent actions safely
- **Approval Queues**: Human oversight without blocking agent productivity

## Long-Term Vision

The aggregator layer transforms Henhouse from a single-instance knowledge management system into a distributed ecosystem where:

- **Knowledge Persists**: Information survives individual system failures through community redundancy
- **Authority Emerges**: Expertise-based leadership develops naturally without central control
- **Quality Improves**: Collective intelligence enhances data accuracy and completeness
- **Access Democratizes**: Anyone can participate at their chosen level of involvement

This creates a self-sustaining network that grows more valuable and resilient as more participants join, while maintaining the technical simplicity and reliability of the underlying Henhouse architecture.

---

## Implementation Scope and Licensing Strategy

### Henhouse Framework (Open Source Core)
The foundational knowledge management framework includes:
- **Tier 1**: MySQL authoritative layer with four-tier access control *(implemented)*
- **Tier 2**: Cache layer with JSON denormalization *(implemented)*  
- **Core Features**: Page system, MCP integration, multi-backend access, Unix security *(implemented)*
- **Potential Addition**: History/version control for selective rollbacks *(minor extension)*

**License**: Mozilla Public License (allows proprietary extensions while keeping core open)

### Premium Extensions (Licensed/Proprietary Options)
Built on Henhouse but potentially monetizable:

#### Guild Management System
- **Puzzle Makers Guild**: Authority hosting for creators
- **Collectors Guild**: Aggregation and collection management
- **Domain-Specific Guilds**: Licensed customizations for other collecting domains

#### Aggregation Layer (Tier 3)
- **Multi-source federation**: Cross-guild data aggregation
- **Market intelligence**: Want-lists, pricing, transaction facilitation
- **Consensus mechanisms**: Authority evolution and pointer management

### Deployment Models

**Decentralized Vision**: Individual collectors/creators run independent nodes with organic authority emergence

**Guild-Federated Hybrid**: Guilds as authority aggregators and trust managers
- **Guild Nodes**: Organizations run Henhouse instances for their domain (e.g., PuzzleMakersGuild.org)
- **Collector Portals**: Subdomains or integrated collection management (e.g., collector.puzzlemakerguild.org)
- **Cross-Guild Trust**: Puzzle Collectors Guild points to Knife Makers Guild for blade collections
- **Team-Sourced Curation**: Guild-level consensus rather than individual crowdsourcing
- **Human Governance**: Board of directors/steering committees can resolve disputes and override automated systems
- **Authority Arbitration**: Guild leadership can settle conflicts (e.g., when someone tries to claim authority over existing records)
- **Network Management**: Trusted pointer retargeting when external authorities go offline
- **Monetization Bottlenecks**: Guilds provide natural payment extraction points while maintaining distributed benefits

**Centralized Alternative**: Single authority with controlled monetization and easier payment extraction

### Open Core Strategy
- **Core Framework**: Free Henhouse enables innovation and adoption
- **Premium Services**: Guild hosting, advanced aggregation, transaction facilitation
- **License Protection**: Legal framework against unauthorized commercial exploitation
- **Ecosystem Growth**: Open core encourages legitimate extensions while protecting premium offerings

*This approach allows community experimentation with the framework while creating sustainable business models around specialized implementations*
