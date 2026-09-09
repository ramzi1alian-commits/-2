# -*- coding: utf-8 -*-
"""
Quran I3rab AI V2
=================
واجهة API محلية لتحليل إعراب القرآن الكريم اعتمادًا على قاعدة بيانات صرفية-نحوية
(مبنية على بيانات The Quranic Arabic Corpus لـ Kais Dukes) + محرك قواعد لتحويل
العلاقات الإعرابية إلى جمل عربية مفهومة.

⚠️ توضيح مهم: هذا النظام محرك قواعد + قاعدة بيانات مرجعية موثوقة، وليس نموذج
لغوي مُدرَّب (LLM). دقّته في حدود ما تغطيه قاعدة البيانات ومحرك القواعد أدناه.
لربطه بنموذج لغوي حقيقي، استخدم `LLM_SYSTEM_PROMPT_AR.txt` كطبقة توجيه فوق
مخرجات هذا الـ API (انظر قسم "الخطوات التالية" في README).
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
DB = ROOT / "quran_i3rab.db"

app = FastAPI(
    title="Quran I3rab AI",
    version="2.1",
    description="API لتحليل إعراب القرآن الكريم اعتمادًا على قاعدة بيانات صرفية-نحوية مرجعية.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Ask(BaseModel):
    question: str
    surah: Optional[int] = None
    ayah: Optional[int] = None


def db() -> sqlite3.Connection:
    if not DB.exists():
        raise HTTPException(500, "قاعدة البيانات غير موجودة على الخادم.")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


CASE = {"NOM": "مرفوع", "ACC": "منصوب", "GEN": "مجرور", "JUS": "مجزوم"}


def word_segments(surah: int, ayah: int) -> List[sqlite3.Row]:
    """يرجع كل المقاطع الصرفية (بادئة/جذع/لاحقة) للآية، مرتبة، باستثناء عقدة
    الجذر النحوي الخاصة بكل جملة (sentence_word = 0) والتي ليست كلمة فعلية."""
    con = db()
    rows = con.execute(
        """SELECT * FROM tokens
           WHERE chapter_id=? AND verse_id=? AND sentence_word<>0
           ORDER BY word_id, tok_id""",
        (surah, ayah),
    ).fetchall()
    con.close()
    return rows


def group_words(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """يجمع المقاطع الصرفية (بادئة+جذع+لاحقة) في كل كلمة قرآنية واحدة، ويختار
    من مقطع الجذع (STEM) معلومات الإعراب (العلاقة والحالة الإعرابية)، لأن
    البادئات (مثل حرف الجر) واللواحق لا تُعرَب استقلالًا عن جذع الكلمة."""
    words: Dict[int, Dict[str, Any]] = {}
    order: List[int] = []
    for r in rows:
        wid = r["word_id"]
        if wid not in words:
            words[wid] = {"segments": [], "stem": None}
            order.append(wid)
        words[wid]["segments"].append(r)
        if r["segment"] == "STEM":
            words[wid]["stem"] = r

    result = []
    for wid in order:
        w = words[wid]
        full_word = "".join(seg["uthmani_token"] for seg in w["segments"])
        stem = w["stem"] or w["segments"][-1]
        result.append(
            {
                "word": full_word,
                "pos": stem["pos_ar"],
                "relation": stem["rel_label_ar"],
                "case_code": stem["nominal_case"],
                "case": CASE.get(stem["nominal_case"]),
                "lemma": stem["lemma_ar"],
                "root": stem["root_ar"],
            }
        )
    return result


MARK = {"مرفوع": "الضمة", "منصوب": "الفتحة", "مجرور": "الكسرة", "مجزوم": "السكون"}

# قوالب ثابتة لأشهر العلاقات الإعرابية (علاقة، حالة) -> نص الإعراب.
# هذه القائمة تغطي الحالات الأكثر تكرارًا في القرآن، وليست شاملة كل الأنواع
# النحوية الدقيقة (~120 نوع علاقة في البيانات الخام) — انظر README لقائمة التغطية.
FIXED_RULES = {
    ("خبر كان", "منصوب"): "خبر «كان» منصوب",
    ("اسم كان", "مرفوع"): "اسم «كان» مرفوع",
    ("اسم إن", "منصوب"): "اسم «إنّ» منصوب",
    ("خبر إن", "منصوب"): "خبر «إنّ» منصوب",
    ("اسم أن", "منصوب"): "اسم «أنّ» منصوب",
    ("خبر أن", "منصوب"): "خبر «أنّ» منصوب",
    ("اسم لا", "منصوب"): "اسم «لا» النافية للجنس منصوب",
    ("مفعول به", "منصوب"): "مفعول به منصوب",
    ("فاعل", "مرفوع"): "فاعل مرفوع",
    ("نائب فاعل", "مرفوع"): "نائب فاعل مرفوع",
    ("مضاف إليه", "مجرور"): "مضاف إليه مجرور",
    ("مجرور", "مجرور"): "اسم مجرور بحرف الجر",
    ("مبتدأ", "مرفوع"): "مبتدأ مرفوع",
    ("خبر", "مرفوع"): "خبر مرفوع",
    ("تمييز", "منصوب"): "تمييز منصوب",
    ("مفعول مطلق", "منصوب"): "مفعول مطلق منصوب",
    ("المفعول لأجله", "منصوب"): "مفعول لأجله منصوب",
    ("منادى", "منصوب"): "منادى منصوب",
}

# علاقات نمطية تُبنى جملتها من (النص + الحالة) مهما كانت الحالة.
PATTERN_RULES = {
    "صفة": "صفة، تتبع موصوفها في إعرابها",
    "بدل": "بدل، يتبع المبدل منه في إعرابه",
    "حال": "حال",
    "معطوف": "معطوف على ما قبله، ويأخذ إعرابه تبعًا للمعطوف عليه",
}

# بادئات أجزاء الكلام غير المُعرَبة استقلالًا (حروف وأدوات مبنية).
PARTICLE_POS_PREFIXES = ("حرف", "أداة")


def explain(w: Dict[str, Any]) -> str:
    word = w["word"]
    rel = w["relation"]
    case = w["case"]
    pos = w.get("pos") or ""

    key = (rel, case)
    if key in FIXED_RULES:
        mark = MARK.get(case, "")
        return f"{word}: {FIXED_RULES[key]}، وعلامة إعرابه {mark} الظاهرة على آخره."

    if rel in PATTERN_RULES:
        base = PATTERN_RULES[rel]
        if case:
            mark = MARK.get(case, "")
            return f"{word}: {base}، وهو {case}{' وعلامة إعرابه ' + mark + ' الظاهرة على آخره' if mark else ''}."
        return f"{word}: {base}."

    if rel == "root":
        return f"{word}: رأس الجملة (الفعل أو العنصر الرئيس) في شجرة التحليل النحوي؛ لا عامل خارجي يحكمه."

    if pos.startswith(PARTICLE_POS_PREFIXES):
        return f"{word}: {pos}، وهو مبني لا محل له من الإعراب غالبًا (تحديد موقعه بدقة من الجملة يحتاج سياقًا نحويًا أوسع لم يُدرَج بعد في محرك القواعد)."

    if case:
        return f"{word}: العلاقة الإعرابية المسجَّلة هي «{rel}»، والحالة الإعرابية {case}. (لم يُبنَ بعد قالب شرح تفصيلي لهذا النوع تحديدًا في محرك القواعد — البيانات المرجعية صحيحة، لكن الصياغة اللغوية الكاملة قيد التطوير)."

    return f"{word}: العلاقة الإعرابية المسجَّلة هي «{rel}»، ولا تحدد البيانات حالة إعرابية صريحة لهذا الموضع."


@app.get("/health")
def health():
    return {"ok": True, "database": DB.exists(), "engine": "quran-i3rab-ai-v2.1"}


@app.get("/ayah/{surah}/{ayah}")
def ayah(surah: int, ayah: int):
    rows = word_segments(surah, ayah)
    if not rows:
        raise HTTPException(404, "الآية غير موجودة أو رقم السورة/الآية غير صحيح.")
    words = group_words(rows)
    return {
        "surah": surah,
        "ayah": ayah,
        "text": " ".join(w["word"] for w in words),
        "analysis": [
            {
                "word": w["word"],
                "pos": w["pos"],
                "relation": w["relation"],
                "case": w["case"],
                "explanation": explain(w),
            }
            for w in words
        ],
    }


@app.post("/ask")
def ask(x: Ask):
    # طبقة سؤال بسيطة وآمنة تعتمد على المطابقة مع الكلمات الفعلية بعد تجميع
    # المقاطع الصرفية؛ لا تدّعي فهم اللغة الطبيعية الحر بعد.
    q = x.question.strip()
    if x.surah and x.ayah:
        rows = word_segments(x.surah, x.ayah)
        if not rows:
            raise HTTPException(404, "الآية غير موجودة أو رقم السورة/الآية غير صحيح.")
        words = group_words(rows)
        for w in words:
            if w["word"] in q:
                return {"answer": explain(w), "source": "Quranic Arabic Corpus + rule engine"}
        return {
            "answer": "أستطيع تحليل الآية، لكن السؤال لا يحدد كلمة موجودة فيها بعينها. اطلب: «أعرب الآية» أو اذكر الكلمة كما وردت في المصحف.",
            "source": "rule engine",
        }
    return {
        "answer": "أرسل رقم السورة والآية مع السؤال لربط الإجابة بالبيانات المرجعية.",
        "source": "rule engine",
    }
