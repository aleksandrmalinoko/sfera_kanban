"""
Генератор тестовых задач для локального запуска без подключения к Sfera.
Запуск: python generate_test_data.py
Создаёт tasks_dict.pickle в корне проекта.
"""
import pickle
import random

STATUSES = ["Создано", "Анализ", "В очереди", "В работе", "В ожидании", "Выполнено", "Закрыто"]

ASSIGNEES = [
    "Иванов Иван Иванович",
    "Петрова Анна Сергеевна",
    "Сидоров Алексей Владимирович",
    "Козлова Мария Дмитриевна",
    "Новиков Дмитрий Александрович",
]

SYSTEMS = [
    "Биллинг",
    "CRM",
    "Портал самообслуживания",
    "АСУ ТП",
    "Шина данных",
    "Мониторинг",
    "Отчётность",
]

FUNDING = [
    ("PRJ-2024-001", "Цифровая трансформация 2024"),
    ("PRJ-2024-002", "Техническое обслуживание инфраструктуры"),
    ("PRJ-2024-003", "Развитие клиентского портала"),
    ("Без источника", ""),
]

PARENTS = [
    {"number": "AREA1-1000", "name": "Эпик: Интеграция с внешними системами", "area": "AREA1"},
    {"number": "AREA1-1001", "name": "Эпик: Миграция данных", "area": "AREA1"},
    {"number": "AREA1-1002", "name": "Эпик: Оптимизация производительности", "area": "AREA1"},
    None,
]

NAMES = [
    # Короткие (< 30 символов)
    "Настройка LDAP авторизации",
    "Исправить баг в логах",
    "Обновить зависимости",
    "Рефакторинг модуля оплаты",
    "Добавить unit-тесты",
    # Средние (30–50 символов)
    "Разработать API для интеграции с биллингом",
    "Добавить фильтрацию по дате в реестре задач",
    "Исправить ошибку авторизации через SSO",
    "Реализовать экспорт отчётов в формате XLSX",
    "Настроить CI/CD pipeline для тестовой среды",
    "Провести нагрузочное тестирование модуля оплат",
    # Длинные (> 50 символов)
    "Разработать механизм автоматической балансировки нагрузки между нодами кластера",
    "Проанализировать и оптимизировать SQL-запросы в модуле формирования отчётности",
    "Реализовать интеграцию с системой мониторинга Zabbix через REST API внешнего шлюза",
    "Провести аудит безопасности и устранить уязвимости в модуле аутентификации пользователей",
]

LABELS = ["23.06-27.06.2025", "30.06-04.07.2025"]

DESCRIPTIONS = [
    "<p>Необходимо реализовать авторизацию через корпоративный LDAP-сервер.</p>",
    "<p>При большой нагрузке в логах появляются ошибки <code>NullPointerException</code>. Нужно воспроизвести и исправить.</p>",
    "",
    "<p>Провести аудит и обновить все сторонние библиотеки до актуальных версий.</p>",
]


def make_task(number: int) -> dict:
    funding_code, funding_name = random.choice(FUNDING)
    parent = random.choice(PARENTS)
    num_systems = random.randint(1, 3)
    systems = random.sample(SYSTEMS, num_systems)
    estimation = round(random.choice([1, 2, 4, 8, 16, 0]), 1)

    return {
        "number": f"AREA1-{2000 + number}",
        "name": random.choice(NAMES),
        "description": random.choice(DESCRIPTIONS),
        "status": random.choice(STATUSES),
        "assignee": random.choice(ASSIGNEES),
        "systems": systems,
        "date": random.choice(["2025-06-27", "2025-07-04", "2025-07-11", None]),
        "estimation": estimation,
        "parents": [parent] if parent else [],
        "label": random.choice(LABELS),
        "area": "AREA1",
        "funding_code": funding_code,
        "funding_name": funding_name,
        "consumer_uuid": None,
    }


if __name__ == "__main__":
    random.seed(42)
    tasks = [make_task(i) for i in range(40)]

    with open("tasks_dict.pickle", "wb") as f:
        pickle.dump(tasks, f)

    print(f"Создано {len(tasks)} тестовых задач → tasks_dict.pickle")

    by_status = {}
    for t in tasks:
        by_status.setdefault(t["status"], 0)
        by_status[t["status"]] += 1
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count}")
