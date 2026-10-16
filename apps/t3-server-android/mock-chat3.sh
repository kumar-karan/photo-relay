#!/bin/bash
/usr/local/bin/opencode run "List the files in /root/servers using a shell command, then reply with exactly: TOOLS-OK:<count> where <count> is the number of files you found."
echo "MOCK3_EXIT:$?"
