# export PYTHONPATH="${PYTHONPATH}:/home/vozman/projects/slides/slide-analysis-service"
# export PYTHONPATH="${PYTHONPATH}:/home/vozman/projects/slides/slide_analysis_nn"

from collections import (
    OrderedDict,
    namedtuple,
)

from PIL import Image
from flask import Flask, abort, make_response, jsonify, request, send_file, send_from_directory
from io import BytesIO, StringIO
from openslide import OpenSlide, OpenSlideError
from openslide.deepzoom import DeepZoomGenerator
import os
from optparse import OptionParser
from threading import Lock
from slide_analysis_service.interface import SlideAnalysisService
# from slide_analysis_nn.prediction import Predict

from constants import SIMILARITY_MAP_PATH

SLIDE_DIR = '/home/vozman/Pictures/'
SLIDE_CACHE_SIZE = 10
DEEPZOOM_FORMAT = 'jpeg'

app = Flask(__name__)
app.config.from_object(__name__)

SlideObject = namedtuple('SlideObject', ['openslide', 'deepzoom', 'path'])


class _SlideCache:
    def __init__(self, cache_size):
        self.cache_size = cache_size
        self._lock = Lock()
        self._cache = OrderedDict()

    def get(self, path):
        with self._lock:
            if path in self._cache:
                # Move to end of LRU
                slide_object = self._cache.pop(path)
                self._cache[path] = slide_object
                return slide_object

        openslide = OpenSlide(path)
        deepzoom = DeepZoomGenerator(openslide)
        slide_object = SlideObject(openslide=openslide, deepzoom=deepzoom, path=path)

        with self._lock:
            if path not in self._cache:
                if len(self._cache) == self.cache_size:
                    self._cache.popitem(last=False)
                self._cache[path] = slide_object
        return slide_object


def _get_slides(basedir, relpath=''):
    children = []
    for name in sorted(os.listdir(os.path.join(basedir, relpath))):
        cur_relpath = os.path.join(relpath, name)
        cur_path = os.path.join(basedir, cur_relpath)
        if os.path.isdir(cur_path):
            cur_dir = _get_slides(basedir, cur_relpath)
            if cur_dir:
                children.append(cur_dir)
        elif OpenSlide.detect_format(cur_path):
            children.append({"name": os.path.basename(cur_path)})
    return children


@app.before_first_request
def _setup():
    app.basedir = os.path.abspath(app.config['SLIDE_DIR'])
    app.cache = _SlideCache(app.config['SLIDE_CACHE_SIZE'])
    app.slide_analysis_service = SlideAnalysisService()


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


def _get_slide(path):
    path = os.path.abspath(os.path.join(app.basedir, path))
    if not path.startswith(app.basedir + os.path.sep):
        # Directory traversal
        abort(404)
    if not os.path.exists(path):
        abort(404)
    try:
        slide = app.cache.get(path)
        return slide
    except OpenSlideError:
        abort(404)


@app.route('/images')
def index():
    return jsonify(_get_slides(app.basedir))


@app.route('/images/<path:filename>/preview')
def get_preview(filename):
    img_io = BytesIO()
    osr = OpenSlide(SLIDE_DIR + '/' + filename)
    osr.get_thumbnail((500, 500)).save(img_io, 'JPEG')
    resp = make_response(img_io.getvalue())
    resp.mimetype = 'image/jpg'
    return resp

@app.route('/images/<path:filename>/properties')
def get_properties(filename):
    properties = _get_slide(filename).openslide.properties
    return jsonify(dict(properties))


@app.route('/images/<path:filename>/dimensions')
def get_dimensions(filename):
    dimensions = _get_slide(filename).openslide.dimensions
    return jsonify({'x': dimensions[0], 'y': dimensions[1]})


@app.route('/images/<path:path>')
def dzi(path):
    slide = _get_slide(path).deepzoom
    format = app.config['DEEPZOOM_FORMAT']
    resp = make_response(slide.get_dzi(format))
    resp.mimetype = 'application/xml'
    return resp


@app.route('/images/<path:path>/similar', methods=['POST'])
def find_similar(path):
    body = request.get_json()
    img_path = os.path.abspath(os.path.join(app.basedir, path))
    slide = app.slide_analysis_service.get_slide(img_path,
                                           app.slide_analysis_service.get_descriptors()[1]())
    if not slide.is_ready():
        slide.precalculate()


    similar = slide.find((body["x"], body["y"], body["width"], body["height"]),
                         app.slide_analysis_service.get_similarities()[1]())

    similar['sim_map'].save(SIMILARITY_MAP_PATH, 'PNG')

    return jsonify(similar["top_n"])

@app.route('/images/<path:path>/similar/map')
def get_similarity_map(path):
    # TODO create map file for every find_similar request
    buf = BytesIO()
    map = Image.open(SIMILARITY_MAP_PATH)
    map.save(buf, 'PNG')
    resp = make_response(buf.getvalue())
    resp.mimetype = 'image/png'
    return resp


@app.route('/images/<path:path>/read_region')
def read_region(path):
    slide = _get_slide(path).openslide
    tile = slide.read_region((int(request.args.get('x')), int(request.args.get('y'))), 0,
                             (int(request.args.get('width')), int(request.args.get('height'))))

    buf = BytesIO()
    tile.save(buf, 'PNG')
    resp = make_response(buf.getvalue())
    resp.mimetype = 'image/png'
    return resp


@app.route('/images/<path:path>_files/<int:level>/<int:col>_<int:row>.<format>')
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


@app.route('/additional_parameters')
def additional_parameters():
    descriptors = list(map(lambda x: x.__name__, app.slide_analysis_service.get_descriptors()))
    similarities = list(map(lambda x: x.__name__, app.slide_analysis_service.get_similarities()))
    return jsonify({"descriptors": descriptors, "similarities": similarities})


if __name__ == '__main__':
    parser = OptionParser(usage='Usage: %prog [options] [slide-directory]')
    parser.add_option('-l', '--listen', metavar='ADDRESS', dest='host',
                      default='127.0.0.1',
                      help='address to listen on [127.0.0.1]')
    parser.add_option('-p', '--port', metavar='PORT', dest='port',
                      type='int', default=5000,
                      help='port to listen on [5000]')

    (opts, args) = parser.parse_args()
    # Set slide directory
    try:
        app.config['SLIDE_DIR'] = args[0]
    except IndexError:
        pass

    app.run(host=opts.host, port=opts.port, threaded=True)
