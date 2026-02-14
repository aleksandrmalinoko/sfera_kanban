from flask import Flask, render_template, request, redirect, url_for, jsonify
from utils.sfera_api import generate_tasks_dates, generate_tasks_label
from utils.task_utils import group_tasks_by_assignee, group_tasks_by_system
from utils.app_config import ASSIGNEE_ORDER, SYSTEM_ORDER, AVAILABLE_AREAS, DEFAULT_AREA

app = Flask(__name__)
tasks = []
label_to_match = None
selected_area = DEFAULT_AREA


def sort_by_order(grouped_items, order):
    ordered_keys = sorted(grouped_items.keys(), key=lambda x: (order.index(x) if x in order else len(order)))
    return {key: grouped_items[key] for key in ordered_keys}

def sort_assignees(grouped_tasks):
    return sort_by_order(grouped_tasks, ASSIGNEE_ORDER)


def sort_systems(grouped_systems):
    return sort_by_order(grouped_systems, SYSTEM_ORDER)


def generate_label(start, end):
    # start: '2025-06-23', end: '2025-06-27' → '23.06-27.06.2025'
    from datetime import datetime
    sd = datetime.strptime(start, "%Y-%m-%d")
    ed = datetime.strptime(end, "%Y-%m-%d")
    return f"{sd.strftime('%d.%m')}-{ed.strftime('%d.%m')}.{ed.strftime('%Y')}"


@app.route('/')
def query_page():
    """
    Стартовая страница с полем для ввода запроса.
    """
    return render_template('query.html', areas=AVAILABLE_AREAS, selected_area=selected_area)


@app.route('/fetch-tasks', methods=['POST'])
def fetch_tasks():
    global tasks, label_to_match, selected_area
    mode = request.form.get('mode')
    requested_area = request.form.get('area', DEFAULT_AREA)
    selected_area = requested_area if requested_area in AVAILABLE_AREAS else DEFAULT_AREA

    try:
        if mode == 'dates':
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            # Можно сформировать метку, либо сделать это внутри функции
            label = generate_label(start_date, end_date)
            tasks = generate_tasks_dates(start_date, end_date, label, selected_area)
            label_to_match = label
        else:
            label = request.form.get('query_label')
            tasks = generate_tasks_label(label, selected_area)
            label_to_match = label

        return redirect(url_for('kanban'))
    except Exception as e:
        return render_template('query.html', error=f"Ошибка: {str(e)}", areas=AVAILABLE_AREAS, selected_area=selected_area)


@app.route('/kanban')
def kanban():
    global tasks, label_to_match
    grouped_tasks = group_tasks_by_assignee(tasks)
    grouped_systems = group_tasks_by_system(tasks)

    # Применяем сортировку
    grouped_tasks = sort_assignees(grouped_tasks)
    grouped_systems = sort_systems(grouped_systems)

    return render_template('kanban.html', grouped_tasks=grouped_tasks, grouped_systems=grouped_systems, label_to_match=label_to_match)


if __name__ == '__main__':
    app.run(debug=True)
