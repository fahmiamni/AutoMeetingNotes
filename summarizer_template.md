<!-- SYSTEM MESSAGE -->
You summarize meeting transcripts into detailed Markdown meeting notes.
Use plain ASCII Markdown with no emoji.

---
<!-- USER PROMPT -->
Summarize this full meeting transcript into clean Markdown meeting notes.

Use these sections exactly, in this order:

## Decisions
List each decision as a concise one-line statement.

## Open questions
List unresolved items or questions raised but not answered.

## Agenda
Include the meeting agenda if mentioned.

## Meeting notes
Organize by topic. Use ### sub-headings for each topic.
Each point should be a concise one-line statement starting with the speaker's name.
Include participants, roles, and key details.

## Follow-up tasks
Use a Markdown table with columns: Task | Assigned to | Due date | Bucket
Only include if action items or follow-ups were discussed.

Transcript:

{transcript}
