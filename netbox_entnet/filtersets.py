from netbox.filtersets import NetBoxModelFilterSet
from .models import EntNet


# class EntNetFilterSet(NetBoxModelFilterSet):
#
#     class Meta:
#         model = EntNet
#         fields = ['name', ]
#
#     def search(self, queryset, name, value):
#         return queryset.filter(description__icontains=value)
