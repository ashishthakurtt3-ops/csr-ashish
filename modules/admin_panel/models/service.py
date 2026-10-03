from django.db import models


class ServiceCatalog(models.Model):
    service_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=100, default='CSR Intelligence')
    description = models.TextField(blank=True, null=True)
    price_inr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Service Catalog Item'
        verbose_name_plural = 'Service Catalog'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (₹{self.price_inr})"
