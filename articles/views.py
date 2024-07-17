from .models import Article, ArticleImage, ArticleComment, ArticleCommentAmbiguityVote
from django.views import generic
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator
from accounts.models import is_ip_banned
from django.http import HttpResponseForbidden


class IndexView(generic.ListView):
    context_object_name = "latest_articles_list"
    template_name = "articles/index.html"
    paginate_by = 5

    def get_queryset(self):
        return Article.objects.order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['background_grid_class'] = 'background-grid background-grid-medium'
        return context


def article(request, title):
    article = get_object_or_404(Article, title=title)
    article.view_count += 1
    article.save()

    ip_address = request.META.get('REMOTE_ADDR')

    _comments = ArticleComment.objects.filter(article=article)
    comment_votes = ArticleCommentAmbiguityVote.objects.filter(ip_address=ip_address,
                                                             article_comment__in=article.comments.all())
    vote_dict = {vote.article_comment_id: vote.vote_type for vote in comment_votes}

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
    return render(request, 'articles/article.html', {'article': article, 'comments': paginated_comments})


@login_required
def create_article(request):
    article = Article.create_placeholder()
    return HttpResponseRedirect(reverse('articles:edit_article', args=(article.id,)))


@login_required
def edit_article(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    error_message = None
    if request.method == 'POST':
        try:
            title = request.POST['title']
            author = request.POST['author']
            description = request.POST['description']
            article_text = request.POST['article-text']
        except KeyError:
            return HttpResponseRedirect(reverse('articles:edit_article', args=(article.id,)))

        article.title = title
        article.author = author
        article.description = description
        article.article_text = article_text
        try:
            article.save()
            article.apply_markup()
            return HttpResponseRedirect(reverse('articles:article', args=(article.title,)))
        except Exception as e:
            error_message = f"the following error occurred: {e}"
    return render(request, 'articles/edit_article.html', {'article': article, 'error_message': error_message})


@login_required
def submit_images(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    images = request.FILES.getlist("images")
    for image in images:
        article_image = ArticleImage(article=article, image=image)
        article_image.save()
    return HttpResponseRedirect(reverse('articles:edit_article', args=(article.id,)))


@login_required
def delete_article(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    article.delete()
    return HttpResponseRedirect(reverse('articles:index'))


def submit_article_comment(request, article_id):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR')
        comment_text = request.POST.get('article_comment_text')
        article = get_object_or_404(Article, pk=article_id)
        if is_ip_banned(ip_address):
            return HttpResponseRedirect(reverse('articles:article', args=(article.title,)))
        try:
            comment = ArticleComment.objects.create(article=article, comment_text=comment_text, ip_address=ip_address)
            return HttpResponseRedirect(reverse('articles:article', args=(article.title,)) + f"#comment-{comment.id}")
        except:
            return HttpResponseRedirect(reverse('articles:article', args=(article.title,)))


def article_comment_ambiguity_vote(request):
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR')
        if is_ip_banned(ip_address):
            return None
        vote_type = request.POST.get('vote_type')
        article_comment_id = request.POST.get('ambiguity_object_id')
        article_comment = ArticleComment.objects.get(id=article_comment_id)  # TODO: what if not found
        execute_vote_logic(ambiguity_object=article_comment, vote_object_type=ArticleCommentAmbiguityVote,
                           ip_address=ip_address,
                           vote_type=vote_type)
        return JsonResponse({'status': 'success'})


def find_page_number_by_obj_id(paginator, obj_id):
    obj_id = int(obj_id)
    for page_number in paginator.page_range:
        page = paginator.page(page_number)
        if any(obj.id == obj_id for obj in page.object_list):
            return page_number
    return None


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
