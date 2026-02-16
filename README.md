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

- Linux/macOS:
  ```bash
  export SFERA_KANBAN_CONFIG=/path/to/app.ini
  ```
- Windows (PowerShell):
  ```powershell
  $env:SFERA_KANBAN_CONFIG = "C:\path\to\app.ini"
  ```

## Запуск из исходников

```bash
pip install -r requirements.txt
python app.py
```

## Сборка в исполняемый файл (PyInstaller)

> Важно: для `--add-data` в Linux/macOS разделитель `:`, в Windows — `;`.

### Linux/macOS

```bash
pip install -r requirements.txt
pyinstaller --onefile --name sfera-kanban \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --add-data "config/app.ini.example:config" \
  app.py
```

### Windows (PowerShell)

```powershell
pip install -r requirements.txt
pyinstaller --onefile --name sfera-kanban `
  --add-data "templates;templates" `
  --add-data "static;static" `
  --add-data "config/app.ini.example;config" `
  app.py
```

Исполняемый файл появится в `dist/`.

После сборки положите рядом с бинарником файл `config/app.ini` с вашими данными.

## Если при запуске EXE появляется ошибка `Failed to execute script 'app'`

Проверьте:
1. Есть ли рядом с EXE папка `config` и файл `app.ini`.
2. В `app.ini` заполнены `username` и `password`.
3. При сборке добавлены `templates` и `static` через `--add-data` с правильным разделителем (`:` или `;`).
