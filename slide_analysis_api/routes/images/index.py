from flask import (
    Blueprint,
)

import os
from io import BytesIO

from PIL import Image
from flask import (
    Blueprint,
)
from flask import (
    make_response,
    jsonify,
    request,
)
from slide_analysis_service.interface import SlideAnalysisService

from slide_analysis_api.constants import (
    SIMILARITY_MAP_PATH,
)
from slide_analysis_api.constants import SLIDE_DIR
from slide_analysis_api.services.slide_cache.index import (
    _get_slide,
)

# from slide_analysis_nn.prediction import Predict

images = Blueprint('images', __name__)


@images.before_app_first_request
def _setup():
    images.slide_analysis_service = SlideAnalysisService()


@images.route('/properties/<path:filename>')
def get_properties(filename):
    properties = _get_slide(filename).openslide.properties
    return jsonify(dict(properties))


@images.route('/similar/<path:path>', methods=['POST'])
def find_similar(path):
    body = request.get_json()
    img_path = os.path.abspath(os.path.join(SLIDE_DIR, path))
    slide = images.slide_analysis_service.get_slide(img_path,
                                                    images.slide_analysis_service.get_descriptors()[
                                                        1]())
    if not slide.is_ready():
        slide.precalculate()

    similar = slide.find((body["x"], body["y"], body["width"], body["height"]),
                         images.slide_analysis_service.get_similarities()[1]())

    similar['sim_map'].save(SIMILARITY_MAP_PATH, 'PNG')

    return jsonify(similar["top_n"])


@images.route('/similar/<path:path>/map')
def get_similarity_map(path):
    # TODO create map file for every find_similar request
    buf = BytesIO()
    map = Image.open(SIMILARITY_MAP_PATH)
    map.save(buf, 'PNG')
    resp = make_response(buf.getvalue())
    resp.mimetype = 'image/png'
    return resp


@images.route('/<path:path>/read_region')
def read_region(path):
    slide = _get_slide(path).openslide
    tile = slide.read_region((int(request.args.get('x')), int(request.args.get('y'))), 0,
                             (int(request.args.get('width')), int(request.args.get('height'))))

    buf = BytesIO()
    tile.save(buf, 'PNG')
    resp = make_response(buf.getvalue())
    resp.mimetype = 'image/png'
    return resp


@images.route('/similar/additional_parameters')
def additional_parameters():
    descriptors = list(map(lambda x: x.__name__, images.slide_analysis_service.get_descriptors()))
    similarities = list(map(lambda x: x.__name__, images.slide_analysis_service.get_similarities()))
    return jsonify({"descriptors": descriptors, "similarities": similarities})
