# Sfera Kanban

## Настройка конфигурации

Все настройки вынесены в `config/app.ini`.

1. Скопируйте шаблон:
   ```bash
   cp config/app.ini.example config/app.ini
   ```
2. Заполните логин/пароль в секции `[sfera]`.
3. При необходимости измените:
   - `host`, `port`, `debug`
   - `default_area`, `available_areas`
   - списки сортировки `assignee_order`, `system_order`

Можно передать путь к конфигу через переменную окружения:

```bash
export SFERA_KANBAN_CONFIG=/path/to/app.ini
```

## Запуск из исходников

```bash
pip install -r requirements.txt
python app.py
```

## Сборка в исполняемый файл (PyInstaller)

```bash
pip install -r requirements.txt
pyinstaller --onefile --name sfera-kanban \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --add-data "config/app.ini.example:config" \
  app.py
```

Исполняемый файл появится в `dist/sfera-kanban`.

После сборки рядом с бинарником нужно положить `config/app.ini` (или передать путь через `SFERA_KANBAN_CONFIG`).
