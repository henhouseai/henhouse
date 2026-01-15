# Henhouse: What It Is, Why It Exists, and What It's For

**Written by Lee Krasnow, January 2026**

This document explains what Henhouse is, how it compares to existing tools, why I built it, and what I plan to do with it. If you're wondering "why not just use WordPress?" or "isn't this just reinventing the wheel?" - this should answer those questions.

---

## What Henhouse Is (And What It Isn't)

### The Elevator Pitch

Henhouse is an agent-first hierarchical content management framework built in Python. It's designed from the ground up for AI agents to read, modify, and extend directly - with humans acting as high-level "vibe curators" rather than button-clickers.

**What that means in practice**: Agents have full visibility into execution flow, can modify code directly, and work with coherent patterns repeated across all modules. It's a glass-box system where understanding the execution is a feature, not hidden infrastructure.

**What it's NOT**: It's not a WordPress competitor for building blogs or e-commerce sites. It's not trying to replace Django for team-built web apps. It's not a SaaS product you subscribe to.

### Comparing to Existing Systems

Let me break down how Henhouse relates to tools you might already know.

---

#### vs. WordPress

**What WordPress Does Well**:
- Thousands of plugins for every use case
- Mature ecosystem, huge community
- Easy for non-technical users
- Great for blogs, marketing sites, e-commerce (WooCommerce)
- Advanced Custom Fields can handle custom hierarchical content

**Where They Overlap**:
- Both manage hierarchical content
- Both have media/file attachments
- Both have user permissions systems
- Both have plugin/extension mechanisms
- Both can serve web content

**Where Henhouse Differs**:
- **Agent-first design**: WordPress optimizes for humans clicking GUIs. Agents helping with WordPress must explain to humans what to click, then wait for execution, then interpret results. **Human is always the bottleneck.**
- **Glass-box architecture**: WordPress plugins are often black boxes (closed source, opaque internals). Henhouse exposes execution flow as a feature - `?log=1` on any URL shows exactly what ran, in what order, and why.
- **Coherent patterns**: WordPress has 1000 different patterns across core/plugins. Henhouse uses one pattern (Page class + registry) everywhere. Every module teaches the same lesson.
- **MCP native**: WordPress would need MCP bolted on as an afterthought. Henhouse uses same RPC 2.0 envelope for HTTP, CLI, and MCP - unified pathway from day one.
- **Zero subscriptions**: WordPress is "free" but achieving what Henhouse does requires premium plugins, custom dev work, hosting upgrades. Hidden costs add up to thousands per year.

**When to use WordPress**: Building a blog, marketing site, or e-commerce store for non-technical team. Need mature ecosystem. Optimize for "time to first blog post."

**When to use Henhouse**: Building custom workflows with agent collaboration. Need full code visibility. Want coherent patterns across all extensions. Willing to collaborate with agents effectively.

---

#### vs. Django

**What Django Does Well**:
- Industry-standard Python web framework
- Mature ORM with model inheritance
- Built-in admin interface
- Django REST Framework for APIs
- Strong conventions and "Django way" of doing things
- Huge ecosystem of packages

**Where They Overlap**:
- Both Python-based
- Both can model hierarchical data (foreign keys)
- Both have permission systems
- Both can build REST APIs
- Both extensible through modules/apps

**Where Henhouse Differs**:
- **Multi-backend parity**: Django assumes HTTP is primary. CLI tools are afterthoughts calling management commands. Henhouse treats CLI, web, and MCP as equal first-class interfaces sharing one gateway.
- **Observability as feature**: Django Debug Toolbar is dev-only. Henhouse makes execution trace user-facing by design - the 3 F's (Folder, File, Function) are always visible when you want them.
- **Hierarchy encodes permissions**: Django needs django-guardian for row-level permissions, then custom logic for "Bill Cutler curates his designs, I curate my production runs, customers curate their instances." Henhouse: ownership flows through hierarchy naturally.
- **Agent collaboration patterns**: Django would need significant customization to be agent-friendly. Henhouse built for it from day one.
- **Coherence**: Django apps follow Django conventions, but each app can have different patterns. Henhouse: one pattern everywhere, self-referential learning built in.

**When to use Django**: Building web app for a team. Need mature ecosystem. Want established conventions. Hiring developers who know Django.

**When to use Henhouse**: Solo or small team building agent-assisted workflows. Need hierarchy-first permissions. Want full execution visibility. Prefer coherence over feature quantity.

---

#### vs. Drupal

