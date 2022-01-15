# Generated by Django 3.2.8 on 2022-01-15 04:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0007_auto_20220113_2213'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='edit_date',
            field=models.DateTimeField(auto_now=True, verbose_name='date published'),
        ),
        migrations.AddField(
            model_name='article',
            name='view_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='article',
            name='pub_date',
            field=models.DateTimeField(auto_now_add=True, verbose_name='date published'),
        ),
    ]
