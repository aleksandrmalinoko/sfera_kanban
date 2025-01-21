from flask import Flask, render_template
from utils.task_utils import group_tasks_by_assignee, group_tasks_by_system
from utils.sfera_api import generate_tasks

app = Flask(__name__)


def sort_assignees(grouped_tasks):
    order = [
        "Иванов Иван Иванович",
        "Петров Пётр Петрович",
        "Сидоров Сидор Сидорович",
        "Кузнецов Кузьма Кузьмич",
        "Смирнов Семён Семёнович",
        "Попов Павел Павлович",
        "Васильев Василий Васильевич",
        "Фёдоров Фёдор Фёдорович",
        "Николаев Николай Николаевич",
        "Михайлов Михаил Михайлович",
        "Алексеев Алексей Алексеевич",
        "Борисов Борис Борисович",
        "Сорокин Максим Владимирович",
        "Морозов Матвей Матвеевич",
        "Волкова Вера Викторовна",
        "Без исполнителя",
        "Тихонов Тимофей Тимофеевич",
        "Зайцев Захар Захарович"
    ]
    ordered_keys = sorted(grouped_tasks.keys(), key=lambda x: (order.index(x) if x in order else len(order)))
    return {key: grouped_tasks[key] for key in ordered_keys}

def sort_systems(grouped_systems):
    order = [
        "Модуль A",
        "Модуль B",
        "Модуль C",
        "Модуль D",
        "Модуль E",
        "Модуль F",
        "Модуль G",
        "Модуль I",
        "Модуль J",
        "Без системы",
        "! Нет Системы"
    ]
    ordered_keys = sorted(grouped_systems.keys(), key=lambda x: (order.index(x) if x in order else len(order)))
    return {key: grouped_systems[key] for key in ordered_keys}

@app.route('/')
def kanban():
    tasks = generate_tasks()
    grouped_tasks = group_tasks_by_assignee(tasks)
    grouped_systems = group_tasks_by_system(tasks)

    # Применяем сортировку
    grouped_tasks = sort_assignees(grouped_tasks)
    grouped_systems = sort_systems(grouped_systems)

    return render_template('kanban.html', grouped_tasks=grouped_tasks, grouped_systems=grouped_systems)


if __name__ == '__main__':
    app.run(debug=True)
