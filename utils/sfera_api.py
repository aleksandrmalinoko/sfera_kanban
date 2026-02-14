import pickle
import time
import requests
import urllib3
from requests import RequestException
from utils import sfera_secrets
from utils.app_config import DEFAULT_AREA

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


BASE_URL = "https://tasks.example.local"
REQUEST_TIMEOUT_SECONDS = 30
REQUEST_RETRIES = 3
RETRY_SLEEP_SECONDS = 2
TASK_URL = f"{BASE_URL}/app/tasks/api/v1/entities"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
sfera_attributes = ['number', 'name', 'description', 'relations', 'status', 'assignee', 'systems', 'dueDate', 'estimation', 'label', 'parent']
atributes = ''
for atr in sfera_attributes[:-1]:
    atributes += f'{atr}%2C'
atributes += sfera_attributes[-1]


def _notify(progress_callback, message):
    print(message)
    if progress_callback:
        progress_callback(message)


def _request_with_retries(method, url, *, progress_callback=None, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs):
    last_error = None
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except RequestException as exc:
            last_error = exc
            _notify(
                progress_callback,
                f"Ошибка запроса к Sfera (попытка {attempt}/{REQUEST_RETRIES}): {exc}"
            )
            if attempt < REQUEST_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS)

    raise RuntimeError(f"Не удалось получить данные из Sfera после {REQUEST_RETRIES} попыток: {last_error}")


def normalize_parent(parent_raw):
    if not parent_raw:
        return []

    parent_items = parent_raw if isinstance(parent_raw, list) else [parent_raw]
    normalized = []

    for item in parent_items:
        if not isinstance(item, dict):
            continue
        parent_number = item.get('number')
        parent_name = item.get('name')
        parent_area = item.get('area') or DEFAULT_AREA

        if parent_number:
            normalized.append({
                'number': parent_number,
                'name': parent_name or parent_number,
                'area': parent_area,
            })

    return normalized


def get_sfera_token(progress_callback=None):
    get_token_headers = {
        "Content-Type": "application/json"
    }
    get_token_body = {
        "username": sfera_secrets.sfera_user,
        "password": sfera_secrets.sfera_password
    }
    _notify(progress_callback, "Авторизация в Sfera...")
    response = _request_with_retries(
        "POST",
        LOGIN_URL,
        json=get_token_body,
        headers=get_token_headers,
        verify=False,
        progress_callback=progress_callback,
    )
    token = response.json()['access_token']
    return token


def get_pages_count(token, sfera_query, progress_callback=None):
    get_pages_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    get_pages_url = f"{BASE_URL}/app/tasks/api/v1/entity-views?attributes=name&query={sfera_query}"
    response = _request_with_retries(
        "GET",
        get_pages_url,
        headers=get_pages_headers,
        verify=False,
        progress_callback=progress_callback,
    )
    tasks_count = int(response.json().get('totalPages', 0))
    _notify(progress_callback, f"Фильтр вернул страниц: {tasks_count}")
    return tasks_count


def get_all_tasks(token, page, sfera_query, progress_callback=None):
    page_size = f"page={page}&size=20&"
    get_all_tasks_url = f"{BASE_URL}/app/tasks/api/v1/entity-views?{page_size}attributes={atributes}&query={sfera_query}"
    get_all_tasks_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = _request_with_retries(
        "GET",
        get_all_tasks_url,
        headers=get_all_tasks_headers,
        verify=False,
        progress_callback=progress_callback,
    )
    all_tasks = response.json().get('content', [])
    _notify(progress_callback, f"Страница {page + 1}: задач получено {len(all_tasks)}")
    return all_tasks


def _build_task(task, area):
    try:
        task_assignee = task['assignee']['name']
    except Exception:
        task_assignee = 'Без исполнителя'

    try:
        task_systems = [system['name'] for system in task['systems']]
    except Exception:
        task_systems = 'Без системы'

    try:
        task_due_date = task['dueDate']
    except Exception:
        task_due_date = 'Без срока исполнения'

    try:
        task_estimation = float(task['estimation']) / 3600
    except Exception:
        task_estimation = 0

    try:
        task_description = task['description']
    except Exception:
        task_description = ' '

    task_parents = normalize_parent(task.get('parent'))

    try:
        task_labels = [label['name'] for label in task['label']]
    except Exception:
        task_labels = []

    return {
        'number': task['number'],
        'name': task['name'],
        'description': task_description,
        'status': task['status']['name'],
        'assignee': task_assignee,
        'systems': task_systems,
        'date': task_due_date,
        'estimation': task_estimation,
        'parents': task_parents,
        'label': task_labels,
        'area': area,
    }


def _generate_tasks_by_query(sfera_query, area, progress_callback=None):
    sfera_token = get_sfera_token(progress_callback=progress_callback)
    tasks_pages_count = get_pages_count(sfera_token, sfera_query, progress_callback=progress_callback)
    tasks_list = []

    if tasks_pages_count <= 0:
        _notify(progress_callback, "Задачи по фильтру не найдены")

    for page in range(tasks_pages_count):
        _notify(progress_callback, f'Обработка {page + 1} страницы из {tasks_pages_count}')
        page_tasks = get_all_tasks(sfera_token, page, sfera_query, progress_callback=progress_callback)
        for task in page_tasks:
            tasks_list.append(_build_task(task, area))

    with open('tasks_dict.pickle', 'wb') as f:
        pickle.dump(tasks_list, f)

    _notify(progress_callback, f"Завершено. Всего задач: {len(tasks_list)}")
    return tasks_list


def generate_tasks_label(query, area, progress_callback=None):
    sfera_query = f"area%20%3D%20%27{area}%27%20and%20label%20%3D%20%27{query}%27"
    return _generate_tasks_by_query(sfera_query, area, progress_callback=progress_callback)


def generate_tasks_dates(start_date, end_date, label, area, progress_callback=None):
    sfera_query = f"area%20%3D%20%27{area}%27%20and%20dueDate%20%3C%3D%20%22{end_date}%22%20and%20dueDate%20%3E%3D%20%22{start_date}%22"
    return _generate_tasks_by_query(sfera_query, area, progress_callback=progress_callback)
