#!/bin/bash
echo "Testing custom workflow"
ls -la
echo "Looking for Python:"
find /nix -name "python3" -type f | head -5 2>/dev/null || echo "Python not found in /nix"
echo "Done testing"