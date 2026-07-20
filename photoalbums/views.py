from .models import PhotoAlbum, PhotoAlbumImage, ImageAmbiguityVote, PhotoAlbumComment, ImageComment,\
    ImageCommentAmbiguityVote, PhotoAlbumCommentAmbiguityVote
from django.views import generic
from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404, render, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from accounts.models import is_ip_banned
from accounts.permissions import admin_required
from django.http import HttpResponseForbidden
import json
import math


class IndexView(generic.ListView):
    context_object_name = "latest_photoalbums_list"
    template_name = "photoalbums/index.html"
    paginate_by = 5

    def get_queryset(self):
        return PhotoAlbum.objects.order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['background_grid_class'] = 'background-grid background-grid-medium'
        return context


ALBUM_PAGE_SIZE = 20


def photoalbum(request, title, album_page):
    # paginate comments by url ?arg
    photoalbum = get_object_or_404(PhotoAlbum, title=title)
    ip_address = request.META.get('REMOTE_ADDR')
    votes = ImageAmbiguityVote.objects.filter(ip_address=ip_address, image__in=photoalbum.images.all())
    vote_dict = {vote.image_id: vote.vote_type for vote in votes}
    images = []
    photoalbum_meta = {'title': photoalbum.title,
                       'id': photoalbum.id,
                       'author': photoalbum.author,
                       'pub_date': photoalbum.pub_date
                       }
    for image in photoalbum.images.all():
        image.vote_type = None
        if image.id in vote_dict:
            if vote_dict[image.id] == 'increase':
                image.vote_type = 'increase'
            elif vote_dict[image.id] == 'decrease':
                image.vote_type = 'decrease'
        images.append(image)
    images = sorted(images, key=lambda x: (-x.ambiguity, x.id))

    highlight_id = request.GET.get('highlight')
    if highlight_id:
        try:
            highlight_id = int(highlight_id)
            ids = [img.id for img in images]
            if highlight_id in ids:
                idx = ids.index(highlight_id)
                target_page = max(1, math.ceil((idx + 1) / ALBUM_PAGE_SIZE))
                if int(album_page) != target_page:
                    url = reverse('photoalbums:photoalbum', args=[title, target_page])
                    return HttpResponseRedirect(f"{url}?highlight={highlight_id}#thumb-{highlight_id}")
        except (TypeError, ValueError):
            highlight_id = None

    paginated_images = Paginator(images, ALBUM_PAGE_SIZE)
    paginated_images = paginated_images.page(album_page)

    lightbox_images = []
    for img in paginated_images.object_list:
        thumb_url = img.thumbnail.url if img.thumbnail else (img.image.url if img.image else '')
        full_url = img.image.url if img.image else ''
        lightbox_images.append({
            'id': img.id,
            'thumb': thumb_url,
            'full': full_url,
            'description': img.description or '',
            'detailUrl': reverse('photoalbums:image', args=[img.id]),
        })

    comment_votes = PhotoAlbumCommentAmbiguityVote.objects.filter(ip_address=ip_address, photoalbum_comment__in=photoalbum.comments.all())
    vote_dict = {vote.photoalbum_comment_id: vote.vote_type for vote in comment_votes}

    comments = []
    for comment in photoalbum.comments.all():
        comment.vote_type = None
        if comment.id in vote_dict:
            if vote_dict[comment.id] == 'increase':
                comment.vote_type = 'increase'
            elif vote_dict[comment.id] == 'decrease':
                comment.vote_type = 'decrease'
        comments.append(comment)
    comments = sorted(comments, key=lambda x: x.date_entered, reverse=True)
    paginated_comments = Paginator(comments, 5)
    comment_id = request.GET.get('comment-id')
    if comment_id:
        comment_page = find_page_number_by_obj_id(paginated_comments, comment_id)
    else:
        comment_page = request.GET.get('comment-page')
    if not comment_page:
        comment_page = 1
    paginated_comments = paginated_comments.page(comment_page)
    return render(request, 'photoalbums/photoalbum.html', {
        'photoalbum_meta': photoalbum_meta,
        'images': paginated_images,
        'comments': paginated_comments,
        'background_grid_class': 'background-grid background-grid-long',
        'lightbox_images_json': json.dumps(lightbox_images),
        'highlight_id': highlight_id,
    })


def get_image_meta_info(image):
    album_url = reverse('photoalbums:photoalbum', args=[image.album.title])
    image_meta = {'album_title': image.album.title,
                  'album_url': album_url,
                  'album_author': image.album.author,
                  'date_uploaded': image.date_uploaded
                  }
    return image_meta


