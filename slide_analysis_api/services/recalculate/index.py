import os

import tqdm as tqdm
from slide_analysis_service.precalculate import precalculate
from slide_analysis_api.constants import SLIDE_DIR


def recalculate_folder(path: str, tqdm=tqdm):
    if not path.startswith(SLIDE_DIR):
        raise Exception('Folder Traversal detected')
    if not os.path.isfile(os.path.join(path, '.recalculate')):
        raise Exception('Folder is not recalculatable')
    return precalculate(path, recursive=False, tqdm=tqdm)
