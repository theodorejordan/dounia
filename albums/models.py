from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class AlbumQuerySet(models.QuerySet):
    """Custom queryset for Album with reusable filter logic"""

    def with_filters(self, artist_search=None, category=None, tags=None):
        """
        Apply filters to albums based on search criteria.

        Args:
            artist_search: Filter by artist name (case-insensitive)
            category: Filter by tag category
            tags: List of tag IDs (all must match)

        Returns:
            Filtered QuerySet
        """
        queryset = self

        # Filter by artist name
        if artist_search:
            queryset = queryset.filter(artist__name__icontains=artist_search)

        # Filter by tag category
        if category:
            queryset = queryset.filter(tags__category=category).distinct()

        # Filter by specific tags (all must match)
        if tags:
            for tag_id in tags:
                queryset = queryset.filter(tags__id=tag_id)
            queryset = queryset.distinct()

        return queryset


class AlbumManager(models.Manager):
    """Custom manager that uses AlbumQuerySet"""

    def get_queryset(self):
        """Override to use our custom QuerySet"""
        return AlbumQuerySet(self.model, using=self._db)

    def with_filters(self, *args, **kwargs):
        """Proxy to QuerySet.with_filters() for convenience"""
        return self.get_queryset().with_filters(*args, **kwargs)


class Tag(models.Model):
    """Tag pour catégoriser les albums"""
    CATEGORY_CHOICES = [
        ('color', 'Colors'),
        ('colorType', 'Color Types'),
        ('disposition', 'Dispositions'),
        ('shape', 'Shapes'),
        ('human', 'Humans'),
        ('animal', 'Animals'),
        ('landscape', 'Environments'),
        ('vehicules', 'Vehicles'),
        ('object', 'Objects'),
        ('style', 'Styles'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='custom')
    parent = models.ForeignKey('self', null=True, blank=True, 
                               on_delete=models.CASCADE, 
                               related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'name']
        indexes = [models.Index(fields=['category'])]
    
    def __str__(self):
        return self.name


class Artist(models.Model):
    """Artiste créateur de l'album"""
    name = models.CharField(max_length=200, unique=True, db_index=True)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Generate base slug from name
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 2

            # Keep trying until we find a unique slug
            # Exclude self when updating an existing artist
            while Artist.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Album(models.Model):
    """Album principal avec métadonnées"""
    # Champs obligatoires
    name = models.CharField(max_length=300, db_index=True)
    artist = models.ForeignKey(Artist, on_delete=models.PROTECT,
                               related_name='albums')
    cover = models.ImageField(upload_to='covers/%Y/%m/')

    # Champs optionnels
    year = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    # Relations
    tags = models.ManyToManyField(Tag, related_name='albums', blank=True)

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Custom manager
    objects = AlbumManager()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['artist', '-created_at']),
            models.Index(fields=['year']),
        ]
    
    def __str__(self):
        return f"{self.artist.name} - {self.name}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return self.user.username