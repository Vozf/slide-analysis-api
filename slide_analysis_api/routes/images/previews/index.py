import os
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
from slide_analysis_api.services.slide_cache.index import _get_slide

previews = Blueprint('previews', __name__)


@previews.before_app_first_request
def _setup():
    previews.slide_analysis_service = SlideAnalysisService()


def _get_slides(basedir, relpath=''):
    children = []
    for name in sorted(os.listdir(os.path.join(basedir, relpath))):
        cur_relpath = os.path.join(relpath, name)
        cur_path = os.path.join(basedir, cur_relpath)
        if os.path.isdir(cur_path):
            cur_dir = _get_slides(basedir, cur_relpath)
            if cur_dir:
                children += cur_dir
        elif OpenSlide.detect_format(cur_path):
            children.append({"name": os.path.join(relpath, os.path.basename(cur_path))})
    return sorted(children, key=lambda x: x['name'])


@previews.route('/')
def index():
    return jsonify(_get_slides(SLIDE_DIR))


@previews.route('/<path:filename>')
def get_preview(filename):
    img_io = BytesIO()
    osr = _get_slide(filename).openslide
    osr.get_thumbnail((500, 500)).save(img_io, 'JPEG')
    resp = make_response(img_io.getvalue())
    resp.mimetype = 'image/jpg'
    return resp
