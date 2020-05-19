import json
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models import Q
from django.db.transaction import atomic
from django.http import Http404
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response

from filters_tutorial_back.common.cons import ERRORS, DATA, MESSAGE, FILTER_PREFIX, ERROR_TYPE, VALIDATION_ERROR, HTTP_404, INTEGRITY_ERROR, INVALID_DATA, OTHER
from filters_tutorial_back.common.exceptions import APIException202, InvalidData

logger = logging.getLogger(__name__)


class CustomListAPIView(ListAPIView):
    queryset = None
    serializer_class = None
    filter_serializer_class = None
    filter_map = {}
    queryset_kwargs = {}

    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    # def list(self, request, *args, **kwargs):
    #     queryset = self.filter_queryset(self.get_queryset())
    #     page = self.paginate_queryset(queryset)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         if 'sort' in self.request.query_params:
    #             sort_variable = self.request.query_params['sort']
    #             sort_direction = self.request.query_params['order']
    #             fields_list = [x.name for x in queryset.model._meta.fields]
    #             if sort_variable in fields_list:
    #                 sorted_data = self.sort_table_data(queryset)
    #                 sorted_serializer = self.get_serializer(sorted_data, many=True)
    #                 sorted_serializer_data = sorted_serializer.data
    #             else:
    #                 sorted_serializer_data = sorted(self.get_serializer(queryset, many=True).data, key=lambda i: i[sort_variable], reverse=sort_direction == 'desc')
    #             return self.get_paginated_response(sorted_serializer_data)
    #         else:
    #             return self.get_paginated_response(serializer.data)
    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response({DATA: serializer.data})

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None or len(self.request.GET.keys()) == 0 or self.request.GET.get('page') == 'null':
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    # def filter_queryset(self, queryset):
    #     query_dict_items = dict(self.request.GET.items())
    #     if query_dict_items:
    #         filter_params = self.get_filter_params(query_dict_items, False)
    #         if filter_params:
    #             return queryset.filter(filter_params)
    #     return queryset

    def get_filter_serializer(self, filter_data):
        filter_serializer = self.filter_serializer_class(data=filter_data)
        try:
            filter_serializer.is_valid(raise_exception=True)
        except ValidationError as ve:
            logger.error('Filter Error: {}'.format(ve))
            filter_serializer = None
        finally:
            return filter_serializer

    def get_filter_params(self, query_dict_items, exact):
        filter_data = {k[len(FILTER_PREFIX):]: v for k, v in query_dict_items.items() if k.startswith(FILTER_PREFIX) and not v == ''}
        filter_serializer = self.get_filter_serializer(filter_data)
        filter_params = None

        if filter_serializer:
            filter_query = {self.get_filter_key(filter_serializer, k, exact): v for k, v in filter_serializer.validated_data.items() if v or v is False}
            if filter_query:
                filter_params = Q(**filter_query)
        return filter_params

    def get_data_params(self, query_dict_items, exact):
        filter_data = {k: v for k, v in query_dict_items if not k.startswith(FILTER_PREFIX)}
        return filter_data

    def get_filter_key(self, filter_serializer, key, exact):
        if not exact and isinstance(filter_serializer.fields[key], serializers.CharField):
            key = self.filter_map.get(key, key)
            return '{}__icontains'.format(key)

        if not exact and isinstance(filter_serializer.fields[key], serializers.DateField):
            key = self.filter_map.get(key, key)
            if key[-4:] == '_min':
                return '{}__gte'.format(key[:-4])
            elif key[-4:] == '_max':
                return '{}__lte'.format(key[:-4])
            return '{}'.format(key)
        return self.filter_map.get(key, key)

    def get_queryset(self):
        """
        :param self: Model instance.
        :return: A filtered queryset.
        """
        formatted_query_params = {}
        for key, value in self.queryset_kwargs.items():
            item_value = int(self.kwargs[key])
            formatted_query_params[value] = item_value
        try:
            self.queryset = self.queryset.filter(**formatted_query_params)
        except Http404:
            self.queryset = None
        finally:
            return self.queryset

    def sort_table_data(self, queryset):
        sort_variable = self.request.query_params['sort']
        order_variable = self.request.query_params['order']
        if sort_variable == 'plan_number':
            if order_variable == 'desc':
                order = queryset.order_by('-plan_number_year', '-plan_number')
            else:
                order = queryset.order_by('plan_number_year', 'plan_number')
        else:
            order = queryset.order_by(self.request.query_params['sort'])
            if self.request.query_params['order'] == 'desc':
                order = queryset.order_by(self.request.query_params['sort']).reverse()
        return self.paginate_queryset(order)


