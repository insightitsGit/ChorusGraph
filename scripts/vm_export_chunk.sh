#!/bin/bash
# Usage: vm_export_chunk.sh <offset> <limit>
set -e
OFFSET="${1:-0}"
LIMIT="${2:-20}"
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
    OFFSET ${OFFSET} LIMIT ${LIMIT}
  ) t
) TO STDOUT
" | base64 -w 0
