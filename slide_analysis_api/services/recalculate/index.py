from slide_analysis_service.precalculate import precalculate
from slide_analysis_api.constants import SLIDE_DIR


def recalculate_folder(path: str):
    if not path.startswith(SLIDE_DIR):
        return

    return precalculate(path, recursive=False)