def image(request, image_id):
    image = get_object_or_404(PhotoAlbumImage, id=image_id)
    image_meta = get_image_meta_info(image)
    ip_address = request.META.get('REMOTE_ADDR')
    try:
        vote = ImageAmbiguityVote.objects.get(ip_address=ip_address, image_id=image_id)
    except ObjectDoesNotExist:
        vote = None
    if vote:
        vote_type = vote.vote_type
    else:
        vote_type = None

    # Same order as the album grid (ambiguity desc) so next/prev match browsing.
    album_images = list(
        PhotoAlbumImage.objects.filter(album=image.album).order_by('-ambiguity', 'id')
    )
    prev_image = next_image = None
    if len(album_images) > 1:
        ids = [img.id for img in album_images]
        idx = ids.index(image.id)
        prev_image = album_images[(idx - 1) % len(album_images)]
        next_image = album_images[(idx + 1) % len(album_images)]
        image_meta['position'] = idx + 1
        image_meta['album_count'] = len(album_images)

    _comments = ImageComment.objects.filter(image=image)
    comment_votes = ImageCommentAmbiguityVote.objects.filter(ip_address=ip_address, image_comment__in=image.comments.all())
    vote_dict = {vote.image_comment_id: vote.vote_type for vote in comment_votes}

    comments = []
    for comment in _comments:
        comment.vote_type = None
        if comment.id in vote_dict:
            if vote_dict[comment.id] == 'increase':
                comment.vote_type = 'increase'
            elif vote_dict[comment.id] == 'decrease':
                comment.vote_type = 'decrease'
        comments.append(comment)
    comments = sorted(comments, key=lambda x: x.date_entered, reverse=True)
    paginated_comments = Paginator(comments, 5)
    comment_id = request.GET.get('comment-id')
    if comment_id:
        comment_page = find_page_number_by_obj_id(paginated_comments, comment_id)
    else:
        comment_page = request.GET.get('comment-page')
    if not comment_page:
        comment_page = 1
    paginated_comments = paginated_comments.page(comment_page)
    return render(request, 'photoalbums/image.html', {
        'image_meta': image_meta,
        'image': image,
        'image_vote_type': vote_type,
        'comments': paginated_comments,
        'prev_image': prev_image,
        'next_image': next_image,
    })

@admin_required
def create_photoalbum(request):
    photoalbum = PhotoAlbum.create_placeholder()
    return HttpResponseRedirect(reverse('photoalbums:edit_photoalbum', args=(photoalbum.id,)))

@admin_required
def edit_photoalbum(request, photoalbum_id):
    photoalbum = get_object_or_404(PhotoAlbum, pk=photoalbum_id)
    error_message = None
    if request.method == 'POST':
        try:
            title = request.POST['title']
            author = request.POST['author']
            description = request.POST['description']
        except KeyError:
            return HttpResponseRedirect(reverse('photoalbums:edit_photoalbum', args=(photoalbum.id,)))

        photoalbum.title = title
        photoalbum.author = author
        photoalbum.description = description
        try:
            photoalbum.save()
            return HttpResponseRedirect(reverse('photoalbums:photoalbum', args=(photoalbum.title,)))
        except Exception as e:
            error_message = f"the following error occurred: {e}"
    return render(request, 'photoalbums/edit_photoalbum.html', {'photoalbum': photoalbum, 'error_message': error_message})

@admin_required
def submit_images(request, photoalbum_id):
    photoalbum = get_object_or_404(PhotoAlbum, pk=photoalbum_id)
    images = request.FILES.getlist("images")
    for image in images:
        photoalbum_image = PhotoAlbumImage(album=photoalbum, image=image)
        photoalbum_image.save()
    return HttpResponseRedirect(reverse('photoalbums:edit_photoalbum', args=(photoalbum.id,)))

@admin_required
@require_POST
def delete_photoalbum(request, photoalbum_id):
    photoalbum = get_object_or_404(PhotoAlbum, pk=photoalbum_id)
    photoalbum.delete()
    return HttpResponseRedirect(reverse('photoalbums:index'))


@admin_required
@require_POST
def update_image(request, image_id):
    image = get_object_or_404(PhotoAlbumImage, pk=image_id)
    PhotoAlbumImage.objects.filter(pk=image.pk).update(
        description=request.POST.get('description', '')
    )
    return HttpResponseRedirect(reverse('photoalbums:edit_photoalbum', args=(image.album_id,)))


@admin_required
@require_POST
def delete_image(request, image_id):
    image = get_object_or_404(PhotoAlbumImage, pk=image_id)
    album_id = image.album_id
    if image.thumbnail:
        image.thumbnail.delete(save=False)
    if image.image:
        image.image.delete(save=False)
    image.delete()
    return HttpResponseRedirect(reverse('photoalbums:edit_photoalbum', args=(album_id,)))


