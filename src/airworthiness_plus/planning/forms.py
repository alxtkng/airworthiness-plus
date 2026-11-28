"""Forms for work planning and release evidence."""

from decimal import Decimal
from typing import Any, cast

from django import forms

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.contracts.models import WorkOrder
from airworthiness_plus.defects.models import Defect
from airworthiness_plus.directives.models import Applicability, Decision
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.maintenance_data.models import DataSet, Revision
from airworthiness_plus.people.models import MaintenanceAuthorisation, Person, StaffGroup
from airworthiness_plus.planning.models import WorkCard, WorkPackage
from airworthiness_plus.planning.services import synthetic_available
from airworthiness_plus.programme.models import Task
from airworthiness_rules.intervals import TaskKind


class BuildPackageForm(Form):
    aircraft = forms.ModelChoiceField(
        label="Aircraft Registration", queryset=Aircraft.objects.all()
    )
    reference = forms.CharField(label="Reference", max_length=40)
    title = forms.CharField(label="Work", max_length=200)
    location = forms.CharField(label="Location", max_length=100)
    starts_on = forms.DateField(label="Planned Start")
    ends_on = forms.DateField(label="Planned End")
    defect = forms.ModelChoiceField(label="Defect", queryset=Defect.objects.all(), required=False)


class WorkOrderChoice(forms.ModelChoiceField):  # type: ignore[type-arg]
    def label_from_instance(self, obj: WorkOrder) -> str:
        return f"{obj.work} ({obj.agreed_on:%d %B %Y})"


class LinkOrderForm(Form):
    order = WorkOrderChoice(label="Work Order", queryset=WorkOrder.objects.none())

    def __init__(self, data: Any = None, *, package: WorkPackage) -> None:
        super().__init__(data)
        cast(WorkOrderChoice, self.fields["order"]).queryset = WorkOrder.objects.filter(
            aircraft_id=package.aircraft_id, closed_on__isnull=True
        )


class DirectiveChoice(forms.ModelChoiceField):  # type: ignore[type-arg]
    def label_from_instance(self, obj: Applicability) -> str:
        return str(obj.directive)


class WorkCardForm(Form):
    title = forms.CharField(label="Task", max_length=200)
    data_set = forms.ModelChoiceField(label="Maintenance Data", queryset=DataSet.objects.all())
    instruction = forms.CharField(label="Instruction Reference", max_length=200)
    planned_hours = forms.DecimalField(
        label="Planned Hours", max_digits=6, decimal_places=1, min_value=0
    )
    critical = forms.BooleanField(label="Critical Task", required=False)
    inspection_hours = forms.DecimalField(
        label="Planned Inspection Hours",
        max_digits=6,
        decimal_places=1,
        min_value=0,
        required=False,
    )
    task = forms.ModelChoiceField(
        label="Programme Task", queryset=Task.objects.none(), required=False
    )
    directive = DirectiveChoice(
        label="Airworthiness Directive",
        queryset=Applicability.objects.none(),
        required=False,
    )

    structured_steps = forms.CharField(
        label="Synthetic Step Instructions",
        widget=forms.Textarea,
        help_text="Enter one training instruction per line. Prefix a critical step with *.",
        max_length=6000,
        required=False,
    )

    def __init__(self, data: Any = None, *, package: WorkPackage) -> None:
        super().__init__(data)
        if not synthetic_available(package):
            del self.fields["structured_steps"]
        cast("forms.ModelChoiceField[Task]", self.fields["task"]).queryset = Task.objects.filter(
            programme__aircraft_id=package.aircraft_id,
            retired=False,
        ).exclude(kind=TaskKind.AIRWORTHINESS_DIRECTIVE.value)
        cast(
            DirectiveChoice, self.fields["directive"]
        ).queryset = Applicability.objects.select_related("directive").filter(
            aircraft_id=package.aircraft_id,
            decision=Decision.APPLICABLE,
            terminated_on__isnull=True,
        )

    def clean_inspection_hours(self) -> Decimal:
        return cast(Decimal | None, self.cleaned_data["inspection_hours"]) or Decimal("0")


class WorkCompletionForm(Form):
    revision = forms.ModelChoiceField(label="Revision Used", queryset=Revision.objects.none())
    performed_by = forms.ModelChoiceField(label="Performed By", queryset=Person.objects.all())
    supervised_by = forms.ModelChoiceField(
        label="Supervised By", queryset=Person.objects.all(), required=False
    )
    completed_on = forms.DateField(label="Completed")
    sign_off_reference = forms.CharField(label="Signed Work Evidence", max_length=200)
    hours = forms.DecimalField(label="Counter Hours", max_digits=8, decimal_places=1, min_value=0)
    cycles = forms.IntegerField(label="Counter Cycles", min_value=0, max_value=2147483647)

    def __init__(self, data: Any = None, *, card: WorkCard) -> None:
        super().__init__(data, initial={"revision": card.revision_id})
        field = cast("forms.ModelChoiceField[Revision]", self.fields["revision"])
        field.queryset = Revision.objects.filter(data_set_id=card.data_set_id)


class InspectionForm(Form):
    inspector = forms.ModelChoiceField(label="Independent Inspector", queryset=Person.objects.all())
    inspected_on = forms.DateField(label="Inspected")
    qualification = forms.CharField(label="Inspector Qualification Evidence", max_length=200)
    evidence = forms.CharField(
        label="Satisfactory Inspection Evidence", widget=forms.Textarea, max_length=500
    )


class AuthorisationChoice(forms.ModelChoiceField):  # type: ignore[type-arg]
    def label_from_instance(self, obj: MaintenanceAuthorisation) -> str:
        return f"{obj.person} ({obj.reference})"


class PackageReleaseForm(Form):
    reference = forms.CharField(label="Certificate Reference", max_length=100)
    issued_by = forms.ModelChoiceField(
        label="Certifying Staff", queryset=Person.objects.filter(staff_group=StaffGroup.CERTIFYING)
    )
    issued_on = forms.DateField(label="Released")
    maintenance_authorisation = AuthorisationChoice(
        label="Maintenance Authorisation",
        queryset=MaintenanceAuthorisation.objects.select_related("person"),
    )
    scope_confirmed = forms.BooleanField(label="Authorisation Covers This Work")
    verification = forms.CharField(label="General Verification Evidence", max_length=200)


class AttestationForm(Form):
    consent = forms.BooleanField(label="Consent to the Reviewed Synthetic Attestation")
    intent = forms.CharField(widget=forms.HiddenInput, max_length=256)


class StepSignOffForm(Form):
    evidence = forms.CharField(label="Step Result", widget=forms.Textarea, max_length=500)
    consent = forms.BooleanField(label="I completed this synthetic step as shown")
