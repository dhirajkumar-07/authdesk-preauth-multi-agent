import sys
import os

# Add the project directory to sys.path so app modules can be imported
base_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.join(base_dir, "..", "authdesk-kit")
if os.path.exists(project_dir):
    sys.path.insert(0, project_dir)
else:
    sys.path.insert(0, os.path.join(base_dir, ".."))

from app.main import app
