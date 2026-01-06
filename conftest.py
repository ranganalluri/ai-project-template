# """Root pytest configuration for the workspace."""
# 
# import sys
# from pathlib import Path
# 
# # Add src directories for each app to Python path
# workspace_root = Path(__file__).parent
# apps = ["api", "common-py", "functions"]
# 
# for app in apps:
#     src_path = workspace_root / "apps" / app / "src"
#     if src_path.exists() and str(src_path) not in sys.path:
#         sys.path.insert(0, str(src_path))
