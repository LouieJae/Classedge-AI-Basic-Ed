from django.db import models


class TransmutationRule(models.Model):
    transmutation_table_name = models.CharField(max_length=100)
    min_grade = models.DecimalField(max_digits=5, decimal_places=2)
    max_grade = models.DecimalField(max_digits=5, decimal_places=2)
    transmuted_value = models.CharField(max_length=10)

    class Meta:
        ordering = ['-max_grade', 'min_grade']
        unique_together = ('transmutation_table_name', 'min_grade', 'max_grade')

    def __str__(self):
        return f"{self.transmutation_table_name}: {self.min_grade}-{self.max_grade} -> {self.transmuted_value}"

    @staticmethod
    def convert_grade(transmutation_table_name, grade):
        rules = TransmutationRule.objects.filter(transmutation_table_name=transmutation_table_name).order_by('-max_grade')
        for rule in rules:
            if rule.min_grade <= grade <= rule.max_grade:
                return rule.transmuted_value
        return "5.00"
