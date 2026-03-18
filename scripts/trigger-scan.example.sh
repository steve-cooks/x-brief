#!/bin/bash
# X Brief scan trigger script
# Copy this file, fill in your values, and make it executable:
#   cp scripts/trigger-scan.example.sh scripts/trigger-scan.sh
#   chmod +x scripts/trigger-scan.sh
#
# Then point XBRIEF_SCAN_COMMAND at your copy in web/.env.local:
#   XBRIEF_SCAN_COMMAND=/path/to/x-brief/scripts/trigger-scan.sh

export HOME="$HOME"
export OPENCLAW_GATEWAY_TOKEN="your-gateway-token-here"

CRON_JOB_ID="your-cron-job-id-here"

openclaw cron run "$CRON_JOB_ID" > /dev/null 2>&1
echo '{"ok":true,"enqueued":true}'
