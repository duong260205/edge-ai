/*
 * http_handlers.cpp
 *
 * Supplemental HTTP handlers for voice authentication and system status.
 * This file does NOT duplicate any handlers from main.cpp.
 *
 * Voice endpoints are registered via register_voice_httpd_handlers().
 * main.cpp's start_camera_server() must call that function to enable
 * voice endpoints, or the user can add a one-line call manually.
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_system.h"
#include "esp_log.h"
#include "esp_http_server.h"
#include "esp_heap_caps.h"
#include "esp_netif.h"
#include "face_recognition.h"
#include "voice_auth.h"
#include "audio_capture.h"
#include "http_handlers.h"

static const char *TAG = "camera_http_server";

#define MAX_JSON_RESPONSE 2048
#define MAX_SPEAKER_NAME 32

// ---------------------------------------------------------------------------
// sys_status — definition of the global variable declared in http_handlers.h
// ---------------------------------------------------------------------------
system_status_t sys_status = {0};

// ---------------------------------------------------------------------------
// Embedded Voice Auth HTML (fallback when SPIFFS is unavailable)
// ---------------------------------------------------------------------------

static const char* voice_html = "<!DOCTYPE html>"
"<html lang=\"en\">"
"<head>"
"<meta charset=\"UTF-8\">"
"<meta name='viewport' content='width=device-width, initial-scale=1'>"
"<title>Voice Authentication</title>"
"<style>"
":root {"
"  --bg: #0f0f23;"
"  --card: #1a1a3e;"
"  --card-hover: #252550;"
"  --primary: #6c63ff;"
"  --primary-hover: #5a52e0;"
"  --success: #00c853;"
"  --error: #ff1744;"
"  --warning: #ffab00;"
"  --text: #e0e0ff;"
"  --text-dim: #8888bb;"
"  --border: #2a2a55;"
"  --radius: 12px;"
"}"
"* { margin: 0; padding: 0; box-sizing: border-box; }"
"body {"
"  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;"
"  background: var(--bg);"
"  color: var(--text);"
"  min-height: 100vh;"
"  padding: 20px;"
"}"
".container {"
"  max-width: 900px;"
"  margin: 0 auto;"
"}"
".header {"
"  display: flex;"
"  align-items: center;"
"  justify-content: space-between;"
"  margin-bottom: 30px;"
"  flex-wrap: wrap;"
"  gap: 10px;"
"}"
".header h1 {"
"  font-size: 24px;"
"  background: linear-gradient(135deg, var(--primary), #a855f7);"
"  -webkit-background-clip: text;"
"  -webkit-text-fill-color: transparent;"
"  background-clip: text;"
"}"
".header .nav-links a {"
"  color: var(--text-dim);"
"  text-decoration: none;"
"  margin-left: 15px;"
"  font-size: 14px;"
"  transition: color 0.2s;"
"}"
".header .nav-links a:hover { color: var(--primary); }"
".grid {"
"  display: grid;"
"  grid-template-columns: 1fr 1fr;"
"  gap: 20px;"
"  margin-bottom: 20px;"
"}"
"@media (max-width: 700px) { .grid { grid-template-columns: 1fr; } }"
".card {"
"  background: var(--card);"
"  border: 1px solid var(--border);"
"  border-radius: var(--radius);"
"  padding: 24px;"
"  transition: all 0.3s ease;"
"}"
".card:hover {"
"  background: var(--card-hover);"
"  border-color: var(--primary);"
"  transform: translateY(-2px);"
"  box-shadow: 0 8px 25px rgba(108,99,255,0.15);"
"}"
".card h2 {"
"  font-size: 16px;"
"  margin-bottom: 16px;"
"  color: var(--text);"
"  display: flex;"
"  align-items: center;"
"  gap: 8px;"
"}"
".card h2 .icon { font-size: 20px; }"
"label {"
"  display: block;"
"  font-size: 12px;"
"  color: var(--text-dim);"
"  margin-bottom: 6px;"
"  text-transform: uppercase;"
"  letter-spacing: 0.5px;"
"}"
"input, select {"
"  width: 100%;"
"  padding: 10px 14px;"
"  background: var(--bg);"
"  border: 1px solid var(--border);"
"  border-radius: 8px;"
"  color: var(--text);"
"  font-size: 14px;"
"  outline: none;"
"  transition: border-color 0.2s;"
"  margin-bottom: 12px;"
"}"
"input:focus { border-color: var(--primary); }"
"input::placeholder { color: var(--text-dim); }"
".btn {"
"  display: inline-flex;"
"  align-items: center;"
"  justify-content: center;"
"  gap: 8px;"
"  padding: 10px 20px;"
"  border: none;"
"  border-radius: 8px;"
"  font-size: 14px;"
"  font-weight: 600;"
"  cursor: pointer;"
"  transition: all 0.2s ease;"
"  width: 100%;"
"}"
".btn:active { transform: scale(0.97); }"
".btn:disabled {"
"  opacity: 0.5;"
"  cursor: not-allowed;"
"  transform: none !important;"
"}"
".btn-primary {"
"  background: var(--primary);"
"  color: white;"
"}"
".btn-primary:hover:not(:disabled) { background: var(--primary-hover); box-shadow: 0 4px 15px rgba(108,99,255,0.4); }"
".btn-success {"
"  background: var(--success);"
"  color: white;"
"}"
".btn-success:hover:not(:disabled) { box-shadow: 0 4px 15px rgba(0,200,83,0.4); }"
".btn-danger {"
"  background: var(--error);"
"  color: white;"
"}"
".btn-danger:hover:not(:disabled) { box-shadow: 0 4px 15px rgba(255,23,68,0.4); }"
".btn-sm {"
"  padding: 6px 12px;"
"  font-size: 12px;"
"  width: auto;"
"}"
".status {"
"  padding: 12px 16px;"
"  border-radius: 8px;"
"  margin-top: 12px;"
"  font-size: 13px;"
"  display: none;"
"  animation: slideIn 0.3s ease;"
"}"
".status.show { display: block; }"
".status.success {"
"  background: rgba(0,200,83,0.15);"
"  border: 1px solid rgba(0,200,83,0.3);"
"  color: var(--success);"
"}"
".status.error {"
"  background: rgba(255,23,68,0.15);"
"  border: 1px solid rgba(255,23,68,0.3);"
"  color: var(--error);"
"}"
".status.info {"
"  background: rgba(108,99,255,0.15);"
"  border: 1px solid rgba(108,99,255,0.3);"
"  color: var(--primary);"
"}"
"@keyframes slideIn {"
"  from { opacity: 0; transform: translateY(-8px); }"
"  to { opacity: 1; transform: translateY(0); }"
"}"
".progress-container {"
"  margin-top: 12px;"
"  display: none;"
"}"
".progress-container.show { display: block; }"
".progress-bar-bg {"
"  width: 100%;"
"  height: 6px;"
"  background: var(--bg);"
"  border-radius: 3px;"
"  overflow: hidden;"
"}"
".progress-bar-fill {"
"  height: 100%;"
"  width: 0%;"
"  background: linear-gradient(90deg, var(--primary), #a855f7);"
"  border-radius: 3px;"
"  transition: width 0.5s ease;"
"}"
".progress-text {"
"  font-size: 12px;"
"  color: var(--text-dim);"
"  margin-top: 6px;"
"  text-align: center;"
"}"
".spinner {"
"  display: inline-block;"
"  width: 16px;"
"  height: 16px;"
"  border: 2px solid rgba(255,255,255,0.3);"
"  border-top-color: white;"
"  border-radius: 50%;"
"  animation: spin 0.6s linear infinite;"
"}"
"@keyframes spin { to { transform: rotate(360deg); } }"
".speaker-list { margin-top: 12px; }"
".speaker-item {"
"  display: flex;"
"  align-items: center;"
"  justify-content: space-between;"
"  padding: 10px 14px;"
"  background: var(--bg);"
"  border-radius: 8px;"
"  margin-bottom: 6px;"
"  transition: all 0.2s;"
"}"
".speaker-item:hover { border-color: var(--primary); }"
".speaker-item .name {"
"  font-weight: 600;"
"  font-size: 14px;"
"}"
".speaker-item .meta {"
"  font-size: 12px;"
"  color: var(--text-dim);"
"}"
".speaker-item .actions { display: flex; gap: 6px; }"
".speaker-empty {"
"  text-align: center;"
"  padding: 20px;"
"  color: var(--text-dim);"
"  font-size: 14px;"
"}"
".result-box {"
"  margin-top: 12px;"
"  padding: 16px;"
"  border-radius: 8px;"
"  text-align: center;"
"  display: none;"
"}"
".result-box.show { display: block; }"
".result-box.matched {"
"  background: rgba(0,200,83,0.1);"
"  border: 1px solid rgba(0,200,83,0.3);"
"}"
".result-box.not-matched {"
"  background: rgba(255,23,68,0.1);"
"  border: 1px solid rgba(255,23,68,0.3);"
"}"
".result-box .confidence {"
"  font-size: 36px;"
"  font-weight: 700;"
"}"
".result-box .label { font-size: 13px; color: var(--text-dim); margin-top: 4px; }"
".result-box.matched .confidence { color: var(--success); }"
".result-box.not-matched .confidence { color: var(--error); }"
".setting-row {"
"  display: flex;"
"  align-items: center;"
"  justify-content: space-between;"
"  margin-bottom: 16px;"
"  gap: 16px;"
"}"
".setting-row .info { flex: 1; }"
".setting-row .info .label { font-size: 12px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }"
".setting-row .info .value { font-size: 14px; font-weight: 600; color: var(--primary); }"
"input[type=\"range\"] {"
"  width: 120px;"
"  -webkit-appearance: none;"
"  appearance: none;"
"  background: var(--bg);"
"  height: 4px;"
"  border-radius: 2px;"
"  outline: none;"
"  margin: 0;"
"  padding: 0;"
"}"
"input[type=\"range\"]::-webkit-slider-thumb {"
"  -webkit-appearance: none;"
"  width: 18px;"
"  height: 18px;"
"  border-radius: 50%;"
"  background: var(--primary);"
"  cursor: pointer;"
"  transition: transform 0.2s;"
"}"
"input[type=\"range\"]::-webkit-slider-thumb:hover { transform: scale(1.2); }"
".badge {"
"  display: inline-flex;"
"  align-items: center;"
"  gap: 4px;"
"  padding: 3px 10px;"
"  border-radius: 20px;"
"  font-size: 11px;"
"  font-weight: 600;"
"  text-transform: uppercase;"
"}"
".badge.on { background: rgba(0,200,83,0.2); color: var(--success); }"
".badge.off { background: rgba(255,23,68,0.2); color: var(--error); }"
".card-full { grid-column: 1 / -1; }"
"@media (max-width: 700px) { .card-full { grid-column: auto; } }"
"</style>"
"</head>"
"<body>"
"<div class=\"container\">"
"  <div class=\"header\">"
"    <h1>Voice Authentication</h1>"
"    <div class=\"nav-links\">"
"      <span id=\"status-badge\" class=\"badge off\">Checking...</span>"
"      <a href=\"/\" target=\"_blank\">Face Camera</a>"
"      <a href=\"/recognition\" target=\"_blank\">Live Stream</a>"
"      <a href=\"/status\" target=\"_blank\">Status</a>"
"    </div>"
"  </div>"
"  <div class=\"grid\">"
"    <div class=\"card\">"
"      <h2>[+] Enroll Speaker</h2>"
"      <label for=\"enroll-name\">Speaker Name</label>"
"      <input type=\"text\" id=\"enroll-name\" placeholder=\"e.g. john\" maxlength=\"31\">"
"      <button class=\"btn btn-primary\" id=\"btn-enroll\" onclick=\"enrollSpeaker()\">"
"        <span id=\"enroll-icon\">[mic]</span>"
"        <span id=\"enroll-text\">Start Enrollment (5 samples)</span>"
"      </button>"
"      <div class=\"progress-container\" id=\"enroll-progress\">"
"        <div class=\"progress-bar-bg\">"
"          <div class=\"progress-bar-fill\" id=\"enroll-progress-fill\" style=\"width:0%\"></div>"
"        </div>"
"        <div class=\"progress-text\" id=\"enroll-progress-text\">Waiting...</div>"
"      </div>"
"      <div id=\"enroll-status\" class=\"status\"></div>"
"    </div>"
"    <div class=\"card\">"
"      <h2>[OK] Verify Speaker</h2>"
"      <label for=\"verify-name\">Speaker Name (optional)</label>"
"      <input type=\"text\" id=\"verify-name\" placeholder=\"Leave empty for any voice\" maxlength=\"31\">"
"      <button class=\"btn btn-success\" id=\"btn-verify\" onclick=\"verifySpeaker()\">"
"        <span id=\"verify-icon\">[mic2]</span>"
"        <span id=\"verify-text\">Start Verification</span>"
"      </button>"
"      <div class=\"result-box\" id=\"verify-result\">"
"        <div class=\"confidence\" id=\"verify-confidence\">0%</div>"
"        <div class=\"label\" id=\"verify-label\">Waiting for voice...</div>"
"      </div>"
"      <div id=\"verify-status\" class=\"status\"></div>"
"    </div>"
"    <div class=\"card card-full\">"
"      <h2>[people] Enrolled Speakers</h2>"
"      <div id=\"speakers-container\">"
"        <div class=\"speaker-empty\">No speakers enrolled yet.</div>"
"      </div>"
"    </div>"
"    <div class=\"card card-full\">"
"      <h2>[gear] Settings</h2>"
"      <div class=\"setting-row\">"
"        <div class=\"info\">"
"          <div class=\"label\">Authentication Threshold</div>"
"          <div class=\"value\" id=\"threshold-value\">0.50</div>"
"        </div>"
"        <input type=\"range\" id=\"threshold-slider\" min=\"0\" max=\"100\" value=\"50\""
"               oninput=\"updateThreshold(this.value)\">"
"      </div>"
"      <div class=\"setting-row\">"
"        <div class=\"info\">"
"          <div class=\"label\">VAD Sensitivity</div>"
"          <div class=\"value\" id=\"sensitivity-value\">0.75</div>"
"        </div>"
"        <input type=\"range\" id=\"sensitivity-slider\" min=\"0\" max=\"100\" value=\"75\""
"               oninput=\"updateSensitivity(this.value)\">"
"      </div>"
"    </div>"
"  </div>"
"</div>"
"<script>"
"let isEnrolling = false;"
"let isVerifying = false;"
"async function updateStatusBadge() {"
"  try {"
"    const r = await fetch('/status');"
"    const d = await r.json();"
"    const badge = document.getElementById('status-badge');"
"    if (d.audio === 'true' && d.voice_auth === 'true') {"
"      badge.className = 'badge on';"
"      badge.textContent = '(*) Voice Ready';"
"    } else {"
"      badge.className = 'badge off';"
"      badge.textContent = '(*) Voice Offline';"
"    }"
"  } catch { /* ignore */ }"
"}"
"updateStatusBadge();"
"setInterval(updateStatusBadge, 5000);"
"function showStatus(id, msg, type) {"
"  const el = document.getElementById(id);"
"  el.className = 'status ' + type + ' show';"
"  el.textContent = msg;"
"  setTimeout(() => { el.className = 'status'; }, 5000);"
"}"
"function setProgress(containerId, fillId, textId, pct, text) {"
"  document.getElementById(containerId).className = 'progress-container show';"
"  document.getElementById(fillId).style.width = pct + '%';"
"  document.getElementById(textId).textContent = text;"
"}"
"function hideProgress(containerId) {"
"  document.getElementById(containerId).className = 'progress-container';"
"}"
"function setButtonLoading(btnId, iconId, textId, loading, text) {"
"  const btn = document.getElementById(btnId);"
"  const icon = document.getElementById(iconId);"
"  const txt = document.getElementById(textId);"
"  btn.disabled = loading;"
"  if (loading) {"
"    icon.innerHTML = '<span class=\"spinner\"></span>';"
"    txt.textContent = text || 'Processing...';"
"  } else {"
"    icon.textContent = '[mic]';"
"    txt.textContent = text || 'Start';"
"  }"
"}"
"async function enrollSpeaker() {"
"  if (isEnrolling) return;"
"  const name = document.getElementById('enroll-name').value.trim();"
"  if (!name) { showStatus('enroll-status', 'Please enter a speaker name', 'error'); return; }"
"  isEnrolling = true;"
"  setButtonLoading('btn-enroll', 'enroll-icon', 'enroll-text', true, 'Enrolling...');"
"  hideProgress('enroll-progress');"
"  setProgress('enroll-progress', 'enroll-progress-fill', 'enroll-progress-text', 30, '[mic] Speak now...');"
"  document.getElementById('enroll-status').className = 'status';"
"  try {"
"    const r = await fetch('/voice/enroll?name=' + encodeURIComponent(name), { method: 'POST' });"
"    const d = await r.json();"
"    if (d.status === 'success') {"
"      setProgress('enroll-progress', 'enroll-progress-fill', 'enroll-progress-text', 100, '[OK] Enrollment complete!');"
"      showStatus('enroll-status', d.message, 'success');"
"      document.getElementById('enroll-name').value = '';"
"      loadSpeakers();"
"      setTimeout(() => hideProgress('enroll-progress'), 3000);"
"    } else {"
"      showStatus('enroll-status', d.message || 'Enrollment failed.', 'error');"
"      hideProgress('enroll-progress');"
"    }"
"  } catch (e) {"
"    showStatus('enroll-status', 'Network error: ' + e.message, 'error');"
"    hideProgress('enroll-progress');"
"  }"
"  isEnrolling = false;"
"  setButtonLoading('btn-enroll', 'enroll-icon', 'enroll-text', false, 'Start Enrollment (5 samples)');"
"}"
"async function verifySpeaker() {"
"  if (isVerifying) return;"
"  const name = document.getElementById('verify-name').value.trim();"
"  const resultBox = document.getElementById('verify-result');"
"  resultBox.className = 'result-box';"
"  document.getElementById('verify-status').className = 'status';"
"  isVerifying = true;"
"  document.getElementById('btn-verify').disabled = true;"
"  document.getElementById('verify-icon').innerHTML = '<span class=\"spinner\"></span>';"
"  document.getElementById('verify-text').textContent = 'Recording...';"
"  document.getElementById('verify-confidence').textContent = '...';"
"  document.getElementById('verify-label').textContent = 'Listening...';"
"  try {"
"    const url = name ? '/voice/verify?name=' + encodeURIComponent(name) : '/voice/verify';"
"    const r = await fetch(url, { method: 'POST' });"
"    const d = await r.json();"
"    resultBox.className = 'result-box show ' + (d.matched === 'true' || d.matched === true ? 'matched' : 'not-matched');"
"    const conf = parseFloat(d.confidence);"
"    const confPct = Math.round(conf * 100);"
"    document.getElementById('verify-confidence').textContent = confPct + '%';"
"    if (d.voice_detected === 'true' || d.voice_detected === true) {"
"      if (d.matched === 'true' || d.matched === true) {"
"        document.getElementById('verify-label').textContent = '[OK] ' + d.message;"
"      } else {"
"        document.getElementById('verify-label').textContent = '[X] ' + d.message;"
"      }"
"    } else {"
"      document.getElementById('verify-label').textContent = '[mute] No voice detected.';"
"    }"
"    if (d.status === 'error' && d.matched !== 'true') {"
"      showStatus('verify-status', d.message, 'info');"
"    }"
"  } catch (e) {"
"    showStatus('verify-status', 'Network error: ' + e.message, 'error');"
"    resultBox.className = 'result-box';"
"  }"
"  isVerifying = false;"
"  document.getElementById('btn-verify').disabled = false;"
"  document.getElementById('verify-icon').textContent = '[mic2]';"
"  document.getElementById('verify-text').textContent = 'Start Verification';"
"}"
"async function loadSpeakers() {"
"  try {"
"    const r = await fetch('/voice/speakers');"
"    const d = await r.json();"
"    const container = document.getElementById('speakers-container');"
"    if (d.count === 0 || !d.speakers || d.speakers.length === 0) {"
"      container.innerHTML = '<div class=\"speaker-empty\">No speakers enrolled yet.</div>';"
"      return;"
"    }"
"    let html = '';"
"    d.speakers.forEach(s => {"
"      const name = s.name || 'Unknown';"
"      const samples = s.samples || 5;"
"      html += '<div class=\"speaker-item\"><div><div class=\"name\">' + escapeHtml(name) + '</div><div class=\"meta\">' + samples + ' sample(s)</div></div><div class=\"actions\"><button class=\"btn btn-success btn-sm\" onclick=\"quickVerify(\\'' + escapeHtml(name) + '\\')\">Verify</button><button class=\"btn btn-danger btn-sm\" onclick=\"deleteSpeaker(\\'' + escapeHtml(name) + '\\')\">Delete</button></div></div>';"
"    });"
"    container.innerHTML = html;"
"  } catch { /* ignore */ }"
"}"
"function escapeHtml(str) {"
"  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\"/g, '&quot;').replace(/'/g, '&#039;');"
"}"
"function quickVerify(name) {"
"  document.getElementById('verify-name').value = name;"
"  verifySpeaker();"
"}"
"async function deleteSpeaker(name) {"
"  if (!confirm('Delete speaker \"' + name + '\"?')) return;"
"  try {"
"    const r = await fetch('/voice/speakers?name=' + encodeURIComponent(name), { method: 'DELETE' });"
"    const d = await r.json();"
"    if (d.status === 'success') {"
"      showStatus('verify-status', d.message, 'success');"
"      loadSpeakers();"
"    } else {"
"      showStatus('verify-status', d.message || 'Delete failed', 'error');"
"    }"
"  } catch (e) {"
"    showStatus('verify-status', 'Error: ' + e.message, 'error');"
"  }"
"}"
"async function loadSettings() {"
"  try {"
"    const r = await fetch('/voice/settings');"
"    const d = await r.json();"
"    if (d.threshold !== undefined) {"
"      document.getElementById('threshold-value').textContent = d.threshold.toFixed(2);"
"      document.getElementById('threshold-slider').value = Math.round(d.threshold * 100);"
"    }"
"    if (d.vad_sensitivity !== undefined) {"
"      document.getElementById('sensitivity-value').textContent = d.vad_sensitivity.toFixed(2);"
"      document.getElementById('sensitivity-slider').value = Math.round(d.vad_sensitivity * 100);"
"    }"
"  } catch { /* ignore */ }"
"}"
"let settingsTimeout = null;"
"function updateThreshold(val) {"
"  const t = (parseInt(val) / 100).toFixed(2);"
"  document.getElementById('threshold-value').textContent = t;"
"  debounceSettings('threshold', parseFloat(t));"
"}"
"function updateSensitivity(val) {"
"  const s = (parseInt(val) / 100).toFixed(2);"
"  document.getElementById('sensitivity-value').textContent = s;"
"  debounceSettings('vad_sensitivity', parseFloat(s));"
"}"
"function debounceSettings(key, val) {"
"  if (settingsTimeout) clearTimeout(settingsTimeout);"
"  settingsTimeout = setTimeout(() => saveSettings(key, val), 500);"
"}"
"async function saveSettings(key, val) {"
"  const body = {};"
"  body[key] = val;"
"  try {"
"    await fetch('/voice/settings', {"
"      method: 'POST',"
"      headers: { 'Content-Type': 'application/json' },"
"      body: JSON.stringify(body)"
"    });"
"  } catch { /* ignore */ }"
"}"
"loadSpeakers();"
"loadSettings();"
"setInterval(loadSpeakers, 3000);"
"</script>"
"</body>"
"</html>";

