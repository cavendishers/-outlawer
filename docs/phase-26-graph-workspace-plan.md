# Phase 26: Graph Workspace And Canvas Editing Plan

Last updated: `2026-04-20`

## Goal

Turn the current graph experience from:

- event detail page with a read-only association rail
- entity story page with a read-only timeline workspace
- timeline overview with a global graph snapshot

into a connected graph workspace where users can:

- traverse event, entity, timeline, and note nodes in one flow
- inspect a focused node without leaving the workspace
- launch curation and review actions from the graph context
- perform lightweight graph editing without dropping back to unrelated pages

## Why This Is The Next Stage

The current product baseline is already strong in:

- ingestion
- extraction
- review
- curation
- replay
- API contracts

The biggest remaining product gap is no longer system capability. It is workflow quality.

Right now the user can:

- see graph fragments
- jump between detail pages
- edit entities and events in dedicated curation pages

But the product still feels like several adjacent tools rather than one graph-native workspace.

## Current State Summary

Existing building blocks already in the codebase:

- [`web/components/event-association-workspace.tsx`](/Users/hongan/Documents/fxxk/web/components/event-association-workspace.tsx)
- [`web/components/entity-timeline-workspace.tsx`](/Users/hongan/Documents/fxxk/web/components/entity-timeline-workspace.tsx)
- [`web/components/graph-overview-canvas.tsx`](/Users/hongan/Documents/fxxk/web/components/graph-overview-canvas.tsx)
- [`web/app/events/[id]/page.tsx`](/Users/hongan/Documents/fxxk/web/app/events/[id]/page.tsx)
- [`web/app/story/entity/[id]/page.tsx`](/Users/hongan/Documents/fxxk/web/app/story/entity/[id]/page.tsx)

Current strengths:

- event detail already exposes related events and participants
- entity story already exposes timeline fragments and side-axis events
- timeline already exposes a global graph overview
- backend already provides curation and review context APIs

Current gaps:

- each workspace is page-local rather than graph-global
- there is no shared graph state or focused-node shell
- there is no unified node inspector
- editing still happens mostly in separate form pages
- graph edges can be seen, but not manipulated in graph context

## Product Outcome

Phase 26 should ship a unified graph workspace with three interaction layers:

1. Graph canvas
- event nodes
- entity nodes
- timeline anchors
- relation edges

2. Focus inspector
- current node summary
- nearby nodes
- source note/time/evidence hints
- quick actions for review and curation

3. Inline edit rail
- add/remove relation
- add/remove participant
- jump into full curation form only when the edit is too large for inline mode

## Scope Boundary

This phase should not try to become a full Figma-like freeform canvas.

Phase 26 should focus on:

- graph-first navigation
- graph-context editing
- connected workspace state

It should not focus on:

- multi-user collaboration
- real-time collaborative cursors
- fully arbitrary node layout persistence
- plugin/importer architecture

## User Flows

### Flow 1: Event-Centered Exploration

1. user opens an event
2. workspace shows the event as the current anchor
3. related events, participants, and nearby entities appear around it
4. user selects a related event node
5. inspector updates without leaving the workspace
6. user adds or edits an event-to-event relation
7. graph refreshes locally

### Flow 2: Person-Centered Timeline Navigation

1. user opens a person
2. timeline fragments appear as the backbone
3. selecting a fragment highlights its event and nearby entities
4. user can jump sideways into related events or back to the person
5. user can confirm alias or launch focused curation from the inspector

### Flow 3: Cross-Node Curation

1. user opens graph workspace from timeline or event detail
2. selects a node
3. inspector shows graph-aware quick actions
4. user edits a relation or participant in place
5. change persists through existing curation APIs
6. workspace refreshes only the affected neighborhood

## Proposed Frontend Architecture

### New route

Add a dedicated graph workspace route:

- `/graph`
- `/graph?event_id=...`
- `/graph?entity_id=...`
- `/graph?note_id=...`

This route becomes the shared shell for graph-first work.

### New frontend components

#### 1. `GraphWorkspaceShell`

Responsibilities:

- holds shared workspace state
- manages selected node
- manages current graph scope
- coordinates canvas, inspector, and edit rail

Suggested location:

- `web/components/graph-workspace-shell.tsx`

#### 2. `GraphCanvas`

Responsibilities:

- render nodes and edges in a reusable workspace canvas
- support hover, select, and neighborhood emphasis
- support switching focus without page navigation

Suggested location:

- `web/components/graph-canvas.tsx`

#### 3. `GraphInspector`

Responsibilities:

- show current node summary
- show timeline clues
- show relation metadata
- offer graph-context actions

