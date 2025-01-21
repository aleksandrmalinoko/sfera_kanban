from flask import Flask, render_template
from utils.task_utils import group_tasks_by_assignee, group_tasks_by_system
from utils.sfera_api import generate_tasks

app = Flask(__name__)


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
        "Коротких Евгений Олегович",
        "Бутенко Дмитрий Михайлович",
        "Котов Федор Васильевич",
        "Сорокин Максим Владимирович",
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
        "1717 Активности с корпоративным клиентом",
        "2032 Управление бизнес-командами Группы ВТБ",
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
