"""Completion daemon used by the Zsh plugin (Unix socket).

Run:
  python -m model_completer.daemon

This starts the same backend as `src/daemon/autocomplete_daemon.py`, but via the
package entrypoint so paths are consistent.
"""

from .autocomplete_daemon import main


if __name__ == "__main__":
    main()
