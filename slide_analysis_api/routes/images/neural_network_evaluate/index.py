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
from slide_analysis_nn.prediction import Predict

from slide_analysis_api.constants import (
    SLIDE_DIR,
    SIMILARITY_MAP_PATH,
)

neural_network_evaluate = Blueprint('neural_network_evaluate', __name__)

@neural_network_evaluate.before_app_first_request
def _setup():
    neural_network_evaluate.predict = Predict()

@neural_network_evaluate.route('/<path:path>', methods=['POST'])
def find_neural_network_evaluate(path):
    body = request.get_json()
    img_path = os.path.abspath(os.path.join(SLIDE_DIR, path))
    prediction = neural_network_evaluate.predict.predict_slide(img_path, area_to_predict=(
        body["x"], body["y"], body["x"] + body["width"], body["y"] + body["height"]))

    prediction.create_map(SIMILARITY_MAP_PATH)

    results = prediction.get_results()

    return jsonify(results)


@neural_network_evaluate.route('/<path:path>/map')
def get_neural_network_evaluate_map(path):
    # TODO create map file for every find_neural_network_evaluate request
    buf = BytesIO()
    map = Image.open(SIMILARITY_MAP_PATH)
    map.save(buf, 'PNG')
    resp = make_response(buf.getvalue())
    resp.mimetype = 'image/png'
    return resp
