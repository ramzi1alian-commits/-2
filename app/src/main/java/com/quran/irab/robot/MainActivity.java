package com.quran.irab.robot;

import android.annotation.SuppressLint;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;

/**
 * روبوت إعراب القرآن — نسخة أوفلاين.
 *
 * التطبيق لا يتصل بالإنترنت إطلاقًا: كل شيء (الواجهة + قاعدة بيانات الإعراب
 * الكاملة لكل كلمات القرآن) مضمّن داخل ملف assets/index.html، ويُعرض هنا عبر
 * WebView محلي بحت. لا توجد صلاحية INTERNET في AndroidManifest عمدًا.
 */
public class MainActivity extends AppCompatActivity {

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        WebView webView = new WebView(this);
        setContentView(webView);

        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setAllowFileAccess(true);
        webView.setWebViewClient(new WebViewClient());

        webView.loadUrl("file:///android_asset/index.html");
    }

    @Override
    public void onBackPressed() {
        super.onBackPressed();
    }
}
