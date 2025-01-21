from flask import Flask, render_template
from utils.task_utils import group_tasks_by_assignee, group_tasks_by_system
from utils.sfera_api import generate_tasks

app = Flask(__name__)


@app.route('/')
def kanban():
    tasks = generate_tasks()
    grouped_tasks = group_tasks_by_assignee(tasks)
    grouped_systems = group_tasks_by_system(tasks)

    return render_template('kanban.html', grouped_tasks=grouped_tasks, grouped_systems=grouped_systems)


if __name__ == '__main__':
    app.run(debug=True)
