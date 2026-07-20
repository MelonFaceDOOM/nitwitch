from django.core.management.base import BaseCommand
from photoalbums.models import PhotoAlbumImage


class Command(BaseCommand):
    help = (
        "Rebuild photoalbum thumbnails with EXIF orientation applied "
        "(fixes sideways thumbs from phone photos)."
    )

    def handle(self, *args, **options):
        qs = PhotoAlbumImage.objects.exclude(image='')
        total = qs.count()
        fixed = 0
        failed = 0
        for i, img in enumerate(qs.iterator(), start=1):
            try:
                img.resize_image()
                fixed += 1
            except Exception as e:
                failed += 1
                self.stderr.write(f"Failed id={img.id}: {e}")
            if i % 25 == 0 or i == total:
                self.stdout.write(f"Processed {i}/{total}")
        self.stdout.write(self.style.SUCCESS(
            f"Done. Regenerated {fixed}, failed {failed}."
        ))
