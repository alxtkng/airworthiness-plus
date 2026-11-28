"""Derive a label from dated control and condition evidence."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from airworthiness_plus.organisations.models import Approval
from airworthiness_plus.tooling.calibration_models import CalibrationOrder, CalibrationReinstatement
from airworthiness_plus.tooling.calibration_status import holding_order, reinstatement_on
from airworthiness_plus.tooling.models import ControlKind, EventKind, Tool, ToolControlEvent
from airworthiness_plus.tooling.models import ToolControlRevision as Revision
from airworthiness_rules.dates import add_months

COMPLETIONS = {
    ControlKind.CALIBRATION: EventKind.CALIBRATED,
    ControlKind.SERVICING: EventKind.SERVICED,
}
CONDITION_EVENTS = (
    EventKind.UNSERVICEABLE,
    EventKind.INTERIM_FAIL,
    EventKind.REINSTATED,
    EventKind.WITHDRAWN,
)
RESTRICTIONS = (EventKind.UNSERVICEABLE, EventKind.INTERIM_FAIL)
UNKNOWN = "Control basis to verify"


@dataclass(frozen=True)
class ControlLine:
    revision: Revision
    completion: ToolControlEvent | CalibrationReinstatement | None
    due_on: date | None
    status: str


@dataclass(frozen=True)
class ToolLabel:
    tool: Tool
    controls: list[ControlLine]
    condition: ToolControlEvent | None
    calibration_hold: CalibrationOrder | None

    @property
    def next_due(self) -> date | None:
        return min((line.due_on for line in self.controls if line.due_on), default=None)

    @property
    def restricted(self) -> bool:
        return self.calibration_hold is not None or (
            self.condition is not None and self.condition.kind != EventKind.REINSTATED
        )

    @property
    def control_status(self) -> str:
        if not self.controls:
            return UNKNOWN
        for status in ("Overdue", "Completion evidence needed", "Due today", "Due soon"):
            if any(line.status == status for line in self.controls):
                return status
        if any(line.status == ControlKind.BEFORE_USE for line in self.controls):
            return ControlKind.BEFORE_USE
        return "Controls current"

    @property
    def needs_attention(self) -> bool:
        if self.condition and self.condition.kind == EventKind.WITHDRAWN:
            return False
        return self.restricted or self.control_status in {
            UNKNOWN,
            "Overdue",
            "Completion evidence needed",
            "Due today",
            "Due soon",
        }


def active_controls(
    tool: Tool, approval: Approval, reference: str, day: date
) -> dict[str, Revision]:
    latest: dict[str, Revision] = {}
    for revision in tool.control_revisions.all():
        if (
            revision.delegation.approval_id == approval.pk
            and revision.delegation.approval_reference == reference
            and revision.effective_on <= day
        ):
            latest.setdefault(revision.kind, revision)
    return latest


def condition_on(tool: Tool, day: date) -> ToolControlEvent | None:
    return next(
        (
            event
            for event in tool.control_events.all()
            if event.kind in CONDITION_EVENTS
            and event.occurred_on <= day
            and event.signed_on <= day
        ),
        None,
    )


def label(
    tool: Tool, approval: Approval | None, reference: str, day: date, lead_days: int
) -> ToolLabel:
    """Derive all control dates for one approval and the shared physical condition."""
    controls = active_controls(tool, approval, reference, day) if approval else {}
    completions: dict[UUID, ToolControlEvent | CalibrationReinstatement] = {}
    for event in tool.control_events.all():
        if (
            event.control_id is not None
            and event.kind in COMPLETIONS.values()
            and event.occurred_on <= day
            and event.signed_on <= day
        ):
            completions.setdefault(event.control_id, event)
    calibration_hold = holding_order(tool, day)
    cases = [
        order.impact_case
        for order in tool.calibration_orders.all()
        if hasattr(order, "impact_case") and order.impact_case.opened_on <= day
    ]
    for order in tool.calibration_orders.all():
        if ready := reinstatement_on(order, day):
            earlier = completions.get(ready.control_id)
            if earlier is None or (ready.occurred_on, ready.entered_at) > (
                earlier.occurred_on,
                earlier.entered_at,
            ):
                completions[ready.control_id] = ready
    lines = []
    for revision in controls.values():
        completion = completions.get(revision.pk)
        due = (
            add_months(completion.occurred_on, revision.interval_months)
            if completion and revision.interval_months is not None
            else None
        )
        if revision.kind == ControlKind.BEFORE_USE:
            state: str = ControlKind.BEFORE_USE
        elif (
            revision.kind == ControlKind.CALIBRATION
            and completion
            and calibration_hold is None
            and any(
                completion.entered_at <= case.entered_at
                or completion.occurred_on < case.trigger.certificate.calibrated_on
                for case in cases
            )
        ):
            state = "Completion evidence needed"
            due = None
        elif due is None:
            state = "Completion evidence needed"
        elif due < day:
            state = "Overdue"
        elif due == day:
            state = "Due today"
        elif (due - day).days <= lead_days:
            state = "Due soon"
        else:
            state = "Current"
        lines.append(ControlLine(revision, completion, due, state))
    return ToolLabel(tool, lines, condition_on(tool, day), calibration_hold)
