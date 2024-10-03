import sys
import os

# getting the absolute path of the project root
project_root = os.path.abspath(os.path.dirname(__file__))

# adding the project root and src directory to the python path
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))