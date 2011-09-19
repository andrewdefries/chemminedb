#  Based on: http://www.djangosnippets.org/snippets/73/
#
#  Modified by Sean Reifschneider to be smarter about surrounding page
#  link context.  For usage documentation see:
#
#     http://www.tummy.com/Community/Articles/django-pagination/
#
#  Further simplified by Eddie C.

from django import template

register = template.Library()

def paginator(context, adjacent_pages=2):
    """
    Adds pagination context variables for use in displaying first, adjacent and
    last page links.
    """
    # build the base query string
    p = context['request'].GET.copy()
    p.pop('page', '')
    qstring = p.urlencode()
    paginator = context['page_obj'].paginator
    page = context['page_obj']
    pages = paginator.num_pages
    startPage = max(page.number - adjacent_pages, 1)
    if startPage <= 3: startPage = 1
    endPage = page.number + adjacent_pages + 1
    if endPage >= pages - 1: endPage = pages + 1
    page_numbers = [n for n in range(startPage, endPage) \
            if n > 0 and n <= pages]

    return {
        'page_numbers': page_numbers,
        'page': page.number,
        'pages': paginator.num_pages,
        'next': page.next_page_number(),
        'previous': page.previous_page_number(),
        'has_next': page.has_next(),
        'has_previous': page.has_previous(),
        'show_first' : 1 not in page_numbers,
        'show_last' : paginator.num_pages not in page_numbers,
        'qstring' : qstring,
    }

register.inclusion_tag('paginator.html', takes_context=True)(paginator)
