package com.quran.irab.robot;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * روبوت إعراب القرآن — نسخة أوفلاين.
 *
 * التطبيق لا يتصل بالإنترنت إلا إذا فعّل المستخدم "الوضع الذكي" الاختياري:
 * كل شيء آخر (الواجهة + قاعدة بيانات الإعراب الكاملة لكل كلمات القرآن)
 * مضمّن داخل ملف assets/index.html، ويُعرض هنا عبر WebView محلي بحت.
 *
 * عمدًا: نشاط عادي (Activity) بدون أي تبعية AndroidX/AppCompat — التطبيق
 * لا يحتاج شيئًا غير WebView، وهذا يتجنّب أي تعارض إصدارات مكتبات خارجية.
 */
public class MainActivity extends Activity {

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        WebView webView = new WebView(this);
        setContentView(webView);

        webView.getSettings().setJavaScriptEnabled(true);
        // مطلوب حتى تُحفَظ إعدادات "الوضع الذكي" (تفعيله + رابط الخادم) عبر localStorage
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setAllowFileAccess(true);
        webView.setWebViewClient(new WebViewClient());

        webView.loadUrl("file:///android_asset/index.html");
    }
}
