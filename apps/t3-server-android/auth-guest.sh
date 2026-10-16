#!/bin/bash
# Runs INSIDE Ubuntu: feeds Enter (selects default OpenCode Zen) to auth login
# through a pty, then waits for browser approval.
{ for i in 1 2 3 4 5 6 7 8; do sleep 15; printf '\n'; done; sleep 400; } | script -qec "/usr/local/bin/opencode auth login" /dev/null
echo "GUEST_EXIT:$?"
