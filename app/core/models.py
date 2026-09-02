# Analiz raporları — ana kayıt + key/value maddeler.
from django.db import models


class Analiz(models.Model):
    MODULE_DNS = "dns_scan"
    MODULE_NETWORK = "network_intel"
    MODULE_IMAGE = "image_osint"
    MODULE_EMAIL = "email_osint"
    MODULE_USERNAME = "username_osint"
    MODULE_NMAP = "nmap_scan"

    MODULE_CHOICES = [
        (MODULE_DNS, "DNS recon"),
        (MODULE_NETWORK, "Network intel"),
        (MODULE_IMAGE, "Image OSINT"),
        (MODULE_EMAIL, "Email OSINT"),
        (MODULE_USERNAME, "Username OSINT"),
        (MODULE_NMAP, "Nmap scan"),
    ]

    target = models.CharField(max_length=255, db_index=True)
    module = models.CharField(max_length=32, choices=MODULE_CHOICES, db_index=True)
    analyst_note = models.TextField(blank=True, default="")
    report_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "analiz"
        ordering = ["-created_at"]
        verbose_name = "Analiz"
        verbose_name_plural = "Analizler"

    def __str__(self) -> str:
        return f"{self.get_module_display()} · {self.target} · #{self.pk}"


class AnalizItem(models.Model):
    analiz = models.ForeignKey(Analiz, on_delete=models.CASCADE, related_name="items")
    key = models.CharField(max_length=512, db_index=True)
    value = models.TextField()

    class Meta:
        db_table = "analiz_item"
        verbose_name = "Analiz maddesi"
        verbose_name_plural = "Analiz maddeleri"

    def __str__(self) -> str:
        return f"{self.key}={self.value[:40]}"
