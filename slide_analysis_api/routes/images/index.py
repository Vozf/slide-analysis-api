from io import BytesIO
from urllib.parse import unquote

from flask import (
    Blueprint,
)
from flask import (
    make_response,
    jsonify,
    request,
)
from slide_analysis_service.interface import SlideAnalysisService

from slide_analysis_api.services.slide_cache.index import (
    _get_slide,
)

images = Blueprint('images', __name__)


@images.before_app_first_request
def _setup():
    images.slide_analysis_service = SlideAnalysisService()


@images.route('/properties/<path:filename>')
def get_properties(filename):
    properties = _get_slide(unquote(filename)).openslide.properties
    return jsonify(dict(properties))


@images.route('/<path:path>/read_region')
def read_region(path):
    slide = _get_slide(unquote(path)).openslide
    tile = slide.read_region((int(request.args.get('x')), int(request.args.get('y'))), 0,
                             (int(request.args.get('width')), int(request.args.get('height'))))

    buf = BytesIO()
    tile.save(buf, 'PNG')
    resp = make_response(buf.getvalue())
    resp.mimetype = 'image/png'
    return resp

