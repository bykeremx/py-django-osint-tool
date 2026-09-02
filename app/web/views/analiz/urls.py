from django.urls import path

from .views import detail, download_json, item_ekle, item_sil, kaydet

urlpatterns = [
    path("kaydet/", kaydet, name="analiz_kaydet"),
    path("<int:pk>/json/", download_json, name="analiz_json"),
    path("<int:pk>/item/ekle/", item_ekle, name="analiz_item_ekle"),
    path("<int:pk>/item/<int:item_id>/sil/", item_sil, name="analiz_item_sil"),
    path("<int:pk>/", detail, name="analiz_detail"),
]
