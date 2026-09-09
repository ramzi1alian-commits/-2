// worker.js — خادم وسيط بسيط بين تطبيق روبوت إعراب القرآن ونموذج Claude.
// يحمي مفتاح API من الظهور داخل كود التطبيق، ويُلزم النموذج بعدم الخروج
// عن البيانات المرجعية (محرك القواعد) المرسلة معه في كل طلب.

const SYSTEM_PROMPT = `أنت مساعد متخصص في إعراب القرآن الكريم.
قواعد العمل:
1) لا تخترع نصًا قرآنيًا.
2) استخدم التحليل المرجعي المُرسَل إليك في هذه الرسالة فقط قبل الإجابة، ولا تخرج عنه.
3) فرّق دائمًا بين الإعراب المرجعي المذكور في السياق وبين أي شرح إضافي تستنتجه أنت.
4) إذا تعددت الأوجه الإعرابية عند النحاة، اذكر ذلك صراحة ولا تجعل وجهًا واحدًا قطعيًا دون دليل من السياق.
5) عند السؤال عن سبب الإعراب، اذكر العامل والموقع الإعرابي وعلامة الإعراب كما وردت في السياق.
6) إذا لم تكن المعلومة المطلوبة موجودة في السياق المرسل إليك، قل بوضوح إن البيانات المتاحة لديك غير كافية، ولا تخمّن.`;

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...corsHeaders() },
  });
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }
    if (request.method !== "POST") {
      return json({ error: "الطريقة غير مدعومة" }, 405);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "الطلب يجب أن يكون JSON صالحًا" }, 400);
    }

    const { context, question } = body || {};
    if (!context || !question) {
      return json({ error: "الحقلان context و question مطلوبان" }, 400);
    }
    if (!env.ANTHROPIC_API_KEY) {
      return json({ error: "لم يُضبَط مفتاح ANTHROPIC_API_KEY في إعدادات الـ Worker" }, 500);
    }

    const userMessage =
      "السياق المرجعي (من قاعدة بيانات إعراب القرآن، محرك قواعد موثوق):\n" +
      context +
      "\n\nسؤال المستخدم: " +
      question;

    try {
      const upstream = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-api-key": env.ANTHROPIC_API_KEY,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: "claude-sonnet-5",
          max_tokens: 700,
          system: SYSTEM_PROMPT,
          messages: [{ role: "user", content: userMessage }],
        }),
      });

      const data = await upstream.json();

      if (!upstream.ok) {
        const msg = (data && data.error && data.error.message) || "خطأ من واجهة Claude API";
        return json({ error: msg }, upstream.status);
      }

      const text = (data.content || [])
        .map((b) => b.text || "")
        .join("\n")
        .trim();

      return json({ answer: text || "لم يصل رد من النموذج." });
    } catch (e) {
      return json({ error: "تعذر الاتصال بواجهة Claude API: " + String(e) }, 502);
    }
  },
};
