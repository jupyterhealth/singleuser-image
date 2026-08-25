#!/bin/bash
set -ex
OPENCODE_VERSION=v1.18.17
# hardcode env for Dockerfile
platform="linux-x64"
curl -s -L https://github.com/anomalyco/opencode/releases/download/${OPENCODE_VERSION}/opencode-${platform}.tar.gz | tar -xzv -C "$CONDA_PREFIX/bin"
test -f $CONDA_PREFIX/bin/opencode
