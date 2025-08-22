#!/bin/bash
echo Starting MCP Server...
cd "$(dirname "$0")"
./expert-stream-server "$@"