**What Drupal Does Well**:
- Actually famous for complex hierarchical content
- Flexible content types and taxonomies
- Powerful Views system for querying
- Granular permissions
- Enterprise-grade for large organizations

**Where They Overlap**:
- Both handle deep hierarchical relationships
- Both have custom content types
- Both have granular permissions
- Both extensible through modules

**Where Henhouse Differs**:
- Same agent-first vs human-first divide as WordPress
- Drupal's complexity is oriented toward human administrators configuring through UI. Henhouse's complexity is in code that agents can read/modify directly.
- Drupal optimizes for "configure through UI." Henhouse optimizes for "agents read and write code."

**When to use Drupal**: Large organization, complex content requirements, need enterprise support, have dedicated Drupal developers.

**When to use Henhouse**: Agent-first workflows, need glass-box visibility, want code-over-configuration approach.

---

#### vs. QuickBooks / Accounting Software

**What QuickBooks Does Well**:
- Modern versions CAN attach documents to transactions (my 15-year-old dealbreaker is solved)
- OCR features (Receipt Capture)
- Bank feed automation
- Tax form generation
- Designed for bookkeepers

**Where They Overlap**:
- Both track transactions
- Both organize scanned receipts
- Both generate reports
- Both calculate tax-relevant numbers

**Where Henhouse Differs**:
- **Scans as first-class citizens**: QB treats transaction as primary, scan as attachment. Henhouse: scan IS the page, transactions are relationships between scan-pages.
- **Agent workflow**: QB has automation (bank feeds, rules). Henhouse has agent reasoning - agents read OCR, decide what type of page to create, set up transfer relationships, ask questions when unsure.
- **Custom tailored**: QB is generic for all businesses. My Henhouse accounting module is tailored to exactly how I file taxes for my specific business structure.
- **Zero subscription**: QB is $25-300/user/month. Henhouse accounting module is free forever.

**When to use QuickBooks**: Normal business doing normal accounting. Want vendor support. Hiring bookkeeper who knows QB.

**When to use Henhouse**: Forensic accounting for decades of chaos. Agent-assisted maintenance. Custom tax workflow. Or just don't want subscriptions.

---

#### vs. Strapi / Directus / Headless CMSs

**What They Do Well**:
- Modern headless approach (API-first)
- GraphQL/REST APIs
- Custom content types
- Nice admin UIs
- Made for teams building apps

**Where They Overlap**:
- Both provide APIs for content
- Both handle custom hierarchical data
- Both extensible

**Where Henhouse Differs**:
- These optimize for teams building apps with web admin as primary interface. Henhouse optimizes for agent-first workflows with code as primary interface.
- These are SaaS ($500-2000+/month for production use). Henhouse is free (just VPS hosting).
- These hide execution. Henhouse exposes it.

**When to use Strapi/Directus**: Building app for a team. Want polished admin UI. Don't mind subscription costs.

**When to use Henhouse**: Agent-first workflows, need execution visibility, want zero subscriptions, solo/small team.

---

### Component-Level Comparisons

Let me break down specific Henhouse features and what you'd use instead:

#### The Debug System (Execution Trace)

**What Henhouse provides**:
- On-demand execution trace showing Folder, File, Function
- User-facing by design (`?log=1` on any URL)
- MCP responses include debug output
- "Paste debug into new chat, agent understands everything" workflow

**Alternatives**:
- **Django Debug Toolbar**: Dev-only, hidden in production
- **Error logs**: Server-side files, not user-facing
- **APM tools** (New Relic, Datadog): Enterprise pricing, observability-as-service
- **None**: Most systems hide execution from users

**Why mine is different**: Observability IS the feature, not infrastructure. The execution trace becomes documentation agents can parse instantly.

---

#### The Work Page System (Project Management)

**What Henhouse provides**:
- Work dockets → asks → tasks → steps hierarchy
- Status tracking (todo/doing/review/done)
- Metadata: log entries, files touched, deviations from spec
- Agent-native: agents understand context, not just executing commands

**Alternatives**:
- **Trello, Asana, Jira**: Human-optimized, GUI-first, agents must explain to humans what to click
- **GitHub Issues/Projects**: Code-adjacent but still human UI
- **WP Project Manager**: WordPress plugin, same human-bottleneck problem

**Why mine is different**: Agents are first-class participants in planning, not just task executors. Work pages live in same system as the work itself. Self-referential: using Henhouse to build Henhouse.

---

#### The MCP Integration

