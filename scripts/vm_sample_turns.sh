#!/bin/bash
set -e
docker exec postgres psql -U meeting_user -d meeting_scheduler -t -A -F $'\t' -c "
SELECT user_message, COALESCE(NULLIF(route,''),'general'), assistant_message, created_at, id
FROM website_chat_turns
WHERE assistant_message IS NOT NULL AND assistant_message <> ''
ORDER BY created_at ASC
LIMIT 3;
"
