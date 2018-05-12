from io import BytesIO

from flask import (
    Blueprint,
)
from flask import (
    make_response,
    jsonify,
)
from openslide import OpenSlide
from slide_analysis_service.interface import SlideAnalysisService

from slide_analysis_api.constants import SLIDE_DIR
from slide_analysis_api.services.slide_cache.index import (
    _get_slides,
)

previews = Blueprint('previews', __name__)


@previews.before_app_first_request
def _setup():
    previews.slide_analysis_service = SlideAnalysisService()


@previews.route('/')
def index():
    return jsonify(_get_slides(SLIDE_DIR))


@previews.route('/<path:filename>')
def get_preview(filename):
    img_io = BytesIO()
    osr = OpenSlide(SLIDE_DIR + '/' + filename)
    osr.get_thumbnail((500, 500)).save(img_io, 'JPEG')
    resp = make_response(img_io.getvalue())
    resp.mimetype = 'image/jpg'
    return resp
