from django import forms
from ipam.models import Prefix
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from utilities.forms.fields import CommentField, DynamicModelChoiceField

from .models import EntNet


class EntNetForm(NetBoxModelForm):
    class Meta:
        model = EntNet
        fields = ("name", "tags")
