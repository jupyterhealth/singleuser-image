#!/bin/bash
set -ex
OPENCODE_VERSION=v1.18.32
# hardcode env for Dockerfile
platform="linux-x64"
curl -s -L https://github.com/anomalyco/opencode/releases/download/${OPENCODE_VERSION}/opencode-${platform}.tar.gz | tar -xzv -C "$CONDA_PREFIX/bin"
test -f $CONDA_PREFIX/bin/opencode

# allow comparison with closed choices
# https://downloads.claude.ai/claude-code-releases/latest
CLAUDE_VERSION=2.1.288
curl -s -o $CONDA_PREFIX/bin/claude -L https://downloads.claude.ai/claude-code-releases/${CLAUDE_VERSION}/${platform}/claude
chmod +x $CONDA_PREFIX/bin/claude
