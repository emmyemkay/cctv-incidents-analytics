from pathlib import Path

from django import forms

from .models import DatasetUpload


MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_TOTAL_SIZE = 100 * 1024 * 1024


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        return [single_file_clean(data, initial)]


class DatasetBulkUploadForm(forms.Form):
    files = MultipleFileField(
        label="Incident CSV files",
        help_text="Select one or more Fire, General Crime, Traffic, or CCTV event CSV files.",
        widget=MultipleFileInput(
            attrs={
                "class": "form-control",
                "accept": ".csv,text/csv",
                "multiple": True,
            }
        ),
    )
    incident_type = forms.ChoiceField(
        label="Incident type",
        choices=DatasetUpload.IncidentType.choices,
        initial=DatasetUpload.IncidentType.AUTO,
        help_text="Keep Auto-detect when uploading different datasets together.",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def clean_files(self):
        files = self.cleaned_data["files"]
        total_size = 0
        for uploaded in files:
            if Path(uploaded.name).suffix.lower() != ".csv":
                raise forms.ValidationError(f"{uploaded.name}: only CSV files are supported.")
            if uploaded.size > MAX_FILE_SIZE:
                raise forms.ValidationError(f"{uploaded.name}: the file must be 50 MB or smaller.")
            total_size += uploaded.size
        if total_size > MAX_TOTAL_SIZE:
            raise forms.ValidationError("The selected files must be 100 MB or smaller in total.")
        return files
