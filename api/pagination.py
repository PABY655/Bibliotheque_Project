from rest_framework.pagination import (
    PageNumberPagination,
    CursorPagination,
)
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size             = 10
    page_size_query_param = 'size'
    max_page_size         = 100
    page_query_param      = 'page'

    def get_paginated_response(self, data):
        return Response({
            'pagination': {
                'total':         self.page.paginator.count,
                'pages':         self.page.paginator.num_pages,
                'page_courante': self.page.number,
                'par_page':      self.get_page_size(self.request),
                'suivante':      self.get_next_link(),
                'precedente':    self.get_previous_link(),
            },
            'resultats': data,
        })


class PerformantePagination(CursorPagination):
    page_size          = 10
    ordering           = '-date_creation'
    cursor_query_param = 'cursor'