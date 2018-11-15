# export PYTHONPATH="${PYTHONPATH}:/D:\projects\slide_analysis_service"
# export PYTHONPATH="${PYTHONPATH}:/home/vozman/projects/slides/slide_analysis_nn"

from optparse import OptionParser

from flask import Flask

from slide_analysis_api.routes.images import images
from slide_analysis_api.routes.images.dzi import dzi
from slide_analysis_api.routes.images.neural_network_evaluate import neural_network_evaluate
from slide_analysis_api.routes.images.previews import previews
from slide_analysis_api.routes.images.similar import similar

app = Flask(__name__)
app.config.from_object(__name__)

app.register_blueprint(images, url_prefix='/images')
app.register_blueprint(previews, url_prefix='/images/previews')
app.register_blueprint(similar, url_prefix='/images/similar')
app.register_blueprint(dzi, url_prefix='/images/dzi')
app.register_blueprint(neural_network_evaluate, url_prefix='/images/neural_network_evaluate')


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


def main():
    parser = OptionParser(usage='Usage: %prog [options] [slide-directory]')
    parser.add_option('-l', '--listen', metavar='ADDRESS', dest='host',
                      default='127.0.0.1',
                      help='address to listen on [127.0.0.1]')
    parser.add_option('-p', '--port', metavar='PORT', dest='port',
                      type='int', default=5000,
                      help='port to listen on [5000]')

    (opts, args) = parser.parse_args()

    app.run(host=opts.host, port=opts.port, threaded=True)

if __name__ == '__main__':
    main()
