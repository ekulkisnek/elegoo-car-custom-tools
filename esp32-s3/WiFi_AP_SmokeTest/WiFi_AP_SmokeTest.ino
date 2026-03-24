/*
 * Minimal soft-AP smoke test — no camera, no STA.
 * If phone sees "ELEGOO-SMOKE", RF + WiFi stack are OK; debug main sketch next.
 */
#include <WiFi.h>
#include "esp_wifi.h"

#ifndef SMOKE_AP_SSID
#define SMOKE_AP_SSID "ELEGOO-SMOKE"
#endif
#ifndef SMOKE_AP_CHANNEL
#define SMOKE_AP_CHANNEL 1
#endif

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println();
  Serial.println("=== WiFi_AP_SmokeTest ===");

  WiFi.mode(WIFI_AP);
  WiFi.setSleep(false);
  esp_wifi_set_ps(WIFI_PS_NONE);

  bool ok = WiFi.softAP(SMOKE_AP_SSID, nullptr, SMOKE_AP_CHANNEL);
  if (!ok) {
    ok = WiFi.softAP(SMOKE_AP_SSID, "", SMOKE_AP_CHANNEL);
  }
  Serial.printf("softAP: %s\n", ok ? "OK" : "FAILED");
  Serial.print("AP IP: ");
  Serial.println(WiFi.softAPIP());
  Serial.println("Look for \"" SMOKE_AP_SSID "\" on 2.4 GHz Wi-Fi list.");
}

void loop() {
  delay(5000);
  Serial.printf("AP stations: %d  IP: %s\n", WiFi.softAPgetStationNum(), WiFi.softAPIP().toString().c_str());
}
