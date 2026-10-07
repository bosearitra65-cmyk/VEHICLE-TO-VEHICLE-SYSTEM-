from enum import StrEnum


class Permission(StrEnum):
    VEHICLE_VIEW = "vehicle.view"
    VEHICLE_MANAGE = "vehicle.manage"

    CONVOY_VIEW = "convoy.view"
    CONVOY_MANAGE = "convoy.manage"
    CONVOY_LEADER_ASSIGN = "convoy.leader.assign"

    JOURNEY_VIEW = "journey.view"
    JOURNEY_MANAGE = "journey.manage"

    ROUTE_VIEW = "route.view"
    ROUTE_MANAGE = "route.manage"

    ALERTS_VIEW = "alerts.view"
    EVENTS_VIEW = "events.view"
    HISTORY_VIEW = "history.view"

    RESEARCH_VIEW = "research.view"
    RESEARCH_CREATE = "research.create"
    RESEARCH_CONFIGURE = "research.configure"
    RESEARCH_RUN = "research.run"
    RESEARCH_FAULT_CONTROL = "research.fault_control"
    RESEARCH_ANALYZE = "research.analyze"
    RESEARCH_EVIDENCE_MANAGE = "research.evidence.manage"

    USER_MANAGE = "user.manage"
    ACCESS_MANAGE = "access.manage"
    SYSTEM_CONFIGURE = "system.configure"