// ===========================================================================
// Voice Authentication HTTP Handlers
// ===========================================================================

static const char* TAG_VOICE_HTTP = "HTTP_VOICE";
static SemaphoreHandle_t s_voice_http_mutex = nullptr;

static bool take_voice_http_mutex(TickType_t timeout)
{
    if (s_voice_http_mutex == nullptr) {
        s_voice_http_mutex = xSemaphoreCreateMutex();
        if (s_voice_http_mutex == nullptr) {
            ESP_LOGE(TAG_VOICE_HTTP, "Failed to create voice HTTP mutex");
            return false;
        }
    }
    return xSemaphoreTake(s_voice_http_mutex, timeout) == pdTRUE;
}

static void give_voice_http_mutex(void)
{
    if (s_voice_http_mutex != nullptr) {
        xSemaphoreGive(s_voice_http_mutex);
    }
}

/** Extract a query parameter value from the request URI. */
static bool get_query_param(httpd_req_t *req, const char* key, char* out, size_t out_size)
{
    char query[256];
    if (httpd_req_get_url_query_str(req, query, sizeof(query)) != ESP_OK) {
        return false;
    }
    return (httpd_query_key_value(query, key, out, out_size) == ESP_OK);
}

/** Send a simple JSON response with CORS header. */
static esp_err_t send_json(httpd_req_t *req, const char* json)
{
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_sendstr(req, json);
}

