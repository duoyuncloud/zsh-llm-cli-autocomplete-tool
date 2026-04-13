#!/usr/bin/env python3
"""Backwards-compatible entrypoint.

The real implementation lives in `model_completer.autocomplete_daemon`.
Keeping this file avoids breaking existing installs that reference
`src/daemon/autocomplete_daemon.py` directly.
"""

from model_completer.autocomplete_daemon import main


if __name__ == "__main__":
    main()
