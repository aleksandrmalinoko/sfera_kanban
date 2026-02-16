from datetime import datetime
from threading import Lock, Thread
from uuid import uuid4

from flask import Flask, jsonify, redirect, render_template, request, url_for

from utils.app_config import (
    APP_DEBUG,
    APP_HOST,
    APP_PORT,
    ASSIGNEE_ORDER,
    AVAILABLE_AREAS,
    DEFAULT_AREA,
    SYSTEM_ORDER,
)
from utils.sfera_api import generate_tasks_dates, generate_tasks_label
from utils.task_utils import group_tasks_by_assignee, group_tasks_by_system

app = Flask(__name__)
tasks = []
label_to_match = None
selected_area = DEFAULT_AREA
last_fetch_params = None

fetch_jobs = {}
fetch_jobs_lock = Lock()


def sort_by_order(grouped_items, order):
    ordered_keys = sorted(grouped_items.keys(), key=lambda x: (order.index(x) if x in order else len(order)))
    return {key: grouped_items[key] for key in ordered_keys}


def sort_assignees(grouped_tasks):
    return sort_by_order(grouped_tasks, ASSIGNEE_ORDER)


def sort_systems(grouped_systems):
    return sort_by_order(grouped_systems, SYSTEM_ORDER)


def generate_label(start, end):
    sd = datetime.strptime(start, "%Y-%m-%d")
    ed = datetime.strptime(end, "%Y-%m-%d")
    return f"{sd.strftime('%d.%m')}-{ed.strftime('%d.%m')}.{ed.strftime('%Y')}"


def create_job(mode, area, label=None, start_date=None, end_date=None):
    job_id = uuid4().hex
    with fetch_jobs_lock:
        fetch_jobs[job_id] = {
            'status': 'running',
            'message': 'Запуск обработки...',
            'logs': [],
            'error': None,
            'mode': mode,
            'area': area,
            'label': label,
            'start_date': start_date,
            'end_date': end_date,
        }
    return job_id


def append_job_log(job_id, message):
    with fetch_jobs_lock:
        job = fetch_jobs.get(job_id)
        if not job:
            return
        job['message'] = message
        logs = job['logs']
        logs.append(message)
        if len(logs) > 100:
            del logs[:len(logs) - 100]


def run_fetch_job(job_id):
    global tasks, label_to_match, last_fetch_params

    with fetch_jobs_lock:
        job = fetch_jobs.get(job_id)
        if not job:
            return
        mode = job['mode']
        area = job['area']
        label = job['label']
        start_date = job['start_date']
        end_date = job['end_date']

    def progress_callback(message):
        append_job_log(job_id, message)

    try:
        if mode == 'dates':
            calculated_label = generate_label(start_date, end_date)
            loaded_tasks = generate_tasks_dates(
                start_date,
                end_date,
                calculated_label,
                area,
                progress_callback=progress_callback,
            )
            current_label = calculated_label
        else:
            loaded_tasks = generate_tasks_label(label, area, progress_callback=progress_callback)
            current_label = label

        tasks = loaded_tasks
        label_to_match = current_label
        last_fetch_params = {
            'mode': mode,
            'area': area,
            'label': label,
            'start_date': start_date,
            'end_date': end_date,
        }

        with fetch_jobs_lock:
            fetch_jobs[job_id]['status'] = 'done'
            fetch_jobs[job_id]['message'] = 'Задачи успешно загружены'
    except Exception as exc:
        error_message = f"Ошибка загрузки задач: {exc}"
        append_job_log(job_id, error_message)
        with fetch_jobs_lock:
            fetch_jobs[job_id]['status'] = 'error'
            fetch_jobs[job_id]['error'] = error_message


@app.route('/')
def query_page():
    return render_template('query.html', areas=AVAILABLE_AREAS, selected_area=selected_area)


