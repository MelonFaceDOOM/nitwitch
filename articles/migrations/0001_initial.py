# Generated by Django 3.2.8 on 2021-11-16 16:09

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('article_text', models.CharField(max_length=10000)),
                ('pub_date', models.DateTimeField(verbose_name='date published')),
                ('author', models.CharField(max_length=200)),
            ],
        ),
    ]
