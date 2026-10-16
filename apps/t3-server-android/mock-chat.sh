#!/bin/bash
# Mock chat: one-shot prompt through the free model, run inside Ubuntu.
/usr/local/bin/opencode run -m pollinations/openai-fast "Reply with exactly this word and nothing else: SAMSUNG-OK"
echo "MOCK_EXIT:$?"