// ---------------------------------------------------------------------------
// Voice HTML page handler
// ---------------------------------------------------------------------------
static esp_err_t voice_page_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    ESP_LOGI(TAG_VOICE_HTTP, "Served /voice from embedded page");
    return httpd_resp_send(req, voice_html, strlen(voice_html));
}

// ---------------------------------------------------------------------------
// POST /voice/enroll?name=john
// Triggers a 5-sample enrollment loop.
// NOTE: The underlying voice_auth_enroll() is currently a stub (no-op).
// ---------------------------------------------------------------------------
static esp_err_t voice_enroll_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG_VOICE_HTTP, "Voice enroll handler called");

    if (!sys_status.audio_ready || !sys_status.voice_auth_ready) {
        return send_json(req, "{\"status\":\"error\",\"message\":\"Voice auth not initialised\"}");
    }

    char speaker_name[MAX_SPEAKER_NAME];
    if (!get_query_param(req, "name", speaker_name, sizeof(speaker_name)) || strlen(speaker_name) == 0) {
        return send_json(req, "{\"status\":\"error\",\"message\":\"Missing 'name' parameter\"}");
    }

    if (!take_voice_http_mutex(pdMS_TO_TICKS(100))) {
        return send_json(req, "{\"status\":\"busy\",\"message\":\"Voice subsystem is busy\"}");
    }

    size_t record_samples = AUDIO_SAMPLE_RATE;
    int16_t *audio_buf = (int16_t *)heap_caps_malloc(record_samples * sizeof(int16_t), MALLOC_CAP_SPIRAM);
    if (audio_buf == nullptr) {
        give_voice_http_mutex();
        return send_json(req, "{\"status\":\"error\",\"message\":\"Memory allocation failed\"}");
    }

    bool record_ok = audio_capture_record(audio_buf, record_samples);
    if (!record_ok) {
        heap_caps_free(audio_buf);
        give_voice_http_mutex();
        return send_json(req, "{\"status\":\"error\",\"message\":\"Audio recording failed\"}");
    }

    bool ok = voice_auth_enroll(speaker_name, audio_buf, (int)record_samples);
    heap_caps_free(audio_buf);
    give_voice_http_mutex();

    char json[MAX_JSON_RESPONSE];
    if (ok) {
        snprintf(json, sizeof(json),
                 "{\"status\":\"success\",\"message\":\"Speaker '%s' enrolled successfully (stub)\"}",
                 speaker_name);
    } else {
        snprintf(json, sizeof(json),
                 "{\"status\":\"error\",\"message\":\"Enrollment failed\"}");
    }
    return send_json(req, json);
}

