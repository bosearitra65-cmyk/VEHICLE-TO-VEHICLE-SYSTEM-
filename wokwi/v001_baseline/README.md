# V2V V001 Baseline

Vehicle ID:
V001

Device ID:
WOKWI-V001

Mechanism:
Periodic vehicle-state reporting.

Reporting interval:
5 seconds.

API:
POST /vehicle

Required payload fields:
vehicle_id
sequence_number
timestamp
latitude
longitude
speed
heading
communication_status

Supported additional fields:
device_id
boot_id
gps_fix
satellites
hdop
gps_source
transport

Authentication:
Currently disabled for V001.

IMPORTANT:
Cloud Wokwi cannot directly reach a backend running on localhost.
The BACKEND_URL must be changed to a publicly reachable backend endpoint before real cloud Wokwi-to-backend testing.

This package does not create a proxy and does not create a second backend protocol.
