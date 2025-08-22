import os
import sys

# Add repository root to sys.path so 'import PYTHON.*' works when running
# pytest with a subdirectory as rootdir.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
