from django.db import models
from django.utils.text import slugify


class Tag(models.Model):
    """Tag pour catégoriser les albums"""
    CATEGORY_CHOICES = [
        ('shape', 'Formes'),
        ('human', 'Humains'),
        ('animal', 'Animaux'),
        ('landscape', 'Paysage'),
        ('object', 'Objet'),
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
            self.slug = slugify(self.name)
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
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['artist', '-created_at']),
            models.Index(fields=['year']),
        ]
    
    def __str__(self):
        return f"{self.artist.name} - {self.name}"