Suggested location:

- `web/components/graph-inspector.tsx`

#### 4. `GraphEditRail`

Responsibilities:

- inline add relation
- inline remove relation
- inline add participant
- inline remove participant
- jump to full curation for advanced edits

Suggested location:

- `web/components/graph-edit-rail.tsx`

#### 5. `GraphScopeTabs`

Responsibilities:

- switch between `event`, `entity`, `timeline`, and `overview`
- keep the same graph state container

Suggested location:

- `web/components/graph-scope-tabs.tsx`

### Reused components

These should be refactored into data/visual slices rather than duplicated:

- [`web/components/event-association-workspace.tsx`](/Users/hongan/Documents/fxxk/web/components/event-association-workspace.tsx)
- [`web/components/entity-timeline-workspace.tsx`](/Users/hongan/Documents/fxxk/web/components/entity-timeline-workspace.tsx)
- [`web/components/graph-overview-canvas.tsx`](/Users/hongan/Documents/fxxk/web/components/graph-overview-canvas.tsx)

The target is not to keep three isolated workspaces. The target is to extract:

- shared node rendering
- shared active-node logic
- shared edge highlighting
- shared inspector patterns

## Proposed Backend Architecture

### Principle

Do not build a second graph data system.

Phase 26 should compose the existing read models from:

- query services
- review context services
- curation context services
- graph service helpers

### New read API

Add a dedicated graph workspace endpoint family:

- `GET /api/v1/graph/workspace`
- `GET /api/v1/graph/nodes/{node_type}/{node_id}`
- `GET /api/v1/graph/neighborhood`

Purpose:

- return a focused graph neighborhood optimized for the workspace
- avoid forcing the frontend to stitch multiple page APIs together

### Suggested response shapes

#### `GET /api/v1/graph/workspace`

Input:

- `event_id` optional
- `entity_id` optional
- `note_id` optional
- `depth` optional

Returns:

- `anchor`
- `nodes`
- `edges`
- `inspector`
- `available_actions`

#### `GET /api/v1/graph/nodes/{node_type}/{node_id}`

Purpose:

- fetch a normalized inspector payload for a single node

Returns:

- normalized node summary
- graph neighbors
- related timeline fragments
- available edit actions

#### `GET /api/v1/graph/neighborhood`

Purpose:

- incremental refresh when the user changes focus or completes an inline edit

Returns:

- nearby nodes and edges only

### Write path

Keep using the current curation and review APIs for persistence:

- relation edits continue through curation endpoints
- participant edits continue through event curation endpoints
- alias confirmation continues through review endpoints

Phase 26 should add a frontend orchestration layer, not duplicate backend write rules.

## Data Model Impact

### Database changes

Phase 26 should avoid schema changes unless a real blocker appears.

Current graph editing can be supported by existing tables:

- `entities`
- `events`
- `event_entities`
- `relations`
- `timeline_items`
- `note_entities`
- `note_events`

### Fields that may be added later if needed

Only add these if the canvas UX truly needs them:

- pinned-node workspace preferences
- saved graph viewpoints
- operator graph bookmarks

These are not required for the first Phase 26 delivery.

## Detailed Delivery Slices

### Slice A: Shared Graph Shell

Goal:

- unify event, entity, and overview graph state into one route and one shell

Deliverables:

- `/graph` route
- `GraphWorkspaceShell`
- shared focused-node state
- shared graph canvas component
- URL-driven anchor selection

Acceptance:

- user can open the graph workspace anchored to an event or entity
- selecting a node updates the inspector without leaving the page

### Slice B: Inspector And Cross-Navigation

Goal:

- make node inspection the core graph interaction pattern

Deliverables:

- normalized inspector UI
- nearby nodes list
- source note and timeline context
- quick navigation to note/event/entity/review/curation targets

Acceptance:

- every selected node has a stable inspector panel
- event and entity navigation feel like one connected workspace

Status update on `2026-04-20`:

- delivered through `/api/v1/graph/nodes/{node_type}/{node_id}`
- shared `/graph` workspace now keeps `active_node_id` in the URL
- node inspector now expands connected nodes, timeline context, and anchor actions without leaving the workspace

### Slice C: Inline Graph Editing

Goal:

- allow small but common edits directly in graph context

Deliverables:

- add relation
- remove relation
- add participant to event
- remove participant from event
- quick jump to advanced curation form

Acceptance:

- user can correct common graph edges without leaving the workspace
- graph refresh happens locally after a successful mutation

Status update on `2026-04-20`:

