from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0007_job_behavioural_skills_job_day_in_the_life_and_more'),
    ]

    operations = [
        migrations.AddField(model_name='job', name='ats_tenant',
                            field=models.CharField(blank=True, max_length=255, null=True)),
        migrations.AddField(model_name='job', name='owner_status',
                            field=models.CharField(blank=True, max_length=40, null=True)),
        migrations.AddField(model_name='job', name='link_http_status',
                            field=models.IntegerField(blank=True, null=True)),
        migrations.AddField(model_name='job', name='link_check_reason',
                            field=models.TextField(blank=True, null=True)),
        migrations.AlterField(model_name='job', name='country',
                              field=models.CharField(blank=True, max_length=80, null=True)),
        migrations.AddConstraint(
            model_name='job',
            constraint=models.UniqueConstraint(fields=('ats_platform', 'ats_tenant', 'external_job_id'),
                                               name='uniq_job_per_ats_tenant'),
        ),
        migrations.AddField(model_name='company', name='jobs_access',
                            field=models.CharField(choices=[('UNKNOWN', 'Not yet checked'), ('PUBLIC', 'Publicly visible on the company website'), ('LOGIN_REQUIRED', 'Visible only after login on the company website'), ('NOT_PUBLISHED', 'Not published on the company website')], default='UNKNOWN', max_length=20)),
        migrations.AddField(model_name='company', name='csr_access',
                            field=models.CharField(choices=[('UNKNOWN', 'Not yet checked'), ('PUBLIC', 'Publicly visible on the company website'), ('LOGIN_REQUIRED', 'Visible only after login on the company website'), ('NOT_PUBLISHED', 'Not published on the company website')], default='UNKNOWN', max_length=20)),
        migrations.AddField(model_name='company', name='contacts_access',
                            field=models.CharField(choices=[('UNKNOWN', 'Not yet checked'), ('PUBLIC', 'Publicly visible on the company website'), ('LOGIN_REQUIRED', 'Visible only after login on the company website'), ('NOT_PUBLISHED', 'Not published on the company website')], default='UNKNOWN', max_length=20)),
        migrations.AddField(model_name='company', name='data_access_note',
                            field=models.TextField(blank=True, null=True)),
        migrations.AddField(model_name='company', name='data_access_checked_at',
                            field=models.DateTimeField(blank=True, null=True)),
    ]
