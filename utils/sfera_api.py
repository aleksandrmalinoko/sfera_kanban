from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import pickle
import time
import sys
import requests
import urllib3
from requests import RequestException
from threading import Thread
from utils.app_config import (
    DEFAULT_AREA,
    REQUEST_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    RETRY_SLEEP_SECONDS,
    SFERA_BASE_URL,
    SFERA_PASSWORD,
    SFERA_USERNAME,
    RESOURCE_DIR
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


BASE_URL = SFERA_BASE_URL
TASK_URL = f"{BASE_URL}/app/tasks/api/v1/entities"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
FUNDING_CACHE_DB = RESOURCE_DIR / "funding_cache.db"
FUNDING_CACHE_LOCK = threading.Lock()
sfera_attributes = ['number', 'name', 'description', 'relations', 'status', 'assignee', 'systems', 'dueDate', 'estimation', 'label', 'parent', 'projectConsumer']
atributes = ''
for atr in sfera_attributes[:-1]:
    atributes += f'{atr}%2C'
atributes += sfera_attributes[-1]


def _notify(progress_callback, message):
    print(message)
    if progress_callback:
        progress_callback(message)


def _init_funding_cache_db():
    with FUNDING_CACHE_LOCK:
        conn = sqlite3.connect(FUNDING_CACHE_DB)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS funding_cache (
                uuid TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()


def _load_funding_cache_from_db() -> Dict[str, Tuple[str, str]]:
    cache = {}
    with FUNDING_CACHE_LOCK:
        try:
            conn = sqlite3.connect(FUNDING_CACHE_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT uuid, code, name FROM funding_cache")
            for row in cursor.fetchall():
                cache[row[0]] = (row[1], row[2])
            conn.close()
        except Exception as e:
            _notify(None, f"Ошибка загрузки кэша проектов: {e}")
    return cache


def _save_funding_to_cache(uuids_data: Dict[str, Tuple[str, str]]) -> None:
    if not uuids_data:
        return
    with FUNDING_CACHE_LOCK:
        try:
            conn = sqlite3.connect(FUNDING_CACHE_DB)
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            for uuid, (code, name) in uuids_data.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO funding_cache (uuid, code, name, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (uuid, code, name, now))
            conn.commit()
            conn.close()
        except Exception as e:
            _notify(None, f"Ошибка сохранения кэша проектов: {e}")


def _request_record(uuid: str, token: str) -> Optional[Tuple[str, str]]:
    """Запрос к /api/v1/records/{uuid}?type=short"""
    url = f"{SFERA_BASE_URL}/app/tasks/api/v1/records/{uuid}?type=short"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        response = _request_with_retries(
            "GET", url, headers=headers, verify=False
        )
        data = response.json()
        if isinstance(data, dict):
            code = data.get("CODE") or ""
            name = data.get("NAME") or ""
            return (str(code).strip(), str(name).strip())
    except Exception:
        pass
    return None


def _get_funding_info_cached(
    uuids: List[str],
    token: Optional[str] = None,
    progress_callback=None
) -> Dict[str, Tuple[str, str]]:
    """
    Возвращает dict[uuid → (code, name)] для списка UUID-проектов.
    Использует кэш SQLite + фоновые запросы в Sfera.
    """
    if not uuids:
        return {}

    # 1. Загружаем из кэша
    cached = _load_funding_cache_from_db()
    result: Dict[str, Tuple[str, str]] = {}
    missing_uuids = []

    for uuid in set(uuids):
        if uuid and uuid in cached:
            result[uuid] = cached[uuid]
        else:
            missing_uuids.append(uuid)

    # 2. Если нет токена — возвращаем только кэшированные (остальные как "Без источника")
    if not token or not missing_uuids:
        for uuid in missing_uuids:
            result[uuid] = ("", "")
        return result

    _notify(progress_callback, f"Загрузка проектов: {len(missing_uuids)} новых / {len(result)} из кэша")

    # 3. Параллельные запросы
    max_workers = min(8, len(missing_uuids))
    new_records = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_request_record, uuid, token): uuid for uuid in missing_uuids
        }
        for future in as_completed(futures):
            uuid = futures[future]
            try:
                record = future.result()
                if record and all(record):
                    new_records[uuid] = record
                else:
                    new_records[uuid] = ("", "")
            except Exception:
                new_records[uuid] = ("", "")

    # 4. Обновляем кэш и результат
    _save_funding_to_cache(new_records)
    result.update(new_records)

    return result



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
        "username": SFERA_USERNAME,
        "password": SFERA_PASSWORD
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


def _get_funding_info(sfera_token, consumer_id: str):
    """
    Получает информацию об источнике финансирования по consumer_id.
    Возвращает словарь с CODE и NAME или None, если данные не найдены.
    """
    funding_url = f"{BASE_URL}/app/tasks/api/v1/records/{consumer_id}?type=short"
    funding_headers = {
            "Authorization": f"Bearer {sfera_token}",
            "Content-Type": "application/json"
        }
    
    try:
        response = _request_with_retries(
            "GET", 
            funding_url, 
            headers=funding_headers,
            verify=False,
            progress_callback=None # Можно добавить callback для прогресс-бара
        )
        
        data = response.json()
        code = data.get('CODE')
        name = data.get('NAME')
        
        return {'code': code, 'name': name} if (code or name) else None

        
    except Exception as exc:
        _notify(None, f"Ошибка получения данных финансирования для {consumer_id}: {exc}")
        return None
    

def _build_task(sfera_token: str, task_data: dict, area: str) -> dict:
    try:
        consumer_raw = task_data.get("projectConsumer")
        # Если это список — берём первый элемент (если есть)
        if isinstance(consumer_raw, list):
            consumer_id = consumer_raw[0] if consumer_raw else None
        elif isinstance(consumer_raw, str):
            consumer_id = consumer_raw.strip() or None
        else:
            consumer_id = None

        if consumer_id and len(consumer_id) == 36:  # UUID v4 length
            consumer_id = consumer_id.lower()
        else:
            consumer_id = None
    except Exception:
        consumer_id = None

    funding_info = {
        "funding_code": "",
        "funding_name": ""
    }
    
    if consumer_id:
        funding_info["consumer_uuid"] = consumer_id
        funding_info["funding_code"] = "⏳"
        funding_info["funding_name"] = "…"

    label_raw = task_data.get('label')
    if isinstance(label_raw, dict):
        label = [label_raw.get('name')] if label_raw.get('name') else []
    elif isinstance(label_raw, list):
        label = []
        for item in label_raw:
            if isinstance(item, dict) and item.get('name'):
                label.append(item['name'])
            elif isinstance(item, str):
                label.append(item)
    elif isinstance(label_raw, str):
        label = [label_raw] if label_raw else []
    else:
        label = []

    try:
        task_due_date = task_data.get("dueDate")
    except Exception:
        task_due_date = 'Без срока исполнения'

    try:
        task_parent = task_data.get("parent")
        task_normilized_parent = normalize_parent(task_parent)
    except Exception:
        task_due_date = 'Без срока исполнения'

    try:
        task_estimation = float(task_data.get("estimation"))
        task_estimation = round(task_estimation / 3600, 1)
    except Exception:
        task_estimation = 0

    return {
        **task_data,
        "area": area,
        "assignee": task_data.get("assignee", {}).get("name") or "Без исполнителя",
        "status": task_data.get("status", {}).get("name") or "Создано",
        "date": task_due_date,
        "label": ", ".join(label),
        "parents": task_normilized_parent,
        "estimation": task_estimation,
        "systems": [s.get("name", "") for s in task_data.get("systems", [])] if task_data.get("systems") else ["! Нет Системы"],
        **funding_info
    }


def _generate_tasks_by_query(
    sfera_query: str,
    area: str,
    progress_callback=None,
    force_reload_projects=False
) -> list:
    """
    Обновлённая функция. После загрузки задач запускает фоновую подгрузку UUID-проектов.
    """
    token = get_sfera_token(progress_callback=progress_callback)
    if not token:
        return []

    _notify(progress_callback, "Запрос списка задач...")
    pages_count = get_pages_count(token, sfera_query, progress_callback)

    tasks_list = []
    all_consumer_uuids = set()

    for page in range(pages_count):
        page_tasks = get_all_tasks(token, page, sfera_query, progress_callback)
        for task_data in page_tasks:
            task = _build_task(token, task_data, area)
            consumer_id = task.get("consumer_uuid")
            if consumer_id and isinstance(consumer_id, str) and len(consumer_id) == 36:
                all_consumer_uuids.add(consumer_id)
            tasks_list.append(task)

    # Запускаем фоновую подгрузку проектов
    def background_funding_load():
        try:
            print(f"[DEBUG] consumer_uuids: {all_consumer_uuids}")
            print(f"[DEBUG] type of uuids: {[type(u) for u in all_consumer_uuids][:5]}")
            funding_info = _get_funding_info_cached(
                list(all_consumer_uuids),
                token=token,
                progress_callback=progress_callback
            )
            for task in tasks_list:
                consumer_id = task.get("consumer_uuid")
                if consumer_id and consumer_id in funding_info:
                    code, name = funding_info[consumer_id]
                    task["funding_code"] = code or "Без источника"
                    task["funding_name"] = name
        except Exception as e:
            _notify(progress_callback, f"Ошибка фоновой загрузки проектов: {e}")

    Thread(target=background_funding_load, daemon=True).start()

    # Сохраняем в pickle (как раньше)
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
