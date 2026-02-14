import pickle
import requests
import urllib3
from utils import sfera_secrets
from utils.app_config import DEFAULT_AREA
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


BASE_URL = "https://tasks.example.local"
REQUEST_TIMEOUT_SECONDS = 30
TASK_URL = f"{BASE_URL}/app/tasks/api/v1/entities"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
sfera_attributes = ['number', 'name', 'description', 'relations', 'status', 'assignee', 'systems', 'dueDate', 'estimation', 'label', 'parent']
atributes = ''
for atr in sfera_attributes[:-1]:
    atributes += f'{atr}%2C'
atributes += sfera_attributes[-1]


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


def get_sfera_token():
    get_token_headers = {
        "Content-Type": "application/json"
    } 
    get_token_body = {
        "username": sfera_secrets.sfera_user,
        "password": sfera_secrets.sfera_password
    }
    response = requests.post(LOGIN_URL, json=get_token_body, headers=get_token_headers, verify=False, timeout=REQUEST_TIMEOUT_SECONDS)
    token = response.json()['access_token']
    return token


def get_pages_count(token, sfera_query):
    get_pages_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    get_pages_url = f"https://tasks.example.local/app/tasks/api/v1/entity-views?attributes=name&query={sfera_query}"
    response = requests.get(get_pages_url, headers=get_pages_headers, verify=False, timeout=REQUEST_TIMEOUT_SECONDS)
    tasks_count = int(response.json()['totalPages'])
    print(f"Фильтр вернул {tasks_count + 1} страниц")
    return tasks_count


def get_all_tasks(token, page, sfera_query):
    page_size = f"page={page}&size=20&"
    get_all_tasks_url = f"https://tasks.example.local/app/tasks/api/v1/entity-views?{page_size}attributes={atributes}&query={sfera_query}"
    get_all_tasks_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.get(get_all_tasks_url, headers=get_all_tasks_headers, verify=False, timeout=REQUEST_TIMEOUT_SECONDS)
    all_tasks = response.json()['content']
    print(f"Задачи получены")
    return all_tasks


def generate_tasks_label(query, area):
    sfera_query = f"area%20%3D%20%27{area}%27%20and%20label%20%3D%20%27{query}%27"
    sfera_token = get_sfera_token()
    tasks_pages_count = get_pages_count(sfera_token, sfera_query)
    tasks_list = []
    for page in range(0, tasks_pages_count):
        print(f'Обработка {page+1} страницы из {tasks_pages_count+1}')
        page_tasks = get_all_tasks(sfera_token, page, sfera_query)
        for task in page_tasks:
            try:
                task_assignee = task['assignee']['name']
            except:
                task_assignee = 'Без исполнителя'

            try:
                task_systems = []
                for system in task['systems']:
                    task_systems.append(system['name'])
            except Exception as e:
                task_systems = 'Без системы'

            try:
                task_dueDate = task['dueDate']
            except:
                task_dueDate = 'Без срока исполнения'
            try:
                task_estimation = float(task['estimation'])
                task_estimation = task_estimation/3600
            except:
                task_estimation = 0
            try:
                task_description = task['description']
            except:
                task_description = ' '
            task_parents = normalize_parent(task.get('parent'))
            try:
                task_labels = []
                for label in task['label']:
                    task_labels.append(label['name'])
            except Exception as e:
                task_labels = []
            new_task_dict = {
                'number': task['number'],
                'name': task['name'],
                'description': task_description,
                'status': task['status']['name'],
                'assignee': task_assignee,
                'systems': task_systems,
                'date': task_dueDate,
                'estimation': task_estimation,
                'parents': task_parents,
                'label': task_labels,
                'area': area,
            }
            tasks_list.append(new_task_dict)
    with open('tasks_dict.pickle', 'wb') as f:
       pickle.dump(tasks_list, f)
    return tasks_list


def generate_tasks_dates(start_date, end_date, label, area):
    sfera_query = f"area%20%3D%20%27{area}%27%20and%20dueDate%20%3C%3D%20%22{end_date}%22%20and%20dueDate%20%3E%3D%20%22{start_date}%22"
    sfera_token = get_sfera_token()
    tasks_pages_count = get_pages_count(sfera_token, sfera_query)
    tasks_list = []
    for page in range(0, tasks_pages_count):
        print(f'Обработка {page+1} страницы из {tasks_pages_count+1}')
        page_tasks = get_all_tasks(sfera_token, page, sfera_query)
        for task in page_tasks:
            try:
                task_assignee = task['assignee']['name']
            except:
                task_assignee = 'Без исполнителя'

            try:
                task_systems = []
                for system in task['systems']:
                    task_systems.append(system['name'])
            except Exception as e:
                task_systems = 'Без системы'
            try:
                task_dueDate = task['dueDate']
            except:
                task_dueDate = 'Без срока исполнения'
            try:
                task_estimation = float(task['estimation'])
                task_estimation = task_estimation/3600
            except:
                task_estimation = 0
            try:
                task_description = task['description']
            except:
                task_description = ' '
            task_parents = normalize_parent(task.get('parent'))
            try:
                task_labels = []
                for label in task['label']:
                    task_labels.append(label['name'])
            except Exception as e:
                task_labels = []
            new_task_dict = {
                'number': task['number'],
                'name': task['name'],
                'description': task_description,
                'status': task['status']['name'],
                'assignee': task_assignee,
                'systems': task_systems,
                'date': task_dueDate,
                'estimation': task_estimation,
                'parents': task_parents,
                'label': task_labels,
                'area': area,
            }
            tasks_list.append(new_task_dict)
    with open('tasks_dict.pickle', 'wb') as f:
       pickle.dump(tasks_list, f)
    return tasks_list