// ---------------------------------------------------------------------------
// POST /voice/verify?name=john
// Records one audio sample and verifies against the model.
// ---------------------------------------------------------------------------
static esp_err_t voice_verify_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG_VOICE_HTTP, "Voice verify handler called");

    if (!sys_status.audio_ready || !sys_status.voice_auth_ready) {
        return send_json(req, "{\"status\":\"error\",\"message\":\"Voice auth not initialised\"}");
    }

    char speaker_name[MAX_SPEAKER_NAME];
    bool has_name = get_query_param(req, "name", speaker_name, sizeof(speaker_name)) && strlen(speaker_name) > 0;

    if (!take_voice_http_mutex(pdMS_TO_TICKS(100))) {
        return send_json(req, "{\"status\":\"busy\",\"message\":\"Voice subsystem is busy\"}");
    }

    size_t num_samples = AUDIO_SAMPLE_RATE;
    int16_t *audio_buf = (int16_t *)heap_caps_malloc(num_samples * sizeof(int16_t), MALLOC_CAP_SPIRAM);
    if (audio_buf == nullptr) {
        give_voice_http_mutex();
        return send_json(req, "{\"status\":\"error\",\"message\":\"Memory allocation failed\"}");
    }

    bool record_ok = audio_capture_record(audio_buf, num_samples);
    if (!record_ok) {
        heap_caps_free(audio_buf);
        give_voice_http_mutex();
        return send_json(req, "{\"status\":\"error\",\"message\":\"Audio recording failed\"}");
    }

    float energy = 0.0f;
    int peak_val = 0;
    for (size_t i = 0; i < num_samples; i++) {
        energy += (float)audio_buf[i] * (float)audio_buf[i];
        int a = abs(audio_buf[i]);
        if (a > peak_val) peak_val = a;
    }
    float rms = sqrtf(energy / (float)num_samples);
    bool voice_detected = (rms > 30.0f && peak_val > 100);

    float confidence = 0.0f;
    bool matched = false;
    if (voice_detected) {
        (void)has_name;
        matched = voice_auth_verify(audio_buf, (int)num_samples, &confidence);
    }

    char json[MAX_JSON_RESPONSE];
    snprintf(json, sizeof(json),
             "{\"status\":\"%s\",\"matched\":%s,\"confidence\":%.3f,\"rms_level\":%.1f,\"voice_detected\":%s,\"message\":\"%s\"}",
             (matched || voice_detected) ? "success" : "error",
             matched ? "true" : "false",
             confidence,
             rms,
             voice_detected ? "true" : "false",
             matched ? "Voice matched!" :
                       (voice_detected ? "Voice detected but not matched" : "No voice detected"));

    heap_caps_free(audio_buf);
    give_voice_http_mutex();
    return send_json(req, json);
}