def execute_vote_logic(ambiguity_object, vote_object_type, ip_address, vote_type):
    vote = vote_object_type.get_by_ambiguity_object(ambiguity_object=ambiguity_object)
    created = False
    if not vote:
        vote = vote_object_type.objects.create(ip_address=ip_address, ambiguity_object=ambiguity_object, vote_type='increase')
        created = True
    # vote, created = vote_object_type.objects.get_or_create(ip_address=ip_address, ambiguity_object=ambiguity_object)
    if vote_type == 'increase':
        if not created and vote.vote_type == 'decrease':
            vote.delete()
            vote_object_type.create_with_ambiguity_object(ip_address=ip_address, ambiguity_object=ambiguity_object, vote_type='increase')
            ambiguity_object.ambiguity += 2
            ambiguity_object.save()
        elif created:
            vote.vote_type = 'increase'
            vote.save()
            ambiguity_object.ambiguity += 1
            ambiguity_object.save()
    elif vote_type == 'decrease':
        if not created and vote.vote_type == 'increase':
            vote.delete()
            vote_object_type.create_with_ambiguity_object(ip_address=ip_address, ambiguity_object=ambiguity_object, vote_type='decrease')
            ambiguity_object.ambiguity -= 2
            ambiguity_object.save()
        elif created:
            vote.vote_type = 'decrease'
            vote.save()
            ambiguity_object.ambiguity -= 1
            ambiguity_object.save()
    elif vote_type == 'remove_decrease':
        if not created and vote.vote_type == 'decrease':
            vote.delete()
            ambiguity_object.ambiguity += 1
            ambiguity_object.save()
    elif vote_type == 'remove_increase':
        if not created and vote.vote_type == 'increase':
            vote.delete()
            ambiguity_object.ambiguity -= 1
            ambiguity_object.save()


def ambiguity_vote(request):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR')
        if is_ip_banned(ip_address):
            return None
        vote_type = request.POST.get('vote_type')
        image_id = request.POST.get('ambiguity_object_id')
        image = PhotoAlbumImage.objects.get(id=image_id)  # TODO: what if not found
        execute_vote_logic(ambiguity_object=image, vote_object_type=ImageAmbiguityVote, ip_address=ip_address,
                           vote_type=vote_type)
        return JsonResponse({'status': 'success'})


def image_comment_ambiguity_vote(request):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR')
        if is_ip_banned(ip_address):
            return None
        vote_type = request.POST.get('vote_type')
        image_comment_id = request.POST.get('ambiguity_object_id')
        image_comment = ImageComment.objects.get(id=image_comment_id)  # TODO: what if not found
        execute_vote_logic(ambiguity_object=image_comment, vote_object_type=ImageCommentAmbiguityVote, ip_address=ip_address,
                           vote_type=vote_type)
        return JsonResponse({'status': 'success'})


def photoalbum_comment_ambiguity_vote(request):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR')
        if is_ip_banned(ip_address):
            return None
        vote_type = request.POST.get('vote_type')
        photoalbum_comment_id = request.POST.get('ambiguity_object_id')
        photoalbum_comment = PhotoAlbumComment.objects.get(id=photoalbum_comment_id)  # TODO: what if not found
        execute_vote_logic(ambiguity_object=photoalbum_comment, vote_object_type=PhotoAlbumCommentAmbiguityVote, ip_address=ip_address,
                           vote_type=vote_type)
        return JsonResponse({'status': 'success'})


def submit_image_comment(request, image_id):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR')
        comment_text = request.POST.get('image_comment_text')
        image = PhotoAlbumImage.objects.get(id=image_id)
        if is_ip_banned(ip_address):
            if is_ip_banned(ip_address):
                return HttpResponseRedirect(reverse('photoalbums:image', args=(image.id,)))
        try:
            comment = ImageComment.objects.create(image=image, comment_text=comment_text, ip_address=ip_address)
            return HttpResponseRedirect(reverse('photoalbums:image', args=(image.id,)) + f"#comment-{comment.id}")
        except:
            return HttpResponseRedirect(reverse('photoalbums:image', args=(image.id,)))

        # return redirect('photoalbums:image', image_id=image.id, fragment=f'comment-{comment.id}')


def submit_photoalbum_comment(request, photoalbum_id):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR')
        comment_text = request.POST.get('photoalbum_comment_text')
        photoalbum = PhotoAlbum.objects.get(id=photoalbum_id)
        if is_ip_banned(ip_address):
            return HttpResponseRedirect(reverse('photoalbums:photoalbum', args=(photoalbum.title,)))
        try:
            comment = PhotoAlbumComment.objects.create(photoalbum=photoalbum, comment_text=comment_text, ip_address=ip_address)
            return HttpResponseRedirect(reverse('photoalbums:photoalbum', args=(photoalbum.title,)) + f"#comment-{comment.id}")
        except:
            return HttpResponseRedirect(reverse('photoalbums:photoalbum', args=(photoalbum.title,)))


def find_page_number_by_obj_id(paginator, obj_id):
    obj_id = int(obj_id)
    for page_number in paginator.page_range:
        page = paginator.page(page_number)
        if any(obj.id == obj_id for obj in page.object_list):
            return page_number
    return None
