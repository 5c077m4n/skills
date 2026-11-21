#!/bin/bash
# Install the pi plugins the delegate runner needs. Must run before `delegate`.
set -euo pipefail

PI_BIN="${PI_BIN:-/root/.pi/agent/bin/pi}"

"$PI_BIN" install npm:@gotgenes/pi-permission-system
"$PI_BIN" install git:github.com/5c077m4n/pi-auto-mode