// ---------------------------------------------------------------------------
// GET /voice/speakers
// ---------------------------------------------------------------------------
static esp_err_t voice_speakers_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG_VOICE_HTTP, "Voice speakers handler called");
    return send_json(req, "{\"count\":0,\"speakers\":[]}");
}

// ---------------------------------------------------------------------------
// DELETE /voice/speakers?name=john
// ---------------------------------------------------------------------------
static esp_err_t voice_delete_speaker_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG_VOICE_HTTP, "Voice delete speaker handler called");
    return send_json(req, "{\"status\":\"error\",\"message\":\"Deletion not supported in current firmware\"}");
}

// ---------------------------------------------------------------------------
// GET /voice/settings
// ---------------------------------------------------------------------------
static esp_err_t voice_settings_get_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG_VOICE_HTTP, "Voice settings GET handler called");
    char json[512];
    snprintf(json, sizeof(json),
             "{\"threshold\":%.2f,\"vad_sensitivity\":%.2f,\"sample_rate\":%d}",
             AUTH_THRESHOLD, 0.75f, AUDIO_SAMPLE_RATE);
    return send_json(req, json);
}

// ---------------------------------------------------------------------------
// POST /voice/settings
// (No-op in current firmware; returns current static settings.)
// ---------------------------------------------------------------------------
static esp_err_t voice_settings_post_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG_VOICE_HTTP, "Voice settings POST handler called (no-op)");
    char json[512];
    snprintf(json, sizeof(json),
             "{\"status\":\"success\",\"settings\":{"
             "\"threshold\":%.2f,"
             "\"vad_sensitivity\":%.2f,"
             "\"sample_rate\":%d}}",
             AUTH_THRESHOLD, 0.75f, AUDIO_SAMPLE_RATE);
    return send_json(req, json);
}

