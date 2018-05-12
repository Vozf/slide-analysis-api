# export PYTHONPATH="${PYTHONPATH}:/home/roskach/PycharmProjects/slide-analysis-service"

from collections import OrderedDict

from PIL import Image
from flask import Flask, abort, make_response, jsonify, request, send_file, send_from_directory
from io import BytesIO, StringIO
from openslide import OpenSlide, OpenSlideError
from openslide.deepzoom import DeepZoomGenerator
import os
from optparse import OptionParser
from threading import Lock
from slide_analysis_service.interface import SlideAnalysisService

from constants import SIMILARITY_MAP_PATH

SLIDE_DIR = 'C:/Study/Course/slide_analysis/images/'
SLIDE_CACHE_SIZE = 10
DEEPZOOM_FORMAT = 'jpeg'

app = Flask(__name__)
app.config.from_object(__name__)


class _SlideCache:
    def __init__(self, cache_size):
        self.cache_size = cache_size
        self._lock = Lock()
        self._cache = OrderedDict()

    def get(self, path):
        with self._lock:
            if path in self._cache:
                # Move to end of LRU
                slide = self._cache.pop(path)
                self._cache[path] = slide
                return slide

        osr = OpenSlide(path)
        slide = DeepZoomGenerator(osr)

        with self._lock:
            if path not in self._cache:
                if len(self._cache) == self.cache_size:
                    self._cache.popitem(last=False)
                self._cache[path] = slide
        return slide


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
        slide.filename = os.path.basename(path)
        return slide
    except OpenSlideError:
        abort(404)


@app.route('/images')
def index():
    return jsonify(_get_slides(app.basedir))


@app.route('/images/<path:filename>')
def get_preview(filename):
    img_io = BytesIO()
    osr = OpenSlide(SLIDE_DIR + '/' + filename)
    osr.get_thumbnail((500, 500)).save(img_io, 'JPEG')
    resp = make_response(img_io.getvalue())
    resp.mimetype = 'image/jpg'
    return resp


@app.route('/image/<path:path>')
def dzi(path):
    slide = _get_slide(path)
    format = app.config['DEEPZOOM_FORMAT']
    resp = make_response(slide.get_dzi(format))
    resp.mimetype = 'application/xml'
    return resp


@app.route('/image/<path:path>/similar', methods=['POST'])
def find_similar(path):
    body = request.get_json()
    img_path = os.path.abspath(os.path.join(app.basedir, path))
    slide = app.slide_analysis_service.get_slide(img_path, body["chosenDescriptor"], body["chosenSimilarity"])
    if not slide.is_ready():
        slide.precalculate()

    similar = slide.find((body["x"], body["y"], body["width"], body["height"]))
    coordinates = []

    similar['sim_map'].save(SIMILARITY_MAP_PATH)

    for similar_tile in similar["top_n"]:
        coordinates.append({"x": str(similar_tile[0]), "y": str(similar_tile[1])})

    return jsonify(coordinates)


@app.route('/image/<path:path>/similar/<int:col>_<int:row>')
def get_similar_tile(path, col, row):
    img_path = os.path.abspath(os.path.join(app.basedir, path))
    try:
        tile = app.slide_analysis_service.get_tile(img_path, col, row)
    except ValueError:
        # Invalid level orname coordinates
        abort(404)
    buf = BytesIO()
    tile.save(buf, 'PNG')
    resp = make_response(buf.getvalue())
    resp.mimetype = 'image/png'
    return resp


@app.route('/image/similar/map')
def get_similarity_map():
    buf = BytesIO()
    map = Image.open(SIMILARITY_MAP_PATH)
    map.save(buf, 'PNG')
    resp = make_response(buf.getvalue())
    resp.mimetype = 'image/png'
    return resp


@app.route('/image/<path:path>_files/<int:level>/<int:col>_<int:row>.<format>')
def tile(path, level, col, row, format):
    slide = _get_slide(path)
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