- delivered in the shared `/graph` workspace inspector instead of separate graph-only edit pages
- event nodes now support inline participant add/remove within the current graph neighborhood
- event and entity nodes now support inline relation add/update/remove with local workspace refresh
- full curation pages remain available as the escape hatch for edits outside the current graph neighborhood

### Slice D: Timeline And Event Backbone Fusion

Goal:

- join person timeline and event network into one mental model

Deliverables:

- timeline fragments shown as node/backbone data inside graph workspace
- event-to-event and person-to-event neighborhoods can coexist in the same canvas
- stronger filtering for `people only`, `events only`, `timeline mode`

Acceptance:

- user can traverse from person timeline to event neighborhood and back without route thrash

Status update on `2026-04-20`:

- shared graph canvas now supports `all`, `events`, `people`, and `timeline` viewing modes
- timeline backbone segments can now select visible event nodes directly inside the shared workspace
- timeline backbone cards and event neighborhood stepping now stay inside the graph shell before falling back to page navigation

### Slice E: UX Hardening

Goal:

- make the workspace production-usable rather than demo-like

Deliverables:

- loading skeletons
- empty states
- optimistic refresh or targeted refetch
- clearer inline validation
- mobile fallback layout

Acceptance:

- workspace remains readable and operable on both desktop and mobile

Status update on `2026-04-20`:

- graph workspace loading now uses skeleton panels for both route-entry and node-detail refresh states
- workspace now exposes a dedicated empty state when the current neighborhood has no graph nodes to render
- stacked and mobile node cards now emphasize the active focus more clearly
- inline governance forms now explain when the current neighborhood has no participant or relation targets available
- long-running inline mutations now expose explicit `写入中...` feedback instead of ambiguous button labels

## API And Service Implementation Notes

### Backend service seam

Add a dedicated workspace query service:

- `server/app/services/graph_workspace_service.py`

Responsibilities:

- build normalized workspace payloads
- merge event, entity, note, and timeline neighborhoods
- compute available quick actions

Keep route logic thin in:

- `server/app/api/v1/graph.py`

### Frontend data seam

Add typed graph workspace client functions:

- `web/lib/graph-workspace.ts`

Responsibilities:

- fetch initial workspace payload
- fetch node inspector payload
- trigger local refresh after graph edits

## UX Rules

### Interaction rules

- selecting a node should not force navigation
- navigation should be explicit, not accidental
- editing should happen in the inspector or edit rail, not by direct drag interactions in the first slice

### Visual rules

- keep the existing brutalist token system
- use one visual hierarchy for anchor node, selected node, and neighboring nodes
- reduce decorative color mixing inside workspace mode
- graph workspace should emphasize state, not just color variety

### Mobile rules

- canvas collapses into stacked neighborhood cards
- inspector becomes the primary mobile interaction layer
- inline editing remains available through drawers or stacked panels

## Verification Plan

### Backend

- extend API contract tests for new graph workspace endpoints
- add service tests for neighborhood composition
- add targeted tests for inline relation and participant edit refresh behavior

### Frontend

- `npm run build`
- page-level smoke for `/graph`
- manual verification for event anchor flow
- manual verification for entity anchor flow
- manual verification for relation add/remove
- manual verification for participant add/remove

### E2E

Add a new graph workspace e2e flow after Slice C:

- create note
- wait for extraction
- open graph workspace by event anchor
- inspect related nodes
- edit a relation
- edit a participant
- verify graph payload refresh and downstream detail pages

## Risks

### Risk 1: Frontend state fragmentation

If event page, story page, and graph route each keep their own divergent state model, the workspace will become harder to maintain.

Mitigation:

- centralize graph workspace types and fetch logic early

### Risk 2: Canvas complexity too early

If we over-invest in draggable freeform layout now, we will slow delivery without improving graph quality.

Mitigation:

- keep layout deterministic in Phase 26
- focus on inspection and inline editing first

### Risk 3: Duplicate API composition

If the frontend keeps calling many existing endpoints instead of using a workspace read model, workspace latency and complexity will grow.

Mitigation:

- introduce one graph workspace read API early in Slice A

## Recommended Execution Order

1. build backend workspace read model
2. add `/graph` route and shared shell
3. extract shared graph canvas and inspector
4. migrate current event/entity workspace UI into the new shell
5. add inline relation editing
6. add inline participant editing
7. harden loading, error, and mobile states

## Definition Of Done

Phase 26 is done when:

- `/graph` exists as a shared workspace route
- event and entity anchors can both open the same workspace
- selected node inspection happens without page navigation
- common graph edits can be completed inline
- existing review and curation flows remain intact
- Docker verification and e2e coverage pass
