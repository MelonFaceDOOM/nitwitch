from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import BannedIP
from .permissions import admin_required
from photoalbums.models import ImageComment, PhotoAlbumComment, ImageAmbiguityVote, ImageCommentAmbiguityVote, PhotoAlbumCommentAmbiguityVote
from articles.models import ArticleComment, ArticleCommentAmbiguityVote
from django.views.decorators.csrf import csrf_exempt
import json

User = get_user_model()


@admin_required
def manage(request):
    comments = list(ImageComment.objects.all()) + \
               list(PhotoAlbumComment.objects.all()) + \
               list(ArticleComment.objects.all())

    votes = list(ImageAmbiguityVote.objects.all()) + \
            list(ImageCommentAmbiguityVote.objects.all()) + \
            list(PhotoAlbumCommentAmbiguityVote.objects.all()) + \
            list(ArticleCommentAmbiguityVote.objects.all())

    banned_ips = list(BannedIP.objects.all())

    comments_sorted = sorted(comments, key=lambda x: x.date_entered, reverse=True)
    votes_sorted = sorted(votes, key=lambda x: x.date_entered, reverse=True)
    banned_ips_sorted = sorted(banned_ips, key=lambda x: x.date_entered, reverse=True)

    users = User.objects.order_by('-is_staff', 'email')

    context = {
        'comments': comments_sorted,
        'votes': votes_sorted,
        'banned_ips': banned_ips_sorted,
        'users': users,
    }
    return render(request, 'accounts/manage.html', context)


def _set_admin(request, make_admin: bool):
    """Shared body for promote/demote. Toggles is_staff on the target user.

    Superusers are never demoted through this UI, and an admin can't demote
    themselves (avoids locking yourself out mid-session)."""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        target = User.objects.get(id=user_id)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)

    if not make_admin:
        if target.is_superuser:
            return JsonResponse({'status': 'error', 'message': 'Cannot demote a superuser'}, status=400)
        if target.pk == request.user.pk:
            return JsonResponse({'status': 'error', 'message': 'You cannot demote yourself'}, status=400)

    target.is_staff = make_admin
    target.save(update_fields=['is_staff'])
    return JsonResponse({'status': 'success'})


@admin_required
@require_POST
def promote_user(request):
    return _set_admin(request, make_admin=True)


@admin_required
@require_POST
def demote_user(request):
    return _set_admin(request, make_admin=False)



@csrf_exempt
@admin_required
@require_POST
def delete_object(request):
    try:
        data = json.loads(request.body)
        object_type = data.get('object_type')
        object_id = data.get('object_id')

        model_mapping = {
            'ImageAmbiguityVote': ImageAmbiguityVote,
            'ImageCommentAmbiguityVote': ImageCommentAmbiguityVote,
            'PhotoAlbumCommentAmbiguityVote': PhotoAlbumCommentAmbiguityVote,
            'ArticleCommentAmbiguityVote': ArticleCommentAmbiguityVote,
            'ImageComment': ImageComment,
            'PhotoAlbumComment': PhotoAlbumComment,
            'ArticleComment': ArticleComment,
        }

        if object_type in model_mapping:
            model_class = model_mapping[object_type]
            try:
                obj = model_class.objects.get(id=object_id)
                if "vote" in object_type.lower():
                    ambiguity_object = obj.ambiguity_object
                    if obj.vote_type == "increase":
                        ambiguity_object.ambiguity -= 1
                    elif obj.vote_type == "decrease":
                        ambiguity_object.ambiguity += 1
                    ambiguity_object.save()
                obj.delete()
                return JsonResponse({'status': 'success'})
            except model_class.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Object not found'}, status=404)
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid object type'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)


@admin_required
@require_POST
def ban_ip(request):
    try:
        data = json.loads(request.body)
        ip_address = data.get('ip_address')
        if ip_address:
            BannedIP.objects.create(ip_address=ip_address)
            submission_object_types = [ImageComment, PhotoAlbumComment, ArticleComment, ImageAmbiguityVote,
                                 ImageCommentAmbiguityVote, PhotoAlbumCommentAmbiguityVote, ArticleCommentAmbiguityVote]
            for object_type in submission_object_types:
                objects_to_delete = object_type.objects.filter(ip_address=ip_address)
                for obj in objects_to_delete:
                    obj.delete()
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid IP address'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@admin_required
@require_POST
def unban_ip(request):
    try:
        data = json.loads(request.body)
        ip_address = data.get('ip_address')
        obj = BannedIP.objects.get(ip_address=ip_address)
        if obj:
            obj.delete()
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid IP address'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)