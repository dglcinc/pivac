#include <OneWire.h>
#include <DallasTemperature.h>

OneWire bus(2);
DallasTemperature sensors(&bus);

#define MAX_DEV 16
DeviceAddress roms[MAX_DEV];
uint8_t nDev = 0;

void printRomFull(const DeviceAddress a) {
  for (uint8_t i = 0; i < 8; i++) {
    if (a[i] < 16) Serial.print('0');
    Serial.print(a[i], HEX);
  }
}

int cmpRom(const uint8_t *a, const uint8_t *b) {
  for (uint8_t i = 0; i < 8; i++) { if (a[i] != b[i]) return (int)a[i] - (int)b[i]; }
  return 0;
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {}
  sensors.begin();
  sensors.setResolution(12);
  nDev = sensors.getDeviceCount();
  if (nDev > MAX_DEV) nDev = MAX_DEV;
  for (uint8_t i = 0; i < nDev; i++) sensors.getAddress(roms[i], i);

  // freeze a deterministic column order: sort by ROM
  for (uint8_t i = 0; i < nDev; i++)
    for (uint8_t j = i + 1; j < nDev; j++)
      if (cmpRom(roms[j], roms[i]) < 0) {
        DeviceAddress t; memcpy(t, roms[i], 8);
        memcpy(roms[i], roms[j], 8); memcpy(roms[j], t, 8);
      }

  Serial.print("# devices: "); Serial.println(nDev);
  Serial.println("# col,rom");
  for (uint8_t i = 0; i < nDev; i++) {
    Serial.print("# "); Serial.print(i); Serial.print(",");
    printRomFull(roms[i]); Serial.println();
  }
  Serial.print("millis");
  for (uint8_t i = 0; i < nDev; i++) { Serial.print(",c"); Serial.print(i); }
  Serial.println();
}

void loop() {
  sensors.requestTemperatures();
  Serial.print(millis());
  for (uint8_t i = 0; i < nDev; i++) {
    Serial.print(",");
    Serial.print(sensors.getTempF(roms[i]), 2);
  }
  Serial.println();
  delay(1000);
}
