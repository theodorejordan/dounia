from django.core.management.base import BaseCommand
from albums.models import Album


class Command(BaseCommand):
    help = 'Generate thumbnails for all existing album covers'

    def handle(self, *args, **options):
        albums = Album.objects.exclude(cover='')
        total = albums.count()

        self.stdout.write(f'Processing {total} albums...')

        success = 0
        errors = 0

        for i, album in enumerate(albums, 1):
            try:
                # Force generate the thumbnail file
                album.cover_thumbnail.generate()
                success += 1
                if i % 50 == 0:
                    self.stdout.write(f'  Processed {i}/{total}...')
            except Exception as e:
                errors += 1
                self.stderr.write(f'  Error for album {album.id}: {e}')

        self.stdout.write(
            self.style.SUCCESS(f'Done! Generated {success} thumbnails, {errors} errors.')
        )
