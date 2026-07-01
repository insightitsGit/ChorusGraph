#!/bin/bash
set -e
OUT=/tmp/website_chat_turns.jsonl
docker exec postgres psql -U meeting_user -d meeting_scheduler -t -A -c "
COPY (
  SELECT row_to_json(t)
  FROM (
    SELECT user_message AS query,
           COALESCE(NULLIF(route,''), 'general') AS category_slug,
           assistant_message AS response,
           created_at AS timestamp,
           id AS section_id
    FROM website_chat_turns
    WHERE assistant_message IS NOT NULL AND assistant_message <> ''
    ORDER BY created_at ASC
  ) t
) TO STDOUT
" > "$OUT"
wc -c "$OUT"
base64 -w 0 "$OUT"
