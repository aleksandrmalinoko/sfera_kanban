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
        systems = task.get('systems', ['! Нет Системы'])

        # Приводим к списку, если строка
        if isinstance(systems, str):
            systems = [systems]

        for system in systems:
            grouped.setdefault(system, []).append(task)

    for system in grouped:
        grouped[system] = sort_tasks(grouped[system])

    return grouped

def group_tasks_by_funding(tasks):
    grouped = {}
    for task in tasks:
        funding_code = task.get('funding_code', '')
        if not funding_code or funding_code == ' ':
            key = 'Без источника'
        else:
            key = f"{funding_code}".strip()
        grouped.setdefault(key, []).append(task)
    
    for funding in grouped:
        grouped[funding] = sort_tasks(grouped[funding])
    
    return grouped