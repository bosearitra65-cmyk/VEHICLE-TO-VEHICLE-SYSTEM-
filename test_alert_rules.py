from app.services.alert_rules import should_create_alert


class TestEvent:
    def __init__(self, event_type, severity):
        self.event_type = event_type
        self.severity = severity


gps_event = TestEvent("gps_quality", "warning")
gap_event = TestEvent("sequence_gap", "warning")

print("GPS warning:", should_create_alert(gps_event))
print("Sequence gap warning:", should_create_alert(gap_event))