import os

from flask import (
    Blueprint,
)

from slide_analysis_api.constants import SLIDE_DIR
from slide_analysis_api.services.recalculate import recalculate_folder

recalculate = Blueprint('recalculate', __name__)


@recalculate.route('/<path:path>', methods=['PUT'])
def recalc(path):
    path = os.path.join(SLIDE_DIR, path)
    print(f'Recalculating path: {path}')
    recalculate_folder(path)
    return '', 204