**What Henhouse provides**:
- MCP speaks same RPC 2.0 envelope as everything else
- Not a wrapper around HTTP API - unified pathway
- Agents call tools directly, see debug output, modify code
- Multi-backend parity: CLI = web = MCP (all first-class)

**Alternatives**:
- **Building MCP wrapper for WordPress**: Possible but awkward. Would translate between MCP and WordPress's PHP internals. Two code paths to maintain.
- **Building MCP wrapper for Django**: Same problem. REST API first, MCP calls REST, translation overhead.
- **Purpose-built MCP servers**: Like filesystem or database servers. Useful but domain-specific, not full application framework.

**Why mine is different**: MCP wasn't bolted on - it drove the gateway/registry architecture from day one. No translation layer. Agents aren't calling APIs wrapped in MCP tools - they're calling native RPC 2.0 actions.

---

#### The Hierarchy System (Family→Design→Run→Instance)

**What Henhouse provides**:
- Deep hierarchies with ownership at each level
- Designer curates design, maker curates run, owner curates instance
- Structure encodes permissions
- Curation zones, not just CRUD rights

**Alternatives**:
- **Django models with foreign keys**: Can represent hierarchy. But permissions are "can edit this model" not "can curate this specific thing in this context." Need django-guardian + custom logic.
- **WordPress custom post types**: Can create hierarchy with parent/child. But three ownership levels gets complex fast with plugins.
- **Spreadsheet**: Fine for 100 items. Stretches for one artisan's body of work. Never works for global repository.

**Why mine is different**: Permissions flow through structure naturally. The hierarchy ISN'T just data organization - it's authority zones. Plus agents understand "this is a design under this family" contextually, not just "row 47 has foreign key to row 12."

---

## Why I Built It (The Abstract Motivation)

### What I've Seen: Agent Coding Changed the Build vs. Buy Equation

I built Henhouse because **agent collaboration fundamentally changed what's possible** for someone in my situation.

