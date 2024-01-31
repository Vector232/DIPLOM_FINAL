from django.shortcuts import render
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from requests import get
from yaml import load as load_yaml, Loader

from backend.models import User, Contact, Shop, Category, Product, ProductParameter, OrderItem, Order


class PartnerUpdate(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'change_price'

    def post(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return Response({'status': False, 'ERROR': 'Только для магазинов'}, status=status.HTTP_403_FORBIDDEN)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return Response({'status': False, 'ERROR': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                stream = get(url).content
                data = load_yaml(stream, Loader=Loader)
                shop, _ = Shop.objects.get_or_create(user_id=request.user.id, defaults={'name': data['shop'], 'url': url})
                if shop.name != data['shop']:
                    return Response({'status': False, 'ERROR': 'Некорректное навание магазина в передаваемом файле!'}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'status': True})
            
        return Response({'status': False, 'ERROR': 'Не все необходимые поля указаны'}, status=status.HTTP_400_BAD_REQUEST)
