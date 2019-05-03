import os
import threading

from flask import (
    Blueprint,
    request,
    jsonify,
)
from tqdm import tqdm

from slide_analysis_api.constants import SLIDE_DIR
from slide_analysis_api.services.recalculate import recalculate_folder

recalculate = Blueprint('recalculate', __name__)
recalculate.exporting_threads = {}


@recalculate.route('/', methods=['PUT'])
def recalc():
    path = os.path.join(SLIDE_DIR, request.get_json()['folderName'])
    print(f'Recalculating path: {path}')
    thread = ExportingThread(path)
    name = thread.getName()
    recalculate.exporting_threads[name] = thread
    thread.start()

    return jsonify({"threadName": name})


@recalculate.route('/progress/<string:thread_name>')
def progress(thread_name):
    if thread_name not in recalculate.exporting_threads:
        return 'No such thread', 404
    thread = recalculate.exporting_threads[thread_name]
    cur_progress = thread.progress
    cur_progress["isAlive"] = thread.is_alive()
    return jsonify(cur_progress)


class ExportingThread(threading.Thread):

    def __init__(self, path):
        self.progress = {"percent": 0, "current": 0, "total": 0}
        self.path = path
        super().__init__()

    def run(self):
        # Your exporting stuff goes here ...
        progress = self.progress

        class TqdmSpy(tqdm):
            @property
            def n(self):
                return self.__n

            @n.setter
            def n(self, value):
                progress["current"] = value
                progress["total"] = self.total
                progress["percent"] = (value / self.total) * 100
                self.__n = value
        recalculate_folder(self.path, tqdm=TqdmSpy)
