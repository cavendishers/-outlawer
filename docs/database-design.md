# Database Design

## Principles

- store raw assets separately from structured knowledge
- keep derived media text separate from original inputs
- treat stylized outputs as derived data
- use migrations for every schema change
- model the system around `entity`, `event`, `time`, and `relation`
- preserve evidence so extracted facts remain traceable

## Core Modeling Strategy

The recommended relationship model is:

- `Entity` answers who, what, and where
- `Event` answers what happened
- event time fields answer when it happened
- `Relation` connects objects that need graph-like traversal
- evidence tables answer why the system believes a fact

The system should be event-centric:

- people participate in events
- events happen at a time
- events may involve places and organizations
- notes and raw assets provide source evidence

This keeps timeline rendering, people pages, and story views aligned with the same truth model.

## Core Tables

### users

```text
id
username
password_hash
display_name
status
created_at
updated_at
last_login_at
```

Notes:

- `username` should be unique

### raw_assets

```text
id
user_id
asset_type
source_type
title
original_text
bucket_name
object_key
mime_type
file_size
checksum
status
created_at
updated_at
```

Notes:

- `asset_type`: text, audio, image, video
- `original_text` is used only when the submitted source is already text

### asset_derivatives

```text
id
asset_id
derivative_type
content
meta_json
version
created_at
```

Notes:

- `derivative_type`: transcript, ocr, frame_caption, normalized_text

### notes

```text
id
user_id
asset_id
title
summary
canonical_text
category
status
primary_time
created_at
updated_at
processed_at
```

### note_chunks

```text
id
note_id
chunk_index
content
token_count
embedding_vector
created_at
```

Notes:

- `embedding_vector` is acceptable as a transitional MVP field
- long term, embeddings should be centralized in the `embeddings` table only

## Entity and Event Modeling

### entities

```text
id
user_id
entity_type
canonical_name
display_name
description
alias_json
normalized_name
status
confidence_score
first_seen_at
last_seen_at
created_at
updated_at
```

Notes:

- `entity_type`: person, org, place, concept
- `canonical_name` is the normalized system name
- `display_name` is the preferred UI label
- `normalized_name` supports matching and de-duplication
- `first_seen_at` and `last_seen_at` should be stored as timezone-aware datetimes, not strings
- `alias_json` is acceptable for MVP display payloads, but a dedicated alias table is the preferred long-term source of truth

### entity_aliases

```text
id
entity_id
alias
normalized_alias
alias_type
created_at
```

Notes:

- recommended as the long-term canonical alias store
- `alias_type`: extracted, manual, imported

### events

```text
id
user_id
title
summary
description
event_type
status
source_note_id
start_time
end_time
time_precision
time_text
timeline_sort_time
location_text
confidence_score
created_at
updated_at
```

Notes:

- `time_precision`: exact, day, month, year, range, unknown
- `time_text` stores the original time phrase such as "last winter"
- `timeline_sort_time` is used for ordering even if the original phrase is fuzzy

### event_entities

```text
id
event_id
entity_id
role
relation_type
display_order
confidence_score
created_at
```

Notes:

- this table is recommended even if `relations` also exists
- it supports high-frequency event-to-person queries efficiently
- example `relation_type`: participates_in, organizes, targets, located_in
- example `role`: speaker, owner, participant, victim, leader

## Relationship Modeling

### relations

```text
id
user_id
source_type
source_id
relation_type
target_type
target_id
evidence_count
confidence_score
meta_json
created_at
updated_at
```

Notes:

- use this for generalized graph edges
- keep high-frequency relationship shapes in dedicated join tables when needed
- recommended `source_type` and `target_type`: note, entity, event
- manual graph curation may add or remove non-extraction relations here without changing raw source material

Recommended first-pass `relation_type` values:

- `mentions`
- `participates_in`
- `related_to`
- `same_as`
- `alias_of`
- `occurs_before`
- `occurs_after`
- `source_of`
- `located_in`

### note_entities

```text
id
note_id
entity_id
mention_text
confidence_score
created_at
```

Notes:

- supports fast lookup for "which entities were mentioned in this note"
- useful for UI evidence preview and reprocessing

