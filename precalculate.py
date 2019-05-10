# Use this script to precalculate descriptors for slides.
# Example: python precalculate.py path/to/folder

from slide_analysis_service.precalculate import precalculate
from slide_analysis_api.constants import SLIDE_DIR

precalculate(SLIDE_DIR, recursive=True)
