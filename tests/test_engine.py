# -*- coding: utf-8 -*-
"""
اختبارات أساسية لمحرك التحليل (بدون الحاجة لتشغيل خادم HTTP فعلي).
شغّلها بـ: pytest -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import word_segments, group_words, explain, DB  # noqa: E402


def test_database_exists():
    assert DB.exists(), "قاعدة البيانات quran_i3rab.db غير موجودة"


def test_al_fatiha_ayah_1_word_count():
    rows = word_segments(1, 1)
    words = group_words(rows)
    # "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ" = 4 كلمات
    assert len(words) == 4
    assert words[0]["word"] == "بِسْمِ"


def test_no_sentence_root_marker_leaks_into_words():
    # عقدة الجذر الخاصة بشجرة التحليل (sentence_word=0) يجب ألا تظهر ككلمة
    rows = word_segments(112, 1)
    words = group_words(rows)
    assert all(w["word"] != "(*)" for w in words)


def test_explain_never_raises_for_any_ayah_sample():
    # عيّنة من آيات متنوعة الطول والتراكيب للتأكد من عدم انهيار محرك القواعد
    samples = [(1, 1), (1, 7), (112, 1), (2, 255), (114, 1)]
    for surah, ayah in samples:
        rows = word_segments(surah, ayah)
        assert rows, f"لم يتم العثور على {surah}:{ayah}"
        words = group_words(rows)
        for w in words:
            text = explain(w)
            assert isinstance(text, str) and len(text) > 0


def test_unknown_ayah_returns_empty():
    rows = word_segments(999, 999)
    assert rows == []