### note_events

```text
id
note_id
event_id
mention_text
confidence_score
created_at
```

Notes:

- supports note-to-event traceability without forcing every query through `relations`

## Timeline and Similarity

### timeline_items

```text
id
user_id
event_id
note_id
title
summary
display_time
sort_time
time_precision
importance_score
created_at
updated_at
```

Notes:

- this is a projection table for fast timeline rendering
- it should be regenerated when the event interpretation changes
- manual event curation should keep `title`, `summary`, `display_time`, `sort_time`, and `time_precision` aligned with the edited event

### embeddings

```text
id
owner_type
owner_id
vector
model_name
created_at
updated_at
```

Notes:

- can store note, chunk, entity, or event embeddings
- use pgvector indexes once vector dimensionality is stable

## AI Tracking and Derived Views

### ai_jobs

```text
id
user_id
job_type
target_type
target_id
status
payload_json
result_json
error_message
retry_count
created_at
updated_at
finished_at
```

### extraction_runs

```text
id
user_id
note_id
source_asset_id
raw_result_json
normalized_result_json
status
extractor_name
extractor_version
created_at
updated_at
```

Notes:

- stores the raw AI output and the normalized post-processed output
- critical for debugging, replay, and reprocessing

### extraction_evidence

```text
id
user_id
source_note_id
source_asset_id
target_type
target_id
field_name
evidence_text
evidence_offset_start
evidence_offset_end
extractor_name
extractor_version
confidence_score
created_at
```

Notes:

- use this to explain why a person, event, or relation exists
- supports inline evidence snippets in the UI

### merge_candidates

```text
id
user_id
object_type
source_id
candidate_id
score
reason_json
status
reviewed_at
review_note
created_at
updated_at
```

Notes:

- supports "possible duplicate" workflows
- recommended statuses: pending, accepted, rejected, superseded
- `reviewed_at` and `review_note` preserve the operator decision timestamp and explanation

### review_actions

```text
id
user_id
target_type
target_id
action_type
status_before
status_after
payload_json
created_at
updated_at
```

Notes:

- append-only audit trail for accept, reject, merge, and alias confirmation
- payload should keep operator-facing context such as survivor selection and note text

### entity_merge_history

```text
id
user_id
survivor_entity_id
merged_entity_id
merge_reason
payload_json
created_at
updated_at
```

Notes:

- records entity-to-entity merge decisions after dependent references are rewritten
- useful for audit, troubleshooting, and future undo tooling

### event_merge_history

```text
id
user_id
survivor_event_id
merged_event_id
merge_reason
payload_json
created_at
updated_at
```

Notes:

- records event-to-event merge decisions after timeline and relation projections are updated
- keeps merge reasoning available even after the merged event row is deleted

### style_views

```text
id
user_id
target_type
target_id
style_type
title
content
version
created_at
updated_at
```

Notes:

- stylized outputs must remain derived and replaceable
- do not overwrite canonical knowledge text

## Required Indexes

- unique index on `users.username`
- index on `raw_assets.user_id`
- index on `raw_assets.status`
- index on `notes.user_id`
- index on `notes.asset_id`
- index on `notes.primary_time`
- composite index on `entities(user_id, entity_type, normalized_name)`
- index on `entities.first_seen_at`
- index on `events(user_id, timeline_sort_time)`
- index on `events(user_id, event_type)`
- index on `event_entities(event_id, entity_id)`
- index on `relations(source_type, source_id)`
- index on `relations(target_type, target_id)`
- index on `timeline_items(user_id, sort_time)`
- index on `ai_jobs(status, created_at)`
- index on `merge_candidates(object_type, status, score)`

## Vector Storage

Use pgvector for:

- note similarity
- chunk similarity
- entity similarity
- event similarity

Vector indexing strategy should be introduced through migrations after vector size and query shape are finalized.

## Implementation Notes

- keep time as an event property for the first version rather than a dedicated `time_entities` table
- keep most graph traversal event-centric
- use `event_entities` for fast people and event pages
- use `relations` for broader cross-object linking
- never trust extraction output without storing evidence and confidence
