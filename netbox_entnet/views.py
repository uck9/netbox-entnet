from django.db.models import Count

from netbox.views import generic
from . import filtersets, forms, models, tables


class EntNetView(generic.ObjectView):
    queryset = models.EntNet.objects.all()


class EntNetListView(generic.ObjectListView):
    queryset = models.EntNet.objects.all()
    table = tables.EntNetTable


class EntNetEditView(generic.ObjectEditView):
    queryset = models.EntNet.objects.all()
    form = forms.EntNetForm


class EntNetDeleteView(generic.ObjectDeleteView):
    queryset = models.EntNet.objects.all()