// ---------------------------------------------------------------------------
// GET /status — JSON endpoint with all sub-system initialisation statuses
// ---------------------------------------------------------------------------
static esp_err_t status_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "application/json");

    if (sys_status.wifi_connected) {
        esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
        if (netif != NULL) {
            esp_netif_ip_info_t ip_info;
            if (esp_netif_get_ip_info(netif, &ip_info) == ESP_OK && ip_info.ip.addr != 0) {
                snprintf(sys_status.ip_address, sizeof(sys_status.ip_address),
                         IPSTR, IP2STR(&ip_info.ip));
            }
        }
    }

    char json[512];
    int n = snprintf(json, sizeof(json),
        "{"
        "\"status\":\"%s\","
        "\"wifi\":%s,"
        "\"camera\":%s,"
        "\"face_recognition\":%s,"
        "\"neopixel\":%s,"
        "\"web_spiffs\":%s,"
        "\"server\":%s,"
        "\"audio\":%s,"
        "\"voice_auth\":%s,"
        "\"ip\":\"%s\""
        "}",
        (sys_status.wifi_connected && sys_status.camera_ok && sys_status.server_started) ? "running" : "degraded",
        sys_status.wifi_connected ? "true" : "false",
        sys_status.camera_ok ? "true" : "false",
        sys_status.face_recognition_ok ? "true" : "false",
        sys_status.neopixel_ok ? "true" : "false",
        sys_status.web_spiffs_mounted ? "true" : "false",
        sys_status.server_started ? "true" : "false",
        sys_status.audio_ready ? "true" : "false",
        sys_status.voice_auth_ready ? "true" : "false",
        sys_status.ip_address
    );

    if (n < 0 || (size_t)n >= sizeof(json)) {
        return httpd_resp_sendstr(req, "{\"status\":\"error\"}");
    }

    return httpd_resp_sendstr(req, json);
}

