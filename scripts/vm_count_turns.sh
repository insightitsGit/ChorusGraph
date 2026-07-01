#!/bin/bash
set -e
docker exec postgres psql -U meeting_user -d meeting_scheduler -t -A -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='website_chat_turns';"
docker exec postgres psql -U meeting_user -d meeting_scheduler -t -A -c "SELECT COUNT(*) FROM website_chat_turns WHERE assistant_message IS NOT NULL AND assistant_message <> '';" 2>/dev/null || echo "query_failed"
