from flask import Flask, render_template, request, redirect, url_for, jsonify
from utils.sfera_api import generate_tasks_dates, generate_tasks_label
from utils.task_utils import group_tasks_by_assignee, group_tasks_by_system

app = Flask(__name__)
tasks = []
label_to_match = None

def sort_assignees(grouped_tasks):
    order = [
        "Шуминов Самир Юсифович",
        "Бибиков Игорь Николаевич",
        "Логинов Юрий Сергеевич",
        "Заболотский Артем Дмитриевич",
        "Макиевский Дмитрий Александрович",
        "Збандут Марк Олегович",
        "Шереметьев Артемий Дмитриевич",
        "Новиков Ярослав Владимирович",
        "Твердохлеб Александр Григорьевич",
        "Чернышев Андрей Викторович",
        "Коротких Евгений Олегович",
        "Бутенко Дмитрий Михайлович",
        "Котов Федор Васильевич",
        "Мелихов Евгений Алексеевич",
        "Мельников Николай Сергеевич",
        "Гусева Мелания Андреевна",
        "Без исполнителя",
        "Ильин Павел Сергеевич",
        "Малинко Александр Васильевич"
    ]
    ordered_keys = sorted(grouped_tasks.keys(), key=lambda x: (order.index(x) if x in order else len(order)))
    return {key: grouped_tasks[key] for key in ordered_keys}


def sort_systems(grouped_systems):
    order = [
        "1498 Карточка ЮЛ",
        "1511 Кросс-ссылки ЮЛ",
        "1630 Полномочия представителя ЮЛ",
        "1550 Данные ЮЛ из внешних источников",
        "1719 Проверка адреса",
        "1925 Машиночитаемые доверенности",
        "1512 Расширенный профиль клиента ЮЛ",
        "3613 Расширенный профиль клиента ЮЛ (КНР)",
        "1717 Активности с корпоративным клиентом",
        "2032 Управление бизнес-командами Группы ВТБ",
        "Без системы",
        "! Нет Системы"
    ]
    ordered_keys = sorted(grouped_systems.keys(), key=lambda x: (order.index(x) if x in order else len(order)))
    return {key: grouped_systems[key] for key in ordered_keys}


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
    return render_template('query.html')


@app.route('/fetch-tasks', methods=['POST'])
def fetch_tasks():
    global tasks, label_to_match
    mode = request.form.get('mode')

    try:
        if mode == 'dates':
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            # Можно сформировать метку, либо сделать это внутри функции
            label = generate_label(start_date, end_date)
            tasks = generate_tasks_dates(start_date, end_date, label)
            label_to_match = label
        else:
            label = request.form.get('query_label')
            tasks = generate_tasks_label(label)
            label_to_match = label

        return redirect(url_for('kanban'))
    except Exception as e:
        return render_template('query.html', error=f"Ошибка: {str(e)}")


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