@app.route('/start-fetch', methods=['POST'])
def start_fetch():
    global selected_area

    mode = request.form.get('mode')
    requested_area = request.form.get('area', DEFAULT_AREA)
    selected_area = requested_area if requested_area in AVAILABLE_AREAS else DEFAULT_AREA

    if mode == 'dates':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        if not start_date or not end_date:
            return jsonify({'ok': False, 'error': 'Нужно указать диапазон дат'}), 400

        job_id = create_job(mode='dates', area=selected_area, start_date=start_date, end_date=end_date)
    else:
        label = (request.form.get('query_label') or '').strip()
        if not label:
            return jsonify({'ok': False, 'error': 'Нужно указать метку'}), 400

        job_id = create_job(mode='label', area=selected_area, label=label)

    thread = Thread(target=run_fetch_job, args=(job_id,), daemon=True)
    thread.start()

    return jsonify({'ok': True, 'job_id': job_id})


@app.route('/fetch-status/<job_id>')
def fetch_status(job_id):
    with fetch_jobs_lock:
        job = fetch_jobs.get(job_id)
        if not job:
            return jsonify({'ok': False, 'error': 'Задача не найдена'}), 404

        return jsonify({
            'ok': True,
            'status': job['status'],
            'message': job['message'],
            'error': job['error'],
            'logs': job['logs'][-20:],
        })


@app.route('/fetch-tasks', methods=['POST'])
def fetch_tasks():
    global tasks, label_to_match, selected_area, last_fetch_params

    mode = request.form.get('mode')
    requested_area = request.form.get('area', DEFAULT_AREA)
    selected_area = requested_area if requested_area in AVAILABLE_AREAS else DEFAULT_AREA

    collected_logs = []

    def progress_callback(message):
        collected_logs.append(message)

    try:
        if mode == 'dates':
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            label = generate_label(start_date, end_date)
            tasks = generate_tasks_dates(start_date, end_date, label, selected_area, progress_callback=progress_callback)
            label_to_match = label
            last_fetch_params = {
                'mode': mode,
                'area': selected_area,
                'label': None,
                'start_date': start_date,
                'end_date': end_date,
            }
        else:
            label = request.form.get('query_label')
            tasks = generate_tasks_label(label, selected_area, progress_callback=progress_callback)
            label_to_match = label
            last_fetch_params = {
                'mode': mode,
                'area': selected_area,
                'label': label,
                'start_date': None,
                'end_date': None,
            }

        return redirect(url_for('kanban'))
    except Exception as exc:
        return render_template(
            'query.html',
            error=f"Ошибка: {exc}",
            areas=AVAILABLE_AREAS,
            selected_area=selected_area,
            progress_logs=collected_logs,
        )


@app.route('/refresh-tasks', methods=['POST'])
def refresh_tasks():
    global tasks, label_to_match, selected_area, last_fetch_params

    if not last_fetch_params:
        return jsonify({'ok': False, 'error': 'Нет параметров последнего запроса для обновления'}), 400

    mode = last_fetch_params.get('mode')
    area = last_fetch_params.get('area', DEFAULT_AREA)
    selected_area = area if area in AVAILABLE_AREAS else DEFAULT_AREA

    try:
        if mode == 'dates':
            start_date = last_fetch_params.get('start_date')
            end_date = last_fetch_params.get('end_date')
            label = generate_label(start_date, end_date)
            tasks = generate_tasks_dates(start_date, end_date, label, selected_area)
            label_to_match = label
        else:
            label = last_fetch_params.get('label')
            tasks = generate_tasks_label(label, selected_area)
            label_to_match = label

        return jsonify({'ok': True})
    except Exception as exc:
        return jsonify({'ok': False, 'error': f'Ошибка обновления задач: {exc}'}), 500


@app.route('/kanban')
def kanban():
    grouped_tasks = group_tasks_by_assignee(tasks)
    grouped_systems = group_tasks_by_system(tasks)

    grouped_tasks = sort_assignees(grouped_tasks)
    grouped_systems = sort_systems(grouped_systems)

    return render_template(
        'kanban.html',
        grouped_tasks=grouped_tasks,
        grouped_systems=grouped_systems,
        label_to_match=label_to_match,
    )


if __name__ == '__main__':
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)
