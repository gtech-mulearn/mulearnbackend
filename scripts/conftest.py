"""Put this directory on sys.path so the drift-check tests import the module
under test regardless of the working directory pytest is invoked from."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
