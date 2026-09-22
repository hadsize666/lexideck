import asyncio
import inspect
from pathlib import Path
import streamlit as st
import pandas as pd

import src.text_processing.pipeline as nlp_module
import src.enrichment.client as enrichment_module
from src.export.anki import create_anki_deck

def _find_callable(module, candidate_names):
    for name in candidate_names:
        if hasattr(module, name) and callable(getattr(module, name)):
            return getattr(module, name)
    for attr_name in dir(module):
        if not attr_name.startswith("_"):
            attr = getattr(module, attr_name)
            if callable(attr) and inspect.isfunction(attr):
                return attr
    raise AttributeError(f"Не удалось найти рабочую функцию в модуле {module.__name__}")

process_text_fn = _find_callable(
    nlp_module, 
    ["process_text", "extract_vocabulary", "analyze_text", "run_pipeline", "extract_words"]
)

enrich_words_fn = _find_callable(
    enrichment_module, 
    ["enrich_vocabulary", "enrich_words", "enrich_entries", "fetch_definitions", "fetch_words", "enrich"]
)

def run_enrichment_safe(entries):
    if inspect.iscoroutinefunction(enrich_words_fn):
        return asyncio.run(enrich_words_fn(entries))
    return enrich_words_fn(entries)


st.set_page_config(page_title="LexiDeck — Генератор карточек Anki", page_icon="📚", layout="centered")

st.title("📚 LexiDeck: Text to Anki")
st.write("Автоматическое извлечение редких слов из текста и сборка колод Anki.")

deck_name = st.text_input("Название колоды", value="English Vocabulary")

uploaded_file = st.file_uploader("Загрузить текстовый файл (.txt)", type=["txt"])
raw_text = st.text_area("Или вставьте текст на английском сюда:", height=200)

target_text = ""
if uploaded_file is not None:
    target_text = uploaded_file.read().decode("utf-8")
elif raw_text.strip():
    target_text = raw_text.strip()

if st.button("Сгенерировать колоду", type="primary"):
    if not target_text:
        st.warning("Пожалуйста, введите текст или загрузите файл.")
    else:
        with st.status("Обработка текста...", expanded=True) as status:
            st.write("🔍 Лемматизация и отбор редких слов через spaCy...")
            vocab_entries = process_text_fn(target_text)
            
            if not vocab_entries:
                status.update(label="Слова не найдены", state="error")
                st.error("В тексте не найдено продвинутых слов вне базового словаря.")
                st.stop()
            
            st.write(f"Найдено уникальных кандидатов: {len(vocab_entries)}. Запрашиваем словарь...")
            enriched_records = run_enrichment_safe(vocab_entries)
            
            valid_entries = [
                e for e in enriched_records 
                if getattr(e, "found", True) and getattr(e, "definition", "").strip()
            ]
            
            if not valid_entries:
                status.update(label="Не удалось найти определения", state="error")
                st.error("Ни одно из найденных слов не удалось верифицировать через Dictionary API.")
                st.stop()
                
            st.write(f"Успешно обработано слов: {len(valid_entries)}. Упаковываем в Anki...")
            deck_path = create_anki_deck(valid_entries, deck_name=deck_name)
            status.update(label="Готово!", state="complete", expanded=False)

        st.success(f"Колода успешно собрана! Добавлено слов: {len(valid_entries)}")

        preview_data = []
        for entry in valid_entries:
            preview_data.append({
                "Word": entry.lemma,
                "Part of Speech": getattr(entry, "part_of_speech", ""),
                "Phonetic": getattr(entry, "phonetic", ""),
                "Definition": getattr(entry, "definition", ""),
                "Context": entry.context
            })
        st.dataframe(pd.DataFrame(preview_data), use_container_width=True)

        with open(deck_path, "rb") as file:
            st.download_button(
                label="📥 Скачать файл .apkg",
                data=file,
                file_name=f"{Path(deck_path).name}",
                mime="application/octet-stream"
            )