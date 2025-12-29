# Chapter 14: Work Page Modules for Project Planning

## Overview

Henhouse includes a built-in work page system for project planning and management. Work pages provide a hierarchical structure for organizing work: work dockets contain asks, asks contain tasks, and tasks contain steps. This system is designed to work seamlessly with AI agents through MCP commands.

## Work Page Hierarchy

### Work Docket

**Class**: `work_docket`

**Purpose**: Top-level container for a project or major work area

**Contains**: Asks

**Example**: "Website Redesign Project", "Q4 Feature Development"

### Ask

**Class**: `ask`

**Purpose**: A request or requirement that needs to be fulfilled

**Contains**: Tasks

**Example**: "Implement user authentication", "Redesign homepage"

### Task

**Class**: `task`

**Purpose**: A high-level work unit representing a major phase of work

**Contains**: Steps (optional - simple tasks may not need steps)

**Common task types**:
- **Code Review**: Verify planning matches codebase, catch planning errors
- **Implementation**: The actual code changes
- **Testing**: Smoke tests, thorough tests, edge case testing
- **Documentation**: Updating docs, cross-referencing
- **Audit**: Review and validation after completion

**Example**: "Review authentication implementation", "Implement login form"

### Step

**Class**: `step`

**Purpose**: Detailed, actionable work item

**Contains**: Nothing (lowest tier)

**Example**: "Add username validation", "Create login route handler"

## Work Page Status

Each work page has a status that tracks progress:

- **`todo`**: Work not yet started
- **`doing`**: Work currently in progress
- **`review`**: Work completed, awaiting review
- **`done`**: Work completed and approved

## Work-Ready State

Work is considered "ready to start" when:

- The ask has been broken down into appropriate tasks
- Each task has been broken down into appropriate steps (unless the task is simple enough to not need steps)
- Each tier has page text appropriate for its scope
- Parent tiers synthesize their children rather than repeating detailed information

## Page Text Detail Level

The amount of detail in page text depends on whether the work item has children:

**If it has children**: The page text should be a broad-level synthesis/summary of all its children. It should not repeat fine-grained details that are already in the children's page texts. Instead, it should synthesize and summarize what all the children accomplish together.

**If it has no children (lowest tier)**: The page text should be fully descriptive with all implementation details needed to complete that work item.

## Planning Workflow

### Initial Planning

When an agent creates a new ask, it may start as a quick jot-down or general idea. This is acceptable - not all asks need to be fully planned immediately.

### Fleshing Out Work

When preparing work to be "work-ready" (ready for implementation), the ask should be:

1. **Broken down into appropriate tasks** (high-level work units)
2. **Each task broken down into appropriate steps** (detailed work items)
3. **Page texts updated appropriately**:
   - Steps: Fully detailed implementation instructions
   - Tasks: Synthesis of what all their steps accomplish
   - Asks: Synthesis of what all their tasks accomplish

### When to Skip Tiers

- **Single-step task**: If a task would only have one step, put all the detail in the task's page text instead of creating a trivial single step.
- **Simple ask**: If an ask is so simple that breaking it into tasks seems unnecessary, the ask itself can be the lowest tier with fully detailed page text.

These decisions are made on a case-by-case basis based on the actual scope of the work.

## Using Work Pages with Agents

### Agent Collaboration Workflow

The work page system is designed for collaborative planning with AI agents:

1. **Cursor IDE**: Open your project in Cursor with MCP configured (see Chapter 11)
2. **Web Browser**: Open `https://panel.yourdomain.com` in a separate window
3. **Agent Planning**: 
   - Ask your agent to create a work docket: "Create a work docket for 'New Feature Development'"
   - Agent uses MCP to create the work docket
   - Refresh browser to see the work docket appear
4. **Iterative Planning**:
   - Agent adds asks to the work docket via MCP
   - You refresh browser and see asks appear
   - Agent breaks down asks into tasks
   - You refresh and see the task hierarchy
   - Agent adds steps to tasks
   - You refresh and see the complete plan
5. **Live Updates**: As the agent makes changes via MCP, you refresh the browser to see live updates

### Example Agent Conversation

```
You: "Create a work docket for 'Website Redesign' and add an ask for 'Implement new homepage'"

Agent: [Uses MCP to create work docket and ask]

You: [Refresh browser, see work docket and ask]

You: "Break down that ask into tasks: code review, implementation, testing, documentation"

Agent: [Uses MCP to create tasks under the ask]

You: [Refresh browser, see tasks appear]

You: "Add steps to the implementation task: create HTML template, add CSS styling, implement JavaScript"

Agent: [Uses MCP to create steps]

You: [Refresh browser, see complete hierarchy]
```

### Status Management

Agents can update work page status as work progresses:

- **Start work**: Agent sets status to `doing` when beginning a task/step
- **Complete work**: Agent sets status to `review` when work is done
- **Approve work**: You can set status to `done` when reviewing in browser
- **Track progress**: View status across all work pages in the browser

## Viewing Work Pages

### In the Web Browser

1. Navigate to a work docket in the browser
2. See the full hierarchy: docket → asks → tasks → steps
3. View status for each work item
4. See page text for each tier
5. Use app actions to modify status, metadata, or content

### In Cursor Chat

Agents can use MCP commands to:
- `show_page` - View work page details
- `get_page` - Get work page data
- `modify_work_status` - Update status
- `modify_work_meta` - Update metadata
- `modify_work_sort_order` - Reorder work items

## Best Practices

### Planning

- **Start broad**: Create work dockets and asks first
- **Break down gradually**: Add tasks and steps as planning progresses
- **Synthesize, don't repeat**: Parent tiers should summarize children, not duplicate details
- **Appropriate granularity**: Break work down to step level for implementation

### Agent Collaboration

- **Use MCP for creation**: Let agents create work pages via MCP
- **Use browser for review**: View and review work in the browser
- **Iterate together**: Agent plans, you review, agent refines
- **Live updates**: Refresh browser frequently to see agent's changes

### Status Management

- **Clear statuses**: Use status to track what's ready, in progress, or done
- **Review regularly**: Check work pages in browser to see overall progress
- **Update as you go**: Agents update status as work progresses

## Troubleshooting

### Work Pages Not Appearing

**Problem**: Work pages created via MCP don't show in browser

**Solutions**:
1. Refresh the browser page
2. Verify work pages were created (check via `show-page` command)
3. Check you're viewing the correct parent page
4. Verify Flask daemons are running

### Status Not Updating

**Problem**: Status changes via MCP don't appear in browser

**Solutions**:
1. Refresh the browser page
2. Verify status was actually updated (check database or command line)
3. Check MCP command succeeded
4. Verify you're looking at the correct work page

## Next Steps

After learning work page planning:

1. **Customizations**: Add your own custom page classes via EXT folder (see Chapter 15)
2. **Framework Upgrades**: Learn how to upgrade the framework (see Chapter 16)

