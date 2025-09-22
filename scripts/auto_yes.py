#!/usr/bin/env python3
"""Auto answer 'y' to interactive prompts using pexpect.
Usage:
  python scripts/auto_yes.py <command with args>
Example:
  python scripts/auto_yes.py pip uninstall paquete
Requires: pexpect (pip install pexpect)
"""
import sys
import pexpect

if len(sys.argv) < 2:
    print("Usage: python scripts/auto_yes.py <command> [args...]")
    sys.exit(1)

command = sys.argv[1:]
# Join into a single string for pexpect.
cmd_str = ' '.join(command)
print(f"[auto_yes.py] Spawning: {cmd_str}")

# Patterns to detect a yes/no style prompt.
patterns = [r"\(Y/n\)", r"\[Y/n\]", r"\(y/n\)", r"?", r"overwrite", r"replace", pexpect.EOF, pexpect.TIMEOUT]
child = pexpect.spawn(cmd_str, encoding='utf-8', timeout=60)

while True:
    i = child.expect(patterns)
    if i in (0, 1, 2, 3, 4, 5):  # matched prompt-like text
        try:
            child.sendline('y')
        except Exception:
            break
    elif patterns[i] is pexpect.EOF:  # ended
        break
    else:  # timeout
        # Optionally continue
        pass

child.close()
print(f"[auto_yes.py] Exit status: {child.exitstatus}")
sys.exit(child.exitstatus or 0)
