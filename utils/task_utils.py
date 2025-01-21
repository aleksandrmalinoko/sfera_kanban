def sort_tasks(tasks):
    status_order = {
        'В очереди': 1, 'Анализ': 2, 'Создано': 3,
        'В работе': 1, 'В ожидании': 2,
        'Выполнено': 1, 'Закрыто': 2
    }
    return sorted(tasks, key=lambda x: status_order.get(x['status'], 99))


def group_tasks_by_assignee(tasks):
    grouped = {}
    for task in tasks:
        grouped.setdefault(task['assignee'], []).append(task)
    for assignee in grouped:
        grouped[assignee] = sort_tasks(grouped[assignee])
    return grouped


def group_tasks_by_system(tasks):
    grouped = {}
    for task in tasks:
        grouped.setdefault(task['systems'], []).append(task)
    for system in grouped:
        grouped[system] = sort_tasks(grouped[system])
    return grouped