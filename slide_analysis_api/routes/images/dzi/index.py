from io import BytesIO

from flask import (
    Blueprint,
)
from flask import (
    abort,
    make_response,
)

from slide_analysis_api.constants import (
    DEEPZOOM_FORMAT,
)
from slide_analysis_api.services.slide_cache.index import (
    _get_slide,
)

dzi = Blueprint('dzi', __name__)


@dzi.route('/<path:path>')
def get_dzi(path):
    slide = _get_slide(path).deepzoom
    format = DEEPZOOM_FORMAT
    resp = make_response(slide.get_dzi(format))
    resp.mimetype = 'dzilication/xml'
    return resp


@dzi.route('/<path:path>_files/<int:level>/<int:col>_<int:row>.<format>')
def tile(path, level, col, row, format):
    slide = _get_slide(path).deepzoom
    format = format.lower()
    if format != 'jpeg' and format != 'png':
        # Not supported by Deep Zoom
        abort(404)
    try:
        tile = slide.get_tile(level, (col, row))
    except ValueError:
        # Invalid level orname coordinates
        abort(404)
    buf = BytesIO()
    tile.save(buf, format)
    resp = make_response(buf.getvalue())
    resp.mimetype = 'image/%s' % format
    return resp