My constraints:
- Self-employed artist, not software company
- Solo proprietor with no employees
- Can't afford commercial solutions or subscriptions
- Need to understand everything myself (can't delegate to team)

**Old reality** (pre-agents):
- Building custom CMS: 2+ years, would need a team
- Buying WordPress: "Free" but premium plugins add up, plus mental overhead of learning their patterns
- **Decision**: Struggled with both options

**New reality** (with agents):
- Building custom CMS: 3-4 months solo with agent collaboration
- Buying WordPress: Still subscriptions, still learning overhead, plus agent friction
- **Decision**: Build became viable

**Productivity multiplier: 10-20x with agent collaboration.**

I'm living proof. I built comprehensive system in 3-4 months that would've taken 2+ years with a team pre-agents.

This isn't universal - teams with budgets and standard requirements should still use established platforms. But for solo developers who can collaborate effectively with agents and have custom needs, the economics shifted dramatically.

### The Mental Bandwidth Problem (For Me)

Every existing system I tried had the same problem for someone like me: **I was always the bottleneck, and I never fully understood what was happening.**

**Using WordPress with agents**:
```
Agent: "Go to Settings → Permalinks → Custom Structure"
Me: *clicks through GUI*
Agent: "Now install this plugin..."
Me: *searches, installs, activates*
Agent: "Configure it with these settings..."
Me: *fills out form*
Agent: "Hmm, that didn't work, try different plugin..."
Me: *repeat*
```

I'm clicking buttons while the agent waits. The agent can't SEE what's happening. The agent must GUESS what went wrong. The agent is explaining a human workflow to a human.

**Using Henhouse with agents**:
```
Agent: *calls MCP tool directly*
Agent: *reads code if confused*
Agent: *sees debug output of execution*
Agent: *modifies code if needed*
Agent: *deploys*
```

No human bottleneck. The agent sees everything, controls everything.

This isn't a minor efficiency gain. It's the difference between "agents help me use a tool" and "agents and I collaborate directly on the work."

### The Glass Box Advantage

Existing systems are **black boxes to agents**:
- Can't see closed-source plugin internals
- Can't see execution flow (just errors after the fact)
- Must guess at database schema
- Documentation written for humans clicking GUIs

Henhouse is a **glass box**:
- All code visible (it's in git)
- Execution flow visible on demand (`?log=1`)
- Database schema documented
- Patterns consistent across modules

When an agent pastes debug output into a new chat, that agent instantly understands:
1. What kind of system is running
2. What business logic executed
3. The flow of execution
4. How the codebase is organized
5. Exactly where to look for details

**No tutorial needed. No documentation search. Just paste and understand.**

This matters for agent collaboration AND for me personally. **This is the opposite of "vibe coding"** where you never peek under the hood. I've spent hundreds of hours reading this codebase, arguing with agents about architecture, ensuring it makes sense. I need to understand my tools deeply.

That understanding enables confident experimentation. When something breaks, I know where to look. That's powerful.

### The Coherence Advantage

I fought agents for **hundreds of arguments** about architecture. They wanted to do things the "standard" way. I insisted on my patterns. Eventually they admitted my architecture was cleaner.

Why? **Coherence.**

**WordPress experience**:
- WordPress core uses hooks/filters
- WooCommerce uses different patterns
- ACF uses different patterns
- Custom code uses your patterns
- JavaScript is different paradigm entirely

Agent (and human) thinks: "Which pattern applies HERE? What's the right way in THIS context?"

**Henhouse experience**:
- Accounting module: Page class + registry
- Puzzle module: Page class + registry
- OCR module: Page class + registry
- Work pages: Page class + registry

Agent (and human) thinks: "Oh, everything is a page class registered in the gateway. I'll follow that pattern."

**Every module is a worked example teaching the same pattern.** Agent studies accounting module, understands the pattern, applies to new module with confidence. Same for me - I understand one, I understand all.

**Quality over quantity.** One pattern repeated everywhere beats 1000 patterns each used once. This benefits both agent collaboration AND reduces mental overhead for the developer.

I've found that systems with coherent patterns are easier for agents to extend and easier for me to maintain. That's a win-win.

### Pattern Recognition & Manifestation

I see great beauty in mimicking the perfection of mathematics to the degree that it is attainable in this imperfect world. That artist statement applies to code too.

Building Henhouse has been practice in manifestation - taking patterns in my mind and making them real through agent collaboration. Like learning piano by visualizing music theory patterns, I'm learning agentic development by recognizing and encoding workflow patterns.

**Pattern recognition is fundamental to how I work**:
- Saw machinist measurement techniques, applied to woodworking
- Saw HSM toolpath optimization, applied to agent workflows
- Saw music theory visualization breakthrough, applied to code architecture

**Agents are the new instrument** for manifestation. Learning Python was fun, but the REAL instrument is learning to harness agent collaboration. Henhouse is both the thing I'm building AND the practice of building that sharpens my manifestation skills.

### The 90% Carryover

I didn't start from scratch. I've been building content management systems since 2001. By 2010, I'd generalized to a Page base class with five static methods (`allow_duplicate_names`, `allow_null_names`, `auto_link_names`, `allow_inside_of`, `allow_inside`) plus custom wiki syntax. That foundation has been **battle-tested for 15 years**.

90% of that foundation carried over to Henhouse. I'm not reinventing wheels - I'm rebuilding on proven patterns, using agent collaboration to implement 10-15 years of back-burner ideas that were only dreams in the PHP version.

**Evolution, not revolution.**

This isn't "Not Invented Here" syndrome. It's rational architecture choice: 15 years of sunk expertise in patterns that work, plus agent collaboration enabling rapid implementation.

---

## Why Anyone Else Might Care

Henhouse isn't for everyone. But if you're in a similar situation or building agent-first systems, these patterns might be worth studying:

### If You're Optimizing for Agent Workflows

If you're building something where agents are primary collaborators (not just occasional helpers), Henhouse demonstrates patterns worth studying:

1. **Make execution visible** - Debug as documentation, not troubleshooting
2. **Use one pattern everywhere** - Self-referential learning built into architecture
3. **Design for programmatic access first** - Multi-backend parity from day one
4. **Let structure encode rules** - Hierarchy defines permissions naturally
5. **Battle-test through real use** - No toy examples

Even if you use Django or Rails or whatever, these principles translate.

### If You're Building Hierarchical Systems

The Family→Design→Run→Instance pattern with curation at each level might map to your domain:
- **Software**: Framework→Library→Package→Version (maintainers at each level)
- **Education**: Curriculum→Course→Lesson→Exercise (teachers/students at different levels)
- **Manufacturing**: Category→Product→Batch→Unit (designers/makers/owners)

The pattern: **ownership flows through hierarchy, structure encodes authority.**

### If You're Tired of Subscriptions

Commercial solutions add up: premium WordPress plugins, QuickBooks subscriptions, project management tools, hosting upgrades. For self-employed developers or small teams, this gets expensive fast.

Henhouse is 100% free (MIT license). You need a VPS ($20-40/month) but no per-user fees, no plugin subscriptions, no "upgrade for advanced features."

For those who can collaborate effectively with agents and have custom requirements, the total cost of ownership (3-4 months of time) can be less than buying + customizing existing platforms (thousands in dev work + ongoing subscriptions).

### If You Want to See Agent-First Design in Practice

Most systems bolt agents on as afterthoughts. Henhouse was designed for agents from day one. Study the codebase to see what that looks like:

- Gateway/registry pattern for unified RPC 2.0 pathway
- Debug system exposing execution to agents
- Coherent patterns across modules enabling self-referential learning
- Work pages where agents are planning participants

This is one approach to agent-first architecture. There are certainly others. But if you're building systems meant for agent collaboration, these patterns might spark ideas.

### If You Like Building Your Own Tools

I'm a craftsman who builds custom tools. That's honorable. If you resonate with:
- "I want to understand every part"
- "I'd rather build it right than fight someone else's assumptions"
- "Coherence matters more than feature quantity"
- "I can collaborate effectively with agents"

Then Henhouse might either be useful directly, or inspire you to build your own agent-first systems.

---

## My Plans: What I'm Using It For

Now the personal stuff - what I'm actually building with this.

### The All Known Puzzles Database

**Vision**: Global repository documenting hundreds of thousands of unique puzzle designs. Like a plant database for identifying inherited collections, connecting buyers with sellers, showcasing designers' portfolios.

**Current state**:
- 250k+ puzzle collection in castle in Italy (World Puzzle Foundation) ready for documentation
- IPP founder's son specifically asked if Henhouse could handle this
- Suggested his nonprofit could help fund development

**Why Henhouse**:
- Family→Design→Run→Instance hierarchy with curation at each level
- Agent-assisted data entry (agents conduct interviews rather than forcing humans through web forms)
- Spoiler control (puzzle folks don't want solutions spoiled)
- Guild model: artisans providing database as community service, extracting small percentages on secondary sales

**This is the big one.** If I succeed here, maybe I shift from puzzle income to tech income. Do art for joy again, not survival.

### Business Accounting (Forensic Reconstruction)

**Problem**: Tens of thousands of scanned receipts spanning 25 years of business operations. Artist lifestyle led to 10 years without filing taxes, forensic accounting crisis, now 5 years behind again.

**Why Henhouse**:
- Scans as first-class citizens (QuickBooks dealbreaker from 15 years ago)
- Agent-assisted OCR: agents read, organize into page types, set up transfers
- Custom tailored to exactly how I file taxes for my business
- Zero subscription costs

**Current state**: OCR module working, agents beginning to process backlog.

### Pacific Puzzleworks Portfolio

Absorbing 25-year legacy portfolio site into Henhouse. Complete catalog with hierarchical relationships, materials, specifications, ownership tracking. Tier-2 verification so customers can register and curate their instance pages.

### Work Docket System

Using work pages to manage Henhouse development itself (self-referential). Agents understand context, contribute to planning, execute tasks. Encoding workflow patterns into protocols to repeat success.

### CNC Tool Management

Already have legacy system running as SAAS (only current revenue source!). Plan: agent refactors into proper Henhouse, adds photo uploads, proves framework works for completely different domain (machine shop inventory).

### The Financial Reality

Henhouse is currently a liability - time and token costs with no revenue. But I'm hoping clear vision generates income through:
- Puzzle collectors funding community database
- Consulting gigs (subject matter specialist on thing I invented)
- Guild marketplace percentages

**Goal**: Second half of career making living from tech instead of struggling with art. Tired of being poor. Want safety net. Want to do art for joy again.

**Hoping Henhouse is the vehicle for that shift.** That's why I'm pouring myself into it now - AI removed all excuses. If it's gonna get done, it needs to HAPPEN.

---

## The Timeline: How We Got Here

### 2001-2010: PHP Era
- Started hand-coding HTML for puzzle catalog
- Friend introduced PHP/MySQL, self-taught in pre-Stack Overflow era
- Built Pacific Puzzleworks-specific system
- 2010: Major generalization breakthrough - Page base class, 5 static methods, wiki syntax
- Pattern: go all-in for months, run out of money, justify to client base why refined AGAIN

### 2022: GPT-4 Discovery
- Read about AI writing code, dove in
- Did fair bit of PHP refactor work with GPT-4
- First taste of agent collaboration

### Summer 2025: Cursor Coordination Hell
- Discovered 2-agent workflow (architect + rotating workers)
- Using agentic Cursor IDE, tearing hair out
- Stumbled into spec-driven development through trial and error
- Hundreds of arguments with agents about architecture (won them all)
- Reading about MCP but hadn't wrapped head around integration

### Late 2025: The Rebuild
- Chose Python (agents prefer it, most popular language)
- Started with table/text modules, config, debugger
- Realized hitting same CRUD boilerplate crossroads as years ago
- **Ah-ha moment**: Why not absorb whole legacy page concept? Throw agents at puzzle/accounting projects!
- Refactored AGAIN to build on page inheritance (90% carryover from 2010)
- Document database refactor (learned from Hacker News)
- Multi-backend vision: CLI = web = MCP (gateway/registry architecture)
- Fought agents every step - novel patterns they had no reference for

### Now: 3-4 Months In
- Comprehensive system operational
- Accounting module processing OCR
- Work dockets managing development
- Planning puzzle database integration
- Proving agent-first architecture works
- Living proof that build vs. buy economics flipped

---

## What Henhouse Is NOT

Let me be clear about what this isn't:

**Not a WordPress Competitor**: If you need blog or e-commerce site for non-technical team, use WordPress. Mature ecosystem wins.

**Not Better Than Django For Everyone**: If you're building web app for team of developers, Django's conventions and ecosystem probably win.

**Not a Product**: This isn't SaaS you subscribe to. It's a framework you install and customize. Requires Linux/VPS knowledge.

**Not Fully Documented Yet**: I'm building it while documenting it. Context docs for agents exist. Human-friendly tutorials are in progress.

**Not Proven at Scale**: Tens of thousands of records works. Hundreds of thousands is the target. Haven't hit that yet.

**Not Polished**: Rough edges everywhere. Built for me + agents first, general public second.

---

## What I've Observed

Here's what building Henhouse taught me:

**Agent collaboration changes what's possible for solo developers.**

Pre-agents, building a comprehensive system solo would take years. With agents, I built Henhouse in 3-4 months. That's a 10-20x productivity multiplier. This isn't theoretical - I'm living proof.

**For people in certain situations, the build vs. buy equation shifted**:
- Can't afford subscriptions/premium plugins
- No employees to delegate to
- Need to understand everything themselves
- Work well with agents
- Have specific workflow needs that don't map to off-the-shelf

For that profile, agent collaboration made bespoke viable in ways it wasn't before.

**Glass-box architecture enables both agent collaboration AND deep understanding.**

Building Henhouse with agents meant I understand every decision. That understanding gives confidence to experiment, modify, and fix things. When something breaks, I know where to look. **This is the opposite of "vibe coding"** where you never peek under the hood.

Agents benefit from the same transparency - they can see execution flow, read code, understand patterns. It's a win-win.

**Coherent patterns reduce friction for both agents and humans.**

One pattern repeated everywhere beats 1000 different patterns. Agents learn faster. I maintain easier. Systems with coherent architecture are easier to extend confidently.

**The takeaway**: If you have a team, budget, and standard requirements, use established platforms. But if you're solo, budget-constrained, work well with agents, and have custom needs - building your own agent-first system became viable in new ways.

---

## Summary: The One-Paragraph Version

Henhouse is an agent-first hierarchical content management framework I built to manage hundreds of thousands of puzzle designs and tens of thousands of accounting records through agent-assisted workflows. Unlike WordPress/Django (human-first, GUI-optimized), Henhouse treats agents as first-class citizens with full code visibility, on-demand execution traces, and coherent patterns across all modules. I built it because agent collaboration enabled 10-20x productivity gains, making bespoke development viable for a solo self-employed developer in ways it wasn't before - 3-4 months to build comprehensive system that would've taken years pre-agents. The architecture demonstrates what "agent-first" means in practice: glass-box transparency (opposite of vibe coding - I understand every design decision), multi-backend parity (CLI = web = MCP), hierarchy encoding permissions, and observability as feature not infrastructure. Others in similar situations might use it directly, steal ideas, or observe that for solo developers with custom needs who work well with agents, the build vs. buy equation shifted in interesting ways.

---

**END OF MOTIVATION DOCUMENT**

*This document is meant to stand alone as complete explanation of what Henhouse is, why it exists, and what it's for. Share this when someone asks "what are you building?" or "why not just use WordPress?"*
