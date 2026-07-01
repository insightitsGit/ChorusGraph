# Query-log export schema (JSONL, one turn per line)
#
# {
#   "query": "<user_message>",
#   "category_slug": "<route column, e.g. site_kb|greeting|general>",
#   "response": "<assistant_message>",
#   "timestamp": "<ISO-8601 created_at>",
#   "section_id": "<turn id, optional>"
# }
#
# Director export SQL (website hub — vm-insightits-prod docker postgres):
#
# SELECT user_message AS query,
#        COALESCE(NULLIF(route,''), 'general') AS category_slug,
#        assistant_message AS response,
#        created_at AS timestamp,
#        id AS section_id
# FROM website_chat_turns
# WHERE assistant_message IS NOT NULL AND assistant_message <> ''
# ORDER BY created_at ASC;
#
# Dashboard hub: no equivalent table confirmed in repo as of H3 — website_chat_turns
# is the Website Hub audit log in meeting_scheduler Postgres.
