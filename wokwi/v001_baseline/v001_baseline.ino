#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>

const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

/*
  Replace this only when the backend is publicly reachable.
  Do NOT use localhost for cloud Wokwi.
*/
const char* BACKEND_URL = "http://YOUR_PUBLIC_BACKEND_HOST/vehicle";

const char* VEHICLE_ID = "V001";
const char* DEVICE_ID = "WOKWI-V001";
const char* BOOT_ID = "wokwi-v001-boot-1";

unsigned long sequenceNumber = 0;
unsigned long lastReport = 0;
const unsigned long REPORT_INTERVAL_MS = 5000;

double latitude = 22.572600;
double longitude = 88.363900;
float speedKmh = 35.0;
float heading = 90.0;

String utcTimestamp() {
  time_t now = time(nullptr);

  if (now < 100000) {
    return "1970-01-01T00:00:00Z";
  }

  struct tm* utc = gmtime(&now);
  char buffer[32];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", utc);
  return String(buffer);
}

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("WIFI_CONNECTING");
  unsigned long start = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(250);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WIFI_CONNECTED");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WIFI_CONNECTION_FAILED");
  }
}

void syncTime() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");

  Serial.print("TIME_SYNC");
  unsigned long start = millis();

  while (time(nullptr) < 100000 && millis() - start < 10000) {
    delay(250);
    Serial.print(".");
  }

  Serial.println();
}

void sendVehicleState() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("REPORT_SKIPPED_WIFI_DISCONNECTED");
    connectWiFi();
    return;
  }

  StaticJsonDocument<768> doc;

  doc["vehicle_id"] = VEHICLE_ID;
  doc["sequence_number"] = sequenceNumber;
  doc["timestamp"] = utcTimestamp();
  doc["latitude"] = latitude;
  doc["longitude"] = longitude;
  doc["speed"] = speedKmh;
  doc["heading"] = heading;
  doc["communication_status"] = "CONNECTED";
  doc["device_id"] = DEVICE_ID;
  doc["boot_id"] = BOOT_ID;
  doc["gps_fix"] = true;
  doc["satellites"] = 8;
  doc["hdop"] = 1.0;
  doc["gps_source"] = "SIMULATED";
  doc["transport"] = "WIFI";

  String payload;
  serializeJson(doc, payload);

  HTTPClient http;
  http.begin(BACKEND_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);

  Serial.println("VEHICLE_REPORT_BEGIN");
  Serial.println(payload);

  int responseCode = http.POST(payload);

  Serial.print("HTTP_STATUS=");
  Serial.println(responseCode);

  if (responseCode > 0) {
    Serial.println("BACKEND_RESPONSE=");
    Serial.println(http.getString());
  } else {
    Serial.println("BACKEND_REQUEST_FAILED");
  }

  http.end();

  sequenceNumber++;
  longitude += 0.0001;

  Serial.print("NEXT_SEQUENCE=");
  Serial.println(sequenceNumber);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("V2V_V001_BASELINE_START");
  Serial.print("VEHICLE_ID=");
  Serial.println(VEHICLE_ID);
  Serial.print("DEVICE_ID=");
  Serial.println(DEVICE_ID);

  connectWiFi();
  syncTime();
}

void loop() {
  if (millis() - lastReport >= REPORT_INTERVAL_MS) {
    lastReport = millis();
    sendVehicleState();
  }

  delay(20);
}
