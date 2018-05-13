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

similar = Blueprint('similar', __name__)


@similar.before_app_first_request
def _setup():
    similar.slide_analysis_service = SlideAnalysisService()


@similar.route('/<path:path>', methods=['POST'])
def find_similar(path):
    body = request.get_json()
    img_path = os.path.abspath(os.path.join(SLIDE_DIR, path))
    slide = similar.slide_analysis_service.get_slide(img_path, body["descriptor"])

    if not slide.is_ready():
        slide.precalculate()

    similar_regions = slide.find((body["x"], body["y"], body["width"], body["height"]),
                                 body["similarity"])

    similar_regions['sim_map'].save(SIMILARITY_MAP_PATH, 'PNG')

    return jsonify(similar_regions["top_n"])


@similar.route('/<path:path>/map')
def get_similarity_map(path):
    # TODO create map file for every find_similar request
    buf = BytesIO()
    map = Image.open(SIMILARITY_MAP_PATH)
    map.save(buf, 'PNG')
    resp = make_response(buf.getvalue())
    resp.mimetype = 'image/png'
    return resp


@similar.route('/additional_parameters')
def additional_parameters():
    descriptors = [{'id': id, 'name': clas.name()} for id, clas in
                   similar.slide_analysis_service.get_descriptors().items()]
    similarities = [{'id': id, 'name': clas.name()} for id, clas in
                    similar.slide_analysis_service.get_similarities().items()]
    return jsonify({"descriptors": descriptors, "similarities": similarities})