// ---------------------------------------------------------------------------
// Register all voice + status HTTP handlers onto an existing server handle
// ---------------------------------------------------------------------------

void register_voice_httpd_handlers(httpd_handle_t server)
{
    if (server == NULL) {
        ESP_LOGE(TAG, "Cannot register voice handlers: server handle is NULL");
        return;
    }

    httpd_uri_t voice_page_uri = {
        .uri = "/voice",
        .method = HTTP_GET,
        .handler = voice_page_handler,
        .user_ctx = NULL
    };

    httpd_uri_t status_uri = {
        .uri = "/status",
        .method = HTTP_GET,
        .handler = status_handler,
        .user_ctx = NULL
    };

    httpd_uri_t voice_enroll_uri = {
        .uri = "/voice/enroll",
        .method = HTTP_POST,
        .handler = voice_enroll_handler,
        .user_ctx = NULL
    };

    httpd_uri_t voice_verify_uri = {
        .uri = "/voice/verify",
        .method = HTTP_POST,
        .handler = voice_verify_handler,
        .user_ctx = NULL
    };

    httpd_uri_t voice_speakers_uri = {
        .uri = "/voice/speakers",
        .method = HTTP_GET,
        .handler = voice_speakers_handler,
        .user_ctx = NULL
    };

    httpd_uri_t voice_delete_speaker_uri = {
        .uri = "/voice/speakers",
        .method = HTTP_DELETE,
        .handler = voice_delete_speaker_handler,
        .user_ctx = NULL
    };

    httpd_uri_t voice_settings_get_uri = {
        .uri = "/voice/settings",
        .method = HTTP_GET,
        .handler = voice_settings_get_handler,
        .user_ctx = NULL
    };

    httpd_uri_t voice_settings_post_uri = {
        .uri = "/voice/settings",
        .method = HTTP_POST,
        .handler = voice_settings_post_handler,
        .user_ctx = NULL
    };

    ESP_LOGI(TAG, "Registering voice / status HTTP handlers...");

    httpd_register_uri_handler(server, &voice_page_uri);
    httpd_register_uri_handler(server, &status_uri);
    httpd_register_uri_handler(server, &voice_enroll_uri);
    httpd_register_uri_handler(server, &voice_verify_uri);
    httpd_register_uri_handler(server, &voice_speakers_uri);
    httpd_register_uri_handler(server, &voice_delete_speaker_uri);
    httpd_register_uri_handler(server, &voice_settings_get_uri);
    httpd_register_uri_handler(server, &voice_settings_post_uri);

    ESP_LOGI(TAG, "Voice / status HTTP handlers registered successfully");
}
