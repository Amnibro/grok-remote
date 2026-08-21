package com.amniscient.grokremote.wear
import android.app.Activity
import android.os.Bundle
import android.view.WindowManager
import android.webkit.WebView
import android.webkit.WebViewClient
class MainActivity:Activity(){
 override fun onCreate(b:Bundle?){
  super.onCreate(b)
  window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
  val wv=WebView(this)
  wv.settings.javaScriptEnabled=true
  wv.settings.domStorageEnabled=true
  wv.settings.builtInZoomControls=false
  wv.webViewClient=WebViewClient()
  setContentView(wv)
  wv.loadUrl(assets.open("watch_url.txt").bufferedReader().use{it.readText()}.trim().ifEmpty{"about:blank"})
 }
}