class HRMCreateAPIView(CreateAPIView):

    @atomic
    def create(self, request, *args, **kwargs):
        data = {}
        if 'data' in request.data:  # POST request with FILES
            for key in request.FILES.keys():
                data[key] = request.FILES[key]
            post_data = json.loads(request.data['data'])
            data.update(post_data)
        else:  # SIMPLE POST request
            data = request.data
        serializer = self.get_serializer(data=data)

        response_data = {}
        response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        response_headers = None
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            response_data = {DATA: serializer.data}
            response_status = status.HTTP_201_CREATED
            response_headers = headers
        except ValidationError as ve:
            logger.error('Create Error: {}'.format(ve))
            error_dict = ve.get_full_details()
            response_data = {
                ERROR_TYPE: VALIDATION_ERROR,
                ERRORS: error_dict,
                MESSAGE: get_validation_error_message(error_dict)
            }
            response_status = status.HTTP_400_BAD_REQUEST
        except ObjectDoesNotExist as dne:
            logger.error('Object does not exist Error: {}'.format(dne))
            response_data = {
                ERROR_TYPE: HTTP_404,
                ERRORS: '{}'.format(dne),
                MESSAGE: 'Nuk ekziston',
            }
            response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        except IntegrityError as ie:
            logger.error('{}'.format(ie))
            response_data = {
                ERROR_TYPE: INTEGRITY_ERROR,
                ERRORS: '{}'.format(ie),
                MESSAGE: 'Gabim në databazë',
            }
            response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        except InvalidData as ex:
            response_data = {
                ERROR_TYPE: INVALID_DATA,
                ERRORS: ex.get_message(),
                MESSAGE: ex.get_message(),
            }
            response_status = status.HTTP_400_BAD_REQUEST
        except APIException202 as ae:
            headers = self.get_success_headers(serializer.data)
            response_data = {DATA: ae.obj, MESSAGE: ae.message}
            response_status = status.HTTP_202_ACCEPTED
            response_headers = headers
        except Exception as e:
            response_data = {
                ERROR_TYPE: OTHER,
                ERRORS: '{}'.format(e),
                MESSAGE: 'Problem në server'
            }
        finally:
            return Response(response_data, status=response_status, headers=response_headers)


class CustomListCreateAPIView(HRMCreateAPIView, CustomListAPIView):
    list_read_serializer_class = None
    read_serializer_class = None
    write_serializer_class = None
    filter_serializer_class = None
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    serializer_error_msg = "'%s' should either include a `serializer_class` attribute, or override the `get_serializer_class()` method."
    queryset = None
    filter_map = {}

    def get_serializer_class(self):
        if self.request.method == 'GET':
            if self.list_read_serializer_class is not None:
                return self.list_read_serializer_class
            assert self.read_serializer_class is not None or self.serializer_class is not None, (self.serializer_error_msg % self.__class__.__name__)
            return self.read_serializer_class
        if self.request.method == 'POST':
            assert self.write_serializer_class is not None or self.serializer_class is not None, (self.serializer_error_msg % self.__class__.__name__)
            return self.write_serializer_class
        assert self.serializer_class is not None, (self.serializer_error_msg % self.__class__.__name__)
        return self.serializer_class


class HRMRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete an object instance.
    """
    queryset = None
    serializer_class = None
    read_serializer_class = None
    write_serializer_class = None
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    serializer_error_msg = "'%s' should either include a `serializer_class` attribute, or override the `get_serializer_class()` method."
    delete_obj_id_physical = None

    def get_serializer_class(self):
        if self.request.method == 'GET':
            assert self.read_serializer_class is not None or self.serializer_class is not None, (self.serializer_error_msg % self.__class__.__name__)
            return self.read_serializer_class
        if self.request.method == 'POST' or self.request.method == 'PUT' or self.request.method == 'PATCH':
            assert self.write_serializer_class is not None or self.serializer_class is not None, (self.serializer_error_msg % self.__class__.__name__)
            return self.write_serializer_class
        assert self.serializer_class is not None, (self.serializer_error_msg % self.__class__.__name__)
        return self.serializer_class

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({DATA: serializer.data})
        except Http404 as e:
            response_data = {
                ERROR_TYPE: HTTP_404,
                ERRORS: '{}'.format(e),
                MESSAGE: 'Nuk u gjet'
            }
            response_status = status.HTTP_404_NOT_FOUND
            return Response(response_data, status=response_status)

    @atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = {}
        if 'data' in request.data:  # POST request with FILES
            for key in request.FILES.keys():
                data[key] = request.FILES[key]
            post_data = json.loads(request.data['data'])
            data.update(post_data)
        else:  # SIMPLE POST request
            data = request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)

        response_data = {}
        response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset, we need to
                # forcibly invalidate the prefetch cache on the instance.
                instance._prefetched_objects_cache = {}
            response_data = {DATA: serializer.data}
            response_status = status.HTTP_200_OK
        except ValidationError as ve:
            logger.error('Create Error: {}'.format(ve))
            error_dict = ve.get_full_details()
            response_data = {
                ERROR_TYPE: VALIDATION_ERROR,
                ERRORS: error_dict,
                MESSAGE: get_validation_error_message(error_dict)
            }
            response_status = status.HTTP_400_BAD_REQUEST
        except ObjectDoesNotExist as dne:
            logger.error('Object does not exist Error: {}'.format(dne))
            response_data = {
                ERROR_TYPE: HTTP_404,
                ERRORS: '{}'.format(dne),
                MESSAGE: 'Nuk ekziston',
            }
            response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        except IntegrityError as ie:
            logger.error('{}'.format(ie))
            response_data = {
                ERROR_TYPE: INTEGRITY_ERROR,
                ERRORS: '{}'.format(ie),
                MESSAGE: 'Gabim në databazë',
            }
            response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        except InvalidData as ex:
            response_data = {
                ERROR_TYPE: INVALID_DATA,
                ERRORS: ex.get_message(),
                MESSAGE: ex.get_message(),
            }
            response_status = status.HTTP_400_BAD_REQUEST
        except APIException202 as ae:
            response_data = {DATA: ae.obj, MESSAGE: ae.message}
            response_status = status.HTTP_202_ACCEPTED
        except Exception as e:
            response_data = {
                ERROR_TYPE: OTHER,
                ERRORS: '{}'.format(e),
                MESSAGE: 'Problem në server'
            }
        finally:
            return Response(response_data, status=response_status)

    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            # if hasattr(instance, 'deleted'):
            #     instance.deleted = True
            #     instance.save()
            # else:
            #     self.perform_destroy(instance)
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Http404 as e:
            response_data = {
                ERROR_TYPE: HTTP_404,
                ERRORS: '{}'.format(e),
                MESSAGE: 'Nuk u gjet'
            }
            response_status = status.HTTP_404_NOT_FOUND
            return Response(response_data, status=response_status)


def get_validation_error_message(error_data):
    try:
        response_message = ''
        if isinstance(error_data, dict):
            for key, value in error_data.items():
                for item in value:
                    if 'message' in item:
                        response_message += '{}: {} '.format(key, item['message'])
                    else:
                        if isinstance(item, dict):
                            for unit_key, unit_value in item.items():
                                for arr_item in unit_value:
                                    response_message += '{}: {} '.format(unit_key, arr_item['message'])
                        elif isinstance(item, str):
                            for item_key, item_val in value.items():
                                for arr_item in item_val:
                                    response_message += '{}: {} '.format(item_key, arr_item['message'])
        elif isinstance(error_data, list):
            for arr_item in error_data:
                response_message += '{} '.format(arr_item['message'])
    except:
        response_message = 'Error {}'.format(error_data)
    return response_message
