# LexiDeck

Скрипт с веб-интерфейсом для автоматического сбора колод Anki из сложных текстов на английском языке.

## Как это работает
1. Анализирует исходный текст через spaCy, фильтрует частотные слова и оставляет продвинутую лексику.
2. Подтягивает контекст (исходное предложение) для каждого найденного слова.
3. Опрашивает словарь Datamuse API для получения части речи и словарного определения.
4. Упаковывает результат в готовый файл `.apkg` через genanki.

## Стек
- Python 3.9+
- Streamlit
- spaCy (`en_core_web_sm`)
- aiohttp
- genanki

## Запуск

1. Склонировать репозиторий и создать виртуальное окружение:
```bash
git clone [https://github.com/hadsize666/lexideck.git](https://github.com/ВАШ_НИК/lexideck.git)
cd lexideck
python3 -m venv .venv
source .venv/bin/activate
```
2. Установить зависимости:
pip install -r requirements.txt
python -m spacy download en_core_web_sm

3. Запустить интерфейс:
streamlit run app.py
